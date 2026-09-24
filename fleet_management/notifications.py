from datetime import timedelta
from html import escape
from urllib.parse import quote

import frappe
from frappe.utils import get_datetime, now_datetime

from fleet_management.permissions import get_permitted_location_names


def _enabled_users():
	users = set(
		frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"
		)
	)
	return users - {"Administrator"}


def _users_with_role(role, enabled_users):
	return {user for user in enabled_users if role in frappe.get_roles(user)}


def _recipients(order, event):
	enabled_users = _enabled_users()
	admins = _users_with_role("Fleet Admin", enabled_users)

	if event in {"pending_approval", "pre_expiry", "expired", "extended"}:
		location = order.assigned_location_snapshot
		approvers = _users_with_role("Fleet Approver", enabled_users)
		approvers = {
			user
			for user in approvers
			if location in get_permitted_location_names(user)
		}
		return approvers | admins

	if event in {"approved", "rejected"}:
		return ({order.submitted_by} & enabled_users) | admins

	frappe.throw(frappe._("Unknown Fuel Order notification event: {0}").format(event))


def _event_content(order, event):
	name = order.name
	valid_until = get_datetime(order.valid_until).strftime("%Y-%m-%d %H:%M:%S") if order.valid_until else ""
	name_html = escape(name)
	asset_html = escape(order.asset or "")
	location_html = escape(order.assigned_location_snapshot or "")
	if event == "pending_approval":
		return (
			f"Fuel Order {name} requires approval",
			f"Fuel Order {name_html} for {asset_html} at {location_html} is pending approval.",
		)
	if event == "approved":
		return (
			f"Fuel Order {name} was approved",
			f"Fuel Order {name_html} was approved. Its validity ends at {escape(valid_until)}.",
		)
	if event == "rejected":
		return (
			f"Fuel Order {name} was rejected",
			f"Fuel Order {name_html} was rejected.",
		)
	if event == "pre_expiry":
		return (
			f"Fuel Order {name} expires in 1 day ({valid_until})",
			f"Fuel Order {name_html} is due to expire at {escape(valid_until)}.",
		)
	if event == "expired":
		return (
			f"Fuel Order {name} expired ({valid_until})",
			f"Fuel Order {name_html} expired at {escape(valid_until)}.",
		)
	if event == "extended":
		return (
			f"Fuel Order {name} validity extended to {valid_until}",
			f"Fuel Order {name_html} is now valid until {escape(valid_until)}. Reprint the updated approval slip before fueling.",
		)

	frappe.throw(frappe._("Unknown Fuel Order notification event: {0}").format(event))


def _outgoing_mail_configured():
	return bool(
		frappe.db.exists(
			"Email Account",
			{
				"enable_outgoing": 1,
				"default_outgoing": 1,
				"awaiting_password": 0,
			},
		)
	)


def notify_fuel_order(order, event):
	"""Create in-app logs, with queued email when a usable default account exists."""
	if isinstance(order, str):
		order = frappe.get_doc("Fuel Order", order)

	subject, message = _event_content(order, event)
	new_recipients = []
	link = f"/app/fuel-order/{quote(order.name, safe='')}"
	for user in sorted(_recipients(order, event)):
		filters = {
			"for_user": user,
			"document_type": "Fuel Order",
			"document_name": order.name,
			"subject": subject,
		}
		if frappe.db.exists("Notification Log", filters):
			continue

		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"email_content": message,
				"for_user": user,
				"from_user": frappe.session.user or "Administrator",
				"type": "Alert",
				"document_type": "Fuel Order",
				"document_name": order.name,
				"link": link,
			}
		).insert(ignore_permissions=True)
		new_recipients.append(user)

	if new_recipients and _outgoing_mail_configured():
		emails = [
			address
			for address in frappe.get_all(
				"User", filters={"name": ["in", new_recipients]}, pluck="email"
			)
			if address
		]
		if emails:
			try:
				frappe.sendmail(
					recipients=emails,
					subject=subject,
					message=f"{message}<br><a href='{escape(link, quote=True)}'>Open Fuel Order</a>",
					delayed=True,
					reference_doctype="Fuel Order",
					reference_name=order.name,
					is_notification=True,
				)
			except frappe.OutgoingEmailError:
				frappe.log_error(frappe.get_traceback(), "Fuel Order notification email")

	return new_recipients


def send_validity_notifications(now=None):
	"""Send each due notice once, using the order's current validity and state."""
	now = get_datetime(now or now_datetime())
	orders = frappe.get_all(
		"Fuel Order",
		filters={
			"docstatus": 1,
			"workflow_state": "Approved",
			"valid_until": ["<=", now + timedelta(days=1)],
		},
		fields=["name", "valid_until"],
	)

	for row in orders:
		if frappe.db.exists(
			"Fueling Transaction", {"fuel_order": row.name, "docstatus": 1}
		):
			continue

		order = frappe.get_doc("Fuel Order", row.name)
		valid_until = get_datetime(order.valid_until)
		notify_fuel_order(order, "expired" if valid_until <= now else "pre_expiry")
