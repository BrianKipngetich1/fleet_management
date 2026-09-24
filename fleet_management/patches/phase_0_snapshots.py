import frappe

from fleet_management.fleet_management.doctype.fleet_asset.fleet_asset import (
	get_assignment_snapshot,
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


def execute():
	"""Backfill immutable Phase 0 snapshots where historical assignments permit it."""
	for order in frappe.get_all(
		"Fuel Order",
		fields=["name", "slip_revision", "printed_slip_revision", "reprint_required"],
	):
		updates = {}
		if not order.slip_revision:
			updates["slip_revision"] = 1
		if order.reprint_required:
			updates["printed_slip_revision"] = order.printed_slip_revision or 0
		elif not order.printed_slip_revision:
			updates["printed_slip_revision"] = order.slip_revision or 1
		if updates:
			frappe.db.set_value("Fuel Order", order.name, updates, update_modified=False)

	for order in frappe.get_all(
		"Fuel Order", fields=["name", "asset", "request_datetime"]
	):
		snapshot = get_assignment_snapshot(order.asset, order.request_datetime)
		if snapshot:
			frappe.db.set_value(
				"Fuel Order",
				order.name,
				snapshot,
				update_modified=False,
			)

	for transaction in frappe.get_all("Fueling Transaction", fields=["name", "fuel_order"]):
		order = frappe.db.get_value(
			"Fuel Order",
			transaction.fuel_order,
			SNAPSHOT_FIELDS,
			as_dict=True,
		)
		if order and all(
			fieldname == "assignment_effective_until" or order.get(fieldname) not in (None, "")
			for fieldname in SNAPSHOT_FIELDS
		):
			frappe.db.set_value(
				"Fueling Transaction",
				transaction.name,
				{fieldname: order.get(fieldname) for fieldname in SNAPSHOT_FIELDS},
				update_modified=False,
			)
