from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate

from fleet_management.permissions import get_permitted_location_names, get_report_query_conditions

TRANSACTION_TABLE = "`tabFueling Transaction`"
ORDER_TABLE = "`tabFuel Order`"
LOCATION_EXPRESSION = (
	f"COALESCE(NULLIF({TRANSACTION_TABLE}.assigned_location_snapshot, ''), "
	f"NULLIF({ORDER_TABLE}.assigned_location_snapshot, ''), "
	f"{TRANSACTION_TABLE}.operational_location, {ORDER_TABLE}.operational_location)"
)

COLUMNS = [
	{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 90},
	{"fieldname": "row_type", "label": _("Row Type"), "fieldtype": "Data", "width": 130},
	{
		"fieldname": "name",
		"label": _("Fueling Transaction"),
		"fieldtype": "Link",
		"options": "Fueling Transaction",
		"width": 170,
	},
	{
		"fieldname": "location",
		"label": _("Location"),
		"fieldtype": "Link",
		"options": "Fleet Location",
		"width": 140,
	},
	{"fieldname": "asset", "label": _("Asset"), "fieldtype": "Link", "options": "Fleet Asset", "width": 150},
	{
		"fieldname": "fuel_type",
		"label": _("Fuel Type"),
		"fieldtype": "Link",
		"options": "Fuel Type",
		"width": 110,
	},
	{
		"fieldname": "station",
		"label": _("Station"),
		"fieldtype": "Link",
		"options": "Fuel Station",
		"width": 160,
	},
	{
		"fieldname": "fueling_date",
		"label": _("Fueling Date"),
		"fieldtype": "Date",
		"width": 110,
	},
	{
		"fieldname": "delivered_litres",
		"label": _("Delivered Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 120,
	},
	{
		"fieldname": "transaction_count",
		"label": _("Transaction Count"),
		"fieldtype": "Int",
		"width": 120,
	},
	{
		"fieldname": "recorded_spend",
		"label": _("Recorded Spend (KES)"),
		"fieldtype": "Currency",
		"width": 150,
	},
	{
		"fieldname": "amount_status",
		"label": _("Amount Status"),
		"fieldtype": "Data",
		"width": 270,
	},
	{
		"fieldname": "calculated_price_per_litre",
		"label": _("Calculated Price (KES/L)"),
		"fieldtype": "Currency",
		"width": 160,
	},
	{
		"fieldname": "printed_unit_price",
		"label": _("Printed Unit Price (KES/L)"),
		"fieldtype": "Currency",
		"width": 180,
	},
]


def execute(filters=None):
	_assert_report_access()
	filters = frappe._dict(filters or {})
	from_date, to_date = _get_date_range(filters)
	_validate_location_filter(filters.get("location"))

	conditions = [
		f"{TRANSACTION_TABLE}.docstatus = 1",
		f"DATE({TRANSACTION_TABLE}.actual_fueling_datetime) BETWEEN %(from_date)s AND %(to_date)s",
	]
	query_filters = {"from_date": from_date, "to_date": to_date}
	for fieldname, column in (
		("location", LOCATION_EXPRESSION),
		("asset", f"{TRANSACTION_TABLE}.asset"),
		("fuel_type", f"{TRANSACTION_TABLE}.fuel_type"),
		("station", f"{TRANSACTION_TABLE}.actual_station"),
	):
		value = filters.get(fieldname)
		if value:
			conditions.append(f"{column} = %({fieldname})s")
			query_filters[fieldname] = value

	location_scope = get_report_query_conditions("Fueling Transaction")
	if location_scope:
		conditions.append(f"({location_scope})")

	transactions = frappe.db.sql(
		f"""
		SELECT
			{TRANSACTION_TABLE}.name,
			{LOCATION_EXPRESSION} AS location,
			{TRANSACTION_TABLE}.asset,
			{TRANSACTION_TABLE}.fuel_type,
			{TRANSACTION_TABLE}.actual_station AS station,
			{TRANSACTION_TABLE}.actual_fueling_datetime AS fueling_datetime,
			{TRANSACTION_TABLE}.invoice_litres AS delivered_litres,
			{TRANSACTION_TABLE}.invoice_amount AS invoice_amount,
			{TRANSACTION_TABLE}.printed_unit_price AS printed_unit_price
		FROM {TRANSACTION_TABLE}
		LEFT JOIN {ORDER_TABLE} ON {ORDER_TABLE}.name = {TRANSACTION_TABLE}.fuel_order
		WHERE {' AND '.join(conditions)}
		ORDER BY {TRANSACTION_TABLE}.actual_fueling_datetime, {TRANSACTION_TABLE}.name
		""",
		query_filters,
		as_dict=True,
	)
	data, chart = _build_report_rows(transactions)
	message = _(
		"Monthly spend totals include only recorded invoice amounts. Transactions without an amount show as Unavailable."
	)
	return COLUMNS, data, message, chart


def _assert_report_access():
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not {"Fleet Approver", "Fleet Admin"}.intersection(roles):
		frappe.throw(_("Only Fleet Approvers and Fleet Admins can access this report."), frappe.PermissionError)
	if frappe.session.user != "Administrator" and not frappe.has_permission("Fueling Transaction", "report"):
		frappe.throw(_("You do not have permission to report on Fueling Transactions."), frappe.PermissionError)


def _get_date_range(filters):
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("Select both From Date and To Date."), frappe.ValidationError)

	try:
		from_date = getdate(filters.from_date)
		to_date = getdate(filters.to_date)
	except (TypeError, ValueError):
		frappe.throw(_("Enter valid From Date and To Date values."), frappe.ValidationError)

	if from_date > to_date:
		frappe.throw(_("From Date cannot be later than To Date."), frappe.ValidationError)
	return from_date, to_date


def _validate_location_filter(location):
	if not location or frappe.session.user == "Administrator":
		return

	roles = set(frappe.get_roles())
	if "Fleet Admin" in roles or "Fleet Approver" not in roles:
		return
	if location not in get_permitted_location_names():
		frappe.throw(_("You do not have access to location {0}.").format(location), frappe.PermissionError)


def _build_report_rows(transactions):
	months = defaultdict(lambda: {"records": [], "litres": 0.0, "spend": 0.0, "priced_litres": 0.0})
	for row in transactions:
		transaction = frappe._dict(row)
		fueling_date = getdate(transaction.fueling_datetime)
		month = fueling_date.strftime("%Y-%m")
		litres = flt(transaction.delivered_litres)
		# Frappe stores an empty Currency field as 0; zero means no amount was recorded.
		amount = flt(transaction.invoice_amount)
		has_amount = amount > 0
		printed_price = flt(transaction.printed_unit_price)
		record = {
			"month": month,
			"row_type": _("Fueling transaction"),
			"name": transaction.name,
			"location": transaction.location,
			"asset": transaction.asset,
			"fuel_type": transaction.fuel_type,
			"station": transaction.station,
			"fueling_date": fueling_date,
			"delivered_litres": litres,
			"transaction_count": 1,
			"recorded_spend": amount if has_amount else None,
			"amount_status": _("Recorded") if has_amount else _("Unavailable"),
			"calculated_price_per_litre": flt(amount / litres, 4) if has_amount and litres > 0 else None,
			"printed_unit_price": printed_price if printed_price > 0 else None,
		}
		bucket = months[month]
		bucket["records"].append(record)
		bucket["litres"] += litres
		if has_amount:
			bucket["spend"] += amount
			bucket["priced_litres"] += litres

	data = []
	labels = []
	spend_values = []
	for month in sorted(months):
		bucket = months[month]
		records = bucket["records"]
		recorded_count = sum(record["amount_status"] == _("Recorded") for record in records)
		unavailable_count = len(records) - recorded_count
		spend = flt(bucket["spend"], 2)
		status = _("{0} recorded; {1} unavailable. Total includes recorded amounts only.").format(
			recorded_count, unavailable_count
		)
		data.append(
			{
				"month": month,
				"row_type": _("Monthly total"),
				"delivered_litres": flt(bucket["litres"], 2),
				"transaction_count": len(records),
				"recorded_spend": spend if recorded_count else None,
				"amount_status": status,
				"calculated_price_per_litre": (
					flt(spend / bucket["priced_litres"], 4) if bucket["priced_litres"] else None
				),
			}
		)
		data.extend(records)
		labels.append(month)
		spend_values.append(spend)

	chart = None
	if labels:
		chart = {
			"data": {
				"labels": labels,
				"datasets": [{"name": _("Recorded Spend (KES)"), "values": spend_values}],
			},
			"type": "line",
		}
	return data, chart
