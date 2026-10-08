from frappe.tests import UnitTestCase

from fleet_management.fuel_signal import (
	evaluate_signal,
	evaluate_signal_result,
	missing_signal_readings,
	signal_colour,
)


# specs/009-fuel-order-ux Requirements 2.2, 2.3, 2.4, 2.5, 3.2; Property 1
class TestFuelSignal(UnitTestCase):
	def _vehicle(self, **overrides):
		facts = {
			"asset_type": "Vehicle",
			"tank_capacity": 60,
			"gauge_percent": 50,
			"previous_reading": 1000,
			"current_reading": 1300,
			"average_km_per_litre": 10,
			"requested_litres": None,
			"has_open_order": False,
			"hours_since_last_fueling": 48,
			"operational_location": "Nairobi",
			"home_location": "Nairobi",
			"driver": "Joseph Mutua",
			"usual_driver": "Joseph Mutua",
			"last_interval_km_per_litre": 10,
			"interval_count": 3,
		}
		facts.update(overrides)
		return facts

	def _with_mileage_baseline(self, **overrides):
		return self._vehicle(
			mileage_baseline={
				"source": "full_authorized_fueling",
				"label": "Full-authorized fueling",
				"reference": "FT-1",
				"vehicle_odometer": 1000,
				"timestamp": "2026-10-01 10:00:00",
				"fuel_order": "FO-1",
			},
			**overrides,
		)

	def test_baseline_is_green(self):
		reasons = evaluate_signal(self._vehicle())
		self.assertEqual(reasons, [])
		self.assertEqual(signal_colour(reasons), "Green")

	def test_any_reason_gives_red(self):
		reasons = evaluate_signal(self._vehicle(has_open_order=True))
		self.assertEqual(signal_colour(reasons), "Red")

	def test_mileage_at_margin_passes(self):
		reasons = evaluate_signal(self._vehicle(current_reading=1345))
		self.assertEqual(reasons, [])

	def test_mileage_past_margin_fails(self):
		reasons = evaluate_signal(self._vehicle(current_reading=1346))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Mileage does not add up"))

	def test_full_tank_check_estimates_consumption_from_current_gauge(self):
		result = evaluate_signal_result(self._with_mileage_baseline())
		check = result["signal_inputs"]["full_tank_mileage_check"]

		self.assertEqual(check["status"], "pass")
		self.assertEqual(check["baseline"]["reference"], "FT-1")
		self.assertEqual(check["distance_km"], 300)
		self.assertEqual(check["estimated_remaining_litres"], 30)
		self.assertEqual(check["estimated_consumed_litres"], 30)
		self.assertEqual(check["expected_distance_km"], 300)

	def test_full_tank_reason_explains_source_readings_economy_and_margin(self):
		result = evaluate_signal_result(
			self._with_mileage_baseline(current_reading=1350, average_source="recent_average"),
			{"mileage_margin_percent": 15},
		)
		reason = next(
			item
			for item in result["reasons"]
			if item["text"].startswith("Full-authorized fueling mileage does not add up")
		)

		self.assertIn("Baseline used: Full-authorized fueling (FT-1)", reason["details"])
		self.assertIn("Baseline Odometer: 1000 km", reason["details"])
		self.assertIn("Current Odometer: 1350 km", reason["details"])
		self.assertIn("Baseline date and time: 2026-10-01 10:00:00", reason["details"])
		self.assertIn("Odometer distance travelled since selected baseline: 350 km", reason["details"])
		self.assertIn("Estimated fuel used: 30 L", reason["details"])
		self.assertIn("Expected distance: 300.0 km", reason["details"])
		self.assertIn(
			"Recent observed full-to-full average: 10 km/L (0.100 L/km; 10.0 L/100 km)",
			reason["details"],
		)
		self.assertIn(
			"Applicable fuel economy used by this check: 10 km/L (recent weighted average)",
			reason["details"],
		)
		self.assertIn("Allowed mileage margin: 15%", reason["details"])
		self.assertTrue(reason["next_action"])

	def test_full_tank_comparison_exact_margin_passes_and_beyond_margin_fails(self):
		for current_reading in (1255, 1345):
			with self.subTest(current_reading=current_reading):
				result = evaluate_signal_result(
					self._with_mileage_baseline(current_reading=current_reading),
					{"mileage_margin_percent": 15},
				)
				self.assertEqual(result["signal_inputs"]["full_tank_mileage_check"]["status"], "pass")

		for current_reading in (1254.97, 1345.03):
			with self.subTest(current_reading=current_reading):
				result = evaluate_signal_result(
					self._with_mileage_baseline(current_reading=current_reading),
					{"mileage_margin_percent": 15},
				)
				check = result["signal_inputs"]["full_tank_mileage_check"]
				self.assertEqual(check["status"], "fail")
				self.assertGreater(round(check["variance_percent"], 6), check["margin_percent"])

	def test_old_mileage_check_stays_unchanged_when_full_tank_result_differs(self):
		reasons = evaluate_signal(self._with_mileage_baseline(previous_reading=1250, current_reading=1550))

		self.assertFalse(any(reason.startswith("Mileage does not add up") for reason in reasons))
		self.assertTrue(
			any(reason.startswith("Full-authorized fueling mileage does not add up") for reason in reasons)
		)

	def test_full_tank_check_cannot_calculate_for_unusable_inputs_or_zero_use(self):
		for overrides in (
			{"tank_capacity": None},
			{"tank_capacity": 0},
			{"gauge_percent": 101},
			{"average_km_per_litre": 0},
			{"average_km_per_litre": None},
			{"gauge_percent": 100},
		):
			with self.subTest(overrides=overrides):
				result = evaluate_signal_result(self._with_mileage_baseline(**overrides))
				check = result["signal_inputs"]["full_tank_mileage_check"]
				self.assertEqual(check["status"], "cannot_calculate")
				self.assertTrue(
					any(
						reason["text"].startswith("Mileage check cannot calculate")
						for reason in result["reasons"]
					)
				)

	def test_fallback_baseline_is_named_and_no_baseline_skips_new_check(self):
		fallback = {
			"source": "previous_entry_fallback",
			"label": "Previous Entry fallback",
			"reference": "Fueling FT-0",
			"vehicle_odometer": 1000,
			"timestamp": "2026-09-30 10:00:00",
		}
		result = evaluate_signal_result(self._vehicle(mileage_baseline=fallback))
		self.assertEqual(
			result["signal_inputs"]["full_tank_mileage_check"]["baseline"]["source"],
			"previous_entry_fallback",
		)

		without_baseline = evaluate_signal_result(self._vehicle(mileage_baseline=None))
		self.assertEqual(without_baseline["signal_inputs"]["full_tank_mileage_check"]["status"], "skipped")

	def test_signal_explanation_names_distance_estimate_economy_margin_and_action(self):
		result = evaluate_signal_result(
			self._vehicle(current_reading=1346, average_source="recent_average"),
			{"mileage_margin_percent": 15},
		)
		self.assertEqual(result["signal"], "Red")
		self.assertTrue(result["reasons"][0]["text"].startswith("Mileage does not add up"))
		self.assertEqual(
			result["reasons"][0]["details"],
			[
				"Previous Entry Odometer: 1000 km",
				"Current Odometer: 1346 km",
				"Odometer distance travelled since Previous Entry: 346 km",
				"Fuel estimate from current gauge: 30 L estimated to fill",
				"Expected distance: 300 km",
				"Recent observed full-to-full average: 10 km/L (0.100 L/km; 10.0 L/100 km)",
				"Applicable fuel economy used by this check: 10 km/L (recent weighted average)",
				"Allowed mileage margin: 15%",
			],
		)
		self.assertIn("Check the Previous Entry", result["reasons"][0]["next_action"])
		self.assertIn("A Fleet User may reject", result["next_action"])
		self.assertIn("permissions", result["note"])
		self.assertEqual(result["signal_inputs"]["previous_reading"], 1000)
		self.assertEqual(result["signal_inputs"]["fuel_estimate_litres"], 30)
		self.assertEqual(result["signal_inputs"]["limits"]["mileage_margin_percent"], 15)

	def test_target_economy_is_not_described_as_observed_efficiency(self):
		result = evaluate_signal_result(
			self._vehicle(current_reading=1346, average_source="vehicle_target"),
			{"mileage_margin_percent": 15},
		)
		details = " ".join(result["reasons"][0]["details"])
		self.assertIn("vehicle target", details)
		self.assertIn("Applicable fuel economy used by this check: 10 km/L (vehicle target)", details)
		self.assertNotIn("Recent observed full-to-full", details)
		self.assertNotIn("L/100 km", details)
		self.assertNotIn("observed interval", details.lower())

	def test_waiting_preview_names_vehicle_and_generator_readings(self):
		self.assertEqual(
			missing_signal_readings(
				{**self._vehicle(current_reading=None, gauge_percent=None), "asset": "VEH-1"}
			),
			["Odometer", "Current Gauge (%)"],
		)
		self.assertEqual(
			missing_signal_readings({"asset": "GEN-1", "asset_type": "Generator"}),
			["Hour Meter"],
		)

	def test_mileage_no_forward_movement_fails(self):
		reasons = evaluate_signal(self._vehicle(current_reading=1000))
		self.assertEqual(len(reasons), 1)
		self.assertIn("has not moved forward", reasons[0])

	def test_mileage_no_previous_entry_skips(self):
		reasons = evaluate_signal(self._vehicle(previous_reading=None))
		self.assertEqual(reasons, [])

	def test_mileage_worked_example(self):
		reasons = evaluate_signal(
			self._vehicle(
				tank_capacity=20,
				gauge_percent=0,
				average_km_per_litre=10,
				previous_reading=100,
				current_reading=110,
			)
		)
		self.assertEqual(len(reasons), 1)
		self.assertIn("95% off", reasons[0])

	def test_mileage_approximate_note(self):
		reasons = evaluate_signal(self._vehicle(current_reading=1346, last_fill_was_full=False))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].endswith("Approximate: the last fill was not a full tank."))

	def test_litres_at_limit_passes(self):
		reasons = evaluate_signal(self._vehicle(requested_litres=36))
		self.assertEqual(reasons, [])

	def test_litres_past_limit_fails(self):
		reasons = evaluate_signal(self._vehicle(requested_litres=36.1))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("More litres than the tank has room for"))

	def test_litres_at_a_limit_float_arithmetic_misses_passes(self):
		# 64 L at 17% leaves 53.12 L of room plus 6.4 L; 53.12 + 6.4 is 59.519999... in floating point.
		reasons = evaluate_signal(self._vehicle(tank_capacity=64, gauge_percent=17, requested_litres=59.52))
		self.assertFalse([r for r in reasons if r.startswith("More litres")])

	def test_litres_just_past_that_limit_fails(self):
		reasons = evaluate_signal(self._vehicle(tank_capacity=64, gauge_percent=17, requested_litres=59.53))
		self.assertTrue([r for r in reasons if r.startswith("More litres")])

	def test_litres_none_skips(self):
		reasons = evaluate_signal(self._vehicle(requested_litres=None))
		self.assertEqual(reasons, [])

	def test_gauge_at_limit_passes(self):
		reasons = evaluate_signal(self._vehicle(gauge_percent=75, current_reading=1150))
		self.assertEqual(reasons, [])

	def test_gauge_past_limit_fails(self):
		reasons = evaluate_signal(self._vehicle(gauge_percent=76, current_reading=1144))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Tank nearly full"))

	def test_open_order_fails(self):
		reasons = evaluate_signal(self._vehicle(has_open_order=True))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Open order exists"))

	def test_hours_at_limit_passes(self):
		reasons = evaluate_signal(self._vehicle(hours_since_last_fueling=24))
		self.assertEqual(reasons, [])

	def test_hours_below_limit_fails(self):
		reasons = evaluate_signal(self._vehicle(hours_since_last_fueling=23.9))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Too soon since the last fueling"))

	def test_hours_none_skips(self):
		reasons = evaluate_signal(self._vehicle(hours_since_last_fueling=None))
		self.assertEqual(reasons, [])

	def test_location_mismatch_fails(self):
		reasons = evaluate_signal(self._vehicle(operational_location="Mombasa"))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Away from home"))

	def test_location_missing_home_skips(self):
		reasons = evaluate_signal(self._vehicle(home_location=None))
		self.assertEqual(reasons, [])

	def test_driver_mismatch_fails(self):
		reasons = evaluate_signal(self._vehicle(driver="Peter Otieno"))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Not the usual driver"))

	def test_driver_no_usual_skips(self):
		reasons = evaluate_signal(self._vehicle(usual_driver=None))
		self.assertEqual(reasons, [])

	def test_trend_at_margin_passes(self):
		reasons = evaluate_signal(self._vehicle(last_interval_km_per_litre=11.5))
		self.assertEqual(reasons, [])

	def test_trend_past_margin_fails(self):
		reasons = evaluate_signal(self._vehicle(last_interval_km_per_litre=11.6))
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Mileage off its own trend"))

	def test_trend_explains_observed_interval_direction_units_and_limit(self):
		result = evaluate_signal_result(
			self._vehicle(last_interval_km_per_litre=5, average_km_per_litre=10),
			{"mileage_margin_percent": 15},
		)
		trend = result["reasons"][0]
		self.assertEqual(
			trend["text"],
			"Mileage off its own trend: Recent reference: 10 km/L (0.100 L/km; 10.0 L/100 km). "
			"Latest observed full-to-full interval: 5 km/L (0.200 L/km; 20.0 L/100 km). "
			"The observed interval is 50% below the reference; the allowed difference is 15%.",
		)
		self.assertIn("weighted across 3 completed full-to-full intervals", trend["details"][0])
		self.assertIn("completed fueling records", trend["next_action"])

		above = evaluate_signal_result(
			self._vehicle(last_interval_km_per_litre=15, average_km_per_litre=10),
			{"mileage_margin_percent": 15},
		)["reasons"][0]["text"]
		self.assertIn("The observed interval is 50% above the reference", above)

	def test_trend_too_few_intervals_skips(self):
		reasons = evaluate_signal(self._vehicle(last_interval_km_per_litre=11.6, interval_count=1))
		self.assertEqual(reasons, [])

	def test_custom_limits_are_applied(self):
		reasons = evaluate_signal(
			self._vehicle(gauge_percent=76, current_reading=1144),
			{"gauge_limit_percent": 80},
		)
		self.assertEqual(reasons, [])

	def test_limits_with_none_fall_back_to_defaults(self):
		reasons = evaluate_signal(
			self._vehicle(gauge_percent=76, current_reading=1144),
			{"gauge_limit_percent": None},
		)
		self.assertEqual(len(reasons), 1)
		self.assertTrue(reasons[0].startswith("Tank nearly full"))

	def test_generator_baseline_is_green(self):
		facts = {
			"asset_type": "Generator",
			"gauge_percent": 95,
			"previous_reading": 1000,
			"current_reading": 1000,
			"requested_litres": 999,
			"driver": "X",
			"usual_driver": "Y",
			"interval_count": 5,
			"last_interval_km_per_litre": 1,
			"average_km_per_litre": 10,
			"has_open_order": False,
			"hours_since_last_fueling": 48,
			"operational_location": "Nairobi",
			"home_location": "Nairobi",
		}
		self.assertEqual(evaluate_signal(facts), [])

	def test_generator_runs_only_checks_four_five_six(self):
		facts = {
			"asset_type": "Generator",
			"gauge_percent": 95,
			"previous_reading": 1000,
			"current_reading": 1000,
			"requested_litres": 999,
			"driver": "X",
			"usual_driver": "Y",
			"interval_count": 5,
			"last_interval_km_per_litre": 1,
			"average_km_per_litre": 10,
			"has_open_order": True,
			"hours_since_last_fueling": 1,
			"operational_location": "Mombasa",
			"home_location": "Nairobi",
			"mileage_baseline": {
				"source": "full_authorized_fueling",
				"vehicle_odometer": 1000,
			},
		}
		reasons = evaluate_signal(facts)
		self.assertEqual(len(reasons), 3)
		self.assertTrue(reasons[0].startswith("Open order exists"))
		self.assertTrue(reasons[1].startswith("Too soon since the last fueling"))
		self.assertTrue(reasons[2].startswith("Away from home"))

	def test_two_failing_checks_are_reported_in_check_order(self):
		reasons = evaluate_signal(self._vehicle(gauge_percent=76, current_reading=1144, has_open_order=True))
		self.assertEqual(len(reasons), 2)
		self.assertTrue(reasons[0].startswith("Tank nearly full"))
		self.assertTrue(reasons[1].startswith("Open order exists"))
