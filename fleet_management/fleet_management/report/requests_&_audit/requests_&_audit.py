import frappe
from frappe import _
from frappe.utils import cint, getdate

from fleet_management.permissions import get_permitted_location_names, get_report_query_conditions
from fleet_management.fleet_management.report.asset_performance.asset_performance import (
	ORDER_LOCATION_EXPRESSION,
	_fulfillment_status,
	_request_status,
)
from fleet_management.fleet_management.report.fueling_summary.fueling_summary import (
	LOCATION_EXPRESSION,
	_get_date_range,
	_validate_location_filter,
)

ORDER_TABLE = "`tabFuel Order`"
TRANSACTION_TABLE = "`tabFueling Transaction`"
DISCREPANCY_TABLE = "`tabFueling Discrepancy`"

COLUMNS = [
	{"fieldname": "activity_date", "label": _("Activity Date"), "fieldtype": "Datetime", "width": 150},
	{"fieldname": "activity", "label": _("Activity"), "fieldtype": "Data", "width": 175},
	{
		"fieldname": "location",
		"label": _("Location"),
		"fieldtype": "Link",
		"options": "Fleet Location",
		"width": 135,
	},
	{"fieldname": "asset", "label": _("Asset"), "fieldtype": "Link", "options": "Fleet Asset", "width": 150},
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
		"width": 155,
	},
	{
		"fieldname": "fuel_order",
		"label": _("Fuel Order"),
		"fieldtype": "Link",
		"options": "Fuel Order",
		"width": 170,
	},
	{
		"fieldname": "fueling_transaction",
		"label": _("Fueling Transaction"),
		"fieldtype": "Link",
		"options": "Fueling Transaction",
		"width": 180,
	},
	{
		"fieldname": "fueling_discrepancy",
		"label": _("Fueling Discrepancy"),
		"fieldtype": "Link",
		"options": "Fueling Discrepancy",
		"width": 180,
	},
	{
		"fieldname": "requester",
		"label": _("Requester"),
		"fieldtype": "Link",
		"options": "Fleet Person",
		"width": 145,
	},
	{
		"fieldname": "request_status",
		"label": _("Request Status"),
		"fieldtype": "Data",
		"width": 130,
	},
	{
		"fieldname": "decision_action",
		"label": _("Decision"),
		"fieldtype": "Data",
		"width": 105,
	},
	{
		"fieldname": "decision_reason",
		"label": _("Decision Reason"),
		"fieldtype": "Small Text",
		"width": 230,
	},
	{
		"fieldname": "decision_by",
		"label": _("Decision By"),
		"fieldtype": "Link",
		"options": "User",
		"width": 165,
	},
	{
		"fieldname": "warning_status",
		"label": _("Warning Status"),
		"fieldtype": "Data",
		"width": 125,
	},
	{
		"fieldname": "warning_reasons",
		"label": _("Warning Reasons"),
		"fieldtype": "Small Text",
		"width": 240,
	},
	{
		"fieldname": "fulfillment_status",
		"label": _("Fulfillment Status"),
		"fieldtype": "Data",
		"width": 145,
	},
	{
		"fieldname": "fueling_status",
		"label": _("Fueling Status"),
		"fieldtype": "Data",
		"width": 120,
	},
	{
		"fieldname": "discrepancy_status",
		"label": _("Discrepancy Status"),
		"fieldtype": "Data",
		"width": 220,
	},
	{
		"fieldname": "discrepancy_type",
		"label": _("Discrepancy Type"),
		"fieldtype": "Data",
		"width": 165,
	},
	{
		"fieldname": "discrepancy_details",
		"label": _("Discrepancy Details"),
		"fieldtype": "Small Text",
		"width": 240,
	},
	{
		"fieldname": "discrepancy_reason",
		"label": _("Discrepancy Reason"),
		"fieldtype": "Small Text",
		"width": 240,
	},
	{
		"fieldname": "recorded_by",
		"label": _("Recorded By"),
		"fieldtype": "Link",
		"options": "User",
		"width": 165,
	},
	{"fieldname": "recorded_on", "label": _("Recorded On"), "fieldtype": "Datetime", "width": 150},
	{
		"fieldname": "delivered_litres",
		"label": _("Delivered Litres"),
		"fieldtype": "Float",
		"precision": 2,
		"width": 120,
	},
]


def execute(filters=None):
	_assert_report_access()
	filters = frappe._dict(filters or {})
	from_date, to_date = _get_date_range(filters)
	_validate_location_filter(filters.get("location"))

	orders = _get_orders(filters, from_date, to_date)
	transactions = _get_transactions(filters, from_date, to_date)
	return COLUMNS, _build_rows(orders, transactions, from_date, to_date), None, None


def _assert_report_access():
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not {"Fleet Approver", "Fleet Admin"}.intersection(roles):
		frappe.throw(_("Only Fleet Approvers and Fleet Admins can access this report."), frappe.PermissionError)
	if frappe.session.user != "Administrator":
		for doctype in ("Fuel Order", "Fueling Transaction", "Fueling Discrepancy"):
			if not frappe.has_permission(doctype, "report"):
				frappe.throw(_("You do not have permission to report on {0}.").format(doctype), frappe.PermissionError)


def _get_orders(filters, from_date, to_date):
	conditions = [
		f"({ORDER_TABLE}.docstatus != 0 OR {ORDER_TABLE}.workflow_state IN ('Pending Approval', 'Rejected'))",
		(
			f"(DATE({ORDER_TABLE}.request_datetime) BETWEEN %(from_date)s AND %(to_date)s "
			f"OR DATE({ORDER_TABLE}.approved_on) BETWEEN %(from_date)s AND %(to_date)s "
			f"OR DATE({ORDER_TABLE}.rejected_on) BETWEEN %(from_date)s AND %(to_date)s)"
		),
	]
	query_filters = {"from_date": from_date, "to_date": to_date}
	for fieldname, expression in (
		("location", ORDER_LOCATION_EXPRESSION),
		("asset", f"{ORDER_TABLE}.asset"),
		("fuel_type", f"{ORDER_TABLE}.fuel_type"),
		("station", f"{ORDER_TABLE}.planned_station"),
	):
		if filters.get(fieldname):
			conditions.append(f"{expression} = %({fieldname})s")
			query_filters[fieldname] = filters[fieldname]

	location_scope = get_report_query_conditions("Fuel Order")
	if location_scope:
		conditions.append(f"({location_scope})")

	return frappe.db.sql(
		f"""
		SELECT
			{ORDER_TABLE}.name,
			{ORDER_LOCATION_EXPRESSION} AS location,
			{ORDER_TABLE}.request_datetime,
			{ORDER_TABLE}.approved_on,
			{ORDER_TABLE}.rejected_on,
			{ORDER_TABLE}.docstatus,
			{ORDER_TABLE}.workflow_state,
			{ORDER_TABLE}.decision_action,
			{ORDER_TABLE}.decision_reason,
			{ORDER_TABLE}.approved_by,
			{ORDER_TABLE}.rejected_by,
			{ORDER_TABLE}.signal,
			{ORDER_TABLE}.signal_reasons,
			{ORDER_TABLE}.valid_until,
			{ORDER_TABLE}.asset,
			{ORDER_TABLE}.actual_requester AS requester,
			{ORDER_TABLE}.fuel_type,
			{ORDER_TABLE}.planned_station AS station,
			EXISTS (
				SELECT 1 FROM {TRANSACTION_TABLE}
				WHERE {TRANSACTION_TABLE}.fuel_order = {ORDER_TABLE}.name
				  AND {TRANSACTION_TABLE}.docstatus = 1
			) AS has_submitted_transaction
		FROM {ORDER_TABLE}
		WHERE {' AND '.join(conditions)}
		ORDER BY {ORDER_TABLE}.request_datetime, {ORDER_TABLE}.name
		""",
		query_filters,
		as_dict=True,
	)


def _get_transactions(filters, from_date, to_date):
	conditions = [
		f"{TRANSACTION_TABLE}.docstatus IN (1, 2)",
		f"DATE({TRANSACTION_TABLE}.actual_fueling_datetime) BETWEEN %(from_date)s AND %(to_date)s",
	]
	query_filters = {"from_date": from_date, "to_date": to_date}
	for fieldname, expression in (
		("location", LOCATION_EXPRESSION),
		("asset", f"{TRANSACTION_TABLE}.asset"),
		("fuel_type", f"{TRANSACTION_TABLE}.fuel_type"),
		("station", f"{TRANSACTION_TABLE}.actual_station"),
	):
		if filters.get(fieldname):
			conditions.append(f"{expression} = %({fieldname})s")
			query_filters[fieldname] = filters[fieldname]
	for doctype in ("Fueling Transaction", "Fuel Order"):
		scope = get_report_query_conditions(doctype)
		if scope:
			conditions.append(f"({scope})")

	discrepancy_scope = get_report_query_conditions("Fueling Discrepancy")
	join_conditions = [f"{DISCREPANCY_TABLE}.fueling_transaction = {TRANSACTION_TABLE}.name"]
	if discrepancy_scope:
		join_conditions.append(f"({discrepancy_scope})")

	return frappe.db.sql(
		f"""
		SELECT
			{TRANSACTION_TABLE}.name,
			{TRANSACTION_TABLE}.docstatus,
			{TRANSACTION_TABLE}.fuel_order,
			{TRANSACTION_TABLE}.actual_fueling_datetime,
			{LOCATION_EXPRESSION} AS location,
			{TRANSACTION_TABLE}.asset,
			{TRANSACTION_TABLE}.fuel_type,
			{TRANSACTION_TABLE}.actual_station AS station,
			{TRANSACTION_TABLE}.invoice_litres AS delivered_litres,
			{ORDER_TABLE}.actual_requester AS requester,
			{DISCREPANCY_TABLE}.name AS discrepancy,
			{DISCREPANCY_TABLE}.discrepancy_type,
			{DISCREPANCY_TABLE}.details AS discrepancy_details,
			{DISCREPANCY_TABLE}.reason AS discrepancy_reason,
			{DISCREPANCY_TABLE}.recorded_by,
			{DISCREPANCY_TABLE}.recorded_on
		FROM {TRANSACTION_TABLE}
		LEFT JOIN {ORDER_TABLE} ON {ORDER_TABLE}.name = {TRANSACTION_TABLE}.fuel_order
		LEFT JOIN {DISCREPANCY_TABLE} ON {' AND '.join(join_conditions)}
		WHERE {' AND '.join(conditions)}
		ORDER BY {TRANSACTION_TABLE}.actual_fueling_datetime, {TRANSACTION_TABLE}.name,
		         {DISCREPANCY_TABLE}.recorded_on, {DISCREPANCY_TABLE}.name
		""",
		query_filters,
		as_dict=True,
	)


def _build_rows(orders, transactions, from_date, to_date):
	rows = []
	for order in orders:
		status = _request_status(order)
		fulfillment = _fulfillment_status(order)
		common = {
			"location": order.location,
			"asset": order.asset,
			"fuel_type": order.fuel_type,
			"station": order.station,
			"fuel_order": order.name,
			"requester": order.requester,
			"request_status": status,
			"warning_status": order.signal,
			"warning_reasons": order.signal_reasons,
			"fulfillment_status": fulfillment,
		}
		if _in_period(order.request_datetime, from_date, to_date):
			rows.append(
				{
					**common,
					"activity_date": order.request_datetime,
					"activity": _("Fuel request"),
				}
			)

		decision_date = order.approved_on or order.rejected_on
		if order.decision_action and _in_period(decision_date, from_date, to_date):
			rows.append(
				{
					**common,
					"activity_date": decision_date,
					"activity": _("Fuel request decision"),
					"decision_action": order.decision_action,
					"decision_reason": order.decision_reason,
					"decision_by": order.approved_by if order.decision_action == "Approve" else order.rejected_by,
				}
			)

	for transaction in transactions:
		cancelled = cint(transaction.docstatus) == 2
		activity = (
			_("Recorded fueling discrepancy")
			if transaction.discrepancy
			else (_("Cancelled fueling transaction") if cancelled else _("Fueling transaction"))
		)
		rows.append(
			{
				"activity_date": transaction.actual_fueling_datetime,
				"activity": activity,
				"location": transaction.location,
				"asset": transaction.asset,
				"fuel_type": transaction.fuel_type,
				"station": transaction.station,
				"fuel_order": transaction.fuel_order,
				"fueling_transaction": transaction.name,
				"fueling_discrepancy": transaction.discrepancy,
				"requester": transaction.requester,
				"fueling_status": _("Cancelled") if cancelled else _("Submitted"),
				"discrepancy_status": (
					_("Recorded") if transaction.discrepancy else _("No discrepancy was recorded")
				),
				"discrepancy_type": transaction.discrepancy_type,
				"discrepancy_details": transaction.discrepancy_details,
				"discrepancy_reason": transaction.discrepancy_reason,
				"recorded_by": transaction.recorded_by,
				"recorded_on": transaction.recorded_on,
				"delivered_litres": transaction.delivered_litres,
			}
		)

	rows.sort(key=lambda row: (row["activity_date"], row["activity"], row.get("fuel_order") or ""))
	return rows


def _in_period(value, from_date, to_date):
	return bool(value and from_date <= getdate(value) <= to_date)
