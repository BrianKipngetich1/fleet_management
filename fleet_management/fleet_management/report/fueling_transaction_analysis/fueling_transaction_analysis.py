from datetime import timedelta
from decimal import Decimal

import frappe
from frappe.utils import flt, get_datetime, getdate

PAGE_SIZE = 500
VARIANCE_TOLERANCE = Decimal("15")


def execute(filters=None):
	frappe.has_permission("Fueling Transaction", "report", throw=True)
	filters = frappe._dict(filters or {})
	query_filters = _transaction_filters(filters)
	transactions = _get_list(
		"Fueling Transaction",
		[
			"name",
			"fuel_order",
			"asset",
			"assigned_location_snapshot",
			"actual_fueling_datetime",
			"actual_station",
			"fuel_type",
			"invoice_litres",
			"vehicle_odometer",
			"hour_meter",
			"full_tank_confirmed",
			"pre_tax_amount",
			"km_per_litre",
			"is_efficiency_baseline",
		],
		filters=query_filters,
		order_by="actual_fueling_datetime asc, name asc",
	)

	assets = _linked_records("Fleet Asset", {row.asset for row in transactions if row.asset}, ["asset_identifier", "asset_type"])
	orders = _linked_records(
		"Fuel Order",
		{row.fuel_order for row in transactions if row.fuel_order},
		["quantity_authorization", "authorized_quantity_litres", "estimated_litres"],
	)
	generator_assets = {
		row.asset
		for row in transactions
		if row.asset and assets.get(row.asset, {}).get("asset_type") == "Generator"
	}
	generator_intervals = _generator_intervals(generator_assets)

	data = []
	for row in transactions:
		asset = assets.get(row.asset, {})
		order = orders.get(row.fuel_order, {})
		asset_type = asset.get("asset_type")
		baseline = _lpo_baseline(order, asset_type)
		variance_litres, variance_percent, variance_status = calculate_litre_variance(
			row.invoice_litres, baseline
		)
		amount = flt(row.pre_tax_amount)
		cost_recorded = amount > 0
		litres = flt(row.invoice_litres)
		interval = generator_intervals.get(row.name, {})
		vehicle_efficiency = (
			flt(row.km_per_litre)
			if asset_type == "Vehicle" and row.full_tank_confirmed and not row.is_efficiency_baseline
			else 0
		)
		data.append(
			{
				"transaction": row.name,
				"fuel_order": row.fuel_order,
				"asset": row.asset,
				"asset_type": asset_type,
				"location": row.assigned_location_snapshot,
				"actual_fueling_datetime": row.actual_fueling_datetime,
				"station": row.actual_station,
				"fuel_type": row.fuel_type,
				"approved_authorization": order.get("quantity_authorization") or "Not recorded",
				"lpo_baseline_litres": baseline,
				"actual_litres": litres,
				"variance_litres": variance_litres,
				"variance_percent": variance_percent,
				"variance_status": variance_status,
				"meter_type": "Odometer (km)" if asset_type == "Vehicle" else "Hour meter (h)",
				"meter_reading": row.vehicle_odometer if asset_type == "Vehicle" else row.hour_meter,
				"full_tank_confirmed": bool(row.full_tank_confirmed),
				"full_tank_exception": _full_tank_exception(row, asset_type, interval),
				"pre_tax_amount": round(amount, 2) if cost_recorded else None,
				"cost_status": "Recorded" if cost_recorded else "Not recorded",
				"pre_tax_cost_per_litre": round(amount / litres, 4) if cost_recorded and litres > 0 else None,
				"vehicle_km_per_litre": vehicle_efficiency if vehicle_efficiency > 0 else None,
				"generator_litres_per_hour": interval.get("litres_per_hour"),
			}
		)

	return _columns(), data, None, None, _summary(data), True


def calculate_litre_variance(actual_litres, baseline_litres):
	"""Return variance litres, percent, and the approved colour status."""
	actual = Decimal(str(actual_litres or 0))
	baseline = Decimal(str(baseline_litres or 0))
	if actual <= 0 or baseline <= 0:
		return None, None, "No comparison available"

	variance = actual - baseline
	percent = variance * Decimal("100") / baseline
	if variance <= 0:
		status = "Within baseline"
	elif percent <= VARIANCE_TOLERANCE:
		status = "Above baseline (0–15%)"
	else:
		status = "Overrun (>15%)"
	return round(float(variance), 2), round(float(percent), 2), status


def calculate_generator_intervals(rows):
	"""Return per-closing-full-tank generator efficiency and reasons when unavailable."""
	result = {}
	previous = None
	for closing in sorted(rows, key=_source_key):
		if not closing.get("full_tank_confirmed") or not _has_fueling_source(closing):
			continue

		if previous is None:
			result[closing.name] = {"exception": "No previous confirmed full tank"}
			previous = closing
			continue

		start_hours = previous.get("hour_meter")
		end_hours = closing.get("hour_meter")
		if start_hours is None or end_hours is None:
			result[closing.name] = {"exception": "Full-tank hour-meter reading is missing"}
		elif flt(end_hours) <= flt(start_hours):
			result[closing.name] = {"exception": "Hour meter did not increase between full tanks"}
		else:
			start_key = _source_key(previous)
			end_key = _source_key(closing)
			litres = sum(
				flt(row.get("invoice_litres"))
				for row in rows
				if _has_fueling_source(row) and start_key < _source_key(row) <= end_key
			)
			result[closing.name] = {
				"litres_per_hour": round(litres / (flt(end_hours) - flt(start_hours)), 4)
			}
		previous = closing
	return result


def _transaction_filters(filters):
	conditions = [["docstatus", "=", 1]]
	from_date = _date_filter(filters.get("from_date"), "From Date")
	to_date = _date_filter(filters.get("to_date"), "To Date")
	if from_date and to_date and to_date < from_date:
		frappe.throw(frappe._("From Date must be on or before To Date."), frappe.ValidationError)
	if from_date:
		conditions.append(["actual_fueling_datetime", ">=", get_datetime(from_date)])
	if to_date:
		conditions.append(["actual_fueling_datetime", "<", get_datetime(to_date) + timedelta(days=1)])
	for filter_name, fieldname in (
		("asset", "asset"),
		("location", "assigned_location_snapshot"),
		("fuel_type", "fuel_type"),
		("station", "actual_station"),
	):
		if filters.get(filter_name):
			conditions.append([fieldname, "=", filters[filter_name]])
	return conditions


def _date_filter(value, label):
	if not value:
		return None
	try:
		return getdate(value)
	except (TypeError, ValueError):
		frappe.throw(frappe._("{0} must be a valid date.").format(label), frappe.ValidationError)


def _lpo_baseline(order, asset_type):
	fieldname = {
		"Vehicle": "estimated_litres",
		"Generator": "authorized_quantity_litres",
	}.get(asset_type)
	if not fieldname:
		return None
	value = flt(order.get(fieldname)) if order else 0
	return value if value > 0 else None


def _generator_intervals(asset_names):
	intervals = {}
	for names in _chunks(asset_names):
		rows = _get_list(
			"Fueling Transaction",
			["name", "asset", "actual_fueling_datetime", "invoice_litres", "hour_meter", "full_tank_confirmed"],
			filters={"docstatus": 1, "asset": ["in", names]},
			order_by="actual_fueling_datetime asc, name asc",
		)
		for asset in names:
			intervals.update(calculate_generator_intervals([row for row in rows if row.asset == asset]))
	return intervals


def _full_tank_exception(row, asset_type, interval):
	if not row.full_tank_confirmed:
		return None
	if asset_type == "Generator":
		return interval.get("exception")
	if asset_type == "Vehicle" and not row.is_efficiency_baseline and flt(row.km_per_litre) <= 0:
		return "Vehicle efficiency interval could not be calculated"
	return None


def _source_key(row):
	return (get_datetime(row.get("actual_fueling_datetime")), str(row.get("name") or ""))


def _has_fueling_source(row):
	return bool(row.get("actual_fueling_datetime")) and flt(row.get("invoice_litres")) > 0


def _summary(data):
	total_litres = sum(flt(row["actual_litres"]) for row in data)
	priced_rows = [row for row in data if row["cost_status"] == "Recorded"]
	pre_tax_spend = sum(flt(row["pre_tax_amount"]) for row in priced_rows)
	priced_litres = sum(flt(row["actual_litres"]) for row in priced_rows)
	return [
		{"label": "Total Litres", "value": round(total_litres, 2), "datatype": "Float"},
		{
			"label": "Recorded Pre-Tax Spend (KES)",
			"value": round(pre_tax_spend, 2),
			"datatype": "Currency",
			"currency": "KES",
		},
		{
			"label": "Pre-Tax Cost per Litre (recorded-cost rows)",
			"value": round(pre_tax_spend / priced_litres, 4) if priced_litres else 0,
			"datatype": "Currency",
			"currency": "KES",
		},
		{"label": "Litres with Recorded Cost", "value": round(priced_litres, 2), "datatype": "Float"},
		{
			"label": "Transactions without Recorded Cost",
			"value": len(data) - len(priced_rows),
			"datatype": "Int",
		},
	]


def _columns():
	return [
		{"fieldname": "transaction", "label": "Transaction", "fieldtype": "Link", "options": "Fueling Transaction", "width": 150},
		{"fieldname": "fuel_order", "label": "Fuel Order", "fieldtype": "Link", "options": "Fuel Order", "width": 145},
		{"fieldname": "asset", "label": "Asset", "fieldtype": "Link", "options": "Fleet Asset", "width": 145},
		{"fieldname": "asset_type", "label": "Asset Type", "fieldtype": "Data", "width": 95},
		{"fieldname": "location", "label": "Location", "fieldtype": "Link", "options": "Fleet Location", "width": 130},
		{"fieldname": "actual_fueling_datetime", "label": "Fueling Date and Time", "fieldtype": "Datetime", "width": 155},
		{"fieldname": "station", "label": "Station", "fieldtype": "Link", "options": "Fuel Station", "width": 140},
		{"fieldname": "fuel_type", "label": "Fuel", "fieldtype": "Link", "options": "Fuel Type", "width": 110},
		{"fieldname": "approved_authorization", "label": "Approved Authorization", "fieldtype": "Data", "width": 155},
		{"fieldname": "lpo_baseline_litres", "label": "LPO Baseline (L)", "fieldtype": "Float", "width": 115},
		{"fieldname": "actual_litres", "label": "Actual Litres", "fieldtype": "Float", "width": 100},
		{"fieldname": "variance_litres", "label": "Variance (L)", "fieldtype": "Float", "width": 95},
		{"fieldname": "variance_percent", "label": "Variance (%)", "fieldtype": "Percent", "width": 95},
		{"fieldname": "variance_status", "label": "Litre Status", "fieldtype": "Data", "width": 170},
		{"fieldname": "meter_type", "label": "Meter", "fieldtype": "Data", "width": 110},
		{"fieldname": "meter_reading", "label": "Meter Reading", "fieldtype": "Float", "width": 105},
		{"fieldname": "full_tank_confirmed", "label": "Full Tank", "fieldtype": "Check", "width": 80},
		{"fieldname": "full_tank_exception", "label": "Full-Tank Exception", "fieldtype": "Data", "width": 210},
		{"fieldname": "pre_tax_amount", "label": "Pre-Tax Fuel Spend (KES)", "fieldtype": "Currency", "options": "KES", "width": 150},
		{"fieldname": "cost_status", "label": "Cost Record", "fieldtype": "Data", "width": 105},
		{"fieldname": "pre_tax_cost_per_litre", "label": "Pre-Tax Cost/Litre (KES)", "fieldtype": "Currency", "options": "KES", "width": 145},
		{"fieldname": "vehicle_km_per_litre", "label": "Vehicle Efficiency (km/L)", "fieldtype": "Float", "width": 150},
		{"fieldname": "generator_litres_per_hour", "label": "Generator Efficiency (L/hour)", "fieldtype": "Float", "width": 165},
	]


def _get_list(doctype, fields, filters=None, order_by="name asc"):
	rows = []
	offset = 0
	while True:
		page = frappe.get_list(
			doctype,
			fields=fields,
			filters=filters or [],
			order_by=order_by,
			limit=PAGE_SIZE,
			offset=offset,
		)
		rows.extend(page)
		if len(page) < PAGE_SIZE:
			return rows
		offset += len(page)


def _linked_records(doctype, names, fields):
	records = {}
	for chunk in _chunks(names):
		rows = _get_list(doctype, ["name", *fields], {"name": ["in", chunk]})
		records.update({row.name: row for row in rows})
	return records


def _chunks(values):
	values = sorted(values)
	for start in range(0, len(values), PAGE_SIZE):
		yield values[start : start + PAGE_SIZE]
