import os
from datetime import timedelta
from io import BytesIO
from itertools import count
from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import get_datetime, now_datetime
from PIL import Image

from fleet_management.tests.concurrency_proof import (
	EXPECTED_UNIQUE_INDEXES,
	assert_concurrency_site,
	run_locked_order_overlap,
	unique_index_names,
)
from fleet_management.fleet_management.doctype.fueling_transaction.fueling_transaction import (
	calculate_vehicle_interval,
)


PDF_CONTENT = (
	b"%PDF-1.4\n"
	b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
	b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
	b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
	b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
	b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n186\n%%EOF\n"
)


_jpg_widths = count(1)


def _make_jpg_content():
	# Frappe re-encodes uploaded JPEGs to strip EXIF, which drops any appended bytes. A distinct
	# width keeps each file distinct afterwards; identical files share one URL, and the
	# invoice and signed order then attach to the wrong fields.
	buffer = BytesIO()
	Image.new("RGB", (next(_jpg_widths), 1), color=(255, 255, 255)).save(buffer, format="JPEG")
	return buffer.getvalue()


PNG_CONTENT = bytes.fromhex("89504e470d0a1a0a0000000d49484452")


class TestVehicleIntervalCalculation(UnitTestCase):
	def test_calculates_distance_litres_and_kilometres_per_litre(self):
		self.assertEqual(
			calculate_vehicle_interval(10000, 10500, 50),
			{"distance_km": 500.0, "qualifying_litres": 50.0, "km_per_litre": 10.0},
		)

	def test_rejects_non_positive_interval_inputs(self):
		with self.assertRaises(ValueError):
			calculate_vehicle_interval(10500, 10000, 50)
		with self.assertRaises(ValueError):
			calculate_vehicle_interval(10000, 10500, 0)


class TestFuelingTransaction(IntegrationTestCase):
	def setUp(self):
		if (
			self._testMethodName == "test_concurrent_submissions_wait_for_order_lock"
			and os.environ.get("FLEET_RUN_CONCURRENCY_PROOF") != "1"
		):
			self.skipTest("Set FLEET_RUN_CONCURRENCY_PROOF=1 on the disposable concurrency site.")
		super().setUp()
		frappe.local.conf["throttle_user_limit"] = max(
			frappe.local.conf.get("throttle_user_limit", 60), 1000
		)
		suffix = frappe.generate_hash(length=8)
		self.location = self._insert("Fleet Location", location_name=f"AC05 Location {suffix}")
		self.other_location = self._insert(
			"Fleet Location", location_name=f"AC05 Other Location {suffix}"
		)
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC05 Diesel {suffix}")
		self.other_fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC07 Petrol {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model",
			make=f"AC05 Make {suffix}",
			model=f"AC05 Model {suffix}",
			tank_capacity_litres=60,
		)
		self.station = self._insert(
			"Fuel Station",
			station_name=f"AC05 Station {suffix}",
			operational_location=self.location.name,
		)
		self.other_station = self._insert(
			"Fuel Station",
			station_name=f"AC05 Other Station {suffix}",
			operational_location=self.other_location.name,
		)
		self.person = self._insert("Fleet Person", person_name=f"AC05 Person {suffix}")
		self.asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC05 Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		self.other_asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC07 Other Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": self.other_location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		self.generator = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC07 Generator {suffix}",
			asset_type="Generator",
			fuel_type=self.fuel_type.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		self.user = self._user(("Fleet User",), self.location.name)
		self.approver = self._user(("Fleet Approver",), self.location.name)
		self.other_user = self._user(("Fleet User",), self.other_location.name)
		self.other_approver = self._user(("Fleet Approver",), self.other_location.name)
		self.order = self._make_approved_order(self.location, self.station, self.user, self.approver)

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _user(self, roles, location):
		email = f"ac05-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AC05",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		self._insert(
			"User Permission",
			user=user.name,
			allow="Fleet Location",
			for_value=location,
		)
		frappe.clear_cache(user=user.name)
		return user.name

	def _make_order(self, location, station, asset=None):
		asset = asset or self.asset
		values = {
			"doctype": "Fuel Order",
			"request_datetime": now_datetime(),
			"actual_requester": self.person.name,
			"driver": self.person.name,
			"custodian": self.person.name,
			"company_representative": self.person.name,
			"asset": asset.name,
			"operational_location": location.name,
			"planned_station": station.name,
			"request_meter_reading": 1000,
		}
		if asset.asset_type == "Vehicle":
			values["request_gauge_percent"] = 40
		return frappe.get_doc(values)

	def _make_approved_order(self, location, station, requester, approver, asset=None):
		with self.set_user(requester):
			order = apply_workflow(
				self._make_order(location, station, asset=asset).insert(), "Submit for Approval"
			)
		with self.set_user(approver):
			order = apply_workflow(order, "Approve")
			frappe.get_print(
				"Fuel Order", order.name, print_format="Fuel Order Approval Slip", no_letterhead=1
			)
			return order

	def _make_transaction(self, order=None, user=None):
		user = user or self.user
		with self.set_user(user):
			return frappe.get_doc(
				{"doctype": "Fueling Transaction", "fuel_order": (order or self.order).name}
			).insert()

	def _make_file(self, extension, private=True):
		content = {
			"pdf": PDF_CONTENT,
			"jpg": _make_jpg_content(),
			"png": PNG_CONTENT,
		}.get(extension, b"plain text")
		content += frappe.generate_hash(length=8).encode()
		return frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"AC05-{frappe.generate_hash(length=8)}.{extension}",
				"content": content,
				"is_private": int(private),
			}
		).insert(ignore_permissions=True)

	def _attach_files(
		self,
		transaction,
		invoice_extension="pdf",
		order_extension="png",
		invoice_private=True,
		order_private=True,
	):
		invoice = self._make_file(invoice_extension, invoice_private)
		order = self._make_file(order_extension, order_private)
		with self.set_user(transaction.owner):
			transaction.update({"signed_invoice": invoice.file_url, "signed_order": order.file_url})
			transaction.save()
		return invoice, order

	def _submit_measured_transaction(self, order, user=None, **values):
		user = user or self.user
		values.setdefault(
			"actual_fueling_datetime", get_datetime(order.approved_on) + timedelta(minutes=1)
		)
		values.setdefault("fueling_time_source", "Printed on invoice")
		values.setdefault("attendant_name", "Test Attendant")
		transaction = self._make_transaction(order, user)
		with self.set_user(user):
			transaction.update(values)
			transaction.save()
		self._attach_files(transaction)
		with self.set_user(user):
			transaction.submit()
		return frappe.get_doc("Fueling Transaction", transaction.name)

	def _submit_valid_transaction(self, order=None, user=None, **values):
		order = order or self.order
		values = {
			"actual_station": order.planned_station,
			"fuel_type": order.fuel_type,
			"actual_fueling_datetime": get_datetime(order.approved_on) + timedelta(minutes=1),
			"invoice_litres": 20,
			"invoice_number": f"INV-{frappe.generate_hash(length=8)}",
			"cu_number": f"CU-{frappe.generate_hash(length=8)}",
			**values,
		}
		if frappe.db.get_value("Fleet Asset", order.asset, "asset_type") == "Vehicle":
			values.setdefault("vehicle_odometer", 1000)
		else:
			values.setdefault("hour_meter", 100)
		return self._submit_measured_transaction(order, user=user, **values)

	def _prepare_transaction(self, order=None, user=None, **values):
		order = order or self.order
		user = user or self.user
		values.setdefault(
			"actual_fueling_datetime", get_datetime(order.approved_on) + timedelta(minutes=1)
		)
		values.setdefault("fueling_time_source", "Printed on invoice")
		values.setdefault("attendant_name", "Test Attendant")
		transaction = self._make_transaction(order, user)
		with self.set_user(user):
			transaction.update(values)
			transaction.save()
		self._attach_files(transaction)
		return transaction

	def test_missing_invoice_attachment_is_rejected(self):
		transaction = self._prepare_transaction(invoice_litres=20, vehicle_odometer=1000)
		transaction.signed_invoice = None
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_missing_signed_order_attachment_is_rejected(self):
		transaction = self._prepare_transaction(invoice_litres=20, vehicle_odometer=1000)
		transaction.signed_order = None
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_public_invoice_or_order_attachment_is_rejected(self):
		for fieldname, kwargs in (
			("signed_invoice", {"invoice_private": False}),
			("signed_order", {"order_private": False}),
		):
			with self.subTest(fieldname=fieldname):
				transaction = self._prepare_transaction(invoice_litres=20, vehicle_odometer=1000)
				self._attach_files(transaction, **kwargs)
				with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
					transaction.submit()

	def test_unsupported_file_type_is_rejected(self):
		transaction = self._prepare_transaction(invoice_litres=20, vehicle_odometer=1000)
		self._attach_files(transaction, invoice_extension="txt")
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_oversize_file_is_rejected_using_actual_content_size(self):
		transaction = self._prepare_transaction(invoice_litres=20, vehicle_odometer=1000)
		self._attach_files(transaction)
		with patch(
			"fleet_management.fleet_management.doctype.fueling_transaction.fueling_transaction.get_max_file_size",
			return_value=1,
		):
			with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
				transaction.submit()

	def test_private_pdf_jpg_and_png_attachments_allow_submission_and_stay_linked(self):
		for extension in ("pdf", "jpg", "png"):
			with self.subTest(extension=extension):
				order = self._make_approved_order(self.location, self.station, self.user, self.approver)
				transaction = self._make_transaction(order)
				transaction.update(
					{
						"actual_fueling_datetime": get_datetime(order.approved_on) + timedelta(minutes=1),
						"fueling_time_source": "Printed on invoice",
						"invoice_litres": 20,
						"vehicle_odometer": 1000,
						"attendant_name": "Test Attendant",
					}
				)
				invoice, signed_order = self._attach_files(
					transaction, invoice_extension=extension, order_extension=extension
				)
				with self.set_user(self.user):
					transaction.submit()

				self.assertEqual(transaction.docstatus, 1)
				self.assertEqual(transaction.submitted_by, self.user)
				for fieldname, file_doc in (
					("signed_invoice", invoice),
					("signed_order", signed_order),
				):
					self.assertEqual(transaction.get(fieldname), file_doc.file_url)
					self.assertTrue(
						frappe.db.exists(
							"File",
							{
								"name": file_doc.name,
								"attached_to_doctype": "Fueling Transaction",
								"attached_to_name": transaction.name,
								"attached_to_field": fieldname,
							},
						)
					)

	def test_extension_requires_current_print_and_rejects_stale_signed_slip(self):
		order = self._make_approved_order(self.location, self.station, self.user, self.approver)
		with self.set_user(self.approver):
			order.extend_validity(
				(get_datetime(order.valid_until) + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
				"AC08 reprint enforcement",
			)

		stale_transaction = self._prepare_transaction(
			order,
			actual_fueling_datetime=now_datetime(),
			invoice_litres=20,
			vehicle_odometer=1000,
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			stale_transaction.submit()

		with self.set_user(self.approver):
			frappe.get_print(
				"Fuel Order", order.name, print_format="Fuel Order Approval Slip", no_letterhead=1
			)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			stale_transaction.submit()

		fresh_transaction = self._prepare_transaction(
			order,
			actual_fueling_datetime=now_datetime(),
			invoice_litres=20,
			vehicle_odometer=1000,
		)
		with self.set_user(self.user):
			fresh_transaction.submit()

		self.assertEqual(fresh_transaction.fuel_order_slip_revision, 2)

	def test_unapproved_fuel_order_cannot_be_submitted(self):
		with self.set_user(self.user):
			order = self._make_order(self.location, self.station).insert()
			transaction = self._make_transaction(order)
			self._attach_files(transaction)
			with self.assertRaises(frappe.ValidationError):
				transaction.submit()

	def test_location_permissions_filter_and_block_out_of_location_access(self):
		other_order = self._make_approved_order(
			self.other_location,
			self.other_station,
			self.other_user,
			self.other_approver,
			asset=self.other_asset,
		)
		north_transaction = self._make_transaction()
		self._attach_files(north_transaction)
		south_transaction = self._make_transaction(other_order, self.other_user)
		self._attach_files(south_transaction)

		with self.set_user(self.user):
			visible = {row.name for row in frappe.get_list("Fueling Transaction", fields=["name"])}
			self.assertIn(north_transaction.name, visible)
			self.assertNotIn(south_transaction.name, visible)
			self.assertTrue(frappe.has_permission("Fueling Transaction", "read", north_transaction))
			self.assertFalse(frappe.has_permission("Fueling Transaction", "read", south_transaction))
			self.assertTrue(frappe.has_permission("Fueling Transaction", "submit", north_transaction))
			self.assertFalse(frappe.has_permission("Fueling Transaction", "submit", south_transaction))
			with self.assertRaises(frappe.PermissionError):
				south_transaction.check_permission("read")
			with self.assertRaises(frappe.PermissionError):
				south_transaction.submit()
				with self.assertRaises(frappe.PermissionError):
					self._make_transaction(other_order, self.user)

	def test_draft_may_omit_fueling_time_but_submission_may_not(self):
		draft = self._make_transaction()
		self.assertFalse(draft.actual_fueling_datetime)
		self.assertFalse(draft.fueling_time_source)
		draft.save()

		transaction = self._prepare_transaction(actual_fueling_datetime=None)
		with self.set_user(self.user), self.assertRaisesRegex(
			frappe.ValidationError, "Actual fueling datetime is required before submission"
		):
			transaction.submit()

	def test_submission_requires_a_supported_fueling_time_source(self):
		transaction = self._prepare_transaction(fueling_time_source=None)
		with self.set_user(self.user), self.assertRaisesRegex(
			frappe.ValidationError, "Select whether the fueling time is printed on the invoice"
		):
			transaction.submit()

	def test_unprinted_fueling_time_requires_an_explanation(self):
		transaction = self._prepare_transaction(
			fueling_time_source="Not printed on invoice", fueling_time_explanation=" \t "
		)
		with self.set_user(self.user), self.assertRaisesRegex(
			frappe.ValidationError,
			"Explain the known station fueling time because it is not printed on the invoice",
		):
			transaction.submit()

	def test_submitted_time_source_and_station_time_are_preserved(self):
		for source, explanation in (
			("Printed on invoice", None),
			("Not printed on invoice", "Station attendant confirmed the pump time."),
		):
			with self.subTest(source=source):
				order = self._make_approved_order(
					self.location, self.station, self.user, self.approver
				)
				event_time = get_datetime(order.approved_on) + timedelta(minutes=1)
				transaction = self._submit_valid_transaction(
					order,
					actual_fueling_datetime=event_time,
					fueling_time_source=source,
					fueling_time_explanation=explanation,
				)
				self.assertEqual(get_datetime(transaction.actual_fueling_datetime), event_time)
				self.assertEqual(transaction.fueling_time_source, source)
				self.assertEqual(transaction.fueling_time_explanation, explanation)

	def test_submitted_fueling_time_facts_are_immutable(self):
		transaction = self._submit_valid_transaction(
			self.order,
			fueling_time_source="Not printed on invoice",
			fueling_time_explanation="Station attendant confirmed the pump time.",
		)
		changes = {
			"actual_fueling_datetime": get_datetime(transaction.actual_fueling_datetime)
			+ timedelta(minutes=1),
			"fueling_time_source": "Printed on invoice",
			"fueling_time_explanation": "Changed after submission.",
		}
		for fieldname, value in changes.items():
			with self.subTest(fieldname=fieldname):
				updated = frappe.get_doc("Fueling Transaction", transaction.name)
				updated.set(fieldname, value)
				with self.set_user(self.user), self.assertRaises(
					frappe.exceptions.UpdateAfterSubmitError
				):
					updated.save(ignore_permissions=True)

	def test_first_full_fill_is_baseline_and_second_creates_server_kpi(self):
		first = self._submit_measured_transaction(
			self.order,
			actual_fueling_datetime=get_datetime(self.order.approved_on) + timedelta(minutes=1),
			vehicle_odometer=10000,
			invoice_litres=60,
			full_tank_confirmed=1,
		)

		self.assertEqual(first.is_efficiency_baseline, 1)
		self.assertFalse(first.previous_full_fill)
		self.assertFalse(first.distance_km)
		self.assertFalse(first.qualifying_litres)
		self.assertFalse(first.km_per_litre)

		partial_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		partial = self._submit_measured_transaction(
			partial_order,
			actual_fueling_datetime=get_datetime(partial_order.approved_on) + timedelta(minutes=1),
			vehicle_odometer=10200,
			invoice_litres=10,
			full_tank_confirmed=0,
		)
		self.assertFalse(partial.km_per_litre)

		closing_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		closing = self._submit_measured_transaction(
			closing_order,
			actual_fueling_datetime=get_datetime(closing_order.approved_on) + timedelta(minutes=1),
			vehicle_odometer=10500,
			invoice_litres=40,
			full_tank_confirmed=1,
			distance_km=999,
			qualifying_litres=999,
			km_per_litre=999,
		)

		self.assertEqual(closing.is_efficiency_baseline, 0)
		self.assertEqual(closing.previous_full_fill, first.name)
		self.assertEqual(closing.closing_full_fill, closing.name)
		self.assertEqual(closing.distance_km, 500)
		self.assertEqual(closing.qualifying_litres, 50)
		self.assertEqual(closing.km_per_litre, 10)
		self.assertEqual(closing.vehicle_odometer, 10500)
		self.assertEqual(closing.invoice_litres, 40)

	def test_kpi_ordering_and_interval_litres_use_actual_fueling_time(self):
		closing_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		after_interval_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		inside_interval_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		baseline_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		first_event = get_datetime(now_datetime()) + timedelta(hours=1)

		# Create drafts in event-time-reverse order, then submit a later-event partial
		# before the closing full fill to distinguish event ordering from row order.
		closing = self._prepare_transaction(
			closing_order,
			actual_fueling_datetime=first_event + timedelta(hours=2),
			vehicle_odometer=10500,
			invoice_litres=40,
			full_tank_confirmed=1,
		)
		after_interval = self._prepare_transaction(
			after_interval_order,
			actual_fueling_datetime=first_event + timedelta(hours=3),
			vehicle_odometer=10400,
			invoice_litres=7,
			full_tank_confirmed=0,
		)
		inside_interval = self._prepare_transaction(
			inside_interval_order,
			actual_fueling_datetime=first_event + timedelta(hours=1),
			vehicle_odometer=10200,
			invoice_litres=10,
			full_tank_confirmed=0,
		)
		first = self._prepare_transaction(
			baseline_order,
			actual_fueling_datetime=first_event,
			vehicle_odometer=10000,
			invoice_litres=60,
			full_tank_confirmed=1,
		)

		for transaction in (first, inside_interval, after_interval, closing):
			with self.set_user(self.user):
				transaction.submit()

		self.assertLess(get_datetime(closing.creation), get_datetime(first.creation))
		self.assertGreater(
			get_datetime(after_interval.actual_fueling_datetime),
			get_datetime(closing.actual_fueling_datetime),
		)
		self.assertEqual(closing.previous_full_fill, first.name)
		self.assertEqual(closing.distance_km, 500)
		self.assertEqual(closing.qualifying_litres, 50)
		self.assertEqual(closing.km_per_litre, 10)

	def test_valid_submission_uses_order_snapshots_and_normalizes_identifiers(self):
		invoice_number = f" INV-42-{frappe.generate_hash(length=8)} "
		cu_number = f" CU-42-{frappe.generate_hash(length=8)} "
		transaction = self._submit_valid_transaction(
			self.order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			approved_station=self.other_station.name,
			approved_fuel_type=self.other_fuel_type.name,
			approved_on="2000-01-01 00:00:00",
			valid_until="2000-01-02 00:00:00",
			invoice_number=invoice_number,
			cu_number=cu_number,
			distance_km=999,
			qualifying_litres=999,
			km_per_litre=999,
		)

		self.assertEqual(transaction.actual_station, self.station.name)
		self.assertEqual(transaction.fuel_type, self.fuel_type.name)
		self.assertEqual(transaction.approved_station, self.station.name)
		self.assertEqual(transaction.approved_fuel_type, self.fuel_type.name)
		self.assertEqual(transaction.asset, self.asset.name)
		self.assertEqual(get_datetime(transaction.approved_on), get_datetime(self.order.approved_on))
		self.assertEqual(get_datetime(transaction.valid_until), get_datetime(self.order.valid_until))
		expected_invoice = "".join(character for character in invoice_number.casefold() if character.isalnum())
		expected_cu = "".join(character for character in cu_number.casefold() if character.isalnum())
		self.assertEqual(transaction.normalized_invoice_number, expected_invoice)
		self.assertEqual(
			transaction.normalized_invoice_station_key, f"{self.station.name}|{expected_invoice}"
		)
		self.assertEqual(transaction.normalized_cu_number, expected_cu)
		self.assertEqual(transaction.active_fuel_order, self.order.name)
		self.assertFalse(transaction.previous_full_fill)
		self.assertFalse(transaction.distance_km)

	def test_station_mismatch_is_rejected(self):
		transaction = self._prepare_transaction(
			actual_station=self.other_station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(self.order.approved_on) + timedelta(minutes=1),
			invoice_number="station-mismatch",
			cu_number="cu-station-mismatch",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_fuel_mismatch_is_rejected(self):
		transaction = self._prepare_transaction(
			actual_station=self.station.name,
			fuel_type=self.other_fuel_type.name,
			actual_fueling_datetime=get_datetime(self.order.approved_on) + timedelta(minutes=1),
			invoice_number="fuel-mismatch",
			cu_number="cu-fuel-mismatch",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_asset_mismatch_is_rejected(self):
		transaction = self._prepare_transaction(
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(self.order.approved_on) + timedelta(minutes=1),
			invoice_number="asset-mismatch",
			cu_number="cu-asset-mismatch",
		)
		transaction.asset = self.other_asset.name
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_fueling_outside_historical_validity_window_is_rejected(self):
		for suffix, fueling_datetime in (
			("before", get_datetime(self.order.approved_on) - timedelta(minutes=1)),
			("after", get_datetime(self.order.valid_until) + timedelta(minutes=1)),
		):
			with self.subTest(suffix=suffix):
				transaction = self._prepare_transaction(
					actual_station=self.station.name,
					fuel_type=self.fuel_type.name,
					actual_fueling_datetime=fueling_datetime,
					invoice_number=f"validity-{suffix}",
					cu_number=f"cu-validity-{suffix}",
				)
				with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
					transaction.submit()

	def test_vehicle_odometer_rollback_is_rejected(self):
		self._submit_valid_transaction(self.order, vehicle_odometer=1000)
		later_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		transaction = self._prepare_transaction(
			later_order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(later_order.approved_on) + timedelta(minutes=1),
			vehicle_odometer=999,
			invoice_number="vehicle-rollback",
			cu_number="cu-vehicle-rollback",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_generator_hour_meter_rollback_is_rejected(self):
		first_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver, asset=self.generator
		)
		self._submit_valid_transaction(first_order, hour_meter=100)
		later_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver, asset=self.generator
		)
		transaction = self._prepare_transaction(
			later_order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(later_order.approved_on) + timedelta(minutes=1),
			hour_meter=99,
			invoice_number="hour-meter-rollback",
			cu_number="cu-hour-meter-rollback",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_duplicate_normalized_invoice_number_is_rejected_per_station(self):
		identifier = frappe.generate_hash(length=8)
		self._submit_valid_transaction(
			self.order, invoice_number=f" INV-{identifier} ", cu_number=f"cu-invoice-{identifier}-1"
		)
		later_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		transaction = self._prepare_transaction(
			later_order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(later_order.approved_on) + timedelta(minutes=1),
			invoice_number=f"inv {identifier}",
			cu_number=f"cu-invoice-{identifier}-2",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_duplicate_normalized_cu_number_is_rejected_globally(self):
		identifier = frappe.generate_hash(length=8)
		self._submit_valid_transaction(
			self.order, invoice_number=f"cu-invoice-{identifier}-1", cu_number=f" CU-{identifier} "
		)
		later_order = self._make_approved_order(
			self.location, self.station, self.user, self.approver
		)
		transaction = self._prepare_transaction(
			later_order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(later_order.approved_on) + timedelta(minutes=1),
			invoice_number=f"cu-invoice-{identifier}-2",
			cu_number=f"cu {identifier}",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_submission_requires_fuel_attendant_name(self):
		for blank in ("", "   "):
			with self.subTest(attendant_name=blank):
				transaction = self._prepare_transaction(
					invoice_litres=20, vehicle_odometer=1000, attendant_name=blank
				)
				with self.set_user(self.user), self.assertRaisesRegex(
					frappe.ValidationError, "attendant name is required"
				):
					transaction.submit()

		submitted = self._submit_valid_transaction(attendant_name="  Jane Pump  ")
		self.assertEqual(submitted.attendant_name, "Jane Pump")

	def test_order_fulfillment_follows_its_active_transaction(self):
		def status():
			return frappe.get_doc("Fuel Order", self.order.name).fulfillment_status

		self.assertEqual(status(), "Awaiting Transaction")
		transaction = self._submit_valid_transaction(self.order)
		self.assertEqual(status(), "Completed")

		frappe.db.set_value(
			"Fuel Order", self.order.name, "valid_until", now_datetime() - timedelta(days=1),
			update_modified=False,
		)
		self.assertEqual(status(), "Completed")

		admin = self._user(("Fleet Admin",), self.location.name)
		with self.set_user(admin):
			frappe.get_doc("Fueling Transaction", transaction.name).cancel()
		self.assertEqual(status(), "Expired")

	def test_second_active_transaction_for_one_fuel_order_is_rejected(self):
		identifier = frappe.generate_hash(length=8)
		self._submit_valid_transaction(
			self.order, invoice_number=f"active-{identifier}-1", cu_number=f"cu-active-{identifier}-1"
		)
		transaction = self._prepare_transaction(
			self.order,
			actual_station=self.station.name,
			fuel_type=self.fuel_type.name,
			actual_fueling_datetime=get_datetime(self.order.approved_on) + timedelta(minutes=2),
			invoice_number=f"active-{identifier}-2",
			cu_number=f"cu-active-{identifier}-2",
		)
		with self.set_user(self.user), self.assertRaises(frappe.ValidationError):
			transaction.submit()

	def test_concurrent_submissions_wait_for_order_lock(self):
		assert_concurrency_site()

		missing_indexes = EXPECTED_UNIQUE_INDEXES - unique_index_names()
		self.assertFalse(missing_indexes, f"Missing unique indexes: {sorted(missing_indexes)}")
		self._concurrency_transaction_names = []
		frappe.db.commit()
		try:
			for run in range(3):
				identifier = frappe.generate_hash(length=8)
				transactions = []
				for worker in ("a", "b"):
					transaction = self._prepare_transaction(
						self.order,
						actual_station=self.station.name,
						fuel_type=self.fuel_type.name,
						vehicle_odometer=1000 + run,
						invoice_litres=20,
						invoice_number=f"concurrent-{identifier}-{worker}",
						cu_number=f"cu-concurrent-{identifier}-{worker}",
					)
					transactions.append(transaction)
					self._concurrency_transaction_names.append(transaction.name)
				frappe.db.commit()
				run_locked_order_overlap(
					self.order.name,
					transactions[0].name,
					transactions[1].name,
					self.user,
				)
				self._cleanup_concurrency_transactions([doc.name for doc in transactions])
				frappe.db.commit()
		finally:
			self._cleanup_concurrency_test_records()
			frappe.db.commit()

	def _cleanup_concurrency_transactions(self, transaction_names):
		files = []
		for name in transaction_names:
			files.extend(
				row.name
				for row in frappe.get_all(
					"File",
					filters={
						"attached_to_doctype": "Fueling Transaction",
						"attached_to_name": name,
					},
					fields=["name"],
				)
			)
			self._delete_concurrency_doc("Fueling Transaction", name)
		for file_name in files:
			self._delete_concurrency_doc("File", file_name)

	def _delete_concurrency_doc(self, doctype, name):
		if not name or not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)

	def _cleanup_concurrency_test_records(self):
		frappe.set_user("Administrator")
		transaction_names = getattr(self, "_concurrency_transaction_names", [])
		self._cleanup_concurrency_transactions(transaction_names)
		references = [("Fuel Order", self.order.name)]
		references.extend(("Fueling Transaction", name) for name in transaction_names)
		for reference_doctype, reference_name in references:
			for row in frappe.get_all(
				"Comment",
				filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
				fields=["name"],
			):
				self._delete_concurrency_doc("Comment", row.name)

		for doctype, name in [
			("Fuel Order", self.order.name),
			("Fleet Asset", self.generator.name),
			("Fleet Asset", self.other_asset.name),
			("Fleet Asset", self.asset.name),
			("Fuel Station", self.other_station.name),
			("Fuel Station", self.station.name),
			("Fleet Person", self.person.name),
			("Fuel Type", self.other_fuel_type.name),
			("Fuel Type", self.fuel_type.name),
			("Fleet Location", self.other_location.name),
			("Fleet Location", self.location.name),
		]:
			self._delete_concurrency_doc(doctype, name)

		users = (self.user, self.approver, self.other_user, self.other_approver)
		for row in frappe.get_all(
			"User Permission", filters={"user": ["in", users]}, fields=["name"]
		):
			self._delete_concurrency_doc("User Permission", row.name)
		for user in users:
			self._delete_concurrency_doc("User", user)
