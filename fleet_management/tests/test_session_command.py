from unittest.mock import patch

import frappe
from click.testing import CliRunner
from frappe.auth import LoginManager
from frappe.tests import IntegrationTestCase

from fleet_management.commands import TEST_SITE, fleet_test_site


class TestSessionCommand(IntegrationTestCase):
	def _run(self, site, email="philip.test@example.com"):
		context = frappe._dict(sites=[site], profile=False)
		with (
			patch.object(LoginManager, "login_as") as login_as,
			patch("frappe.init"),
			patch("frappe.connect"),
			patch("frappe.destroy"),
		):
			result = CliRunner().invoke(fleet_test_site, ["session", email], obj=context)
		return result, login_as

	def test_a_site_other_than_the_test_site_is_refused(self):
		result, login_as = self._run("fleet_management.localhost")
		self.assertNotEqual(result.exit_code, 0)
		self.assertIn(TEST_SITE, result.output)
		self.assertNotIn("sid=", result.output)
		login_as.assert_not_called()

	def test_the_test_site_without_developer_mode_is_refused(self):
		with patch.object(frappe.local, "conf", frappe._dict(developer_mode=0)):
			result, login_as = self._run(TEST_SITE)
		self.assertNotEqual(result.exit_code, 0)
		self.assertIn("developer_mode", result.output)
		self.assertNotIn("sid=", result.output)
		login_as.assert_not_called()
