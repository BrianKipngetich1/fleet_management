from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from fleet_management import master_data
from fleet_management.fleet_management.doctype.fuel_order.fuel_order import record_decision_reason
from fleet_management.tests.utils import attach_request_photos

# Vehicles at each company, held by their real holders, who request and drive (spec 006 D-9).
# Each test uses its own, so one test's open order never turns another's red.
GREEN_VEHICLES = (
	("KCL225R", "Deepak Kanji Patel", master_data.KABETE),
	("KDE189V", "Mukesh Singh", master_data.KANHA),
)
RED_VEHICLES = (
	("KBX093J", "Amrat Deepak Patel", master_data.KABETE),
	("KDE169V", "Vinu Pindoria", master_data.KANHA),
)
SLIP_VEHICLE = ("KCL966X", "Joseph Wakhungu", master_data.KANHA)


class TestRealFleetRoutes(IntegrationTestCase):
	"""Phyllis enters orders for both companies and Vishal signs off the red ones (spec 006)."""

	def setUp(self):
		super().setUp()
		no_mail = patch("fleet_management.notifications._outgoing_mail_configured", return_value=False)
		no_mail.start()
		self.addCleanup(no_mail.stop)
		master_data.load()
		settings = frappe.get_single("Fleet Management Settings")
		settings.update(
			{
				"mileage_margin_percent": 15,
				"litres_excess_percent": 10,
				"gauge_limit_percent": 75,
				"min_hours_between_fuelings": 24,
			}
		)
		settings.save(ignore_permissions=True)
		both = (master_data.KABETE, master_data.KANHA)
		self.phyllis = self._user("Fleet User", "Phyllis", both)
		self.vishal = self._user("Fleet Approver", "Vishal", both)

	def _user(self, role, first_name, locations):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"s006-{frappe.scrub(first_name)}-{frappe.generate_hash(length=6)}@example.com",
				"first_name": first_name,
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
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

	def _draft(self, vehicle, gauge=40):
		asset, holder, location = vehicle
		with self.set_user(self.phyllis):
			order = frappe.get_doc(
				{
					"doctype": "Fuel Order",
					"request_datetime": now_datetime(),
					"asset": asset,
					"actual_requester": holder,
					"driver": holder,
					"custodian": holder,
					"company_representative": master_data.REPRESENTATIVE[location],
					"operational_location": location,
					"planned_station": master_data.ECOFLAME,
					"quantity_authorization": "Full",
					"request_meter_reading": 50000,
					"request_gauge_percent": gauge,
				}
			).insert()
			return attach_request_photos(order)

	def test_phyllis_orders_for_both_companies_with_the_holder_driving(self):
		"""006-master-data-import: Requirements 5.1, 5.4, 4.1; Property 7. Each company's order goes to
		Ecoflame with its holder as driver and Phyllis as representative, and she approves it green."""
		for vehicle in GREEN_VEHICLES:
			with self.subTest(asset=vehicle[0]):
				order = self._draft(vehicle)
				self.assertEqual(order.signal, "Green", order.signal_reasons)
				self.assertEqual((order.driver, order.custodian), (vehicle[1], vehicle[1]))
				self.assertEqual(order.company_representative, master_data.PHYLLIS)
				self.assertEqual(order.assigned_location_snapshot, vehicle[2])
				with self.set_user(self.phyllis):
					approved = apply_workflow(order, "Approve")
				self.assertEqual(approved.workflow_state, "Approved")
				self.assertEqual(approved.approved_by, self.phyllis)

	def test_a_red_order_reaches_vishal_who_signs_it_off(self):
		"""006-master-data-import: Requirements 5.2, 2.5; Property 7. Phyllis cannot approve a red
		order; with her reason it waits for Vishal, for either company."""
		for vehicle in RED_VEHICLES:
			with self.subTest(asset=vehicle[0]):
				red = self._draft(vehicle, gauge=80)
				self.assertEqual(red.signal, "Red", red.signal_reasons)
				with self.set_user(self.phyllis):
					with self.assertRaises(frappe.ValidationError):
						apply_workflow(red, "Approve")
					record_decision_reason(red.name, "Submit for Approval", "Long delivery run tomorrow")
					pending = apply_workflow(frappe.get_doc("Fuel Order", red.name), "Submit for Approval")
				self.assertEqual(pending.workflow_state, "Pending Approval")

				with self.set_user(self.vishal):
					waiting = frappe.get_list(
						"Fuel Order", filters={"workflow_state": "Pending Approval"}, pluck="name"
					)
					self.assertIn(pending.name, waiting)
					record_decision_reason(pending.name, "Approve", "Checked with the holder")
					approved = apply_workflow(frappe.get_doc("Fuel Order", pending.name), "Approve")
				self.assertEqual(approved.workflow_state, "Approved")
				self.assertEqual(approved.approved_by, self.vishal)

	def test_the_slip_shows_ecoflames_address_and_email(self):
		"""006-master-data-import: Requirements 4.3; Property 7. The printed slip carries Ecoflame's
		postal address and email for a Kanha vehicle's order."""
		order = self._draft(SLIP_VEHICLE)
		with self.set_user(self.phyllis):
			approved = apply_workflow(order, "Approve")
			printed = frappe.get_print(
				"Fuel Order", approved.name, print_format="Fuel Order Approval Slip", no_letterhead=1
			)
		for value in (master_data.ECOFLAME, "P.O Box 818", "00606", "NAIROBI", "ecoflamelimited@gmail.com"):
			self.assertIn(value, printed)
