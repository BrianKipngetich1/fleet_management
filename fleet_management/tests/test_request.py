import orjson
from frappe.tests import UnitTestCase
from werkzeug.wrappers import Response

from fleet_management.request import strip_api_tracebacks


class FakeRequest:
	def __init__(self, path):
		self.path = path


def json_response(body):
	return Response(orjson.dumps(body), mimetype="application/json")


class TestApiTracebackStripping(UnitTestCase):
	def test_api_errors_lose_traceback_fields_only(self):
		response = json_response(
			{
				"exc_type": "PermissionError",
				"exc": '["Traceback (most recent call last): ..."]',
				"_exc_source": "fleet_management (app)",
				"exception": "frappe.exceptions.PermissionError: Not permitted",
				"_debug_messages": "[]",
				"_server_messages": '["Not permitted"]',
				"errors": [{"type": "PermissionError", "exception": "Traceback ..."}],
			}
		)

		strip_api_tracebacks(response, FakeRequest("/api/method/missing.method"))

		self.assertEqual(
			orjson.loads(response.get_data()),
			{
				"exc_type": "PermissionError",
				"_server_messages": '["Not permitted"]',
				"errors": [{"type": "PermissionError"}],
			},
		)

	def test_desk_pages_are_untouched(self):
		body = {"exc": "Traceback ..."}
		response = json_response(body)

		strip_api_tracebacks(response, FakeRequest("/app/fuel-order"))

		self.assertEqual(orjson.loads(response.get_data()), body)
