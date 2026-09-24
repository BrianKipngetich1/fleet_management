from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from fleet_management.permissions import (
	get_permission_query_conditions,
	has_permission,
)
from fleet_management.request import guard_invalid_api_method


class TestFleetPermissions(UnitTestCase):
	user = "fleet.user@example.com"

	def user_permissions(self, *locations):
		return {
			"Fleet Location": [{"doc": location} for location in locations],
		}

	@patch("fleet_management.permissions._escaped_locations", return_value="'North'")
	@patch("fleet_management.permissions.get_user_permissions")
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet User"])
	def test_list_query_is_limited_to_permitted_location(self, roles, permissions, locations):
		permissions.return_value = self.user_permissions("North")

		condition = get_permission_query_conditions(self.user, "Fuel Station")

		self.assertIn("`tabFuel Station`.`operational_location` IN ('North')", condition)

	@patch("fleet_management.permissions.get_user_permissions", return_value={"Fleet Location": []})
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet Approver"])
	def test_list_query_denies_user_without_a_location(self, roles, permissions):
		self.assertEqual(get_permission_query_conditions(self.user, "Fleet Location"), "1=0")

	@patch("fleet_management.permissions.get_user_permissions")
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet User"])
	def test_direct_access_denies_other_location_for_all_document_actions(self, roles, permissions):
		permissions.return_value = self.user_permissions("North")
		doc = frappe._dict(
			doctype="Fuel Station",
			name="South Station",
			operational_location="South",
		)

		for ptype in ("read", "print", "report", "write", "submit", "cancel"):
			self.assertFalse(has_permission(doc, ptype=ptype, user=self.user), ptype)

	@patch("fleet_management.permissions.get_user_permissions")
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet Approver"])
	def test_direct_access_allows_permitted_asset(self, roles, permissions):
		permissions.return_value = self.user_permissions("North")
		doc = frappe._dict(
			doctype="Fleet Asset",
			name="Vehicle-001",
			assignments=[
				frappe._dict(
					assigned_location="North",
					effective_from="2026-01-01",
					effective_until=None,
				)
			],
		)

		self.assertTrue(has_permission(doc, ptype="read", user=self.user))

	@patch("fleet_management.permissions.get_user_permissions")
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet User"])
	def test_fuel_order_uses_its_assigned_location_snapshot(self, roles, permissions):
		permissions.return_value = self.user_permissions("North")
		doc = frappe._dict(
			doctype="Fuel Order",
			name="FO-0001",
			assigned_location_snapshot="North",
			operational_location="South",
		)

		self.assertTrue(has_permission(doc, ptype="print", user=self.user))

	@patch("fleet_management.permissions.get_user_permissions", return_value={})
	@patch("fleet_management.permissions.get_roles", return_value=["Fleet Admin"])
	def test_fleet_admin_is_unrestricted(self, roles, permissions):
		doc = frappe._dict(
			doctype="Fuel Station",
			name="South Station",
			operational_location="South",
		)

		self.assertEqual(get_permission_query_conditions(self.user, "Fuel Station"), "")
		self.assertTrue(has_permission(doc, ptype="print", user=self.user))


class TestFleetPermissionIntegration(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		suffix = frappe.generate_hash(length=8)
		self.north = self._insert("Fleet Location", location_name=f"AC02 North {suffix}")
		self.south = self._insert("Fleet Location", location_name=f"AC02 South {suffix}")
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC02 Diesel {suffix}")
		self.person = self._insert("Fleet Person", person_name=f"AC02 Person {suffix}")
		self.north_station = self._insert(
			"Fuel Station",
			station_name=f"AC02 North Station {suffix}",
			operational_location=self.north.name,
			active=1,
			approved=1,
		)
		self.south_station = self._insert(
			"Fuel Station",
			station_name=f"AC02 South Station {suffix}",
			operational_location=self.south.name,
			active=1,
			approved=1,
		)
		self.north_asset = self._insert_asset(f"AC02 North Asset {suffix}", self.north.name)
		self.south_asset = self._insert_asset(f"AC02 South Asset {suffix}", self.south.name)
		self.north_order = self._insert_order(self.north, self.north_station, self.north_asset)
		self.south_order = self._insert_order(self.south, self.south_station, self.south_asset)
		self.mixed_order = self._insert_order(self.south, self.south_station, self.north_asset)

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _insert_asset(self, identifier, location):
		return self._insert(
			"Fleet Asset",
			asset_identifier=identifier,
			asset_type="Vehicle",
			fuel_type=self.fuel_type.name,
			tank_capacity_litres=60,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": location,
					"effective_from": "2026-01-01",
				}
			],
		)

	def _insert_order(self, location, station, asset, ignore_permissions=True):
		return frappe.get_doc(
			{
				"doctype": "Fuel Order",
				"request_datetime": "2026-01-01 10:00:00",
				"actual_requester": self.person.name,
				"driver": self.person.name,
				"custodian": self.person.name,
				"company_representative": self.person.name,
				"asset": asset.name,
				"operational_location": location.name,
				"planned_station": station.name,
				"request_meter_reading": 1000,
				"request_gauge_percent": 40,
			}
		).insert(ignore_permissions=ignore_permissions)

	def _user(self, role, location=None):
		email = f"ac02-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AC02",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
			}
		).insert(ignore_permissions=True)
		if role != "Fleet Admin":
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user.name,
					"allow": "Fleet Location",
					"for_value": location or self.north.name,
				}
			).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		return user.name

	def _dispatch_get(self, command, **params):
		from frappe.handler import execute_cmd

		request = frappe._dict(path=f"/api/method/{command}", method="GET")
		form_dict = frappe._dict(cmd=command, **params)
		with patch.object(frappe.local, "request", request, create=True):
			with patch.object(frappe.local, "form_dict", form_dict, create=True):
				guard_invalid_api_method()
				return execute_cmd(command)

	def test_list_and_direct_access_are_location_scoped(self):
		user = self._user("Fleet User")
		self.assertEqual(self.mixed_order.assigned_location_snapshot, self.north.name)
		self.assertEqual(
			frappe.db.get_value("Fuel Order", self.mixed_order.name, "assigned_location_snapshot"),
			self.north.name,
		)
		with self.set_user(user):
			station_names = {
				row.name for row in frappe.get_list("Fuel Station", fields=["name"])
			}
			self.assertIn(self.north_station.name, station_names)
			self.assertNotIn(self.south_station.name, station_names)
			order_names = {row.name for row in frappe.get_list("Fuel Order", fields=["name"])}
			self.assertIn(self.north_order.name, order_names)
			self.assertIn(self.mixed_order.name, order_names)
			self.assertNotIn(self.south_order.name, order_names)
			self.assertTrue(frappe.has_permission("Fuel Station", "read", self.north_station))
			self.assertFalse(frappe.has_permission("Fuel Station", "read", self.south_station))
			self.assertTrue(frappe.has_permission("Fuel Order", "submit", self.north_order))
			self.assertTrue(frappe.has_permission("Fuel Order", "submit", self.mixed_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "submit", self.south_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "print", self.south_order))

		south_user = self._user("Fleet User", self.south.name)
		with self.set_user(south_user):
			order_names = {row.name for row in frappe.get_list("Fuel Order", fields=["name"])}
			self.assertIn(self.south_order.name, order_names)
			self.assertNotIn(self.mixed_order.name, order_names)

	def test_approver_can_report_and_print_only_permitted_orders(self):
		user = self._user("Fleet Approver")
		with self.set_user(user):
			self.assertTrue(frappe.has_permission("Fuel Order", "print", self.north_order))
			self.assertTrue(frappe.has_permission("Fuel Order", "report", self.north_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "print", self.south_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "report", self.south_order))

		user = self._user("Fleet User")
		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Fuel Order", "report", self.north_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "print", self.north_order))

	def test_fleet_user_can_request_location_list_without_report_permission(self):
		user = self._user("Fleet User")
		self.assertTrue(frappe.has_permission("Fleet Location", "read", user=user))
		self.assertFalse(frappe.has_permission("Fleet Location", "report", user=user))

		with self.set_user(user):
			result = self._dispatch_get(
				"frappe.desk.reportview.get",
				doctype="Fleet Location",
				fields='["name"]',
			)

		names = {row[0] for row in result["values"]}
		self.assertEqual(names, {self.north.name})
		self.assertNotIn(self.south.name, names)

	def test_restricted_query_report_remains_denied(self):
		user = self._user("Fleet User")
		report = self._insert(
			"Report",
			report_name=f"AC02 Restricted Report {frappe.generate_hash(length=8)}",
			ref_doctype="Fleet Location",
			report_type="Report Builder",
			is_standard="No",
			roles=[{"role": "Fleet Approver"}],
		)

		with self.set_user(user):
			with self.assertRaises(frappe.PermissionError):
				self._dispatch_get(
					"frappe.desk.query_report.run",
					report_name=report.name,
					filters="{}",
				)

	def test_fleet_user_can_create_orders_only_for_permitted_assets(self):
		user = self._user("Fleet User")

		with self.set_user(user):
			north_order = self._insert_order(
				self.north, self.north_station, self.north_asset, ignore_permissions=False
			)
			self.assertEqual(north_order.assigned_location_snapshot, self.north.name)
			with self.assertRaises(frappe.PermissionError):
				self._insert_order(
					self.south, self.south_station, self.south_asset, ignore_permissions=False
				)

	def test_planned_station_must_match_operational_location(self):
		with self.assertRaisesRegex(
			frappe.ValidationError,
			r"Planned station must belong to the operational location\.",
		):
			self._insert_order(self.north, self.south_station, self.north_asset)

	def test_fleet_admin_can_create_orders_for_any_location(self):
		admin = self._user("Fleet Admin")

		with self.set_user(admin):
			north_order = self._insert_order(
				self.north, self.north_station, self.north_asset, ignore_permissions=False
			)
			south_order = self._insert_order(
				self.south, self.south_station, self.south_asset, ignore_permissions=False
			)

		self.assertEqual(north_order.assigned_location_snapshot, self.north.name)
		self.assertEqual(south_order.assigned_location_snapshot, self.south.name)
