import frappe
from frappe.tests import IntegrationTestCase

from fleet_management.site_defaults import (
	ADDRESS_PERMISSIONS,
	DATE_FORMAT,
	ensure_address_permissions,
	ensure_address_template,
	ensure_date_format,
)


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


class TestStationAddressPermissions(IntegrationTestCase):
	def test_fleet_roles_can_see_station_addresses(self):
		ensure_address_permissions()
		ensure_address_permissions()  # idempotent: no duplicate rules
		for role, rights in ADDRESS_PERMISSIONS.items():
			rules = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": "Address", "role": role, "permlevel": 0, "if_owner": 0},
				fields=["read", "write", "create"],
			)
			self.assertEqual(len(rules), 1, role)
			for right in ("read", "write", "create"):
				self.assertEqual(rules[0][right], int(right in rights), f"{role} {right}")
		# Frappe's own rules are kept alongside.
		self.assertTrue(frappe.db.exists("Custom DocPerm", {"parent": "Address", "role": "System Manager"}))

	def test_fleet_admin_reads_a_station_address_a_fleet_user_cannot_edit(self):
		ensure_address_permissions()
		suffix = frappe.generate_hash(length=8)
		location = frappe.get_doc(
			{"doctype": "Fleet Location", "location_name": f"AC13 Location {suffix}"}
		).insert(ignore_permissions=True)
		station = frappe.get_doc(
			{
				"doctype": "Fuel Station",
				"station_name": f"AC13 Station {suffix}",
				"operational_location": location.name,
			}
		).insert(ignore_permissions=True)
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"AC13 Address {suffix}",
				"address_type": "Office",
				"address_line1": "1 Salt Road",
				"city": "Nairobi",
				"links": [{"link_doctype": "Fuel Station", "link_name": station.name}],
			}
		).insert(ignore_permissions=True)

		fleet_admin = self._user("Fleet Admin", suffix)
		fleet_user = self._user("Fleet User", suffix)

		self.assertTrue(
			frappe.has_permission("Address", "read", address.name, user=fleet_admin)
		)
		self.assertTrue(frappe.has_permission("Address", "read", address.name, user=fleet_user))
		self.assertFalse(
			frappe.has_permission("Address", "write", address.name, user=fleet_user)
		)

	def _user(self, role, suffix):
		email = f"ac13-{role.lower().replace(' ', '-')}-{suffix}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AC13",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		return user.name


class TestAddressTemplate(IntegrationTestCase):
	def test_a_default_address_template_exists_for_the_site_country(self):
		ensure_address_template()
		country = frappe.db.get_single_value("System Settings", "country")
		self.assertTrue(country)
		self.assertTrue(frappe.db.exists("Address Template", {"is_default": 1}))

	def test_it_is_created_when_missing(self):
		# Frappe refuses to delete the default template through the document API.
		frappe.db.delete("Address Template")
		ensure_address_template()
		country = frappe.db.get_single_value("System Settings", "country")
		self.assertEqual(frappe.db.get_value("Address Template", {"is_default": 1}, "name"), country)
		self.assertTrue(frappe.db.get_value("Address Template", country, "template"))
