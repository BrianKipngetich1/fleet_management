import frappe
from frappe.boot import get_bootinfo
from frappe.desk.desktop import get_workspaces
from frappe.tests import IntegrationTestCase


class TestFleetOversightWorkspace(IntegrationTestCase):
	"""Integration checks for spec 008-overseer-reports Requirements 1.6, 4.1, and 4.3."""

	def setUp(self):
		super().setUp()
		self.users = {role: self._user(role) for role in ("Fleet Approver", "Fleet Admin", "Fleet User")}

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

	def test_fleet_sidebar_lists_reports_only_for_users_with_report_access(self):
		sidebar = frappe.get_doc("Workspace Sidebar", "Fleet")
		reports_section = next(item for item in sidebar.items if item.label == "Reports")
		self.assertEqual(reports_section.type, "Section Break")
		self.assertEqual(reports_section.collapsible, 1)
		self.assertEqual(reports_section.show_arrow, 0)
		expected_reports = {"Fueling Summary", "Asset Performance", "Requests & Audit"}
		configured_reports = {
			item.link_to for item in sidebar.items if item.child and item.link_type == "Report"
		}
		self.assertEqual(configured_reports, expected_reports)

		for role in ("Fleet Approver", "Fleet Admin"):
			with self.subTest(role=role), self.set_user(self.users[role]):
				visible = get_bootinfo().workspace_sidebar_item["fleet"]["items"]
				reports = {
					item["link_to"]
					for item in visible
					if item["type"] == "Link" and item["link_type"] == "Report"
				}
				self.assertEqual(reports, expected_reports)

		with self.set_user(self.users["Fleet User"]):
			visible = get_bootinfo().workspace_sidebar_item["fleet"]["items"]
			reports = {
				item["link_to"]
				for item in visible
				if item["type"] == "Link" and item["link_type"] == "Report"
			}
			self.assertEqual(reports, set())
