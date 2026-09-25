import json
from datetime import timedelta

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, getdate, now_datetime


class TestFuelOrder(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		suffix = frappe.generate_hash(length=8)
		self.location = self._insert("Fleet Location", location_name=f"AC01 Location {suffix}")
		self.inactive_location = self._insert(
			"Fleet Location", location_name=f"AC01 Inactive Location {suffix}", active=0
		)
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC01 Diesel {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model",
			make=f"AC01 Make {suffix}",
			model=f"AC01 Model {suffix}",
			tank_capacity_litres=60,
		)
		self.inactive_fuel_type = self._insert(
			"Fuel Type", fuel_type_name=f"AC01 Inactive Fuel {suffix}", active=0
		)
		self.station = self._insert(
			"Fuel Station",
			station_name=f"AC01 Station {suffix}",
			operational_location=self.location.name,
		)
		self.inactive_station = self._insert(
			"Fuel Station",
			station_name=f"AC01 Inactive Station {suffix}",
			operational_location=self.location.name,
			active=0,
		)
		self.requester = self._insert("Fleet Person", person_name=f"AC01 Requester {suffix}")
		self.driver = self._insert("Fleet Person", person_name=f"AC01 Driver {suffix}")
		self.custodian = self._insert("Fleet Person", person_name=f"AC01 Custodian {suffix}")
		self.company_representative = self._insert(
			"Fleet Person", person_name=f"AC01 Representative {suffix}"
		)
		self.inactive_person = self._insert(
			"Fleet Person", person_name=f"AC01 Inactive Person {suffix}", active=0
		)
		assignment = {
			"doctype": "Asset Assignment",
			"custodian": self.custodian.name,
			"assigned_location": self.location.name,
			"effective_from": "2026-01-01",
		}
		self.asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC01 Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[dict(assignment)],
		)
		self.inactive_asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC01 Inactive Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[dict(assignment)],
			active=0,
		)

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _save_settings(self, **values):
		settings = frappe.get_single("Fleet Management Settings")
		for fieldname, value in values.items():
			settings.set(fieldname, value)
		settings.save(ignore_permissions=True)
		return settings

	def make_order(self, **overrides):
		values = {
			"doctype": "Fuel Order",
			"request_datetime": now_datetime(),
			"actual_requester": self.requester.name,
			"driver": self.driver.name,
			"custodian": self.custodian.name,
			"company_representative": self.company_representative.name,
			"asset": self.asset.name,
			"operational_location": self.location.name,
			"planned_station": self.station.name,
			"request_meter_reading": 1000,
			"request_gauge_percent": 40,
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def _make_approved_order(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)
		with self.set_user(requester):
			order = apply_workflow(self.make_order().insert(), "Submit for Approval")
		with self.set_user(approver):
			order = apply_workflow(order, "Approve")
		return order, requester, approver

	def _user(self, roles, location):
		email = f"ac03-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AC03",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Fleet Location",
				"for_value": location,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		return user.name

	def test_records_people_without_login_as_requester_and_participants(self):
		order = self.make_order().insert(ignore_permissions=True)

		self.assertRegex(order.name, rf"^FO-{getdate().year}-\d{{5}}$")
		self.assertEqual(order.actual_requester, self.requester.name)
		self.assertEqual(order.driver, self.driver.name)
		self.assertEqual(order.custodian, self.custodian.name)
		self.assertEqual(order.company_representative, self.company_representative.name)
		self.assertEqual(order.fuel_type, self.fuel_type.name)
		self.assertEqual(order.assigned_location_snapshot, self.location.name)
		self.assertEqual(order.assigned_custodian_snapshot, self.custodian.name)
		self.assertEqual(str(order.assignment_effective_from), "2026-01-01")
		self.assertIsNone(order.assignment_effective_until)
		self.assertEqual(order.asset_fuel_type_snapshot, self.fuel_type.name)
		self.assertEqual(order.asset_tank_capacity_snapshot, 60)
		self.assertEqual(order.asset_target_km_per_litre_snapshot, 10)
		self.assertEqual(order.asset_tolerance_percent_snapshot, 2)
		self.assertTrue(order.owner)
		for person in (self.requester, self.driver, self.custodian, self.company_representative):
			self.assertFalse(frappe.db.get_value("Fleet Person", person.name, "user"))

	def test_rejects_inactive_references(self):
		invalid_references = (
			("actual_requester", self.inactive_person.name),
			("asset", self.inactive_asset.name),
			("operational_location", self.inactive_location.name),
			("planned_station", self.inactive_station.name),
			("fuel_type", self.inactive_fuel_type.name),
		)

		for fieldname, value in invalid_references:
			with self.subTest(fieldname=fieldname):
				with self.assertRaises(frappe.ValidationError):
					self.make_order(**{fieldname: value}).insert(ignore_permissions=True)

	def test_rejects_missing_participant_reference(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_order(actual_requester="Missing AC01 Person").insert(ignore_permissions=True)

	def test_different_permitted_approver_can_approve_and_reject(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = apply_workflow(self.make_order().insert(), "Submit for Approval")

		self.assertEqual(order.workflow_state, "Pending Approval")
		self.assertEqual(order.submitted_by, requester)
		self.assertTrue(order.submitted_on)

		with self.set_user(approver):
			approved = apply_workflow(order, "Approve")

		self.assertEqual(approved.workflow_state, "Approved")
		self.assertEqual(approved.docstatus, 1)
		self.assertEqual(approved.approved_by, approver)
		self.assertTrue(approved.approved_on)

		with self.set_user(requester):
			rejected_order = apply_workflow(
				self.make_order(request_meter_reading=2000).insert(), "Submit for Approval"
			)

		with self.set_user(approver):
			rejected = apply_workflow(rejected_order, "Reject")

		self.assertEqual(rejected.workflow_state, "Rejected")
		self.assertEqual(rejected.docstatus, 0)
		self.assertEqual(rejected.rejected_by, approver)
		self.assertTrue(rejected.rejected_on)

	def test_self_approval_is_denied_for_owner_and_linked_requester(self):
		self_approver = self._user(("Fleet User", "Fleet Approver"), self.location.name)

		with self.set_user(self_approver):
			order = apply_workflow(self.make_order().insert(), "Submit for Approval")
			for action in ("Approve", "Reject"):
				with self.subTest(action=action):
					with self.assertRaises(frappe.ValidationError):
						apply_workflow(order, action)

		self.assertEqual(frappe.db.get_value("Fuel Order", order.name, "workflow_state"), "Pending Approval")

		owner = self._user(("Fleet User",), self.location.name)
		submitter = self._user(("Fleet User", "Fleet Approver"), self.location.name)
		with self.set_user(owner):
			order = self.make_order().insert()
		with self.set_user(submitter):
			order = apply_workflow(order, "Submit for Approval")
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(order, "Approve")

		approver = self._user(("Fleet Approver",), self.location.name)
		requester = self._user(("Fleet User",), self.location.name)
		linked_requester = self._insert(
			"Fleet Person", person_name=f"AC03 Linked Requester {frappe.generate_hash(length=8)}", user=approver
		)

		with self.set_user(requester):
			order = apply_workflow(
				self.make_order(actual_requester=linked_requester.name).insert(), "Submit for Approval"
			)

		with self.set_user(approver):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(order, "Approve")

	def test_approval_persists_valid_until_from_approval_timestamp(self):
		self._save_settings(default_validity_days=5)
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = apply_workflow(self.make_order().insert(), "Submit for Approval")
		with self.set_user(approver):
			apply_workflow(order, "Approve")

		persisted = frappe.get_doc("Fuel Order", order.name)
		expected_valid_until = get_datetime(persisted.approved_on) + timedelta(days=5)
		self.assertEqual(get_datetime(persisted.valid_until), expected_valid_until)

		self._save_settings(default_validity_days=1)
		persisted.reload()
		self.assertEqual(get_datetime(persisted.valid_until), expected_valid_until)

	def test_pre_fueling_extension_changes_only_validity_and_requires_reprint(self):
		order, _requester, approver = self._make_approved_order()
		old_valid_until = get_datetime(order.valid_until)
		snapshot = {
			fieldname: order.get(fieldname)
			for fieldname in (
				"asset",
				"operational_location",
				"planned_station",
				"fuel_type",
				"quantity_authorization",
				"authorized_quantity_litres",
				"actual_requester",
				"driver",
				"custodian",
				"company_representative",
				"submitted_by",
				"submitted_on",
				"approved_by",
				"approved_on",
			)
		}
		new_valid_until = old_valid_until.replace(microsecond=0) + timedelta(hours=12)
		reason = "AC08 pre-fueling extension"

		with self.set_user(approver):
			result = order.extend_validity(
				new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), reason
			)
			printed = frappe.get_print(
				"Fuel Order",
				order.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=1,
			)

		persisted = frappe.get_doc("Fuel Order", order.name)
		self.assertEqual(get_datetime(persisted.valid_until), new_valid_until)
		self.assertEqual(persisted.reprint_required, 0)
		self.assertEqual(persisted.slip_revision, 2)
		self.assertEqual(persisted.printed_slip_revision, 2)
		self.assertTrue(persisted.last_slip_printed_on)
		self.assertEqual(result["reprint_required"], 1)
		self.assertEqual(result["valid_until"], str(persisted.valid_until))
		for fieldname, value in snapshot.items():
			self.assertEqual(persisted.get(fieldname), value, fieldname)

		history = json.loads(persisted.validity_extension_history)
		self.assertEqual(len(history), 1)
		self.assertEqual(get_datetime(history[0]["old_valid_until"]), old_valid_until)
		self.assertEqual(get_datetime(history[0]["new_valid_until"]), new_valid_until)
		self.assertEqual(history[0]["actor"], approver)
		self.assertEqual(history[0]["reason"], reason)
		self.assertTrue(history[0]["timestamp"])
		self.assertIn(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), printed)

	def test_extension_requires_non_blank_reason(self):
		order, _requester, approver = self._make_approved_order()
		old_valid_until = get_datetime(order.valid_until)

		for reason in ("", "   "):
			with self.subTest(reason=repr(reason)), self.set_user(approver):
				with self.assertRaises(frappe.ValidationError):
					order.extend_validity(
						(old_valid_until + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
						reason,
					)

		order.reload()
		self.assertEqual(get_datetime(order.valid_until), old_valid_until)
		self.assertFalse(order.reprint_required)
		self.assertEqual(json.loads(order.validity_extension_history), [])

	def test_extension_preserves_role_and_location_boundaries(self):
		order, _requester, _approver = self._make_approved_order()
		old_valid_until = get_datetime(order.valid_until)
		new_valid_until = old_valid_until.replace(microsecond=0) + timedelta(hours=1)
		fleet_user = self._user(("Fleet User",), self.location.name)
		other_location = self._insert(
			"Fleet Location", location_name=f"AC08 Other Location {frappe.generate_hash(length=8)}"
		)
		other_approver = self._user(("Fleet Approver",), other_location.name)
		fleet_admin = self._user(("Fleet Admin",), self.location.name)

		for user in (fleet_user, other_approver):
			with self.subTest(user=user), self.set_user(user):
				with self.assertRaises(frappe.PermissionError):
					order.extend_validity(
						new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "not permitted"
					)

		with self.set_user(fleet_admin):
			order.extend_validity(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "admin extension")
		self.assertEqual(get_datetime(order.valid_until), new_valid_until)

	def test_expired_order_cannot_be_extended_retroactively(self):
		order, _requester, approver = self._make_approved_order()
		order.db_set("valid_until", now_datetime() - timedelta(minutes=1), update_modified=False)
		order.reload()

		with self.set_user(approver):
			with self.assertRaises(frappe.ValidationError):
				order.extend_validity(
					(now_datetime() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
					"too late",
				)

	def test_order_cannot_be_extended_after_fueling_has_started(self):
		order, _requester, approver = self._make_approved_order()
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"fuel_order": order.name,
				"actual_fueling_datetime": get_datetime(order.approved_on) + timedelta(minutes=1),
			}
		).insert(ignore_permissions=True)

		with self.set_user(approver):
			with self.assertRaises(frappe.ValidationError):
				order.extend_validity(
					(get_datetime(order.valid_until) + timedelta(hours=1)).strftime(
						"%Y-%m-%d %H:%M:%S"
					),
					"after fueling",
				)

	def test_approved_print_contains_ac04_fields_and_instruction(self):
		instruction = f"AC04 instruction {frappe.generate_hash(length=8)}"
		self._save_settings(default_validity_days=4, print_instruction=instruction)
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = apply_workflow(
				self.make_order(
					quantity_authorization="Partial", authorized_quantity_litres=42.5
				).insert(),
				"Submit for Approval",
			)
		with self.set_user(approver):
			approved = apply_workflow(order, "Approve")
			printed = frappe.get_print(
				"Fuel Order",
				approved.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=1,
			)

		expected_valid_until = get_datetime(approved.valid_until).strftime("%Y-%m-%d %H:%M:%S")
		expected_approved_on = get_datetime(approved.approved_on).strftime("%Y-%m-%d %H:%M:%S")
		for value in (
			approved.name,
			self.asset.name,
			self.location.name,
			self.station.name,
			self.fuel_type.name,
			"Partial authorization",
			"42.5 litres",
			"Request gauge",
			"40%",
			"Estimated litres to fill (from gauge):",
			"36.0 litres",
			approved.approved_by,
			expected_approved_on,
			expected_valid_until,
			instruction,
			self.company_representative.name,
			self.driver.name,
			"Approver physical signature",
			"Company representative signature",
			"Driver signature",
			"Fuel station attendant signature",
			"Do not dispense after the valid-until timestamp",
		):
			self.assertIn(str(value), printed)

	def test_vehicle_request_gauge_is_required_whole_and_estimates_litres(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Request gauge is required"):
			self.make_order(request_gauge_percent=None).insert(ignore_permissions=True)
		for gauge in (-1, 101):
			with self.subTest(gauge=gauge), self.assertRaises(frappe.ValidationError):
				self.make_order(request_gauge_percent=gauge).insert(ignore_permissions=True)

		draft = self.make_order(request_gauge_percent=40).insert(ignore_permissions=True)
		self.assertEqual(draft.asset_type, "Vehicle")
		self.assertEqual(draft.estimated_litres, 36)
		draft.update({"request_gauge_percent": 75, "estimated_litres": 999})
		draft.save(ignore_permissions=True)
		self.assertEqual(draft.estimated_litres, 15)

		order, _requester, _approver = self._make_approved_order()
		self.assertEqual(frappe.db.get_value("Fuel Order", order.name, "estimated_litres"), 36)

	def test_generator_order_has_no_request_gauge(self):
		generator = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC04 Generator {frappe.generate_hash(length=8)}",
			asset_type="Generator",
			fuel_type=self.fuel_type.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.custodian.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		order = self.make_order(asset=generator.name, request_gauge_percent=None).insert(
			ignore_permissions=True
		)
		self.assertIsNone(order.estimated_litres)
		with self.assertRaisesRegex(frappe.ValidationError, "vehicles only"):
			self.make_order(asset=generator.name, request_gauge_percent=40).insert(
				ignore_permissions=True
			)

	def test_fulfillment_status_is_derived_and_never_stored(self):
		self.assertFalse(frappe.db.has_column("Fuel Order", "fulfillment_status"))
		draft = self.make_order().insert(ignore_permissions=True)
		self.assertIsNone(draft.fulfillment_status)

		order, _requester, _approver = self._make_approved_order()
		order = frappe.get_doc("Fuel Order", order.name)
		self.assertEqual(order.fulfillment_status, "Awaiting Transaction")
		self.assertEqual(order.as_dict()["fulfillment_status"], "Awaiting Transaction")

		frappe.db.set_value(
			"Fuel Order", order.name, "valid_until", now_datetime() - timedelta(hours=1),
			update_modified=False,
		)
		self.assertEqual(frappe.get_doc("Fuel Order", order.name).fulfillment_status, "Expired")

	def test_only_approved_permitted_orders_can_be_printed(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)
		other_location = self._insert(
			"Fleet Location", location_name=f"AC04 Other Location {frappe.generate_hash(length=8)}"
		)
		unauthorized = self._user(("Fleet Approver",), other_location.name)

		with self.set_user(requester):
			draft = self.make_order().insert()
			pending = apply_workflow(self.make_order(request_meter_reading=2000).insert(), "Submit for Approval")
		with self.set_user(approver):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", draft.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)
			rejected = apply_workflow(pending, "Reject")
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", rejected.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)

		with self.set_user(requester):
			approved = apply_workflow(
				self.make_order(request_meter_reading=3000).insert(), "Submit for Approval"
			)
		with self.set_user(approver):
			approved = apply_workflow(approved, "Approve")

		with self.set_user(requester):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", approved.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)

		with self.set_user(unauthorized):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", approved.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)
