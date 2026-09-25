import frappe
from frappe.utils import flt


def execute():
	"""Move existing vehicle capacities onto linked Vehicle Model records."""
	if not frappe.db.table_exists("Fleet Asset") or not frappe.db.has_column(
		"Fleet Asset", "tank_capacity_litres"
	):
		return

	assets = frappe.db.sql(
		"""
		SELECT name, vehicle_model, tank_capacity_litres
		FROM `tabFleet Asset`
		WHERE asset_type = 'Vehicle'
			AND tank_capacity_litres IS NOT NULL
			AND tank_capacity_litres > 0
		""",
		as_dict=True,
	)

	for asset in assets:
		capacity = flt(asset.tank_capacity_litres)
		if asset.vehicle_model:
			model_capacity = frappe.db.get_value(
				"Vehicle Model", asset.vehicle_model, "tank_capacity_litres"
			)
			if model_capacity not in (None, "", 0) and flt(model_capacity) != capacity:
				frappe.throw(
					frappe._(
						"Vehicle Model {0} has tank capacity {1}, but asset {2} has {3}."
					).format(asset.vehicle_model, model_capacity, asset.name, capacity)
				)
			if model_capacity in (None, "", 0):
				frappe.db.set_value(
					"Vehicle Model",
					asset.vehicle_model,
					"tank_capacity_litres",
					capacity,
					update_modified=False,
				)
			continue

		model_label = f"Capacity {capacity:g} L"
		model_name = frappe.db.get_value(
			"Vehicle Model", {"make": "Legacy", "model": model_label}, "name"
		)
		if not model_name:
			model_name = frappe.get_doc(
				{
					"doctype": "Vehicle Model",
					"make": "Legacy",
					"model": model_label,
					"tank_capacity_litres": capacity,
				}
			).insert(ignore_permissions=True).name

		frappe.db.set_value(
			"Fleet Asset", asset.name, "vehicle_model", model_name, update_modified=False
		)
