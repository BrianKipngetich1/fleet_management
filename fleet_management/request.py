from urllib.parse import unquote

import frappe
import orjson

TRACEBACK_KEYS = ("exc", "_exc_source", "_debug_messages", "exception")


def guard_invalid_api_method():
	"""Turn missing or non-whitelisted RPC methods into a controlled 403."""
	request = getattr(frappe.local, "request", None)
	if not request or not any(
		request.path.startswith(prefix)
		for prefix in ("/api/method/", "/api/v1/method/", "/api/v2/method/")
	):
		return

	# API callers receive only the controlled error payload. This flag covers a production
	# server; strip_api_tracebacks covers the development server, which ignores it.
	frappe.local.flags.disable_traceback = True

	cmd = frappe.form_dict.get("cmd")
	if not cmd:
		path = request.path
		for prefix in ("/api/method/", "/api/v1/method/", "/api/v2/method/"):
			if path.startswith(prefix):
				cmd = unquote(path.removeprefix(prefix).split("/", 1)[0])
				break
	if not cmd:
		return

	try:
		# Use Frappe's dispatcher lookup so shorthand RPCs such as
		# ``run_doc_method`` are handled the same way as normal requests.
		from frappe.handler import get_attr

		method = get_attr(frappe.override_whitelisted_method(cmd))
	except Exception:
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	# Frappe's dispatcher deliberately skips this check for run_doc_method;
	# that endpoint checks the bound controller method itself.
	if cmd != "run_doc_method":
		frappe.is_whitelisted(method)


def strip_api_tracebacks(response=None, request=None):
	"""Remove traceback fields from an API response, one response at a time.

	With DEV_SERVER set, Frappe adds tracebacks to every API error. Turning the process-wide
	dev-server flag off instead would also turn it off for every later Desk page, which then
	looks for Socket.IO on the web port and never connects.
	"""
	if not response or not request or not request.path.startswith("/api/"):
		return
	if response.mimetype != "application/json":
		return
	try:
		body = orjson.loads(response.get_data())
	except orjson.JSONDecodeError:
		return
	if not isinstance(body, dict):
		return

	changed = False
	for key in TRACEBACK_KEYS:
		changed |= body.pop(key, None) is not None
	for error in body.get("errors") or []:
		if isinstance(error, dict):
			changed |= error.pop("exception", None) is not None
	if changed:
		response.set_data(orjson.dumps(body))
