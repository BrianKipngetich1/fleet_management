import frappe
from frappe.tests import IntegrationTestCase

from fleet_management.site_defaults import DATE_FORMAT, ensure_date_format


class TestSiteDateFormat(IntegrationTestCase):
	def test_site_uses_day_month_year(self):
		self.assertEqual(DATE_FORMAT, "dd/mm/yyyy")
		self.assertEqual(frappe.db.get_single_value("System Settings", "date_format"), DATE_FORMAT)
		self.assertEqual(frappe.db.get_default("date_format"), DATE_FORMAT)

	def test_a_changed_format_is_restored(self):
		self.addCleanup(ensure_date_format)
		settings = frappe.get_single("System Settings")
		settings.date_format = "mm-dd-yyyy"
		settings.save(ignore_permissions=True)

		ensure_date_format()

		self.assertEqual(frappe.db.get_single_value("System Settings", "date_format"), DATE_FORMAT)
		self.assertEqual(frappe.db.get_default("date_format"), DATE_FORMAT)
