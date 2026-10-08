from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from fleet_management.fleet_management.report.fueling_summary.fueling_summary import (
	_validate_location_filter,
)
from fleet_management.permissions import get_report_query_conditions

ORDER_TABLE = "`tabFuel Order`"
TRANSACTION_TABLE = "`tabFueling Transaction`"
LOCATION_EXPRESSION = (
	f"COALESCE(NULLIF({TRANSACTION_TABLE}.assigned_location_snapshot, ''), "
	f"NULLIF({ORDER_TABLE}.assigned_location_snapshot, ''), "
	f"{TRANSACTION_TABLE}.operational_location, {ORDER_TABLE}.operational_location)"
)
ORDER_LOCATION_EXPRESSION = (
	f"COALESCE(NULLIF({ORDER_TABLE}.assigned_location_snapshot, ''), {ORDER_TABLE}.operational_location)"
)

COLUMNS = [
	{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 90},
	{"fieldname": "activity_date", "label": _("Activity Date"), "fieldtype": "Datetime", "width": 145},
	{"fieldname": "record_type", "label": _("Activity"), "fieldtype": "Data", "width": 145},
	{
		"fieldname": "location",
		"label": _("Location"),
		"fieldtype": "Link",
		"options": "Fleet Location",
		"width": 130,
	},
	{"fieldname": "asset", "label": _("Asset"), "fieldtype": "Link", "options": "Fleet Asset", "width": 145},
	{"fieldname": "asset_type", "label": _("Asset Type"), "fieldtype": "Data", "width": 100},
	{
		"fieldname": "fuel_order",
		"label": _("Fuel Order"),
		"fieldtype": "Link",
		"options": "Fuel Order",
		"width": 165,
	},
	{
		"fieldname": "fueling_transaction",
		"label": _("Fueling Transaction"),
		"fieldtype": "Link",
		"options": "Fueling Transaction",
		"width": 180,
	},
	{"fieldname": "request_date", "label": _("Request Date"), "fieldtype": "Datetime", "width": 145},
	{"fieldname": "decision_date", "label": _("Decision Date"), "fieldtype": "Datetime", "width": 145},
	{
		"fieldname": "requester",
		"label": _("Requester"),
		"fieldtype": "Link",
		"options": "Fleet Person",
		"width": 145,
	},
	{
		"fieldname": "driver",
		"label": _("Driver"),
		"fieldtype": "Link",
		"options": "Fleet Person",
		"width": 145,
	},
	{"fieldname": "fuel_attendant", "label": _("Fuel Attendant"), "fieldtype": "Data", "width": 145},
	{
		"fieldname": "fuel_type",
		"label": _("Fuel Type"),
		"fieldtype": "Link",
		"options": "Fuel Type",
		"width": 115,
	},
	{
		"fieldname": "station",
		"label": _("Station"),
		"fieldtype": "Link",
		"options": "Fuel Station",
		"width": 150,
	},
	{
		"fieldname": "requested_litres",
		"label": _("Requested Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 125,
	},
	{
		"fieldname": "authorized_litres",
		"label": _("Authorized Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 125,
	},
	{
		"fieldname": "delivered_litres",
		"label": _("Delivered Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 125,
	},
	{"fieldname": "fuel_order_count", "label": _("Fuel Order Count"), "fieldtype": "Int", "width": 125},
	{"fieldname": "fueling_count", "label": _("Fueling Count"), "fieldtype": "Int", "width": 115},
	{
		"fieldname": "request_status",
		"label": _("Request Status"),
		"fieldtype": "Data",
		"width": 130,
	},
	{
		"fieldname": "fulfillment_status",
		"label": _("Fulfillment Status"),
		"fieldtype": "Data",
		"width": 145,
	},
	{
		"fieldname": "cancellation_status",
		"label": _("Cancellation Status"),
		"fieldtype": "Data",
		"width": 145,
	},
	{"fieldname": "vehicle_odometer", "label": _("Vehicle Odometer"), "fieldtype": "Float", "width": 135},
	{"fieldname": "hour_meter", "label": _("Hour Meter"), "fieldtype": "Float", "width": 110},
	{
		"fieldname": "distance_km",
		"label": _("Interval Distance (km)"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 140,
	},
	{
		"fieldname": "qualifying_litres",
		"label": _("Interval Qualifying Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 160,
	},
	{
		"fieldname": "efficiency_km_per_litre",
		"label": _("Vehicle Efficiency (km/L)"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 165,
	},
	{
		"fieldname": "target_km_per_litre",
		"label": _("Target (km/L)"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 115,
	},
	{
		"fieldname": "efficiency_rating",
		"label": _("Efficiency Rating"),
		"fieldtype": "Data",
		"width": 145,
	},
	{
		"fieldname": "efficiency_status",
		"label": _("Efficiency Status"),
		"fieldtype": "Data",
		"width": 200,
	},
]


def execute(filters=None):
	_assert_report_access()
	filters = frappe._dict(filters or {})
	if not filters.get("asset"):
		frappe.throw(_("Select an asset."), frappe.ValidationError)

	from_date, to_date = _get_optional_date_range(filters)
	_validate_location_filter(filters.get("location"))
	asset = frappe.get_doc("Fleet Asset", filters.asset)
	asset.check_permission("read")

	orders = _get_orders(filters, from_date, to_date)
	transactions = _get_transactions(filters, from_date, to_date)
	rows, chart = _build_rows(asset, orders, transactions, from_date, to_date)
	return COLUMNS, rows, None, chart


def _assert_report_access():
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not {"Fleet Approver", "Fleet Admin"}.intersection(roles):
		frappe.throw(
			_("Only Fleet Approvers and Fleet Admins can access this report."), frappe.PermissionError
		)
	if frappe.session.user != "Administrator":
		for doctype in ("Fuel Order", "Fueling Transaction"):
			if not frappe.has_permission(doctype, "report"):
				frappe.throw(
					_("You do not have permission to report on {0}.").format(doctype), frappe.PermissionError
				)


def _get_optional_date_range(filters):
	try:
		from_date = getdate(filters.from_date) if filters.get("from_date") else None
		to_date = getdate(filters.to_date) if filters.get("to_date") else None
	except (TypeError, ValueError):
		frappe.throw(_("Enter valid From Date and To Date values."), frappe.ValidationError)
	if from_date and to_date and from_date > to_date:
		frappe.throw(_("From Date cannot be later than To Date."), frappe.ValidationError)
	return from_date, to_date


def _date_filter_conditions(field, from_date, to_date, query_filters):
	conditions = []
	if from_date:
		conditions.append(f"DATE({field}) >= %(from_date)s")
		query_filters["from_date"] = from_date
	if to_date:
		conditions.append(f"DATE({field}) <= %(to_date)s")
		query_filters["to_date"] = to_date
	return conditions


def _get_orders(filters, from_date, to_date):
	conditions = [
		f"{ORDER_TABLE}.asset = %(asset)s",
		(
			f"({ORDER_TABLE}.docstatus != 0 OR "
			f"{ORDER_TABLE}.workflow_state IN ('Pending Approval', 'Rejected'))"
		),
	]
	query_filters = {"asset": filters.asset}
	event_conditions = []
	for fieldname in ("request_datetime", "approved_on", "rejected_on"):
		date_conditions = _date_filter_conditions(
			f"{ORDER_TABLE}.{fieldname}", from_date, to_date, query_filters
		)
		if date_conditions:
			event_conditions.append("(" + " AND ".join(date_conditions) + ")")
	cancellation_conditions = _date_filter_conditions(
		f"{ORDER_TABLE}.modified", from_date, to_date, query_filters
	)
	if cancellation_conditions:
		event_conditions.append(
			f"({ORDER_TABLE}.docstatus = 2 AND " + " AND ".join(cancellation_conditions) + ")"
		)
	if event_conditions:
		conditions.append("(" + " OR ".join(event_conditions) + ")")
	for fieldname, expression in (
		("location", ORDER_LOCATION_EXPRESSION),
		("fuel_type", f"{ORDER_TABLE}.fuel_type"),
		("station", f"{ORDER_TABLE}.planned_station"),
	):
		if filters.get(fieldname):
			conditions.append(f"{expression} = %({fieldname})s")
			query_filters[fieldname] = filters.get(fieldname)
	order_scope = get_report_query_conditions("Fuel Order")
	if order_scope:
		conditions.append(f"({order_scope})")

	transaction_scope = get_report_query_conditions("Fueling Transaction")
	has_transaction = [
		f"{TRANSACTION_TABLE}.fuel_order = {ORDER_TABLE}.name",
		f"{TRANSACTION_TABLE}.docstatus = 1",
	]
	if transaction_scope:
		has_transaction.append(f"({transaction_scope})")

	return frappe.db.sql(
		f"""
		SELECT
			{ORDER_TABLE}.name,
			{ORDER_LOCATION_EXPRESSION} AS location,
			{ORDER_TABLE}.request_datetime,
			{ORDER_TABLE}.approved_on,
			{ORDER_TABLE}.rejected_on,
			{ORDER_TABLE}.modified,
			{ORDER_TABLE}.docstatus,
			{ORDER_TABLE}.workflow_state,
			{ORDER_TABLE}.decision_action,
			{ORDER_TABLE}.valid_until,
			{ORDER_TABLE}.asset,
			{ORDER_TABLE}.asset_type,
			{ORDER_TABLE}.actual_requester AS requester,
			{ORDER_TABLE}.driver,
			{ORDER_TABLE}.fuel_type,
			{ORDER_TABLE}.planned_station AS station,
			{ORDER_TABLE}.estimated_litres,
			{ORDER_TABLE}.authorized_quantity_litres,
			{ORDER_TABLE}.request_meter_reading,
			EXISTS (
				SELECT 1 FROM {TRANSACTION_TABLE}
				WHERE {" AND ".join(has_transaction)}
			) AS has_submitted_transaction
		FROM {ORDER_TABLE}
		WHERE {" AND ".join(conditions)}
		ORDER BY {ORDER_TABLE}.request_datetime, {ORDER_TABLE}.name
		""",
		query_filters,
		as_dict=True,
	)


def _get_transactions(filters, from_date, to_date):
	conditions = [
		f"{TRANSACTION_TABLE}.asset = %(asset)s",
		f"{TRANSACTION_TABLE}.docstatus = 1",
	]
	query_filters = {"asset": filters.asset}
	conditions.extend(
		_date_filter_conditions(
			f"{TRANSACTION_TABLE}.actual_fueling_datetime", from_date, to_date, query_filters
		)
	)
	for fieldname, expression in (
		("location", LOCATION_EXPRESSION),
		("fuel_type", f"{TRANSACTION_TABLE}.fuel_type"),
		("station", f"{TRANSACTION_TABLE}.actual_station"),
	):
		if filters.get(fieldname):
			conditions.append(f"{expression} = %({fieldname})s")
			query_filters[fieldname] = filters.get(fieldname)
	for doctype in ("Fueling Transaction", "Fuel Order"):
		scope = get_report_query_conditions(doctype)
		if scope:
			conditions.append(f"({scope})")

	return frappe.db.sql(
		f"""
		SELECT
			{TRANSACTION_TABLE}.name,
			{LOCATION_EXPRESSION} AS location,
			{TRANSACTION_TABLE}.actual_fueling_datetime,
			{TRANSACTION_TABLE}.asset,
			{TRANSACTION_TABLE}.fuel_type,
			{TRANSACTION_TABLE}.actual_station AS station,
			{TRANSACTION_TABLE}.invoice_litres AS delivered_litres,
			{TRANSACTION_TABLE}.vehicle_odometer,
			{TRANSACTION_TABLE}.hour_meter,
			{TRANSACTION_TABLE}.full_tank_confirmed,
			{TRANSACTION_TABLE}.previous_full_fill,
			{TRANSACTION_TABLE}.closing_full_fill,
			{TRANSACTION_TABLE}.distance_km,
			{TRANSACTION_TABLE}.qualifying_litres,
			{TRANSACTION_TABLE}.km_per_litre,
			{TRANSACTION_TABLE}.asset_target_km_per_litre_snapshot,
			{TRANSACTION_TABLE}.attendant_name AS fuel_attendant,
			{ORDER_TABLE}.name AS fuel_order,
			{ORDER_TABLE}.request_datetime,
			{ORDER_TABLE}.approved_on,
			{ORDER_TABLE}.rejected_on,
			{ORDER_TABLE}.docstatus AS order_docstatus,
			{ORDER_TABLE}.workflow_state,
			{ORDER_TABLE}.decision_action,
			{ORDER_TABLE}.valid_until,
			{ORDER_TABLE}.actual_requester AS requester,
			{ORDER_TABLE}.driver,
			{ORDER_TABLE}.estimated_litres,
			{ORDER_TABLE}.authorized_quantity_litres
		FROM {TRANSACTION_TABLE}
		INNER JOIN {ORDER_TABLE} ON {ORDER_TABLE}.name = {TRANSACTION_TABLE}.fuel_order
		WHERE {" AND ".join(conditions)}
		ORDER BY {TRANSACTION_TABLE}.actual_fueling_datetime, {TRANSACTION_TABLE}.name
		""",
		query_filters,
		as_dict=True,
	)


def _build_rows(asset, orders, transactions, from_date, to_date):
	rows = []
	interval_states = (
		_get_interval_target_states(asset.name, transactions) if asset.asset_type == "Vehicle" else {}
	)
	for order in orders:
		activity_date, record_type = _order_activity(order, from_date, to_date)
		status = _request_status(order)
		rows.append(
			{
				"activity_date": activity_date,
				"record_type": record_type,
				"location": order.location,
				"asset": order.asset,
				"asset_type": asset.asset_type,
				"fuel_order": order.name,
				"fuel_order_count": 1,
				"request_date": order.request_datetime,
				"decision_date": _decision_date(order),
				"requester": order.requester,
				"driver": order.driver,
				"fuel_type": order.fuel_type,
				"station": order.station,
				"requested_litres": _optional_float(order.estimated_litres),
				"authorized_litres": _optional_float(order.authorized_quantity_litres),
				"vehicle_odometer": (
					_optional_float(order.request_meter_reading) if asset.asset_type == "Vehicle" else None
				),
				"hour_meter": _optional_float(order.request_meter_reading)
				if asset.asset_type == "Generator"
				else None,
				"request_status": status,
				"fulfillment_status": _fulfillment_status(order),
				"cancellation_status": _("Cancelled") if cint(order.docstatus) == 2 else None,
			}
		)

	for transaction in transactions:
		order = frappe._dict(
			{
				"docstatus": transaction.order_docstatus,
				"workflow_state": transaction.workflow_state,
				"decision_action": transaction.decision_action,
				"valid_until": transaction.valid_until,
				"has_submitted_transaction": 1,
			}
		)
		rows.append(
			{
				"activity_date": transaction.actual_fueling_datetime,
				"record_type": _("Fueling Transaction"),
				"location": transaction.location,
				"asset": transaction.asset,
				"asset_type": asset.asset_type,
				"fuel_order": transaction.fuel_order,
				"fueling_transaction": transaction.name,
				"fueling_count": 1,
				"request_date": transaction.request_datetime,
				"decision_date": _decision_date(transaction),
				"requester": transaction.requester,
				"driver": transaction.driver,
				"fuel_attendant": transaction.fuel_attendant,
				"fuel_type": transaction.fuel_type,
				"station": transaction.station,
				"requested_litres": _optional_float(transaction.estimated_litres),
				"authorized_litres": _optional_float(transaction.authorized_quantity_litres),
				"delivered_litres": _optional_float(transaction.delivered_litres),
				"vehicle_odometer": (
					_optional_float(transaction.vehicle_odometer) if asset.asset_type == "Vehicle" else None
				),
				"hour_meter": (
					_optional_float(transaction.hour_meter) if asset.asset_type == "Generator" else None
				),
				"request_status": _request_status(order),
				"fulfillment_status": _fulfillment_status(order),
				"cancellation_status": None,
				**(
					_vehicle_efficiency_columns(transaction, interval_states)
					if asset.asset_type == "Vehicle"
					else {}
				),
			}
		)

	rows.sort(key=lambda row: (get_datetime(row["activity_date"]), row["record_type"]))
	rows_by_month = {}
	for row in rows:
		month = get_datetime(row["activity_date"]).strftime("%Y-%m")
		row["month"] = month
		rows_by_month.setdefault(month, []).append(row)

	data = []
	labels = []
	litre_values = []
	for month in sorted(rows_by_month):
		month_rows = rows_by_month[month]
		delivered_litres = sum(flt(row.get("delivered_litres")) for row in month_rows)
		monthly_total = {
			"month": month,
			"record_type": _("Monthly total"),
			"asset": asset.name,
			"asset_type": asset.asset_type,
			"fuel_order_count": sum(cint(row.get("fuel_order_count")) for row in month_rows),
			"fueling_count": sum(cint(row.get("fueling_count")) for row in month_rows),
			"delivered_litres": flt(delivered_litres, 2),
		}
		if asset.asset_type == "Vehicle":
			monthly_total["efficiency_km_per_litre"] = _monthly_efficiency(month_rows)
		data.append(monthly_total)
		data.extend(month_rows)
		labels.append(month)
		litre_values.append(flt(delivered_litres, 2))

	chart = None
	if labels:
		chart = {
			"data": {"labels": labels, "datasets": [{"name": _("Delivered Litres"), "values": litre_values}]},
			"type": "line",
		}
	return data, chart


def _monthly_efficiency(rows):
	intervals = [
		row for row in rows if flt(row.get("distance_km")) > 0 and flt(row.get("qualifying_litres")) > 0
	]
	qualifying_litres = sum(flt(row["qualifying_litres"]) for row in intervals)
	if not intervals or qualifying_litres <= 0:
		return None
	return flt(sum(flt(row["distance_km"]) for row in intervals) / qualifying_litres, 4)


def _order_activity(order, from_date, to_date):
	request_date = order.request_datetime
	if _matches_date_range(request_date, from_date, to_date):
		return request_date, _("Fuel Order")

	decision_date = _decision_date(order)
	if _matches_date_range(decision_date, from_date, to_date):
		return decision_date, _("Fuel Order decision")

	if cint(order.docstatus) == 2 and _matches_date_range(order.modified, from_date, to_date):
		return order.modified, _("Fuel Order cancellation")

	return request_date or decision_date or order.modified, _("Fuel Order")


def _matches_date_range(value, from_date, to_date):
	if not value:
		return False
	day = getdate(value)
	return (not from_date or from_date <= day) and (not to_date or day <= to_date)


def _decision_date(order):
	return order.approved_on or order.rejected_on


def _request_status(order):
	if cint(order.docstatus) == 2:
		return _("Cancelled")
	if order.workflow_state == "Pending Approval":
		return _("Pending")
	if order.workflow_state == "Rejected":
		return _("Withdrawn") if order.decision_action == "Withdraw" else _("Rejected")
	if order.workflow_state == "Approved":
		return _("Approved")
	return order.workflow_state


def _fulfillment_status(order, now=None):
	if cint(order.docstatus) == 2:
		return _("Cancelled")
	if order.workflow_state != "Approved":
		return None
	if cint(order.get("has_submitted_transaction")):
		return _("Completed")
	if order.valid_until and get_datetime(now or now_datetime()) > get_datetime(order.valid_until):
		return _("Expired")
	return _("Awaiting fueling")


def _optional_float(value):
	return flt(value) if value not in (None, "") else None


def _valid_interval(transaction):
	return (
		transaction.closing_full_fill == transaction.name
		and transaction.previous_full_fill
		and flt(transaction.distance_km) > 0
		and flt(transaction.qualifying_litres) > 0
		and flt(transaction.km_per_litre) > 0
	)


def _fueling_source_key(transaction):
	# Keep the full-fill ordering used by FuelingTransaction._source_key.
	return get_datetime(transaction.actual_fueling_datetime), str(transaction.name)


def _vehicle_efficiency_columns(transaction, target_states):
	if not _valid_interval(transaction):
		return {"efficiency_status": _("Unavailable")}

	efficiency = flt(transaction.km_per_litre)
	target = _optional_float(transaction.asset_target_km_per_litre_snapshot)
	state = target_states.get(transaction.name, "unknown")
	if not target:
		status = _("Target unavailable; not rated")
		rating = None
	elif state == "changed":
		status = _("Target changed within interval; not rated")
		rating = None
	elif state != "stable":
		status = _("Target history unavailable; not rated")
		rating = None
	else:
		status = None
		rating = _rate_efficiency(efficiency, target)

	return {
		"distance_km": _optional_float(transaction.distance_km),
		"qualifying_litres": _optional_float(transaction.qualifying_litres),
		"efficiency_km_per_litre": efficiency,
		"target_km_per_litre": target,
		"efficiency_rating": rating,
		"efficiency_status": status,
	}


def _rate_efficiency(efficiency, target):
	efficiency_value = _decimal(efficiency)
	target_value = _decimal(target)
	if efficiency_value is None or target_value is None or target_value <= 0:
		return None
	deviation = abs((efficiency_value - target_value) / target_value)
	if deviation <= Decimal("0.10"):
		return _("Green")
	if deviation <= Decimal("0.20"):
		return _("Orange")
	return _("Red")


def _decimal(value):
	try:
		return Decimal(str(value)) if value not in (None, "") else None
	except (InvalidOperation, ValueError):
		return None


def _target_history_state(baseline, values):
	baseline_value = _decimal(baseline)
	if baseline_value is None or baseline_value <= 0:
		return "unknown"
	missing = False
	for value in values:
		value = _decimal(value)
		if value is None:
			missing = True
		elif value != baseline_value:
			return "changed"
	return "unknown" if missing else "stable"


def _get_interval_target_states(asset, transactions):
	closings = [row for row in transactions if _valid_interval(row)]
	if not closings:
		return {}

	opening_names = sorted({row.previous_full_fill for row in closings})
	escaped_names = ", ".join(frappe.db.escape(name, percent=False) for name in opening_names)
	transaction_scope = get_report_query_conditions("Fueling Transaction")
	opening_conditions = [
		f"{TRANSACTION_TABLE}.asset = %(asset)s",
		f"{TRANSACTION_TABLE}.docstatus = 1",
		f"{TRANSACTION_TABLE}.name IN ({escaped_names})",
	]
	if transaction_scope:
		opening_conditions.append(f"({transaction_scope})")
	openings = frappe.db.sql(
		f"""
		SELECT name, actual_fueling_datetime, asset_target_km_per_litre_snapshot
		FROM {TRANSACTION_TABLE}
		WHERE {" AND ".join(opening_conditions)}
		""",
		{"asset": asset},
		as_dict=True,
	)
	openings = {row.name: row for row in openings}
	known_openings = [openings.get(name) for name in opening_names]
	known_openings = [row for row in known_openings if row and row.actual_fueling_datetime]
	if not known_openings:
		return {row.name: "unknown" for row in closings}

	from_datetime = min(get_datetime(row.actual_fueling_datetime) for row in known_openings)
	to_datetime = max(get_datetime(row.actual_fueling_datetime) for row in closings)
	interval_conditions = [
		f"{TRANSACTION_TABLE}.asset = %(asset)s",
		f"{TRANSACTION_TABLE}.docstatus = 1",
		f"{TRANSACTION_TABLE}.actual_fueling_datetime BETWEEN %(from_datetime)s AND %(to_datetime)s",
	]
	if transaction_scope:
		interval_conditions.append(f"({transaction_scope})")
	interval_transactions = frappe.db.sql(
		f"""
		SELECT name, actual_fueling_datetime, asset_target_km_per_litre_snapshot
		FROM {TRANSACTION_TABLE}
		WHERE {" AND ".join(interval_conditions)}
		""",
		{"asset": asset, "from_datetime": from_datetime, "to_datetime": to_datetime},
		as_dict=True,
	)

	order_scope = get_report_query_conditions("Fuel Order")
	order_conditions = [
		f"{ORDER_TABLE}.asset = %(asset)s",
		f"{ORDER_TABLE}.request_datetime BETWEEN %(from_datetime)s AND %(to_datetime)s",
	]
	if order_scope:
		order_conditions.append(f"({order_scope})")
	interval_orders = frappe.db.sql(
		f"""
		SELECT request_datetime, asset_target_km_per_litre_snapshot
		FROM {ORDER_TABLE}
	WHERE {" AND ".join(order_conditions)}
		""",
		{"asset": asset, "from_datetime": from_datetime, "to_datetime": to_datetime},
		as_dict=True,
	)

	states = {}
	for closing in closings:
		opening = openings.get(closing.previous_full_fill)
		if not opening or not opening.actual_fueling_datetime:
			states[closing.name] = "unknown"
			continue
		start_key = _fueling_source_key(opening)
		end_key = _fueling_source_key(closing)
		if start_key >= end_key:
			states[closing.name] = "unknown"
			continue
		start = start_key[0]
		end = end_key[0]

		values = [closing.asset_target_km_per_litre_snapshot]
		values.extend(
			row.asset_target_km_per_litre_snapshot
			for row in interval_transactions
			if start_key < _fueling_source_key(row) <= end_key
		)
		values.extend(
			row.asset_target_km_per_litre_snapshot
			for row in interval_orders
			if start < get_datetime(row.request_datetime) <= end
		)
		states[closing.name] = _target_history_state(opening.asset_target_km_per_litre_snapshot, values)
	return states
