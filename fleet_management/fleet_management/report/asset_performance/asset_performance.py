import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from fleet_management.permissions import get_report_query_conditions
from fleet_management.fleet_management.report.fueling_summary.fueling_summary import (
	_get_date_range,
	_validate_location_filter,
)

ORDER_TABLE = "`tabFuel Order`"
TRANSACTION_TABLE = "`tabFueling Transaction`"
LOCATION_EXPRESSION = (
	f"COALESCE(NULLIF({TRANSACTION_TABLE}.assigned_location_snapshot, ''), "
	f"NULLIF({ORDER_TABLE}.assigned_location_snapshot, ''), "
	f"{TRANSACTION_TABLE}.operational_location, {ORDER_TABLE}.operational_location)"
)
ORDER_LOCATION_EXPRESSION = (
	f"COALESCE(NULLIF({ORDER_TABLE}.assigned_location_snapshot, ''), "
	f"{ORDER_TABLE}.operational_location)"
)

COLUMNS = [
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
	{"fieldname": "meter_reading", "label": _("Meter Reading"), "fieldtype": "Float", "width": 120},
]


def execute(filters=None):
	_assert_report_access()
	filters = frappe._dict(filters or {})
	if not filters.get("asset"):
		frappe.throw(_("Select an asset."), frappe.ValidationError)

	from_date, to_date = _get_date_range(filters)
	_validate_location_filter(filters.get("location"))
	asset = frappe.get_doc("Fleet Asset", filters.asset)
	asset.check_permission("read")

	orders = _get_orders(filters.asset, from_date, to_date)
	transactions = _get_transactions(filters.asset, from_date, to_date)
	return COLUMNS, _build_rows(asset, orders, transactions, from_date, to_date), None, None


def _assert_report_access():
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not {"Fleet Approver", "Fleet Admin"}.intersection(roles):
		frappe.throw(_("Only Fleet Approvers and Fleet Admins can access this report."), frappe.PermissionError)
	if frappe.session.user != "Administrator":
		for doctype in ("Fuel Order", "Fueling Transaction"):
			if not frappe.has_permission(doctype, "report"):
				frappe.throw(_("You do not have permission to report on {0}.").format(doctype), frappe.PermissionError)


def _get_orders(asset, from_date, to_date):
	conditions = [
		f"{ORDER_TABLE}.asset = %(asset)s",
		f"({ORDER_TABLE}.docstatus != 0 OR {ORDER_TABLE}.workflow_state = 'Pending Approval')",
		(
			f"(DATE({ORDER_TABLE}.request_datetime) BETWEEN %(from_date)s AND %(to_date)s "
			f"OR DATE({ORDER_TABLE}.approved_on) BETWEEN %(from_date)s AND %(to_date)s "
			f"OR DATE({ORDER_TABLE}.rejected_on) BETWEEN %(from_date)s AND %(to_date)s "
			f"OR ({ORDER_TABLE}.docstatus = 2 AND DATE({ORDER_TABLE}.modified) "
			"BETWEEN %(from_date)s AND %(to_date)s))"
		),
	]
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
			EXISTS (
				SELECT 1 FROM {TRANSACTION_TABLE}
				WHERE {' AND '.join(has_transaction)}
			) AS has_submitted_transaction
		FROM {ORDER_TABLE}
		WHERE {' AND '.join(conditions)}
		ORDER BY {ORDER_TABLE}.request_datetime, {ORDER_TABLE}.name
		""",
		{"asset": asset, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)


def _get_transactions(asset, from_date, to_date):
	conditions = [
		f"{TRANSACTION_TABLE}.asset = %(asset)s",
		f"{TRANSACTION_TABLE}.docstatus = 1",
		f"DATE({TRANSACTION_TABLE}.actual_fueling_datetime) BETWEEN %(from_date)s AND %(to_date)s",
	]
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
		WHERE {' AND '.join(conditions)}
		ORDER BY {TRANSACTION_TABLE}.actual_fueling_datetime, {TRANSACTION_TABLE}.name
		""",
		{"asset": asset, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)


def _build_rows(asset, orders, transactions, from_date, to_date):
	rows = []
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
				"request_date": order.request_datetime,
				"decision_date": _decision_date(order),
				"requester": order.requester,
				"driver": order.driver,
				"fuel_type": order.fuel_type,
				"station": order.station,
				"requested_litres": _optional_float(order.estimated_litres),
				"authorized_litres": _optional_float(order.authorized_quantity_litres),
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
				"request_status": _request_status(order),
				"fulfillment_status": _fulfillment_status(order),
				"cancellation_status": None,
				"meter_reading": _optional_float(transaction.hour_meter or transaction.vehicle_odometer),
			}
		)

	return sorted(rows, key=lambda row: (get_datetime(row["activity_date"]), row["record_type"]))


def _order_activity(order, from_date, to_date):
	request_date = order.request_datetime
	if request_date and from_date <= getdate(request_date) <= to_date:
		return request_date, _("Fuel Order")

	decision_date = _decision_date(order)
	if decision_date and from_date <= getdate(decision_date) <= to_date:
		return decision_date, _("Fuel Order decision")

	if cint(order.docstatus) == 2 and order.modified and from_date <= getdate(order.modified) <= to_date:
		return order.modified, _("Fuel Order cancellation")

	return request_date or decision_date or order.modified, _("Fuel Order")


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
