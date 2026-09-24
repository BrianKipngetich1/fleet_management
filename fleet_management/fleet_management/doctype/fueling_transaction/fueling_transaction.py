from pathlib import Path

import filetype
import frappe
from frappe.core.api.file import get_max_file_size
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime


ALLOWED_EVIDENCE_TYPES = {
	".pdf": "application/pdf",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".png": "image/png",
}
EVIDENCE_FIELDS = (
	("signed_invoice", "Signed invoice"),
	("signed_order", "Signed Fuel Order"),
)
SNAPSHOT_FIELDS = (
	"assigned_location_snapshot",
	"assigned_custodian_snapshot",
	"assignment_effective_from",
	"assignment_effective_until",
	"asset_fuel_type_snapshot",
	"asset_tank_capacity_snapshot",
	"asset_target_km_per_litre_snapshot",
	"asset_tolerance_percent_snapshot",
)
KPI_FIELDS = (
	"previous_full_fill",
	"closing_full_fill",
	"distance_km",
	"qualifying_litres",
	"km_per_litre",
)


def normalize_identifier(value):
	"""Normalize invoice/CU identifiers for duplicate checks."""
	return "".join(character for character in str(value or "").casefold() if character.isalnum())


def on_doctype_update():
	for fieldname, constraint_name in (
		("normalized_invoice_station_key", "unique_fueling_invoice_station"),
		("normalized_cu_number", "unique_fueling_cu_number"),
		("active_fuel_order", "unique_active_fueling_order"),
	):
		frappe.db.add_unique("Fueling Transaction", [fieldname], constraint_name=constraint_name)


def calculate_vehicle_interval(previous_odometer, current_odometer, qualifying_litres):
	"""Return the server-derived vehicle interval values."""
	try:
		previous_odometer = float(previous_odometer)
		current_odometer = float(current_odometer)
		qualifying_litres = float(qualifying_litres)
	except (TypeError, ValueError) as error:
		raise ValueError("Vehicle interval readings must be numeric") from error

	distance_km = current_odometer - previous_odometer
	if distance_km <= 0:
		raise ValueError("Vehicle interval distance must be positive")
	if qualifying_litres <= 0:
		raise ValueError("Vehicle interval litres must be positive")

	return {
		"distance_km": distance_km,
		"qualifying_litres": qualifying_litres,
		"km_per_litre": distance_km / qualifying_litres,
	}


class FuelingTransaction(Document):
	def before_validate(self):
		self._set_location_from_order()

	def validate(self):
		self._validate_submitted_immutability()

	def before_submit(self):
		if not {"Fleet User", "Fleet Admin"}.intersection(frappe.get_roles()):
			frappe.throw(
				frappe._("Only Fleet Users and Fleet Admins can submit Fueling Transactions."),
				frappe.PermissionError,
			)
		order = self._get_order(for_update=True)
		if order.docstatus != 1 or order.workflow_state != "Approved":
			frappe.throw(
				frappe._("Fueling Transactions can only be submitted for an approved Fuel Order."),
				frappe.ValidationError,
			)

		self._set_order_snapshots(order)
		self._validate_submission_facts(order)
		self._validate_measured_values()
		self._validate_meter_progression()
		self._validate_no_active_transaction()
		self._prepare_unique_keys(order)
		self._validate_evidence(order)
		self._prepare_vehicle_efficiency()
		self.submitted_by = frappe.session.user
		self.submitted_on = now_datetime()

	def _get_order(self, for_update=False):
		if not self.fuel_order:
			frappe.throw(frappe._("Fuel Order is required."), frappe.ValidationError)

		return frappe.get_doc("Fuel Order", self.fuel_order, for_update=for_update)

	def _set_location_from_order(self):
		if not self.fuel_order:
			return

		self._set_order_snapshots(self._get_order())

	def _set_order_snapshots(self, order=None):
		order = order or self._get_order()
		if self.asset and self.asset != order.asset:
			frappe.throw(
				frappe._("Asset must match the approved Fuel Order."), frappe.ValidationError
			)

		self.operational_location = order.operational_location
		self.asset = order.asset
		self.fuel_order_slip_revision = order.slip_revision
		self.approved_station = order.planned_station
		self.approved_fuel_type = order.fuel_type
		self.approved_on = order.approved_on
		self.valid_until = order.valid_until
		for fieldname in SNAPSHOT_FIELDS:
			self.set(fieldname, order.get(fieldname))

		if any(
			fieldname != "assignment_effective_until"
			and self.get(fieldname) in (None, "")
			for fieldname in SNAPSHOT_FIELDS
		):
			frappe.throw(
				frappe._("Fuel Order assignment and asset snapshots are required."),
				frappe.ValidationError,
			)

		if not self.flags.ignore_permissions and not frappe.has_permission("Fuel Order", "read", order):
			frappe.throw(
				frappe._("You do not have access to the linked Fuel Order."), frappe.PermissionError
			)

	def _validate_submission_facts(self, order):
		if (
			cint(order.reprint_required)
			or cint(order.printed_slip_revision) != cint(order.slip_revision)
		):
			frappe.throw(
				frappe._("The current Fuel Order approval slip must be printed before fueling."),
				frappe.ValidationError,
			)

		for fieldname in ("actual_station", "station"):
			value = self.get(fieldname)
			if value and value != order.planned_station:
				frappe.throw(
					frappe._("Actual station must match the approved Fuel Order station."),
					frappe.ValidationError,
				)
		self.actual_station = order.planned_station

		for fieldname in ("fuel_type", "actual_fuel_type", "fuel"):
			value = self.get(fieldname)
			if value and value != order.fuel_type:
				frappe.throw(
					frappe._("Fuel type must match the approved Fuel Order."), frappe.ValidationError
				)
		self.fuel_type = order.fuel_type
		asset_fuel_type = frappe.db.get_value("Fleet Asset", order.asset, "fuel_type")
		if asset_fuel_type != order.fuel_type or order.asset_fuel_type_snapshot != order.fuel_type:
			frappe.throw(
				frappe._("Fuel type must match the Fleet Asset and approved Fuel Order."),
				frappe.ValidationError,
			)

		if self.fueling_time_source not in {"Printed on invoice", "Not printed on invoice"}:
			frappe.throw(
				frappe._("Select whether the fueling time is printed on the invoice."),
				frappe.ValidationError,
			)
		if self.fueling_time_source == "Not printed on invoice" and not str(
			self.fueling_time_explanation or ""
		).strip():
			frappe.throw(
				frappe._("Explain the known station fueling time because it is not printed on the invoice."),
				frappe.ValidationError,
			)
		if not self.actual_fueling_datetime:
			frappe.throw(
				frappe._("Actual fueling datetime is required before submission."),
				frappe.ValidationError,
			)

		try:
			actual_fueling_datetime = get_datetime(self.actual_fueling_datetime)
			approved_on = get_datetime(order.approved_on)
			valid_until = get_datetime(order.valid_until)
		except (TypeError, ValueError) as error:
			raise frappe.ValidationError(
				frappe._("Actual fueling datetime and Fuel Order validity timestamps must be valid.")
			) from error

		if not approved_on or not valid_until:
			frappe.throw(
				frappe._("Approved Fuel Order validity timestamps are required."),
				frappe.ValidationError,
			)
		if actual_fueling_datetime < approved_on or actual_fueling_datetime > valid_until:
			frappe.throw(
				frappe._("Actual fueling datetime must be within the approved Fuel Order validity window."),
				frappe.ValidationError,
			)

		self.actual_fueling_datetime = actual_fueling_datetime

	def _validate_measured_values(self):
		if flt(self.invoice_litres) <= 0:
			frappe.throw(frappe._("Invoice litres must be positive."), frappe.ValidationError)

		self.attendant_name = str(self.attendant_name or "").strip()
		if not self.attendant_name:
			frappe.throw(
				frappe._("Fuel attendant name is required before submission."),
				frappe.ValidationError,
			)

		asset_type = frappe.db.get_value("Fleet Asset", self.asset, "asset_type")
		meter_field = {"Vehicle": "vehicle_odometer", "Generator": "hour_meter"}.get(asset_type)
		if meter_field and self.get(meter_field) in (None, ""):
			frappe.throw(
				frappe._("{0} is required for this asset.").format(
					"Vehicle odometer" if meter_field == "vehicle_odometer" else "Hour-meter"
				),
				frappe.ValidationError,
			)

	def _validate_submitted_immutability(self):
		previous = getattr(self, "_doc_before_save", None)
		if not previous or previous.docstatus != 1:
			return

		for fieldname in (
			"fuel_order",
			"fuel_order_slip_revision",
			"operational_location",
			"asset",
			"actual_station",
			"fuel_type",
			"actual_fueling_datetime",
			"fueling_time_source",
			"fueling_time_explanation",
			"approved_station",
			"approved_fuel_type",
			"attendant_name",
			*SNAPSHOT_FIELDS,
		):
			if self.get(fieldname) != previous.get(fieldname):
				frappe.throw(
					frappe._("Submitted Fueling Transactions are immutable."),
					frappe.ValidationError,
				)

	def _validate_meter_progression(self):
		if not self.asset:
			return

		asset_type = frappe.db.get_value("Fleet Asset", self.asset, "asset_type")
		meter_field = {"Vehicle": "vehicle_odometer", "Generator": "hour_meter"}.get(asset_type)
		if not meter_field or self.get(meter_field) in (None, ""):
			return

		current_reading = flt(self.get(meter_field))
		previous_readings = frappe.db.get_all(
			"Fueling Transaction",
			filters={"docstatus": 1, "asset": self.asset, "name": ["!=", self.name]},
			fields=[meter_field],
		)
		previous_readings = [
			flt(row.get(meter_field))
			for row in previous_readings
			if row.get(meter_field) is not None
		]
		if previous_readings and current_reading < max(previous_readings):
			frappe.throw(
				frappe._("{0} cannot be lower than a previous submitted reading.").format(
					"Odometer" if meter_field == "vehicle_odometer" else "Hour-meter"
				),
				frappe.ValidationError,
			)

	def _validate_no_active_transaction(self):
		existing = frappe.db.get_value(
			"Fueling Transaction",
			{
				"fuel_order": self.fuel_order,
				"docstatus": 1,
				"name": ["!=", self.name],
			},
			"name",
		)
		if existing:
			frappe.throw(
				frappe._("Fuel Order {0} already has an active Fueling Transaction.").format(
					self.fuel_order
				),
				frappe.ValidationError,
			)

		self.active_fuel_order = self.fuel_order

	def _prepare_unique_keys(self, order):
		invoice_number = normalize_identifier(self.invoice_number)
		if invoice_number:
			invoice_key = f"{order.planned_station}|{invoice_number}"
			existing = frappe.db.get_value(
				"Fueling Transaction",
				{
					"normalized_invoice_station_key": invoice_key,
					"docstatus": 1,
					"name": ["!=", self.name],
				},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._("Invoice number already exists for this Fuel Station."),
					frappe.ValidationError,
				)
			self.normalized_invoice_number = invoice_number
			self.normalized_invoice_station_key = invoice_key
		else:
			self.normalized_invoice_number = None
			self.normalized_invoice_station_key = None

		cu_number = normalize_identifier(self.cu_number)
		if cu_number:
			existing = frappe.db.get_value(
				"Fueling Transaction",
				{
					"normalized_cu_number": cu_number,
					"docstatus": 1,
					"name": ["!=", self.name],
				},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._("CU number already exists on a submitted Fueling Transaction."),
					frappe.ValidationError,
				)
			self.normalized_cu_number = cu_number
		else:
			self.normalized_cu_number = None

	def _prepare_vehicle_efficiency(self):
		self.is_efficiency_baseline = 0
		for fieldname in KPI_FIELDS:
			self.set(fieldname, None)

		if not self._is_qualifying_full_fill():
			return

		previous = self._find_previous_full_fill()
		if not previous:
			self.is_efficiency_baseline = 1
			return

		qualifying_litres = self._interval_litres(previous)
		try:
			calculation = calculate_vehicle_interval(
				previous.vehicle_odometer,
				self.vehicle_odometer,
				qualifying_litres,
			)
		except ValueError:
			return

		self.update(
			{
				"previous_full_fill": previous.name,
				"closing_full_fill": self.name,
				**calculation,
			}
		)

	def _is_qualifying_full_fill(self):
		if not self.asset or not cint(self.full_tank_confirmed):
			return False

		asset_type = frappe.db.get_value("Fleet Asset", self.asset, "asset_type")
		return (
			asset_type == "Vehicle"
			and bool(self.actual_fueling_datetime)
			and self.vehicle_odometer is not None
			and flt(self.invoice_litres) > 0
		)

	def _find_previous_full_fill(self):
		current_key = self._source_key(self)
		previous = [
			row
			for row in self._submitted_vehicle_transactions()
			if self._is_full_fill_row(row) and self._source_key(row) < current_key
		]
		return max(previous, key=self._source_key) if previous else None

	def _interval_litres(self, previous):
		previous_key = self._source_key(previous)
		current_key = self._source_key(self)
		rows = self._submitted_vehicle_transactions()
		rows.append(
			frappe._dict(
				name=self.name,
				actual_fueling_datetime=self.actual_fueling_datetime,
				invoice_litres=self.invoice_litres,
			)
		)

		return sum(
			flt(row.invoice_litres)
			for row in rows
			if self._has_fueling_source(row)
			and previous_key < self._source_key(row) <= current_key
		)

	def _submitted_vehicle_transactions(self):
		return frappe.db.get_all(
			"Fueling Transaction",
			filters={"docstatus": 1, "asset": self.asset},
			fields=[
				"name",
				"actual_fueling_datetime",
				"vehicle_odometer",
				"invoice_litres",
				"full_tank_confirmed",
			],
		)

	@staticmethod
	def _source_key(row):
		return (get_datetime(row.actual_fueling_datetime), str(row.name))

	@staticmethod
	def _has_fueling_source(row):
		return bool(row.actual_fueling_datetime) and flt(row.invoice_litres) > 0

	@classmethod
	def _is_full_fill_row(cls, row):
		return (
			cint(row.full_tank_confirmed)
			and cls._has_fueling_source(row)
			and row.vehicle_odometer is not None
		)

	def _validate_evidence(self, order=None):
		for fieldname, label in EVIDENCE_FIELDS:
			file_doc = self._resolve_file(fieldname, label)
			self._validate_file(file_doc, label)
			if fieldname == "signed_order" and order and cint(order.slip_revision) > 1:
				printed_on = get_datetime(order.last_slip_printed_on)
				file_created = get_datetime(file_doc.creation)
				if not printed_on or not file_created or file_created < printed_on:
					frappe.throw(
						frappe._(
							"The signed Fuel Order attachment must be uploaded after the current slip is printed."
						),
						frappe.ValidationError,
					)

	def _resolve_file(self, fieldname, label):
		value = self.get(fieldname)
		if not value:
			frappe.throw(
				frappe._("{0} attachment is required before submission.").format(label),
				frappe.ValidationError,
			)

		file_url = value.split("?", 1)[0]
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": file_url,
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"attached_to_field": fieldname,
				"is_folder": 0,
			},
			"name",
		)
		if not file_name:
			frappe.throw(
				frappe._("{0} must resolve to a File attached to this transaction.").format(label),
				frappe.ValidationError,
			)

		return frappe.get_doc("File", file_name)

	def _validate_file(self, file_doc, label):
		if not file_doc.is_private or not (file_doc.file_url or "").startswith("/private/files/"):
			frappe.throw(
				frappe._("{0} must be a private attachment.").format(label), frappe.ValidationError
			)

		extension = Path(file_doc.file_name or "").suffix.lower()
		expected_mime = ALLOWED_EVIDENCE_TYPES.get(extension)
		if not expected_mime:
			frappe.throw(
				frappe._("{0} must be a PDF, JPG, or PNG file.").format(label), frappe.ValidationError
			)

		try:
			content = file_doc.get_content(encodings=())
		except (OSError, frappe.ValidationError):
			frappe.throw(
				frappe._("{0} could not be read as a valid attachment.").format(label),
				frappe.ValidationError,
			)

		if isinstance(content, str):
			content = content.encode()
		if not isinstance(content, bytes):
			content = bytes(content)

		if len(content) > get_max_file_size():
			frappe.throw(
				frappe._("{0} exceeds the maximum permitted file size.").format(label),
				frappe.ValidationError,
			)

		if filetype.guess_mime(content) != expected_mime:
			frappe.throw(
				frappe._("{0} does not contain a valid {1} file.").format(label, extension.lstrip(".")),
				frappe.ValidationError,
			)
