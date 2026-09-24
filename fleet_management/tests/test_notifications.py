from datetime import timedelta
from unittest.mock import patch
from urllib.parse import quote

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from fleet_management.notifications import notify_fuel_order, send_validity_notifications
from fleet_management.permissions import get_permitted_location_names


class TestFuelOrderNotifications(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.no_mail = patch("fleet_management.notifications._outgoing_mail_configured", return_value=False)
		self.no_mail.start()
		self.addCleanup(self.no_mail.stop)

		suffix = frappe.generate_hash(length=8)
		self.location = self._insert("Fleet Location", location_name=f"Notify Location {suffix}")
		self.other_location = self._insert(
			"Fleet Location", location_name=f"Notify Other Location {suffix}"
		)
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"Notify Diesel {suffix}")
		self.station = self._insert(
			"Fuel Station",
			station_name=f"Notify Station {suffix}",
			operational_location=self.location.name,
			active=1,
			approved=1,
		)
		self.person = self._insert("Fleet Person", person_name=f"Notify Person {suffix}")
		self.asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"Notify Asset {suffix}",
			asset_type="Vehicle",
			fuel_type=self.fuel_type.name,
			tank_capacity_litres=60,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		self.requester = self._user(("Fleet User",), self.location.name)
		self.approver = self._user(("Fleet Approver",), self.location.name)
		self.disabled_approver = self._user(("Fleet Approver",), self.location.name)
		frappe.db.set_value("User", self.disabled_approver, "enabled", 0)
		frappe.clear_cache(user=self.disabled_approver)
		self.other_approver = self._user(("Fleet Approver",), self.other_location.name)
		self.local_admin = self._user(
			("Fleet Admin", "Fleet Approver"), self.location.name
		)
		self.other_admin = self._user(("Fleet Admin",), self.other_location.name)

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _user(self, roles, *locations):
		email = f"notify-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Notification Test",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		for location in locations:
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user.name,
					"allow": "Fleet Location",
					"for_value": location,
				}
			).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		return user.name

	def _make_order(self):
		return frappe.get_doc(
			{
				"doctype": "Fuel Order",
				"request_datetime": now_datetime(),
				"actual_requester": self.person.name,
				"driver": self.person.name,
				"custodian": self.person.name,
				"company_representative": self.person.name,
				"asset": self.asset.name,
				"operational_location": self.location.name,
				"planned_station": self.station.name,
				"request_meter_reading": 1000,
				"request_gauge_percent": 40,
			}
		)

	def _make_approved_order(self):
		with self.set_user(self.requester):
			order = apply_workflow(self._make_order().insert(), "Submit for Approval")
		with self.set_user(self.approver):
			order = apply_workflow(order, "Approve")
		return order

	def _logs(self, order):
		return frappe.get_all(
			"Notification Log",
			filters={"document_type": "Fuel Order", "document_name": order.name},
			fields=["for_user", "subject", "email_content", "link"],
		)

	def _recipients_for(self, order, text):
		return {row.for_user for row in self._logs(order) if text in row.subject}

	def _users_with_role(self, role):
		users = frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"
		)
		return {user for user in users if user != "Administrator" and role in frappe.get_roles(user)}

	def test_pending_approval_is_location_scoped_deduplicated_and_secure(self):
		enabled = frappe.get_all("User", filters={"enabled": 1}, pluck="name")
		permitted_approvers = {
			user
			for user in enabled
			if "Fleet Approver" in frappe.get_roles(user)
			and self.location.name in get_permitted_location_names(user)
		}
		self.assertEqual(permitted_approvers, {self.approver, self.local_admin})
		self.assertEqual(
			get_permitted_location_names(self.approver), {self.location.name},
			msg=f"Approver scope: {get_permitted_location_names(self.approver)}",
		)
		self.assertEqual(
			get_permitted_location_names(self.other_approver), {self.other_location.name},
			msg=f"Other approver scope: {get_permitted_location_names(self.other_approver)}",
		)
		with self.set_user(self.requester):
			order = apply_workflow(self._make_order().insert(), "Submit for Approval")

		logs = [row for row in self._logs(order) if "requires approval" in row.subject]
		admins = self._users_with_role("Fleet Admin")
		self.assertEqual(
			{row.for_user for row in logs},
			{self.approver} | admins,
		)
		self.assertEqual(len({row.for_user for row in logs}), len(logs))
		self.assertNotIn(self.other_approver, {row.for_user for row in logs})
		self.assertNotIn(self.disabled_approver, {row.for_user for row in logs})
		self.assertEqual(logs[0].link, f"/app/fuel-order/{quote(order.name, safe='')}")

		with self.set_user(self.other_approver):
			self.assertFalse(frappe.has_permission("Fuel Order", "read", order))

	def test_approval_and_rejection_notify_submitter_and_fleet_admins(self):
		with self.set_user(self.requester):
			approved_order = apply_workflow(self._make_order().insert(), "Submit for Approval")
			rejected_order = apply_workflow(self._make_order().insert(), "Submit for Approval")

		with self.set_user(self.approver):
			apply_workflow(approved_order, "Approve")
			apply_workflow(rejected_order, "Reject")

		admins = self._users_with_role("Fleet Admin")
		self.assertEqual(
			self._recipients_for(approved_order, "was approved"),
			{self.requester} | admins,
		)
		self.assertEqual(
			self._recipients_for(rejected_order, "was rejected"),
			{self.requester} | admins,
		)
		self.assertNotIn(self.approver, self._recipients_for(approved_order, "was approved"))

	def test_scheduler_notices_are_idempotent_and_skip_completed_or_inactive_orders(self):
		order = self._make_approved_order()
		soon = now_datetime() + timedelta(hours=12)
		frappe.db.set_value("Fuel Order", order.name, "valid_until", soon)

		send_validity_notifications()
		send_validity_notifications()
		pre_expiry = [row for row in self._logs(order) if "expires in 1 day" in row.subject]
		self.assertEqual(
			{row.for_user for row in pre_expiry},
			{self.approver} | self._users_with_role("Fleet Admin"),
		)
		self.assertEqual(len(pre_expiry), len({row.for_user for row in pre_expiry}))

		frappe.db.set_value("Fuel Order", order.name, "valid_until", now_datetime() - timedelta(minutes=1))
		send_validity_notifications()
		send_validity_notifications()
		expired = [row for row in self._logs(order) if "expired (" in row.subject]
		self.assertEqual(
			{row.for_user for row in expired},
			{self.approver} | self._users_with_role("Fleet Admin"),
		)
		self.assertEqual(len(expired), len({row.for_user for row in expired}))

		completed = self._make_approved_order()
		frappe.db.set_value(
			"Fuel Order", completed.name, "valid_until", now_datetime() - timedelta(minutes=1)
		)
		transaction = self._insert("Fueling Transaction", fuel_order=completed.name)
		frappe.db.set_value("Fueling Transaction", transaction.name, "docstatus", 1)

		inactive = self._make_approved_order()
		frappe.db.set_value("Fuel Order", inactive.name, "valid_until", now_datetime() - timedelta(minutes=1))
		frappe.db.set_value("Fuel Order", inactive.name, "docstatus", 2)
		send_validity_notifications()
		self.assertFalse(any("expired (" in row.subject for row in self._logs(completed)))
		self.assertFalse(any("expired (" in row.subject for row in self._logs(inactive)))

	def test_extension_notice_uses_new_validity_and_reprint_requirement(self):
		order = self._make_approved_order()
		new_valid_until = order.valid_until + timedelta(days=2)
		with self.set_user(self.approver):
			order.extend_validity(new_valid_until, "Notification test extension")

		extension_logs = [row for row in self._logs(order) if "validity extended" in row.subject]
		self.assertEqual(
			{row.for_user for row in extension_logs},
			{self.approver} | self._users_with_role("Fleet Admin"),
		)
		valid_until_text = new_valid_until.strftime("%Y-%m-%d %H:%M:%S")
		self.assertTrue(all(valid_until_text in row.subject for row in extension_logs))
		self.assertTrue(
			all("Reprint the updated approval slip before fueling" in row.email_content for row in extension_logs)
		)

		# A scheduler run after extension uses the new deadline, so the old due date is obsolete.
		send_validity_notifications()
		self.assertFalse(any("expires in 1 day" in row.subject for row in self._logs(order)))

	def test_email_uses_frappe_queue_only_when_default_outgoing_is_configured(self):
		without_mail = self._make_order().insert(ignore_permissions=True)
		with patch("fleet_management.notifications._outgoing_mail_configured", return_value=False):
			with patch("fleet_management.notifications.frappe.sendmail") as sendmail:
				notify_fuel_order(without_mail, "pending_approval")
			sendmail.assert_not_called()

		with patch("fleet_management.notifications._outgoing_mail_configured", return_value=True):
			with patch("fleet_management.notifications.frappe.sendmail") as sendmail:
				second = self._make_order().insert(ignore_permissions=True)
				notify_fuel_order(second, "pending_approval")

		sendmail.assert_called_once()
		self.assertTrue(sendmail.call_args.kwargs["delayed"])
		self.assertEqual(
			set(sendmail.call_args.kwargs["recipients"]),
			{
				frappe.db.get_value("User", user, "email")
				for user in {self.approver} | self._users_with_role("Fleet Admin")
			},
		)
		self.assertFalse(sendmail.call_args.kwargs.get("now", False))
