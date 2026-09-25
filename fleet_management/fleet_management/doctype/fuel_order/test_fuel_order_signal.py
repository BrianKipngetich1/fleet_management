from datetime import timedelta

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import (
	get_average_km_per_litre,
	get_mileage_intervals,
	has_open_order,
)
from fleet_management.tests.utils import attach_request_photos


class TestFuelOrderSignal(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		suffix = frappe.generate_hash(length=8)
		self.suffix = suffix
		self.location = self._insert("Fleet Location", location_name=f"AC09 Location {suffix}")
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC09 Diesel {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model",
			make=f"AC09 Make {suffix}",
			model=f"AC09 Model {suffix}",
			tank_capacity_litres=60,
		)
		self.station = self._insert(
			"Fuel Station",
			station_name=f"AC09 Station {suffix}",
			operational_location=self.location.name,
		)
		self.requester = self._insert("Fleet Person", person_name=f"AC09 Requester {suffix}")
		self.driver = self._insert("Fleet Person", person_name=f"AC09 Driver {suffix}")
		self.custodian = self._insert("Fleet Person", person_name=f"AC09 Custodian {suffix}")
		self.company_representative = self._insert(
			"Fleet Person", person_name=f"AC09 Representative {suffix}"
		)
		self.asset = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC09 Asset {suffix}",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.custodian.name,
					"assigned_location": self.location.name,
					"effective_from": "2026-01-01",
					"primary_driver": self.driver.name,
				}
			],
		)
		self._save_settings(
			mileage_margin_percent=15,
			litres_excess_percent=10,
			gauge_limit_percent=75,
			min_hours_between_fuelings=24,
		)

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

	def _user(self, roles, location):
		email = f"ac09-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AC09",
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

	def _send_up(self, **overrides):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			return apply_workflow(
				attach_request_photos(self.make_order(**overrides).insert()), "Submit for Approval"
			)

	def _approve(self, order):
		approver = self._user(("Fleet Approver",), self.location.name)
		with self.set_user(approver):
			return apply_workflow(order, "Approve"), approver

	def _reasons(self, order):
		return order.signal_reasons.split("\n") if order.signal_reasons else []

	def test_first_order_at_home_with_the_usual_driver_is_green(self):
		order = self.make_order().insert(ignore_permissions=True)

		self.assertEqual(order.signal, "Green")
		self.assertEqual(self._reasons(order), [])
		self.assertEqual(order.average_km_per_litre, 10)

	def test_signal_is_recomputed_on_every_save(self):
		order = self.make_order().insert(ignore_permissions=True)

		order.request_gauge_percent = 80
		order.save(ignore_permissions=True)
		self.assertEqual(order.signal, "Red")
		reasons = self._reasons(order)
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Tank nearly full"), reasons)

		order.request_gauge_percent = 40
		order.save(ignore_permissions=True)
		self.assertEqual(order.signal, "Green")
		self.assertEqual(self._reasons(order), [])
		self.assertEqual(frappe.db.get_value("Fuel Order", order.name, "signal"), "Green")

	def test_limits_come_from_settings(self):
		self._save_settings(gauge_limit_percent=85)
		order = self.make_order(request_gauge_percent=80).insert(ignore_permissions=True)
		self.assertEqual(order.signal, "Green")

		for gauge, colour in ((85, "Green"), (86, "Red")):
			with self.subTest(gauge=gauge):
				order.request_gauge_percent = gauge
				order.save(ignore_permissions=True)
				self.assertEqual(order.signal, colour)

	def test_open_order_turns_a_new_order_red(self):
		draft = self.make_order().insert(ignore_permissions=True)
		self.assertFalse(has_open_order(self.asset.name))

		pending = self._send_up()
		self.assertTrue(has_open_order(self.asset.name, exclude_order=draft.name))
		self.assertFalse(has_open_order(self.asset.name, exclude_order=pending.name))

		approved, _approver = self._approve(pending)
		self.assertEqual(approved.workflow_state, "Approved")
		# The approved order is never counted against itself.
		self.assertEqual(approved.signal, "Green")
		self.assertEqual(frappe.db.get_value("Fuel Order", approved.name, "signal"), "Green")

		# 36 L of room at 10 km/L since the approved order's 1000 km, so only the open order is flagged.
		order = self.make_order(request_meter_reading=1360).insert(ignore_permissions=True)
		self.assertEqual(order.signal, "Red")
		reasons = self._reasons(order)
		self.assertEqual(len(reasons), 1, reasons)
		self.assertTrue(reasons[0].startswith("Open order exists"), reasons)

	def test_away_from_home_and_not_the_usual_driver(self):
		away = self._insert("Fleet Location", location_name=f"AC09 Away {self.suffix}")
		away_station = self._insert(
			"Fuel Station", station_name=f"AC09 Away Station {self.suffix}", operational_location=away.name
		)
		other_driver = self._insert("Fleet Person", person_name=f"AC09 Other Driver {self.suffix}")

		order = self.make_order(
			operational_location=away.name, planned_station=away_station.name, driver=other_driver.name
		).insert(ignore_permissions=True)

		self.assertEqual(order.signal, "Red")
		reasons = self._reasons(order)
		self.assertEqual(len(reasons), 2, reasons)
		self.assertTrue(reasons[0].startswith("Away from home"), reasons)
		self.assertTrue(reasons[1].startswith("Not the usual driver"), reasons)

	def test_average_is_taken_over_the_last_five_intervals(self):
		# These rows stand in for completed full-to-full intervals without running the
		# Fueling Transaction workflow; the oldest is 400 km / 80 L, the five newest 300 km / 30 L.
		for days_ago, distance, litres in ((7, 400, 80), *((days, 300, 30) for days in (6, 5, 4, 3, 2))):
			frappe.get_doc(
				{
					"doctype": "Fueling Transaction",
					"name": frappe.generate_hash(length=10),
					"docstatus": 1,
					"asset": self.asset.name,
					"actual_fueling_datetime": now_datetime() - timedelta(days=days_ago),
					"distance_km": distance,
					"qualifying_litres": litres,
					"km_per_litre": distance / litres,
					"full_tank_confirmed": 1,
				}
			).db_insert()

		intervals = get_mileage_intervals(self.asset.name)
		self.assertEqual(len(intervals), 5)
		self.assertEqual([row.km_per_litre for row in intervals], [10] * 5)
		# Newest first: with room for all six, the 5 km/L interval comes last.
		self.assertEqual(get_mileage_intervals(self.asset.name, limit=6)[-1].km_per_litre, 5)

		self.assertEqual(get_average_km_per_litre(intervals, 7.5), 10.0)
		self.assertEqual(get_average_km_per_litre([], 7.5), 7.5)

		order = self.make_order().insert(ignore_permissions=True)
		self.assertEqual(order.average_km_per_litre, 10.0)

	def test_signal_is_frozen_once_approved(self):
		approved, approver = self._approve(self._send_up())
		self.assertEqual(approved.signal, "Green")

		self._save_settings(gauge_limit_percent=10)
		new_valid_until = get_datetime(approved.valid_until) + timedelta(hours=1)
		with self.set_user(approver):
			approved.extend_validity(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "Signal freeze check")

		persisted = frappe.get_doc("Fuel Order", approved.name)
		self.assertEqual(persisted.slip_revision, 2)
		self.assertEqual(persisted.signal, "Green")
		self.assertFalse(persisted.signal_reasons)

	def test_settings_refuse_a_gauge_limit_of_100(self):
		with self.assertRaises(frappe.ValidationError):
			self._save_settings(gauge_limit_percent=100)
