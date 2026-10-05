import json
import re
from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, getdate, now_datetime

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import (
	get_previous_entry,
	get_request_facts,
)
from fleet_management.tests.utils import attach_request_photos, decide, make_photo, send_up


# specs/009-fuel-order-ux Requirements 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 3.3
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
		# The 001 tests below exercise the sign-off route, which only red orders take (spec 002 D-10).
		self._save_settings(
			gauge_limit_percent=30,
			mileage_margin_percent=15,
			litres_excess_percent=10,
			min_hours_between_fuelings=24,
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
			order = send_up(attach_request_photos(self.make_order().insert()))
		with self.set_user(approver):
			order = decide(order, "Approve")
		return order, requester, approver

	def _user(self, roles, location, first_name="AC03", last_name=None):
		email = f"ac03-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
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
		summary = json.loads(order.signal_details_json)["request_summary"]
		self.assertEqual(summary["vehicle_target_km_per_litre"], 10)
		self.assertIsNone(summary["recent_observed_average_km_per_litre"])
		self.assertEqual(summary["applicable_fuel_economy_source"], "vehicle_target")
		facts = get_request_facts(self.asset.name)
		self.assertEqual(facts["asset_type"], "Vehicle")
		self.assertEqual(facts["vehicle_model"], self.vehicle_model.name)
		self.assertEqual(facts["fuel_type"], self.fuel_type.name)
		self.assertTrue(order.owner)
		for person in (self.requester, self.driver, self.custodian, self.company_representative):
			self.assertFalse(frappe.db.get_value("Fleet Person", person.name, "user"))

	def test_entry_form_groups_and_conditions_review_fields(self):
		meta = frappe.get_meta("Fuel Order")
		section_labels = [field.label for field in meta.fields if field.fieldtype == "Section Break"]
		self.assertEqual(
			section_labels[:4],
			[
				"Vehicle and Order",
				"People and Location",
				"Readings and Evidence",
				"Quantity, Approval and Audit",
			],
		)
		self.assertEqual(meta.get_field("section_break_system_details").collapsible, 1)

		field_positions = {field.fieldname: index for index, field in enumerate(meta.fields)}
		self.assertLess(field_positions["asset"], field_positions["column_break_vehicle_driver"])
		self.assertLess(field_positions["driver"], field_positions["column_break_vehicle_requester"])
		self.assertLess(field_positions["column_break_vehicle_requester"], field_positions["actual_requester"])
		self.assertLess(field_positions["company_representative"], field_positions["operational_location"])
		self.assertLess(field_positions["request_meter_reading"], field_positions["meter_photo"])
		self.assertLess(field_positions["meter_photo"], field_positions["column_break_readings_gauge"])
		self.assertLess(field_positions["column_break_readings_gauge"], field_positions["request_gauge_percent"])
		self.assertLess(field_positions["request_gauge_percent"], field_positions["gauge_photo"])
		self.assertLess(field_positions["meter_photo"], field_positions["quantity_authorization"])
		self.assertLess(field_positions["partial_authorization_reason"], field_positions["signal_panel_html"])
		self.assertLess(field_positions["signal_panel_html"], field_positions["workflow_state"])
		self.assertLess(field_positions["send_up_explanation"], field_positions["column_break_approval_decision"])
		self.assertLess(field_positions["column_break_approval_decision"], field_positions["approved_by"])
		self.assertFalse(meta.get_field("workflow_state").hidden)
		self.assertEqual(
			meta.get_field("column_break_readings_gauge").depends_on,
			"eval:doc.asset_type=='Vehicle'",
		)
		self.assertIn("column_break_approval_decision", field_positions)
		self.assertLess(field_positions["section_break_history"], field_positions["section_break_system_details"])
		self.assertEqual(meta.get_field("section_break_history").collapsible, 1)
		self.assertGreater(field_positions["signal"], field_positions["section_break_system_details"])
		self.assertGreater(field_positions["signal_reasons"], field_positions["section_break_system_details"])
		self.assertEqual(meta.get_field("signal_reasons").fieldtype, "Long Text")
		self.assertFalse(meta.get_field("signal_panel_html").hidden)

		for fieldname in (
			"asset",
			"driver",
			"actual_requester",
			"company_representative",
			"operational_location",
			"planned_station",
			"request_meter_reading",
			"quantity_authorization",
		):
			self.assertFalse(meta.get_field(fieldname).read_only, fieldname)
			self.assertEqual(meta.get_field(fieldname).reqd, 1, fieldname)
		for fieldname in ("actual_requester", "company_representative", "request_datetime"):
			self.assertFalse(meta.get_field(fieldname).default, fieldname)
		self.assertFalse(meta.get_field("request_gauge_percent").read_only)
		self.assertEqual(
			meta.get_field("request_gauge_percent").mandatory_depends_on,
			"eval:doc.asset_type=='Vehicle'",
		)
		self.assertFalse(meta.get_field("meter_photo").read_only)
		self.assertFalse(meta.get_field("gauge_photo").read_only)

		for fieldname in (
			"vehicle_model",
			"asset_type",
			"fuel_type",
			"custodian",
			"assigned_location_snapshot",
			"asset_tank_capacity_snapshot",
			"asset_target_km_per_litre_snapshot",
			"previous_entry_source",
			"previous_meter_reading",
			"previous_entry_date",
			"estimated_litres",
			"average_km_per_litre",
		):
			self.assertEqual(meta.get_field(fieldname).read_only, 1, fieldname)

		for fieldname in ("request_gauge_percent", "gauge_photo"):
			self.assertEqual(meta.get_field(fieldname).depends_on, "eval:doc.asset_type=='Vehicle'", fieldname)
		self.assertEqual(meta.get_field("meter_photo").fieldtype, "Attach Image")
		self.assertEqual(
			meta.get_field("authorized_quantity_litres").depends_on,
			"eval:doc.quantity_authorization=='Partial'",
		)
		self.assertEqual(
			meta.get_field("authorized_quantity_litres").mandatory_depends_on,
			"eval:doc.quantity_authorization=='Partial'",
		)
		self.assertFalse(meta.get_field("authorized_quantity_litres").read_only)
		self.assertEqual(
			meta.get_field("partial_authorization_reason").depends_on,
			"eval:doc.quantity_authorization=='Partial'",
		)
		self.assertEqual(
			meta.get_field("partial_authorization_reason").mandatory_depends_on,
			"eval:doc.quantity_authorization=='Partial' && doc.workflow_state!='Draft'",
		)

	def test_partial_authorization_requires_reason_before_leaving_draft(self):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			order = attach_request_photos(
				self.make_order(
					quantity_authorization="Partial",
					authorized_quantity_litres=42.5,
					request_gauge_percent=80,
				).insert()
			)
			with self.assertRaises(frappe.ValidationError):
				send_up(order)

			order.reload()
			order.partial_authorization_reason = "Only 42.5 litres are needed for this trip."
			order.save()
			pending = send_up(order)

		self.assertEqual(pending.workflow_state, "Pending Approval")
		self.assertEqual(
			pending.partial_authorization_reason,
			"Only 42.5 litres are needed for this trip.",
		)

	def test_rejects_inactive_references(self):
		invalid_references = (
			("actual_requester", self.inactive_person.name),
			("asset", self.inactive_asset.name),
			("operational_location", self.inactive_location.name),
			("planned_station", self.inactive_station.name),
		)

		for fieldname, value in invalid_references:
			with self.subTest(fieldname=fieldname):
				with self.assertRaises(frappe.ValidationError):
					self.make_order(**{fieldname: value}).insert(ignore_permissions=True)

		with self.subTest(fieldname="fuel_type"):
			# The fuel type comes from the vehicle (spec 002 D-4), so it is refused when the vehicle's is inactive.
			frappe.db.set_value("Fuel Type", self.fuel_type.name, "active", 0)
			with self.assertRaises(frappe.ValidationError):
				self.make_order().insert(ignore_permissions=True)

	def test_rejects_missing_participant_reference(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_order(actual_requester="Missing AC01 Person").insert(ignore_permissions=True)

	def test_different_permitted_approver_can_approve_and_reject(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = send_up(attach_request_photos(self.make_order().insert()))

		self.assertEqual(order.workflow_state, "Pending Approval")
		self.assertEqual(order.submitted_by, requester)
		self.assertTrue(order.submitted_on)

		with self.set_user(approver):
			approved = decide(order, "Approve")

		self.assertEqual(approved.workflow_state, "Approved")
		self.assertEqual(approved.docstatus, 1)
		self.assertEqual(approved.approved_by, approver)
		self.assertTrue(approved.approved_on)

		with self.set_user(requester):
			rejected_order = send_up(
				attach_request_photos(self.make_order(request_meter_reading=2000).insert())
			)

		with self.set_user(approver):
			rejected = decide(rejected_order, "Reject")

		self.assertEqual(rejected.workflow_state, "Rejected")
		self.assertEqual(rejected.docstatus, 0)
		self.assertEqual(rejected.rejected_by, approver)
		self.assertTrue(rejected.rejected_on)

	def test_self_approval_is_denied_for_owner_and_linked_requester(self):
		self_approver = self._user(("Fleet User", "Fleet Approver"), self.location.name)

		with self.set_user(self_approver):
			order = send_up(attach_request_photos(self.make_order().insert()))
			for action in ("Approve", "Reject"):
				with self.subTest(action=action):
					with self.assertRaises(frappe.ValidationError):
						decide(order, action)

		self.assertEqual(frappe.db.get_value("Fuel Order", order.name, "workflow_state"), "Pending Approval")

		owner = self._user(("Fleet User",), self.location.name)
		submitter = self._user(("Fleet User", "Fleet Approver"), self.location.name)
		with self.set_user(owner):
			order = attach_request_photos(self.make_order().insert())
		with self.set_user(submitter):
			order = send_up(order)
			with self.assertRaises(frappe.ValidationError):
				decide(order, "Approve")

		approver = self._user(("Fleet Approver",), self.location.name)
		requester = self._user(("Fleet User",), self.location.name)
		linked_requester = self._insert(
			"Fleet Person",
			person_name=f"AC03 Linked Requester {frappe.generate_hash(length=8)}",
			user=approver,
		)

		with self.set_user(requester):
			order = send_up(
				attach_request_photos(self.make_order(actual_requester=linked_requester.name).insert())
			)

		with self.set_user(approver):
			with self.assertRaises(frappe.ValidationError):
				decide(order, "Approve")

	def test_approval_persists_valid_until_from_approval_timestamp(self):
		self._save_settings(default_validity_days=5)
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = send_up(attach_request_photos(self.make_order().insert()))
		with self.set_user(approver):
			decide(order, "Approve")

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
			result = order.extend_validity(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), reason)
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
		self.assertIn(frappe.utils.format_datetime(new_valid_until), printed)

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
					order.extend_validity(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "not permitted")

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
					(get_datetime(order.valid_until) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
					"after fueling",
				)

	def test_approved_print_contains_ac04_fields_and_instruction(self):
		instruction = f"AC04 instruction {frappe.generate_hash(length=8)}"
		self._save_settings(default_validity_days=4, print_instruction=instruction)
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)

		with self.set_user(requester):
			order = send_up(
				attach_request_photos(
					self.make_order(
						quantity_authorization="Partial",
						authorized_quantity_litres=42.5,
						partial_authorization_reason="One trip requires 42.5 litres.",
					).insert()
				)
			)
		with self.set_user(approver):
			approved = decide(order, "Approve")
			printed = frappe.get_print(
				"Fuel Order",
				approved.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=1,
			)

		expected_valid_until = frappe.utils.format_datetime(approved.valid_until)
		expected_approved_on = frappe.utils.format_datetime(approved.approved_on)
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
			"36 litres",
			frappe.utils.get_fullname(approved.approved_by),
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

		# Readings print without a trailing ".0" and timestamps in the site's dd/mm/yyyy format.
		self.assertIn(">1000<", printed)
		self.assertNotIn(get_datetime(approved.valid_until).strftime("%Y-%m-%d"), printed)

	def test_approved_slip_reads_like_the_company_paper_slip(self):
		suffix = frappe.generate_hash(length=8)
		self._insert(
			"Letter Head",
			letter_head_name=f"AC01 Heading {suffix}",
			source="HTML",
			content="<p>KRYSTALLINE SALT LIMITED</p><p>PIN NO. P000000000T</p>",
			is_default=1,
		)
		self._insert(
			"Address",
			address_title=self.station.name,
			address_type="Postal",
			address_line1="P.O Box 10001",
			pincode="00100",
			city="Nairobi",
			country="Kenya",
			email_id="station.test@example.com",
			is_primary_address=1,
			links=[{"link_doctype": "Fuel Station", "link_name": self.station.name}],
		)
		order, _requester, approver = self._make_approved_order()

		with self.set_user(approver):
			printed = frappe.get_print(
				"Fuel Order",
				order.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=0,
			)
			bare = frappe.get_print(
				"Fuel Order",
				order.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=1,
			)

		for value in (
			"COPY TO BE ATTACHED WITH STATEMENT",
			"FUEL ORDER SLIP",
			"KRYSTALLINE SALT LIMITED",
			"PIN NO. P000000000T",
			order.name,
			frappe.utils.formatdate(order.request_datetime),
			self.station.name,
			"P.O Box 10001 – 00100 NAIROBI",  # noqa: RUF001
			"station.test@example.com",
			"Please supply",
			"FULL TANK",
			"Ltrs of",
			self.fuel_type.name,
			"to the following motor vehicle",
			"Reg No:",
			self.asset.name,
			"speedometer",
			f"{order.request_meter_reading:g}",
			"NAMES OF AUTHORISED PERSON",
			"Company stamp",
		):
			with self.subTest(value=value):
				self.assertIn(str(value), printed)

		self.assertNotIn("KRYSTALLINE SALT LIMITED", bare)

		css = frappe.db.get_value("Print Format", "Fuel Order Approval Slip", "css")
		self.assertIn("page-size: A5", css)
		self.assertIn("size: A5 portrait", css)
		self.assertEqual(
			frappe.db.get_value("Print Format", "Fuel Order Approval Slip", "pdf_generator"), "chrome"
		)

	def test_slip_names_the_authorised_person_by_full_name(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(
			("Fleet Approver",), self.location.name, first_name="Vikas", last_name="Test Approver"
		)

		with self.set_user(requester):
			order = send_up(attach_request_photos(self.make_order().insert()))
		with self.set_user(approver):
			order = decide(order, "Approve")
			printed = frappe.get_print(
				"Fuel Order",
				order.name,
				print_format="Fuel Order Approval Slip",
				no_letterhead=1,
			)

		self.assertEqual(order.approved_by, approver)
		self.assertGreaterEqual(printed.count("Vikas Test Approver"), 2)
		# Frappe's print view closes the page with an HTML comment naming the viewer; it is never printed.
		self.assertNotIn(approver, re.sub(r"<!--.*?-->", "", printed, flags=re.S))

	def test_request_date_is_set_by_the_server_and_never_changes(self):
		before = now_datetime().replace(microsecond=0)
		order = self.make_order(request_datetime="2020-01-01 08:00:00").insert(ignore_permissions=True)
		self.assertGreaterEqual(get_datetime(order.request_datetime), before)

		saved = get_datetime(order.request_datetime)
		order.request_datetime = "2021-06-01 09:00:00"
		order.save(ignore_permissions=True)
		self.assertEqual(get_datetime(order.request_datetime), saved)
		self.assertEqual(
			get_datetime(frappe.db.get_value("Fuel Order", order.name, "request_datetime")), saved
		)

		meta = frappe.get_meta("Fuel Order")
		self.assertEqual(meta.get_field("request_datetime").read_only, 1)
		self.assertFalse(meta.get_field("request_datetime").reqd)
		self.assertFalse(meta.get_field("request_datetime").default)
		self.assertEqual(meta.get_field("naming_series").read_only, 1)

	def test_custodian_comes_from_the_effective_assignment(self):
		other = self._insert(
			"Fleet Person", person_name=f"AC05 Other Custodian {frappe.generate_hash(length=8)}"
		)
		order = self.make_order(custodian=other.name).insert(ignore_permissions=True)
		self.assertEqual(order.custodian, self.custodian.name)
		self.assertEqual(order.assigned_custodian_snapshot, self.custodian.name)

		order.custodian = other.name
		order.save(ignore_permissions=True)
		self.assertEqual(order.custodian, self.custodian.name)

		self.assertEqual(order.asset_tank_capacity_snapshot, 60)
		self.assertEqual(order.asset_target_km_per_litre_snapshot, 10)
		self.assertEqual(order.assigned_location_snapshot, self.location.name)
		self.assertEqual(order.fuel_type, self.fuel_type.name)

	def test_previous_entry_is_none_for_a_vehicle_never_ordered(self):
		order = self.make_order().insert(ignore_permissions=True)

		self.assertEqual(order.previous_entry_source, "none")
		self.assertFalse(order.previous_meter_reading)
		self.assertIsNone(order.previous_entry_date)

	def test_previous_entry_falls_back_to_the_last_approved_order(self):
		approved, _requester, _approver = self._make_approved_order()
		order = self.make_order(request_meter_reading=1500).insert(ignore_permissions=True)

		self.assertEqual(order.previous_entry_source, f"Approved order {approved.name}")
		self.assertEqual(order.previous_meter_reading, approved.request_meter_reading)
		self.assertEqual(get_datetime(order.previous_entry_date), get_datetime(approved.approved_on))

		# The approved order's own previous entry was computed before it was
		# approved and is now frozen; it never picks up the new order.
		persisted_approved = frappe.get_doc("Fuel Order", approved.name)
		self.assertEqual(persisted_approved.previous_entry_source, "none")

		self.assertEqual(
			get_previous_entry(self.asset.name, exclude_order=approved.name)["previous_entry_source"],
			"none",
		)

	def test_request_facts_suggest_driver_home_location_and_a_single_station(self):
		suffix = frappe.generate_hash(length=8)
		location = self._insert("Fleet Location", location_name=f"AC05 Home {suffix}")
		station = self._insert(
			"Fuel Station", station_name=f"AC05 Only Station {suffix}", operational_location=location.name
		)
		asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC05 Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.custodian.name,
					"assigned_location": location.name,
					"effective_from": "2026-01-01",
					"primary_driver": self.driver.name,
				}
			],
		)

		facts = get_request_facts(asset.name)

		self.assertEqual(facts["custodian"], self.custodian.name)
		self.assertEqual(facts["primary_driver"], self.driver.name)
		self.assertEqual(facts["assigned_location_snapshot"], location.name)
		self.assertEqual(facts["asset_tank_capacity_snapshot"], 60)
		self.assertEqual(facts["asset_target_km_per_litre_snapshot"], 10)
		self.assertEqual(facts["suggested_station"], station.name)
		self.assertEqual(facts["previous_entry_source"], "none")

		self._insert(
			"Fuel Station", station_name=f"AC05 Second Station {suffix}", operational_location=location.name
		)
		self.assertIsNone(get_request_facts(asset.name)["suggested_station"])

	def test_an_order_cannot_be_sent_up_without_its_photos(self):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			order = self.make_order().insert()
			with self.assertRaisesRegex(frappe.ValidationError, "Meter photo is required"):
				send_up(order)

			order = frappe.get_doc("Fuel Order", order.name)
			order.meter_photo = make_photo().file_url
			order.save()
			with self.assertRaisesRegex(frappe.ValidationError, "Gauge photo is required"):
				send_up(order)

			order = frappe.get_doc("Fuel Order", order.name)
			attach_request_photos(order)
			sent = send_up(order)

		self.assertEqual(sent.workflow_state, "Pending Approval")
		self.assertEqual(
			frappe.db.get_value("File", {"file_url": sent.meter_photo}, "attached_to_name"),
			sent.name,
		)

	def test_a_public_or_wrong_type_photo_is_refused(self):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			for case, kwargs, message in (
				("public", {"private": False}, "must be a private attachment"),
				("wrong type", {"extension": "pdf"}, "must be a JPG or PNG file"),
			):
				with self.subTest(case=case):
					order = self.make_order().insert()
					attach_request_photos(order, **kwargs)
					order = frappe.get_doc("Fuel Order", order.name)
					with self.assertRaisesRegex(frappe.ValidationError, message):
						send_up(order)

	def test_orders_already_past_draft_are_not_rechecked(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)
		with self.set_user(requester):
			pending = send_up(attach_request_photos(self.make_order().insert()))

		# Stands in for an order sent up before photos were required (spec 002 D-6).
		frappe.db.set_value("Fuel Order", pending.name, {"meter_photo": None, "gauge_photo": None})

		with self.set_user(approver):
			approved = decide(pending, "Approve")

		self.assertEqual(approved.workflow_state, "Approved")

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
			self.make_order(asset=generator.name, request_gauge_percent=40).insert(ignore_permissions=True)

	def test_fulfillment_status_is_derived_and_never_stored(self):
		self.assertFalse(frappe.db.has_column("Fuel Order", "fulfillment_status"))
		draft = self.make_order().insert(ignore_permissions=True)
		self.assertIsNone(draft.fulfillment_status)

		order, _requester, _approver = self._make_approved_order()
		order = frappe.get_doc("Fuel Order", order.name)
		self.assertEqual(order.fulfillment_status, "Awaiting Transaction")
		self.assertEqual(order.as_dict()["fulfillment_status"], "Awaiting Transaction")

		frappe.db.set_value(
			"Fuel Order",
			order.name,
			"valid_until",
			now_datetime() - timedelta(hours=1),
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
			pending = send_up(attach_request_photos(self.make_order(request_meter_reading=2000).insert()))
		with self.set_user(approver):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", draft.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)
			rejected = decide(pending, "Reject")
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", rejected.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)

		with self.set_user(requester):
			approved = send_up(attach_request_photos(self.make_order(request_meter_reading=3000).insert()))
		with self.set_user(approver):
			approved = decide(approved, "Approve")

		# A Fleet User may print an approved order at his permitted location (spec 002 D-10).
		with self.set_user(requester):
			printed = frappe.get_print(
				"Fuel Order", approved.name, print_format="Fuel Order Approval Slip", no_letterhead=1
			)
		self.assertIn(approved.name, printed)

		with self.set_user(unauthorized):
			with self.assertRaises(frappe.PermissionError):
				frappe.get_print(
					"Fuel Order", approved.name, print_format="Fuel Order Approval Slip", no_letterhead=1
				)
