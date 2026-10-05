import json
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import record_decision_reason
from fleet_management.history import stage_cancel_reason
from fleet_management.tests.utils import attach_request_photos


class TestFuelOrderDecisions(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.no_mail = patch("fleet_management.notifications._outgoing_mail_configured", return_value=False)
		self.no_mail.start()
		self.addCleanup(self.no_mail.stop)

		suffix = frappe.generate_hash(length=8)
		self.location = self._insert("Fleet Location", location_name=f"AC12 Location {suffix}")
		self.other_location = self._insert("Fleet Location", location_name=f"AC12 Other Location {suffix}")
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC12 Diesel {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model",
			make=f"AC12 Make {suffix}",
			model=f"AC12 Model {suffix}",
			tank_capacity_litres=60,
		)
		self.station = self._insert(
			"Fuel Station",
			station_name=f"AC12 Station {suffix}",
			operational_location=self.location.name,
		)
		self.requester = self._insert("Fleet Person", person_name=f"AC12 Requester {suffix}")
		self.driver = self._insert("Fleet Person", person_name=f"AC12 Driver {suffix}")
		self.custodian = self._insert("Fleet Person", person_name=f"AC12 Custodian {suffix}")
		self.company_representative = self._insert(
			"Fleet Person", person_name=f"AC12 Representative {suffix}"
		)
		self.asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC12 Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.custodian.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
				}
			],
		)
		self._save_settings(
			mileage_margin_percent=15,
			litres_excess_percent=10,
			gauge_limit_percent=75,
			min_hours_between_fuelings=24,
		)
		self.philip = self._user(("Fleet User",), self.location.name, "Philip", "Test Clerk")
		self.vikas = self._user(("Fleet Approver",), self.location.name, "Vikas", "Test Approver")
		self.amina = self._user(("Fleet Approver",), self.other_location.name, "Amina", "Test Approver")
		self.admin = self._user(("Fleet Admin",), self.location.name, "AC12", "Test Admin")

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _save_settings(self, **values):
		settings = frappe.get_single("Fleet Management Settings")
		settings.update(values)
		settings.save(ignore_permissions=True)
		return settings

	def make_order(self, **overrides):
		values = {
			"doctype": "Fuel Order",
			"request_datetime": now_datetime(),
			"actual_requester": self.requester.name,
			"driver": self.driver.name,
			"custodian": self.custodian.name,
			"company_representative": self.company_representative.name,
			"asset": self.asset.name,
			"operational_location": self.location.name,
			"planned_station": self.station.name,
			"quantity_authorization": "Full",
			"request_meter_reading": 1000,
			"request_gauge_percent": 40,
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def _user(self, roles, location, first_name="AC12", last_name=None):
		email = f"ac12-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
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

	def _draft(self, user=None, **overrides):
		"""A saved draft with its photos, entered by the given user (Philip by default)."""
		with self.set_user(user or self.philip):
			return attach_request_photos(self.make_order(**overrides).insert())

	def _send_up(self, user=None, **overrides):
		"""A red order entered and sent up with an explanation."""
		user = user or self.philip
		order = self._draft(user, request_gauge_percent=80, **overrides)
		self.assertEqual(order.signal, "Red")
		with self.set_user(user):
			record_decision_reason(order.name, "Submit for Approval", "Driver on a long field trip")
			return apply_workflow(order, "Submit for Approval")

	def _actions(self, order, user):
		with self.set_user(user):
			order = frappe.get_doc("Fuel Order", order.name)
			return {transition.action for transition in get_transitions(order)}

	def _logs(self, order, user):
		return frappe.get_all(
			"Notification Log",
			filters={"document_type": "Fuel Order", "document_name": order.name, "for_user": user},
			pluck="subject",
		)

	def _print(self, order, user):
		with self.set_user(user):
			return frappe.get_print(
				"Fuel Order", order.name, print_format="Fuel Order Approval Slip", no_letterhead=1
			)

	def _state(self, order):
		return frappe.db.get_value("Fuel Order", order.name, "workflow_state")

	def test_philip_approves_his_own_green_order(self):
		order = self._draft()
		self.assertEqual(order.signal, "Green")

		with self.set_user(self.philip):
			approved = apply_workflow(order, "Approve")

		self.assertEqual(approved.workflow_state, "Approved")
		self.assertEqual(approved.docstatus, 1)
		self.assertEqual(approved.approved_by, self.philip)
		self.assertTrue(approved.approved_on)
		self.assertTrue(approved.valid_until)
		self.assertFalse(approved.submitted_by)
		notices = self._logs(order, self.vikas)
		self.assertFalse([subject for subject in notices if "requires approval" in subject])

	def test_philip_can_never_approve_a_red_order(self):
		red = self._draft(request_gauge_percent=80)
		self.assertEqual(red.signal, "Red")
		self.assertNotIn("Approve", self._actions(red, self.philip))
		with self.set_user(self.philip), self.assertRaises(frappe.ValidationError):
			apply_workflow(red, "Approve")
		self.assertEqual(self._state(red), "Draft")

		# Both drafts start green; approving one opens an order for the vehicle and turns the other red.
		draft = self._draft()
		other = self._draft()
		self.assertEqual(draft.signal, "Green")
		self.assertEqual(other.signal, "Green")
		with self.set_user(self.philip):
			apply_workflow(other, "Approve")
			with self.assertRaisesRegex(frappe.ValidationError, "turned red"):
				apply_workflow(draft, "Approve")

		self.assertEqual(self._state(draft), "Draft")
		self.assertEqual(frappe.db.get_value("Fuel Order", draft.name, "docstatus"), 0)

	def test_only_a_red_order_with_an_explanation_is_sent_up(self):
		green = self._draft()
		self.assertNotIn("Submit for Approval", self._actions(green, self.philip))
		with self.set_user(self.philip):
			with self.assertRaises(frappe.ValidationError):
				apply_workflow(green, "Submit for Approval")
			with self.assertRaises(frappe.PermissionError):
				record_decision_reason(green.name, "Submit for Approval", "It is green")
		self.assertEqual(self._state(green), "Draft")

		red = self._draft(request_gauge_percent=80)
		with self.set_user(self.philip):
			with self.assertRaisesRegex(frappe.ValidationError, "explanation is required"):
				apply_workflow(red, "Submit for Approval")
			self.assertEqual(self._state(red), "Draft")

			record_decision_reason(red.name, "Submit for Approval", "  Long trip to the Mombasa plant  ")
			sent = apply_workflow(red, "Submit for Approval")

		self.assertEqual(sent.workflow_state, "Pending Approval")
		self.assertEqual(sent.submitted_by, self.philip)
		self.assertEqual(
			frappe.db.get_value("Fuel Order", sent.name, "send_up_explanation"),
			"Long trip to the Mombasa plant",
		)

	def test_philip_rejects_or_withdraws_only_with_a_reason(self):
		draft = self._draft()
		with self.set_user(self.philip):
			with self.assertRaisesRegex(frappe.ValidationError, "written reason is required"):
				apply_workflow(draft, "Reject")
			self.assertEqual(self._state(draft), "Draft")

			record_decision_reason(draft.name, "Reject", "Vehicle is off the road")
			rejected = apply_workflow(draft, "Reject")

		self.assertEqual(rejected.workflow_state, "Rejected")
		self.assertEqual(rejected.rejected_by, self.philip)
		self.assertTrue(rejected.rejected_on)
		self.assertEqual(rejected.decision_reason, "Vehicle is off the road")
		self.assertEqual(rejected.decision_action, "Reject")
		self.assertEqual(rejected.decision_reason_by, self.philip)

		pending = self._send_up()
		self.assertIn("Withdraw", self._actions(pending, self.philip))
		with self.set_user(self.philip):
			with self.assertRaisesRegex(frappe.ValidationError, "written reason is required"):
				apply_workflow(pending, "Withdraw")
			record_decision_reason(pending.name, "Withdraw", "Entered against the wrong vehicle")
			withdrawn = apply_workflow(pending, "Withdraw")

		self.assertEqual(withdrawn.workflow_state, "Rejected")
		self.assertEqual(withdrawn.rejected_by, self.philip)
		self.assertEqual(withdrawn.decision_action, "Withdraw")

	def test_only_a_permitted_independent_approver_decides_a_sent_up_order(self):
		pending = self._send_up()
		with self.set_user(self.vikas):
			with self.assertRaisesRegex(frappe.ValidationError, "written reason is required"):
				apply_workflow(pending, "Approve")
			self.assertEqual(self._state(pending), "Pending Approval")

		with self.set_user(self.amina), self.assertRaises(frappe.PermissionError):
			apply_workflow(pending, "Approve")
		self.assertEqual(self._state(pending), "Pending Approval")

		with self.set_user(self.vikas):
			record_decision_reason(pending.name, "Approve", "Confirmed the trip with the site manager")
			approved = apply_workflow(pending, "Approve")

		self.assertEqual(approved.workflow_state, "Approved")
		self.assertEqual(approved.approved_by, self.vikas)
		self.assertEqual(approved.decision_reason_by, self.vikas)
		self.assertEqual(approved.submitted_by, self.philip)

		self_approver = self._user(("Fleet User", "Fleet Approver"), self.location.name)
		own = self._send_up(self_approver)
		with self.set_user(self_approver):
			record_decision_reason(own.name, "Approve", "My own order")
			with self.assertRaisesRegex(frappe.ValidationError, "Self approval is not allowed"):
				apply_workflow(own, "Approve")
		self.assertEqual(self._state(own), "Pending Approval")

		linked_approver = self._user(("Fleet Approver",), self.location.name)
		linked_requester = self._insert(
			"Fleet Person",
			person_name=f"AC14 Linked Requester {frappe.generate_hash(length=8)}",
			user=linked_approver,
		)
		asked = self._send_up(actual_requester=linked_requester.name)
		with self.set_user(linked_approver):
			record_decision_reason(asked.name, "Reject", "I asked for it")
			with self.assertRaisesRegex(frappe.ValidationError, "Self approval is not allowed"):
				apply_workflow(asked, "Reject")
		self.assertEqual(self._state(asked), "Pending Approval")

	def test_a_sent_up_order_notifies_the_approver_and_admin_once_each(self):
		pending = self._send_up()
		for user in (self.vikas, self.admin):
			with self.subTest(user=user):
				self.assertEqual(len(self._logs(pending, user)), 1)
		self.assertFalse(self._logs(pending, self.amina))

		with self.set_user(self.admin):
			frappe.get_doc("Fuel Order", pending.name).save(ignore_permissions=True)

		for user in (self.vikas, self.admin):
			with self.subTest(user=user, after="second save"):
				self.assertEqual(len(self._logs(pending, user)), 1)

	def test_the_slip_names_whoever_approved_it(self):
		green = self._draft()
		with self.set_user(self.philip):
			green = apply_workflow(green, "Approve")
		self.assertIn("Philip Test Clerk", self._print(green, self.philip))

		pending = self._send_up()
		with self.set_user(self.vikas):
			record_decision_reason(pending.name, "Approve", "Genuine long trip")
			red = apply_workflow(pending, "Approve")
		printed = self._print(red, self.vikas)

		self.assertGreaterEqual(printed.count("Vikas Test Approver"), 2)
		self.assertNotIn("Philip Test Clerk", printed)

	def test_record_decision_reason_refuses_blank_reasons_and_unavailable_actions(self):
		draft = self._draft(request_gauge_percent=80)
		with self.set_user(self.philip):
			for reason in ("", "   "):
				with self.subTest(reason=repr(reason)), self.assertRaises(frappe.ValidationError):
					record_decision_reason(draft.name, "Submit for Approval", reason)
			with self.assertRaises(frappe.PermissionError):
				record_decision_reason(draft.name, "Approve", "A red order")
		self.assertFalse(frappe.db.get_value("Fuel Order", draft.name, "send_up_explanation"))

		pending = self._send_up()
		with self.set_user(self.philip), self.assertRaises(frappe.PermissionError):
			record_decision_reason(pending.name, "Approve", "Philip is not the approver")
		self.assertFalse(frappe.db.get_value("Fuel Order", pending.name, "decision_reason"))

		# The fields change only through the recorded reason, never through a save.
		with self.set_user(self.philip):
			order = frappe.get_doc("Fuel Order", pending.name)
			order.update(
				{
					"decision_reason": "typed in",
					"decision_action": "Approve",
					"decision_reason_by": self.philip,
					"send_up_explanation": "changed",
				}
			)
			order.save()
		persisted = frappe.get_doc("Fuel Order", pending.name)
		self.assertFalse(persisted.decision_reason)
		self.assertFalse(persisted.decision_action)
		self.assertEqual(persisted.send_up_explanation, "Driver on a long field trip")


	def test_history_keeps_workflow_reasons_and_separate_partial_authorization(self):
		partial = self._draft(
			request_gauge_percent=20,
			quantity_authorization="Partial",
			authorized_quantity_litres=7,
			partial_authorization_reason="Only seven litres are available at this station",
		)
		with self.set_user(self.philip):
			partial = apply_workflow(partial, "Approve")
		partial_event = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": partial.name, "event_type": "Partial Authorization"},
			fields=["name", "actor", "reason", "related_event", "source_facts_json"],
			limit=1,
		)[0]
		self.assertEqual(partial_event.actor, self.philip)
		self.assertEqual(partial_event.reason, "Only seven litres are available at this station")
		self.assertTrue(partial_event.related_event)
		partial_facts = json.loads(partial_event.source_facts_json)
		self.assertEqual(partial_facts["authorized_quantity_litres"], 7)
		self.assertEqual(partial_facts["approval_event"], partial_event.related_event)

		pending = self._send_up()
		issue_event = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": pending.name, "event_type": "Signal Issue"},
			fields=["name", "issue_key"],
			limit=1,
		)[0]
		sent_event = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": pending.name, "event_type": "Sent for Approval"},
			fields=[
				"name",
				"actor",
				"event_datetime",
				"reason",
				"source_facts_json",
				"issue_key",
				"related_event",
			],
			limit=1,
		)[0]
		self.assertEqual(sent_event.actor, self.philip)
		self.assertEqual(sent_event.reason, "Driver on a long field trip")
		facts = json.loads(sent_event.source_facts_json)
		self.assertEqual(facts["workflow_state_before"], "Draft")
		self.assertEqual(facts["order"]["signal_details"]["signal"], "Red")
		self.assertEqual(sent_event.issue_key, issue_event.issue_key)
		self.assertEqual(sent_event.related_event, issue_event.name)
		self.assertEqual(facts["signal_history_event"], issue_event.name)
		self.assertTrue(sent_event.event_datetime)

		with self.set_user(self.vikas):
			record_decision_reason(pending.name, "Approve", "Confirmed with the site manager")
			approved = apply_workflow(pending, "Approve")
		approved_event = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": approved.name, "event_type": "Approved"},
			fields=["name", "actor", "reason", "source_facts_json", "issue_key", "related_event"],
			limit=1,
		)[0]
		self.assertEqual(approved_event.actor, self.vikas)
		self.assertEqual(approved_event.reason, "Confirmed with the site manager")
		self.assertEqual(
			json.loads(approved_event.source_facts_json)["order"]["signal_details"]["signal"],
			"Red",
		)
		self.assertEqual(approved_event.issue_key, issue_event.issue_key)
		self.assertEqual(approved_event.related_event, issue_event.name)

		immutable = frappe.get_doc("Fuel Order History Event", sent_event.name)
		immutable.summary = "Changed later"
		with self.assertRaises(frappe.PermissionError):
			immutable.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(
				"Fuel Order History Event", sent_event.name, force=True, ignore_permissions=True
			)

	def test_signal_issue_history_snapshots_changes_deduplicates_resolves_and_reopens(self):
		with self.set_user(self.philip):
			order = self.make_order(request_gauge_percent=20).insert()
			order = attach_request_photos(order)
			order.request_gauge_percent = 80
			order.save()

			issues = frappe.get_all(
				"Fuel Order History Event",
				filters={"fuel_order": order.name, "event_type": "Signal Issue"},
				fields=["name", "actor", "issue_key", "related_event", "source_facts_json", "evidence_references_json"],
				order_by="event_datetime asc, creation asc",
			)
			self.assertEqual(len(issues), 1)
			first = issues[0]
			self.assertEqual(first.actor, self.philip)
			self.assertFalse(first.related_event)
			first_facts = json.loads(first.source_facts_json)
			self.assertEqual(first_facts["signal_result"]["signal"], "Red")
			self.assertIn("Tank nearly full", first_facts["signal_result"]["reasons"][0]["text"])
			self.assertEqual(len(json.loads(first.evidence_references_json)), 2)

			order = frappe.get_doc("Fuel Order", order.name)
			order.save()
			self.assertEqual(
				frappe.db.count(
					"Fuel Order History Event",
					{"fuel_order": order.name, "event_type": "Signal Issue"},
				),
				1,
			)

			order = frappe.get_doc("Fuel Order", order.name)
			order.request_gauge_percent = 90
			order.save()
			issues = frappe.get_all(
				"Fuel Order History Event",
				filters={"fuel_order": order.name, "event_type": "Signal Issue"},
				fields=["name", "issue_key", "related_event", "source_facts_json"],
				order_by="event_datetime asc, creation asc",
			)
			self.assertEqual(len(issues), 2)
			self.assertEqual(issues[1].issue_key, first.issue_key)
			self.assertEqual(issues[1].related_event, first.name)
			self.assertIn("90%", json.loads(issues[1].source_facts_json)["signal_result"]["reasons"][0]["details"][0])

			self._save_settings(gauge_limit_percent=82)
			order = frappe.get_doc("Fuel Order", order.name)
			order.save()
			issues = frappe.get_all(
				"Fuel Order History Event",
				filters={"fuel_order": order.name, "event_type": "Signal Issue"},
				fields=["name", "issue_key", "related_event", "source_facts_json"],
				order_by="event_datetime asc, creation asc",
			)
			self.assertEqual(len(issues), 3)
			self.assertEqual(issues[2].issue_key, first.issue_key)
			self.assertEqual(issues[2].related_event, issues[1].name)
			self.assertIn("above 82%", json.loads(issues[2].source_facts_json)["signal_result"]["reasons"][0]["text"])

			order = frappe.get_doc("Fuel Order", order.name)
			order.request_gauge_percent = 20
			order.save()
			resolved = frappe.get_all(
				"Fuel Order History Event",
				filters={"fuel_order": order.name, "event_type": "Signal Resolved"},
				fields=["name", "issue_key", "related_event", "source_facts_json"],
				limit=1,
			)
			self.assertEqual(len(resolved), 1)
			self.assertEqual(resolved[0].issue_key, first.issue_key)
			self.assertEqual(resolved[0].related_event, issues[2].name)
			self.assertEqual(json.loads(resolved[0].source_facts_json)["signal_result"]["signal"], "Green")

			order = frappe.get_doc("Fuel Order", order.name)
			order.save()
			self.assertEqual(
				frappe.db.count(
					"Fuel Order History Event",
					{"fuel_order": order.name, "event_type": "Signal Resolved"},
				),
				1,
			)

			order = frappe.get_doc("Fuel Order", order.name)
			order.request_gauge_percent = 85
			order.save()
			reopened = frappe.get_all(
				"Fuel Order History Event",
				filters={"fuel_order": order.name, "event_type": "Signal Issue"},
				fields=["name", "issue_key", "related_event"],
				order_by="event_datetime desc, creation desc",
				limit=1,
			)[0]
			self.assertNotEqual(reopened.issue_key, first.issue_key)
			self.assertEqual(reopened.related_event, resolved[0].name)

	def test_cancelling_an_order_requires_a_reason_and_keeps_current_permissions(self):
		draft = self._draft(request_gauge_percent=20)
		with self.set_user(self.philip):
			approved = apply_workflow(draft, "Approve")
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Fuel Order", approved.name).cancel()

		with self.set_user(self.admin):
			with self.assertRaisesRegex(frappe.ValidationError, "cancellation reason is required"):
				frappe.get_doc("Fuel Order", approved.name).cancel()
			stage_cancel_reason("Fuel Order", approved.name, "Order was created for the wrong vehicle")
			frappe.get_doc("Fuel Order", approved.name).cancel()

		event = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": approved.name, "event_type": "Cancelled"},
			fields=["actor", "reason", "source_facts_json"],
			limit=1,
		)[0]
		self.assertEqual(event.actor, self.admin)
		self.assertEqual(event.reason, "Order was created for the wrong vehicle")
		self.assertEqual(json.loads(event.source_facts_json)["workflow_state"], "Approved")

	def test_history_records_each_print_reprint_and_extension(self):
		pending = self._send_up()
		with self.set_user(self.vikas):
			record_decision_reason(pending.name, "Approve", "Confirmed with the site manager")
			approved = apply_workflow(pending, "Approve")
		self._print(approved, self.vikas)
		self._print(approved, self.vikas)

		with self.set_user(self.vikas):
			approved = frappe.get_doc("Fuel Order", approved.name)
			new_valid_until = get_datetime(approved.valid_until) + timedelta(hours=12)
			approved.extend_validity(
				new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "Station closure delayed the trip"
			)
			approved = frappe.get_doc("Fuel Order", approved.name)
			self._print(approved, self.vikas)

		prints = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": approved.name, "event_type": "Slip Printed"},
			fields=["slip_revision"],
			order_by="event_datetime asc, creation asc",
		)
		self.assertEqual([event.slip_revision for event in prints], [1, 1, 2])
		extension = frappe.get_all(
			"Fuel Order History Event",
			filters={"fuel_order": approved.name, "event_type": "Validity Extended"},
			fields=["actor", "reason", "source_facts_json", "slip_revision"],
			limit=1,
		)[0]
		self.assertEqual(extension.actor, self.vikas)
		self.assertEqual(extension.reason, "Station closure delayed the trip")
		self.assertEqual(extension.slip_revision, 2)
		self.assertIn("old_valid_until", json.loads(extension.source_facts_json))
