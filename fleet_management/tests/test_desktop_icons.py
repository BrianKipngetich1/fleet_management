import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache
from frappe.tests import IntegrationTestCase


class TestDesktopIcons(IntegrationTestCase):
	"""Spec 005 property 1: which home-screen icons each Fleet role sees."""

	def _user(self, role):
		email = f"icons-{frappe.generate_hash(length=8)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Icons",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def _boot(self, user):
		clear_desktop_icons_cache(user)
		with self.set_user(user):
			boot = get_bootinfo()
		clear_desktop_icons_cache(user)
		return boot

	def _icons(self, user):
		"""The icon labels /desk lists for the user: the boot payload's desktop icons."""
		return {icon.label for icon in self._boot(user).desktop_icons}

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_both_icons_are_standard_records_of_this_app(self):
		for label in ("Fleet", "Fleet Setup"):
			self.assertEqual(frappe.db.get_value("Desktop Icon", label, "app"), "fleet_management", label)

	def test_every_fleet_role_sees_the_fleet_icon(self):
		for role in ("Fleet User", "Fleet Approver", "Fleet Admin"):
			self.assertIn("Fleet", self._icons(self._user(role)), role)

	def test_only_fleet_admin_sees_fleet_setup(self):
		self.assertIn("Fleet Setup", self._icons(self._user("Fleet Admin")))
		for role in ("Fleet User", "Fleet Approver"):
			self.assertNotIn("Fleet Setup", self._icons(self._user(role)), role)

	def test_fleet_setup_sidebar_is_empty_for_non_admins(self):
		for role in ("Fleet User", "Fleet Approver"):
			sidebars = self._boot(self._user(role)).workspace_sidebar_item
			self.assertNotIn("fleet setup", sidebars, role)
			self.assertIn("fleet", sidebars, role)
		sidebars = self._boot(self._user("Fleet Admin")).workspace_sidebar_item
		self.assertIn("fleet setup", sidebars)

	def test_system_manager_still_sees_the_standard_icons(self):
		self.assertIn("Users", self._icons(self._user("System Manager")))
