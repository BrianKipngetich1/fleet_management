"""Green/red signal for a Fuel Order (spec 002 D-8). Pure: callers gather the facts."""

import math

DEFAULT_LIMITS = {
	"mileage_margin_percent": 15,
	"litres_excess_percent": 10,
	"gauge_limit_percent": 75,
	"min_hours_between_fuelings": 24,
}


def _approx_note(facts):
	if facts.get("last_fill_was_full", True) is False:
		return " Approximate: the last fill was not a full tank."
	return ""


def _room_litres(facts):
	tank_capacity = facts.get("tank_capacity")
	gauge_percent = facts.get("gauge_percent")
	if tank_capacity is None or gauge_percent is None:
		return None
	return tank_capacity * (100 - gauge_percent) / 100


def _check_mileage(facts, limits):
	previous_reading = facts.get("previous_reading")
	average = facts.get("average_km_per_litre")
	room = _room_litres(facts)
	if previous_reading is None or average is None or room is None or facts.get("current_reading") is None:
		return None

	distance = facts.get("current_reading") - previous_reading
	if distance <= 0:
		return (
			f"Mileage does not add up: the Odometer has not moved forward since the Previous Entry "
			f"({previous_reading:g} km)."
		)

	expected = average * room
	if expected <= 0:
		return None

	variance = abs(distance - expected) / expected * 100
	margin = limits["mileage_margin_percent"]
	if round(variance, 6) > margin:
		expected_rounded = round(expected, 1)
		return (
			f"Mileage does not add up: {distance:g} km of Odometer distance since the Previous Entry, "
			f"{expected_rounded:g} km expected ({variance:.0f}% off; limit {margin:g}%)."
			f"{_approx_note(facts)}"
		)
	return None


def _full_tank_mileage_result(facts, limits):
	"""Calculate the separate baseline check without changing the Previous Entry check."""
	baseline = facts.get("mileage_baseline")
	if facts.get("asset_type") != "Vehicle" or not baseline:
		return {"status": "skipped", "reason": None}
	if facts.get("current_reading") in (None, "") or facts.get("gauge_percent") in (None, ""):
		return {"status": "waiting", "reason": None, "baseline": baseline}

	try:
		capacity = float(facts.get("tank_capacity"))
		gauge = float(facts.get("gauge_percent"))
		average = float(facts.get("average_km_per_litre"))
		current = float(facts.get("current_reading"))
		baseline_reading = float(baseline.get("vehicle_odometer"))
	except (TypeError, ValueError):
		capacity = gauge = average = current = baseline_reading = math.nan

	if (
		not all(math.isfinite(value) for value in (capacity, gauge, average, current, baseline_reading))
		or capacity <= 0
		or not 0 <= gauge <= 100
		or average <= 0
	):
		return {
			"status": "cannot_calculate",
			"reason": (
				"Mileage check cannot calculate: the baseline, tank capacity, gauge, or fuel economy "
				"is unusable."
			),
			"baseline": baseline,
			"tank_capacity_litres": facts.get("tank_capacity"),
			"gauge_percent": facts.get("gauge_percent"),
			"average_km_per_litre": facts.get("average_km_per_litre"),
			"average_source": facts.get("average_source"),
			"current_odometer": facts.get("current_reading"),
		}

	remaining = capacity * gauge / 100
	consumed = capacity - remaining
	if consumed <= 0:
		return {
			"status": "cannot_calculate",
			"reason": "Mileage check cannot calculate: the current gauge estimates zero fuel use.",
			"baseline": baseline,
			"current_odometer": current,
			"tank_capacity_litres": capacity,
			"gauge_percent": gauge,
			"estimated_remaining_litres": remaining,
			"estimated_consumed_litres": consumed,
			"average_km_per_litre": average,
			"average_source": facts.get("average_source"),
		}

	expected = average * consumed
	distance = current - baseline_reading
	variance = abs(distance - expected) / expected * 100
	margin = limits["mileage_margin_percent"]
	passed = round(variance, 6) <= margin
	baseline_label = baseline.get("label") or "Mileage baseline"
	result = {
		"status": "pass" if passed else "fail",
		"reason": None,
		"baseline": baseline,
		"baseline_odometer": baseline_reading,
		"current_odometer": current,
		"distance_km": distance,
		"tank_capacity_litres": capacity,
		"gauge_percent": gauge,
		"estimated_remaining_litres": remaining,
		"estimated_consumed_litres": consumed,
		"average_km_per_litre": average,
		"average_source": facts.get("average_source"),
		"expected_distance_km": expected,
		"variance_percent": variance,
		"margin_percent": margin,
		"passed": passed,
	}
	if not passed:
		result["reason"] = (
			f"{baseline_label} mileage does not add up: {distance:g} km of Odometer distance since "
			f"the selected baseline, "
			f"{expected:.1f} km expected ({variance:.0f}% off; limit {margin:g}%)."
		)
	return result


def _check_full_tank_mileage(facts, limits):
	return _full_tank_mileage_result(facts, limits).get("reason")


def _check_litres(facts, limits):
	requested = facts.get("requested_litres")
	tank_capacity = facts.get("tank_capacity")
	room = _room_litres(facts)
	if requested is None or tank_capacity is None or room is None:
		return None

	excess = limits["litres_excess_percent"]
	if round(requested - (room + excess / 100 * tank_capacity), 6) > 0:
		room_rounded = round(room, 1)
		return (
			f"More litres than the tank has room for: {requested:g} L requested, room for "
			f"{room_rounded:g} L plus {excess:g}% of the tank.{_approx_note(facts)}"
		)
	return None


def _check_gauge(facts, limits):
	gauge_percent = facts.get("gauge_percent")
	if gauge_percent is None:
		return None

	limit = limits["gauge_limit_percent"]
	if gauge_percent > limit:
		return f"Tank nearly full: the gauge reads {gauge_percent:g}%, above {limit:g}%."
	return None


def _check_open_order(facts, limits):
	if facts.get("has_open_order"):
		return (
			"Open order exists: another order for this asset is waiting for approval, "
			"or approved and not yet fuelled."
		)
	return None


def _check_hours(facts, limits):
	hours = facts.get("hours_since_last_fueling")
	if hours is None:
		return None

	minimum = limits["min_hours_between_fuelings"]
	if hours < minimum:
		return f"Too soon since the last fueling: {hours:.1f} hours ago; the minimum is {minimum:g}."
	return None


def _check_location(facts, limits):
	operational_location = facts.get("operational_location")
	home_location = facts.get("home_location")
	if not operational_location or not home_location:
		return None

	if operational_location != home_location:
		return (
			f"Away from home: fuelling at {operational_location}, but its home location is {home_location}."
		)
	return None


def _check_driver(facts, limits):
	usual_driver = facts.get("usual_driver")
	if not usual_driver:
		return None

	driver = facts.get("driver")
	if driver != usual_driver:
		return f"Not the usual driver: {driver} instead of {usual_driver}."
	return None


def _check_trend(facts, limits):
	interval_count = facts.get("interval_count")
	if not interval_count or interval_count < 2:
		return None

	last = facts.get("last_interval_km_per_litre")
	average = facts.get("average_km_per_litre")
	if last is None or average is None or average == 0:
		return None

	off = abs(last - average) / average * 100
	margin = limits["mileage_margin_percent"]
	if round(off, 6) > margin:
		direction = "below" if last < average else "above"
		return (
			f"Mileage off its own trend: {_economy_comparison(average, 'Recent reference')}. "
			f"{_economy_comparison(last, 'Latest observed full-to-full interval')}. "
			f"The observed interval is {off:g}% {direction} the reference; "
			f"the allowed difference is {margin:g}%."
		)
	return None


def evaluate_signal(facts, limits=None):
	merged_limits = dict(DEFAULT_LIMITS)
	for key, value in (limits or {}).items():
		if value is not None:
			merged_limits[key] = value

	if facts.get("asset_type") == "Generator":
		checks = (_check_open_order, _check_hours, _check_location)
	else:
		checks = (
			_check_mileage,
			_check_full_tank_mileage,
			_check_litres,
			_check_gauge,
			_check_open_order,
			_check_hours,
			_check_location,
			_check_driver,
			_check_trend,
		)

	reasons = []
	for check in checks:
		reason = check(facts, merged_limits)
		if reason is not None:
			reasons.append(reason)
	return reasons


def missing_signal_readings(facts):
	"""Name the minimum entry inputs needed before a live preview can be shown."""
	if not facts.get("asset"):
		return ["Asset"]

	missing = []
	reading_name = "Odometer" if facts.get("asset_type") == "Vehicle" else "Hour Meter"
	if facts.get("current_reading") in (None, ""):
		missing.append(reading_name)
	if facts.get("asset_type") == "Vehicle" and facts.get("gauge_percent") in (None, ""):
		missing.append("Current Gauge (%)")
	return missing


def waiting_signal_result(waiting_for):
	"""A waiting response replaces any prior result while required readings are incomplete."""
	return {
		"status": "waiting",
		"signal": None,
		"reasons": [],
		"waiting_for": waiting_for,
		"next_action": "Enter the missing reading to refresh the signal preview.",
	}


def _display(value):
	if value is None:
		return "not available"
	return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _economy_comparison(value, label):
	return (
		f"{label}: {_display(value)} km/L ({1 / value:.3f} L/km; {100 / value:.1f} L/100 km)"
		if value is not None and value > 0
		else f"{label}: not available"
	)


def _economy_details(facts):
	average = facts.get("average_km_per_litre")
	if average in (None, ""):
		return ["Applicable fuel economy used by this check: not available"]

	source = facts.get("average_source")
	if source == "recent_average" and average > 0:
		return [
			_economy_comparison(average, "Recent observed full-to-full average"),
			f"Applicable fuel economy used by this check: {average:g} km/L (recent weighted average)",
		]
	return [
		f"Vehicle target fuel economy: {average:g} km/L",
		f"Applicable fuel economy used by this check: {average:g} km/L (vehicle target)",
	]


def _explain_reason(text, facts, limits):
	"""Attach the source values and next step to a reason already selected by evaluate_signal."""
	details = []
	if text.startswith("Mileage does not add up"):
		previous = facts.get("previous_reading")
		current = facts.get("current_reading")
		room = _room_litres(facts)
		average = facts.get("average_km_per_litre")
		previous_source = facts.get("previous_entry_source")
		if previous_source:
			details.append(f"Previous Entry source: {previous_source}")
		details.extend(
			[
				f"Previous Entry Odometer: {_display(previous)} km",
				f"Current Odometer: {_display(current)} km",
			]
		)
		if facts.get("previous_entry_date"):
			details.append(f"Previous Entry date and time: {facts['previous_entry_date']}")
		if previous is not None and current is not None:
			details.append(
				f"Odometer distance travelled since Previous Entry: {_display(current - previous)} km"
			)
		if room is not None:
			details.append(f"Fuel estimate from current gauge: {room:g} L estimated to fill")
		if average not in (None, "") and room is not None:
			details.append(f"Expected distance: {round(average * room, 1):g} km")
			details.extend(_economy_details(facts))
		details.append(f"Allowed mileage margin: {limits['mileage_margin_percent']:g}%")
		action = "Check the Previous Entry, odometer, and gauge; correct a reading or send the red order for review."
	elif text.startswith("Mileage check cannot calculate") or "mileage does not add up:" in text.lower():
		check = facts.get("full_tank_mileage_check") or {}
		baseline = check.get("baseline") or {}
		label = baseline.get("label") or "Selected baseline"
		details.extend(
			[
				f"Baseline used: {label} ({_display(baseline.get('reference'))})",
				f"Baseline Odometer: {_display(check.get('baseline_odometer', baseline.get('vehicle_odometer')))} km",
				f"Current Odometer: {_display(check.get('current_odometer', facts.get('current_reading')))} km",
				f"Tank capacity: {_display(check.get('tank_capacity_litres', facts.get('tank_capacity')))} L",
				f"Current gauge: {_display(check.get('gauge_percent', facts.get('gauge_percent')))}%",
			]
		)
		details.append(f"Baseline date and time: {baseline.get('timestamp') or 'not available'}")
		if check.get("distance_km") is not None:
			details.append(
				f"Odometer distance travelled since selected baseline: {_display(check['distance_km'])} km"
			)
		if check.get("estimated_remaining_litres") is not None:
			details.append(f"Estimated remaining fuel: {_display(check['estimated_remaining_litres'])} L")
		if check.get("estimated_consumed_litres") is not None:
			details.append(f"Estimated fuel used: {_display(check['estimated_consumed_litres'])} L")
		if check.get("expected_distance_km") is not None:
			details.append(f"Expected distance: {check['expected_distance_km']:.1f} km")
			if check.get("average_km_per_litre") and check["average_km_per_litre"] > 0:
				details.extend(_economy_details(facts))
		if check.get("variance_percent") is not None:
			details.append(f"Difference from expected distance: {check['variance_percent']:.1f}%")
		if check.get("expected_distance_km") is None:
			if check.get("average_km_per_litre") in (None, ""):
				details.append("Applicable fuel economy used by this check: not available")
			elif check.get("average_km_per_litre") <= 0:
				details.append(
					f"Applicable fuel economy used by this check: {check['average_km_per_litre']:g} km/L (not usable)"
				)
			else:
				details.extend(_economy_details(facts))
		details.append(f"Allowed mileage margin: {limits['mileage_margin_percent']:g}%")
		action = (
			"Check the baseline, odometer, gauge, tank capacity, and applicable fuel economy; correct "
			"source data or ask a permitted approver to review the order."
		)
	elif text.startswith("More litres than the tank has room for"):
		room = _room_litres(facts)
		details.extend(
			[
				f"Partial litres requested: {_display(facts.get('requested_litres'))} L",
				f"Estimated room from current gauge: {_display(room)} L",
				f"Allowed excess: {limits['litres_excess_percent']:g}% of a {_display(facts.get('tank_capacity'))} L tank",
			]
		)
		action = "Check the requested quantity and gauge, or send the red order for review."
	elif text.startswith("Tank nearly full"):
		details.extend(
			[
				f"Current gauge: {_display(facts.get('gauge_percent'))}%",
				f"Gauge limit: {limits['gauge_limit_percent']:g}%",
			]
		)
		action = "Confirm the gauge reading; if it is correct, ask a permitted approver to review the order."
	elif text.startswith("Open order exists"):
		details.append("Another order for this asset is awaiting approval or fueling.")
		action = "Check the other order's status before creating or approving another one."
	elif text.startswith("Too soon since the last fueling"):
		details.extend(
			[
				f"Hours since last fueling: {_display(facts.get('hours_since_last_fueling'))}",
				f"Required interval: {limits['min_hours_between_fuelings']:g} hours",
			]
		)
		action = "Confirm the last fueling time and explain why an early request needs review."
	elif text.startswith("Away from home"):
		details.extend(
			[
				f"Operating location: {_display(facts.get('operational_location'))}",
				f"Assigned home location: {_display(facts.get('home_location'))}",
			]
		)
		action = "Confirm the operating location or explain why fueling away from home is needed."
	elif text.startswith("Not the usual driver"):
		details.extend(
			[
				f"Selected driver: {_display(facts.get('driver'))}",
				f"Usual assigned driver: {_display(facts.get('usual_driver'))}",
			]
		)
		action = "Confirm the driver or explain why a different driver is using the asset."
	elif text.startswith("Mileage off its own trend"):
		details.append(
			f"Recent reference is weighted across {facts.get('interval_count', 0)} completed full-to-full intervals."
		)
		action = "Check the completed fueling records and readings for this vehicle."
	else:
		action = "Check the source information and ask a permitted approver to review the red order."

	return {"text": text, "details": details, "next_action": action}


def evaluate_signal_result(facts, limits=None, workflow_state="Draft"):
	"""Run the shared signal rules and return a presentation-ready server result."""
	merged_limits = dict(DEFAULT_LIMITS)
	for key, value in (limits or {}).items():
		if value is not None:
			merged_limits[key] = value
	full_tank_mileage_check = _full_tank_mileage_result(facts, merged_limits)
	explanation_facts = {**facts, "full_tank_mileage_check": full_tank_mileage_check}
	reasons = evaluate_signal(facts, merged_limits)
	findings = [_explain_reason(reason, explanation_facts, merged_limits) for reason in reasons]
	colour = signal_colour(reasons)
	if workflow_state == "Pending Approval":
		next_action = "A permitted Fleet Approver may approve or reject this order with a reason."
	elif colour == "Red":
		next_action = (
			"A Fleet User may reject this order or send it to a permitted Fleet Approver with an explanation."
		)
	else:
		next_action = "A Fleet User may approve this green order."

	return {
		"status": "complete",
		"signal": colour,
		"reasons": findings,
		"signal_inputs": {
			"asset": facts.get("asset"),
			"asset_type": facts.get("asset_type"),
			"full_tank_baseline": facts.get("full_tank_baseline"),
			"mileage_baseline": facts.get("mileage_baseline"),
			"full_tank_mileage_check": full_tank_mileage_check,
			"current_reading": facts.get("current_reading"),
			"previous_entry_source": facts.get("previous_entry_source"),
			"previous_reading": facts.get("previous_reading"),
			"previous_entry_date": facts.get("previous_entry_date"),
			"gauge_percent": facts.get("gauge_percent"),
			"tank_capacity": facts.get("tank_capacity"),
			"fuel_estimate_litres": _room_litres(facts),
			"average_km_per_litre": facts.get("average_km_per_litre"),
			"average_source": facts.get("average_source"),
			"requested_litres": facts.get("requested_litres"),
			"last_fill_was_full": facts.get("last_fill_was_full"),
			"has_open_order": facts.get("has_open_order"),
			"hours_since_last_fueling": facts.get("hours_since_last_fueling"),
			"operational_location": facts.get("operational_location"),
			"home_location": facts.get("home_location"),
			"driver": facts.get("driver"),
			"usual_driver": facts.get("usual_driver"),
			"last_interval_km_per_litre": facts.get("last_interval_km_per_litre"),
			"interval_count": facts.get("interval_count"),
			"limits": merged_limits,
		},
		"next_action": next_action,
		"note": "A signal is review information; evidence, permissions, and required-field checks still apply.",
	}


def signal_colour(reasons):
	return "Red" if reasons else "Green"
