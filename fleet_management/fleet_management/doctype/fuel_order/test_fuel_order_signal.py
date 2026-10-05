import json
from datetime import timedelta

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import (
	get_average_km_per_litre,
	get_latest_full_tank_baseline,
	get_mileage_intervals,
	has_open_order,
	preview_signal,
	record_decision_reason,
)
from fleet_management.tests.utils import attach_request_photos, decide, send_up


# specs/009-fuel-order-ux Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3; Property 3
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

	def _approve_green(self, **overrides):
		# A green order is approved straight from Draft by the Fleet User who entered it.
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			return decide(attach_request_photos(self.make_order(**overrides).insert()), "Approve")

	def _reasons(self, order):
		return order.signal_reasons.split("\n") if order.signal_reasons else []

	def test_first_order_at_home_with_the_usual_driver_is_green(self):
		order = self.make_order().insert(ignore_permissions=True)

		self.assertEqual(order.signal, "Green")
		self.assertEqual(self._reasons(order), [])
		self.assertEqual(order.average_km_per_litre, 10)
		self.assertEqual(
			json.loads(order.signal_details_json)["signal_inputs"]["full_tank_mileage_check"]["status"],
			"skipped",
		)

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

	def test_signal_preview_waits_for_required_readings_without_reusing_old_result(self):
		waiting = preview_signal(
			asset=self.asset.name,
			request_meter_reading="",
			request_gauge_percent=80,
			operational_location=self.location.name,
			driver=self.driver.name,
		)
		self.assertEqual(waiting["status"], "waiting")
		self.assertEqual(waiting["waiting_for"], ["Odometer"])
		self.assertIsNone(waiting["signal"])
		self.assertEqual(waiting["reasons"], [])
		self.assertEqual(waiting["request_summary"]["estimated_litres"], 12)
		gauge_waiting = preview_signal(
			asset=self.asset.name,
			request_meter_reading=1000,
			request_gauge_percent="",
			operational_location=self.location.name,
			driver=self.driver.name,
		)
		self.assertEqual(gauge_waiting["status"], "waiting")
		self.assertEqual(gauge_waiting["waiting_for"], ["Current Gauge (%)"])
		self.assertEqual(gauge_waiting["reasons"], [])
		partial_waiting = preview_signal(
			asset=self.asset.name,
			request_meter_reading=1000,
			request_gauge_percent=40,
			quantity_authorization="Partial",
			authorized_quantity_litres="",
			operational_location=self.location.name,
			driver=self.driver.name,
		)
		self.assertEqual(partial_waiting["status"], "complete")

		preview = preview_signal(
			asset=self.asset.name,
			request_meter_reading=1000,
			request_gauge_percent=80,
			operational_location=self.location.name,
			driver=self.driver.name,
		)
		self.assertEqual(preview["status"], "complete")
		self.assertEqual(preview["signal"], "Red")
		self.assertTrue(preview["reasons"][0]["text"].startswith("Tank nearly full"))

	def test_preview_and_save_use_the_same_server_signal_calculation(self):
		values = {
			"asset": self.asset.name,
			"request_meter_reading": 1000,
			"request_gauge_percent": 80,
			"operational_location": self.location.name,
			"driver": self.driver.name,
			"quantity_authorization": "Full",
		}
		preview = preview_signal(**values)
		order = self.make_order(**{key: value for key, value in values.items() if key != "asset"}).insert(
			ignore_permissions=True
		)
		saved = json.loads(order.signal_details_json)
		self.assertEqual(preview["signal"], saved["signal"])
		self.assertEqual(preview["reasons"], saved["reasons"])
		self.assertEqual(preview["signal_inputs"], saved["signal_inputs"])
		self.assertEqual(preview["request_summary"], saved["request_summary"])

	def test_browser_string_inputs_are_normalized_before_signal_calculation(self):
		preview = preview_signal(
			asset=self.asset.name,
			request_meter_reading="1000",
			request_gauge_percent="40",
			quantity_authorization="Partial",
			authorized_quantity_litres="",
			operational_location=self.location.name,
			driver=self.driver.name,
		)

		self.assertEqual(preview["status"], "complete")
		self.assertEqual(preview["signal"], "Green")
		self.assertEqual(preview["signal_inputs"]["current_reading"], 1000)
		self.assertEqual(preview["signal_inputs"]["gauge_percent"], 40)

	def test_client_signal_values_are_replaced_by_server_calculation(self):
		order = self.make_order(
			request_gauge_percent=80,
			signal="Green",
			signal_reasons="Client supplied reason",
			signal_details_json=(
				'{"signal":"Green","signal_inputs":{"full_tank_mileage_check":{"status":"fail"}}}'
			),
		).insert(ignore_permissions=True)

		self.assertEqual(order.signal, "Red")
		self.assertTrue(order.signal_reasons.startswith("Tank nearly full"))
		server_signal = json.loads(order.signal_details_json)
		self.assertEqual(server_signal["signal"], "Red")
		self.assertEqual(server_signal["signal_inputs"]["full_tank_mileage_check"]["status"], "skipped")

	def test_signal_is_recomputed_before_approval_after_limits_change(self):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			order = attach_request_photos(self.make_order(request_gauge_percent=75).insert())
			self.assertEqual(order.signal, "Green")

		self._save_settings(gauge_limit_percent=74)
		with self.set_user(requester):
			with self.assertRaises(frappe.ValidationError):
				decide(order, "Approve")

		preview = preview_signal(
			name=order.name,
			asset=self.asset.name,
			request_meter_reading=1000,
			request_gauge_percent=75,
			operational_location=self.location.name,
			driver=self.driver.name,
		)
		self.assertEqual(preview["signal"], "Red")
		self.assertIn("Gauge limit: 74%", preview["reasons"][0]["details"])
		self.assertEqual(frappe.db.get_value("Fuel Order", order.name, "workflow_state"), "Draft")

	def test_estimate_uses_current_reading_at_approval_then_stays_frozen(self):
		requester = self._user(("Fleet User",), self.location.name)
		approver = self._user(("Fleet Approver",), self.location.name)
		with self.set_user(requester):
			pending = attach_request_photos(
				self.make_order(request_gauge_percent=80).insert()
			)
			pending = send_up(pending)

		with self.set_user(approver):
			# Approval reloads the saved order. Persist a newer entry value so the
			# approval path must replace the earlier red server snapshot.
			frappe.db.set_value("Fuel Order", pending.name, "request_gauge_percent", 40)
			record_decision_reason(pending.name, "Approve", "The new gauge reading is confirmed.")
			approved = apply_workflow(pending, "Approve")

		self.assertEqual(approved.signal, "Green", approved.signal_reasons)
		self.assertEqual(approved.estimated_litres, 36)
		self.assertEqual(
			json.loads(approved.signal_details_json)["request_summary"]["estimated_litres"],
			36,
		)
		approved_estimate = approved.estimated_litres
		self._save_settings(gauge_limit_percent=10)
		approved.reload()
		self.assertEqual(approved.signal, "Green")
		self.assertEqual(approved.estimated_litres, approved_estimate)

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

		approved = self._approve_green()
		self.assertEqual(approved.workflow_state, "Approved")
		self.assertTrue(has_open_order(self.asset.name, exclude_order=draft.name))
		self.assertFalse(has_open_order(self.asset.name, exclude_order=approved.name))

		# The approved order is never counted against itself.
		self.assertEqual(approved.signal, "Green")
		self.assertEqual(frappe.db.get_value("Fuel Order", approved.name, "signal"), "Green")

		# 36 L of room at 10 km/L since the approved order's 1000 km, so only the open order is flagged.
		order = self.make_order(request_meter_reading=1360).insert(ignore_permissions=True)
		self.assertEqual(order.signal, "Red")
		reasons = self._reasons(order)
		self.assertEqual(len(reasons), 1, reasons)
		self.assertTrue(reasons[0].startswith("Open order exists"), reasons)

	def test_an_order_waiting_for_sign_off_counts_as_open(self):
		requester = self._user(("Fleet User",), self.location.name)
		with self.set_user(requester):
			pending = attach_request_photos(self.make_order(request_gauge_percent=80).insert())
			pending = send_up(pending)
			self.assertEqual(pending.workflow_state, "Pending Approval")
			pending_signal = json.loads(pending.signal_details_json)
			self.assertIn("Fleet Approver", pending_signal["next_action"])
			self.assertIn("with a reason", pending_signal["next_action"])

			order = self.make_order(request_gauge_percent=40).insert()
			self.assertEqual(order.signal, "Red")
			reasons = self._reasons(order)
			self.assertEqual(len(reasons), 1, reasons)
			self.assertTrue(reasons[0].startswith("Open order exists"), reasons)

			pending = decide(pending, "Withdraw")
			self.assertEqual(pending.workflow_state, "Rejected")

			order.save()
			self.assertEqual(order.signal, "Green")

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

		self.asset.target_km_per_litre = 7.5
		self.asset.save(ignore_permissions=True)
		order = self.make_order().insert(ignore_permissions=True)
		self.assertEqual(order.average_km_per_litre, 10.0)
		summary = json.loads(order.signal_details_json)["request_summary"]
		self.assertEqual(summary["vehicle_target_km_per_litre"], 7.5)
		self.assertEqual(summary["recent_observed_average_km_per_litre"], 10.0)
		self.assertEqual(summary["average_km_per_litre"], 10.0)
		self.assertEqual(summary["applicable_fuel_economy_source"], "recent_average")

	def test_latest_full_authorized_baseline_ignores_partial_and_cancelled_transactions(self):
		first_time = now_datetime() - timedelta(days=3)
		newer_full_time = now_datetime() - timedelta(days=2)
		partial_time = now_datetime() - timedelta(days=1)
		cancelled_full_time = now_datetime()
		orders = {
			"baseline": self.make_order(request_gauge_percent=10).insert(ignore_permissions=True),
			"newer-full": self.make_order(request_gauge_percent=70).insert(ignore_permissions=True),
			"partial": self.make_order(
				quantity_authorization="Partial",
				authorized_quantity_litres=10,
				partial_authorization_reason="Limited station stock",
				request_gauge_percent=40,
			).insert(ignore_permissions=True),
			"cancelled-full": self.make_order(request_gauge_percent=20).insert(ignore_permissions=True),
		}
		rows = (
			("baseline", first_time, 10000, 0, 1),
			("newer-full", newer_full_time, 10500, 0, 1),
			("partial", partial_time, 11000, 1, 1),
			("cancelled-full", cancelled_full_time, 12000, 0, 2),
		)
		for suffix, fueling_time, odometer, full_tank, docstatus in rows:
			frappe.get_doc(
				{
					"doctype": "Fueling Transaction",
					"name": f"AC09-{suffix}-{self.suffix}",
					"docstatus": docstatus,
					"asset": self.asset.name,
					"fuel_order": orders[suffix].name,
					"vehicle_odometer": odometer,
					"actual_fueling_datetime": fueling_time,
					"invoice_litres": 25 if suffix == "partial" else 30,
					"full_tank_confirmed": full_tank,
				}
			).db_insert()

		baseline = get_latest_full_tank_baseline(self.asset.name)
		self.assertEqual(baseline.name, f"AC09-newer-full-{self.suffix}")
		self.assertEqual(baseline.fuel_order, orders["newer-full"].name)
		self.assertEqual(baseline.fuel_order_quantity_authorization, "Full")
		self.assertEqual(baseline.vehicle_odometer, 10500)
		self.assertEqual(baseline.actual_fueling_datetime, newer_full_time)

		order = self.make_order(request_meter_reading=10800, request_gauge_percent=50).insert(
			ignore_permissions=True
		)
		check = json.loads(order.signal_details_json)["signal_inputs"]["full_tank_mileage_check"]
		self.assertEqual(check["baseline"]["reference"], baseline.name)
		self.assertEqual(check["baseline_odometer"], 10500)
		self.assertEqual(check["estimated_consumed_litres"], 30)
		self.assertEqual(check["expected_distance_km"], 300)
		self.assertEqual(check["status"], "pass")

	def test_full_tank_baseline_is_missing_without_vehicle_history_or_for_generator(self):
		self.assertIsNone(get_latest_full_tank_baseline(self.asset.name))
		generator = self._insert(
			"Fleet Asset",
			asset_identifier=f"AC09 Generator {self.suffix}",
			asset_type="Generator",
			fuel_type=self.fuel_type.name,
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
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": f"AC09-generator-full-{self.suffix}",
				"docstatus": 1,
				"asset": generator.name,
				"vehicle_odometer": 10000,
				"actual_fueling_datetime": now_datetime(),
				"full_tank_confirmed": 1,
			}
		).db_insert()
		self.assertIsNone(get_latest_full_tank_baseline(generator.name))

	def test_mileage_baseline_falls_back_to_previous_entry_without_full_history(self):
		partial_order = self.make_order(
			quantity_authorization="Partial",
			authorized_quantity_litres=10,
			partial_authorization_reason="Limited station stock",
		).insert(ignore_permissions=True)
		fueling_time = now_datetime() - timedelta(days=1)
		fueling_name = f"AC09-partial-fallback-{self.suffix}"
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": fueling_name,
				"docstatus": 1,
				"asset": self.asset.name,
				"fuel_order": partial_order.name,
				"vehicle_odometer": 900,
				"actual_fueling_datetime": fueling_time,
				"full_tank_confirmed": 0,
			}
		).db_insert()

		order = self.make_order(request_meter_reading=1000).insert(ignore_permissions=True)
		inputs = json.loads(order.signal_details_json)["signal_inputs"]
		self.assertIsNone(inputs["full_tank_baseline"])
		self.assertEqual(inputs["mileage_baseline"]["source"], "previous_entry_fallback")
		self.assertEqual(inputs["mileage_baseline"]["reference"], f"Fueling {fueling_name}")
		self.assertEqual(inputs["mileage_baseline"]["vehicle_odometer"], 900)
		self.assertEqual(
			inputs["full_tank_mileage_check"]["baseline"]["source"], "previous_entry_fallback"
		)
		self.assertEqual(
			get_datetime(inputs["mileage_baseline"]["timestamp"]),
			get_datetime(
				frappe.db.get_value("Fueling Transaction", fueling_name, "actual_fueling_datetime")
			),
		)

	def test_server_preview_and_save_refresh_the_full_tank_result_from_newer_history(self):
		first_baseline_order = self.make_order().insert(ignore_permissions=True)
		first_baseline_time = now_datetime() - timedelta(days=2)
		first_baseline_name = f"AC09-preview-full-1-{self.suffix}"
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": first_baseline_name,
				"docstatus": 1,
				"asset": self.asset.name,
				"fuel_order": first_baseline_order.name,
				"vehicle_odometer": 1000,
				"actual_fueling_datetime": first_baseline_time,
				"full_tank_confirmed": 0,
			}
		).db_insert()
		values = {
			"asset": self.asset.name,
			"request_meter_reading": 1300,
			"request_gauge_percent": 50,
			"operational_location": self.location.name,
			"driver": self.driver.name,
			"quantity_authorization": "Full",
		}

		preview = preview_signal(**values)
		order = self.make_order(**{key: value for key, value in values.items() if key != "asset"}).insert(
			ignore_permissions=True
		)
		saved = json.loads(order.signal_details_json)
		self.assertEqual(
			preview["signal_inputs"]["full_tank_mileage_check"],
			saved["signal_inputs"]["full_tank_mileage_check"],
		)
		self.assertEqual(
			saved["signal_inputs"]["full_tank_mileage_check"]["baseline"]["reference"],
			first_baseline_name,
		)

		newer_baseline_order = self.make_order().insert(ignore_permissions=True)
		newer_baseline_name = f"AC09-preview-full-2-{self.suffix}"
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": newer_baseline_name,
				"docstatus": 1,
				"asset": self.asset.name,
				"fuel_order": newer_baseline_order.name,
				"vehicle_odometer": 1100,
				"actual_fueling_datetime": now_datetime() - timedelta(days=1),
				"full_tank_confirmed": 0,
			}
		).db_insert()
		preview = preview_signal(**values)
		self.assertEqual(
			preview["signal_inputs"]["full_tank_mileage_check"]["baseline"]["reference"],
			newer_baseline_name,
		)
		values["request_gauge_percent"] = 40
		preview = preview_signal(**values)
		self.assertEqual(
			preview["signal_inputs"]["full_tank_mileage_check"]["expected_distance_km"], 360
		)
		order.request_gauge_percent = 40
		order.save(ignore_permissions=True)
		saved_check = json.loads(order.signal_details_json)["signal_inputs"]["full_tank_mileage_check"]
		self.assertEqual(saved_check["baseline"]["reference"], newer_baseline_name)
		self.assertEqual(saved_check, preview["signal_inputs"]["full_tank_mileage_check"])

	def test_signal_is_frozen_once_approved(self):
		first_baseline_time = now_datetime() - timedelta(days=2)
		first_baseline = f"AC09-initial-full-{self.suffix}"
		baseline_order = self.make_order().insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": first_baseline,
				"docstatus": 1,
				"asset": self.asset.name,
				"fuel_order": baseline_order.name,
				"vehicle_odometer": 650,
				"actual_fueling_datetime": first_baseline_time,
				"full_tank_confirmed": 0,
			}
		).db_insert()
		approved = self._approve_green()
		self.assertEqual(approved.signal, "Green")
		approved_details = approved.signal_details_json
		self.assertEqual(
			json.loads(approved_details)["signal_inputs"]["full_tank_baseline"]["name"],
			first_baseline,
		)
		frozen_baseline = json.loads(approved_details)["signal_inputs"]["full_tank_baseline"]
		self.assertEqual(frozen_baseline["fuel_order"], baseline_order.name)
		self.assertEqual(frozen_baseline["quantity_authorization"], "Full")
		selected_baseline = json.loads(approved_details)["signal_inputs"]["mileage_baseline"]
		self.assertEqual(selected_baseline["source"], "full_authorized_fueling")
		self.assertEqual(selected_baseline["fuel_order"], baseline_order.name)
		frozen_check = json.loads(approved_details)["signal_inputs"]["full_tank_mileage_check"]
		self.assertEqual(frozen_check["status"], "pass")
		self.assertEqual(frozen_check["baseline"]["reference"], first_baseline)
		self.assertEqual(frozen_check["estimated_consumed_litres"], 36)
		self.assertEqual(frozen_check["expected_distance_km"], 360)
		self.assertIn("signal_details_json", frappe.get_meta("Fuel Order").get_valid_fields())
		self.assertTrue(frappe.db.has_column("Fuel Order", "signal_details_json"))
		self.assertEqual(
			frappe.db.sql(
				"SELECT signal_details_json FROM `tabFuel Order` WHERE name=%s",
				approved.name,
				as_dict=True,
			)[0].signal_details_json,
			approved_details,
		)
		approver = self._user(("Fleet Approver",), self.location.name)

		self._save_settings(gauge_limit_percent=10)
		newer_baseline_order = self.make_order().insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Fueling Transaction",
				"name": f"AC09-new-full-{self.suffix}",
				"docstatus": 1,
				"asset": self.asset.name,
				"fuel_order": newer_baseline_order.name,
				"vehicle_odometer": 1100,
				"actual_fueling_datetime": now_datetime() + timedelta(hours=1),
				"full_tank_confirmed": 0,
			}
		).db_insert()
		new_valid_until = get_datetime(approved.valid_until) + timedelta(hours=1)
		with self.set_user(approver):
			approved.extend_validity(new_valid_until.strftime("%Y-%m-%d %H:%M:%S"), "Signal freeze check")
		self.assertEqual(approved.signal_details_json, approved_details)

		persisted = frappe.get_doc("Fuel Order", approved.name)
		self.assertEqual(persisted.slip_revision, 2)
		self.assertEqual(persisted.signal, "Green")
		self.assertFalse(persisted.signal_reasons)
		self.assertEqual(persisted.signal_details_json, approved_details)

	def test_settings_refuse_a_gauge_limit_of_100(self):
		with self.assertRaises(frappe.ValidationError):
			self._save_settings(gauge_limit_percent=100)
