import frappe


def execute():
	"""Backfill the fetched asset type on Fuel Orders created before the field existed."""
	for order in frappe.get_all("Fuel Order", filters={"asset_type": ["is", "not set"]}, fields=["name", "asset"]):
		asset_type = frappe.db.get_value("Fleet Asset", order.asset, "asset_type") if order.asset else None
		if asset_type:
			frappe.db.set_value("Fuel Order", order.name, "asset_type", asset_type, update_modified=False)
