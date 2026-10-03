import frappe
from frappe.desk.desktop import get_workspaces
from frappe.tests import IntegrationTestCase


class TestFleetOversightWorkspace(IntegrationTestCase):
	"""Integration checks for spec 008-overseer-reports Requirements 1.6 and 4.1."""

	def setUp(self):
		super().setUp()
		self.users = {
			role: self._user(role)
			for role in ("Fleet Approver", "Fleet Admin", "Fleet User")
		}

	def _user(self, role):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"fleet-oversight-test-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Fleet Oversight Test",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		return user.name

	def test_workspace_links_exactly_three_reports_and_is_limited_to_existing_roles(self):
		workspace = frappe.get_doc("Workspace", "Fleet Oversight")
		self.assertEqual({row.role for row in workspace.roles}, {"Fleet Approver", "Fleet Admin"})
		self.assertEqual(len(workspace.links), 3)
		self.assertEqual(
			{row.link_to for row in workspace.links},
			{"Fueling Summary", "Asset Performance", "Requests & Audit"},
		)
		self.assertTrue(all(row.link_type == "Report" for row in workspace.links))

		for report_name in ("Fueling Summary", "Asset Performance", "Requests & Audit"):
			report = frappe.get_doc("Report", report_name)
			self.assertEqual({row.role for row in report.roles}, {"Fleet Approver", "Fleet Admin"})

		for role in ("Fleet Approver", "Fleet Admin"):
			with self.subTest(role=role), self.set_user(self.users[role]):
				visible = {page.name for page in get_workspaces()["pages"]}
				self.assertIn("Fleet Oversight", visible)

		with self.set_user(self.users["Fleet User"]):
			visible = {page.name for page in get_workspaces()["pages"]}
			self.assertNotIn("Fleet Oversight", visible)
