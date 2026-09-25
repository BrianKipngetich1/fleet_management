import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime


def get_effective_assignment(asset, at=None):
	"""Return the one assignment effective on the requested date."""
	if not asset:
		return None

	if isinstance(asset, str):
		asset = frappe.get_doc("Fleet Asset", asset)

	effective_on = getdate(get_datetime(at or now_datetime()))
	matches = []
	for assignment in asset.get("assignments") or []:
		start = getdate(assignment.effective_from) if assignment.effective_from else None
		end = getdate(assignment.effective_until) if assignment.effective_until else None
		if start and start <= effective_on and (not end or effective_on <= end):
			matches.append(assignment)

	return matches[0] if len(matches) == 1 else None


def get_assignment_snapshot(asset, at=None):
	"""Return immutable order/transaction facts for the effective assignment."""
	if isinstance(asset, str):
		asset = frappe.get_doc("Fleet Asset", asset)

	assignment = get_effective_assignment(asset, at)
	if not assignment:
		return None

	default_tolerance = frappe.db.get_single_value(
		"Fleet Management Settings", "default_tolerance_percent"
	)
	if default_tolerance in (None, ""):
		default_tolerance = 2
	return {
		"assigned_location_snapshot": assignment.assigned_location,
		"assigned_custodian_snapshot": assignment.custodian,
		"assignment_effective_from": assignment.effective_from,
		"assignment_effective_until": assignment.effective_until,
		"asset_fuel_type_snapshot": asset.fuel_type,
		"asset_tank_capacity_snapshot": get_vehicle_model_tank_capacity(asset),
		"asset_target_km_per_litre_snapshot": asset.target_km_per_litre,
		"asset_tolerance_percent_snapshot": (
			asset.tolerance_percent
			if asset.tolerance_percent not in (None, "", 0)
			else default_tolerance
		),
	}


def get_vehicle_model_tank_capacity(asset):
	if asset.get("asset_type") != "Vehicle" or not asset.get("vehicle_model"):
		return None
	return frappe.db.get_value("Vehicle Model", asset.vehicle_model, "tank_capacity_litres")


class FleetAsset(Document):
	def validate(self):
		self.validate_vehicle_model()
		self.validate_assignments()

	def validate_vehicle_model(self):
		if self.asset_type == "Vehicle" and not self.vehicle_model:
			frappe.throw(frappe._("Vehicle assets must reference a Vehicle Model."))

	def validate_assignments(self):
		periods = []
		for assignment in self.assignments or []:
			start = getdate(assignment.effective_from) if assignment.effective_from else None
			end = getdate(assignment.effective_until) if assignment.effective_until else None

			if not start:
				frappe.throw(frappe._("Assignment {0} needs an effective-from date.").format(assignment.idx))
			if end and end < start:
				frappe.throw(
					frappe._("Assignment {0} cannot end before it starts.").format(assignment.idx)
				)

			periods.append((start, end, assignment.idx))

		periods.sort(key=lambda period: period[0])
		for previous, current in zip(periods, periods[1:]):
			previous_end = previous[1]
			if previous_end is None or current[0] <= previous_end:
				frappe.throw(
					frappe._("Assignment periods {0} and {1} overlap.").format(previous[2], current[2])
				)
