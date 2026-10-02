"""Green/red signal for a Fuel Order (spec 002 D-8). Pure: callers gather the facts."""

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
			f"Mileage does not add up: the meter has not moved forward since the previous "
			f"entry ({previous_reading:g})."
		)

	expected = average * room
	if expected <= 0:
		return None

	variance = abs(distance - expected) / expected * 100
	margin = limits["mileage_margin_percent"]
	if round(variance, 6) > margin:
		expected_rounded = round(expected, 1)
		return (
			f"Mileage does not add up: {distance:g} km since the previous entry, "
			f"{expected_rounded:g} km expected ({variance:.0f}% off; limit {margin:g}%)."
			f"{_approx_note(facts)}"
		)
	return None


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
		last_rounded = round(last, 2)
		average_rounded = round(average, 2)
		return (
			f"Mileage off its own trend: the last interval gave {last_rounded:g} km/L against "
			f"an average of {average_rounded:g} km/L ({off:.0f}% off; limit {margin:g}%)."
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


def _economy_details(facts):
	average = facts.get("average_km_per_litre")
	if average in (None, ""):
		return ["Applicable fuel economy: not available"]

	source = facts.get("average_source")
	if source == "recent_average" and average > 0:
		return [
			f"Observed full-to-full average: {average:g} km/L "
			f"({1 / average:.3f} L/km; {100 / average:.1f} L/100 km)"
		]
	return [f"Applicable fuel economy: {average:g} km/L (vehicle target)"]


def _explain_reason(text, facts, limits):
	"""Attach the source values and next step to a reason already selected by evaluate_signal."""
	details = []
	if text.startswith("Mileage does not add up"):
		previous = facts.get("previous_reading")
		current = facts.get("current_reading")
		room = _room_litres(facts)
		average = facts.get("average_km_per_litre")
		details.extend(
			[
				f"Previous Entry: {_display(previous)} km",
				f"Current odometer: {_display(current)} km",
			]
		)
		if previous is not None and current is not None:
			details.append(f"Distance since Previous Entry: {_display(current - previous)} km")
		if room is not None:
			details.append(f"Fuel estimate from current gauge: {room:g} L estimated to fill")
		if average not in (None, "") and room is not None:
			details.append(f"Expected distance: {round(average * room, 1):g} km")
			details.extend(_economy_details(facts))
		details.append(f"Allowed mileage margin: {limits['mileage_margin_percent']:g}%")
		action = "Check the Previous Entry, odometer, and gauge; correct a reading or send the red order for review."
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
		last = facts.get("last_interval_km_per_litre")
		average = facts.get("average_km_per_litre")
		details.extend(
			[
				f"Latest completed interval: {_display(last)} km/L",
				f"Recent full-to-full average: {_display(average)} km/L",
				f"Allowed mileage margin: {limits['mileage_margin_percent']:g}%",
			]
		)
		if last and last > 0 and average and average > 0:
			details.extend(
				[
					f"Latest interval equivalent: {1 / last:.3f} L/km; {100 / last:.1f} L/100 km",
					f"Average equivalent: {1 / average:.3f} L/km; {100 / average:.1f} L/100 km",
				]
			)
		action = "Check the completed fueling records and readings for this vehicle."
	else:
		action = "Check the source information and ask a permitted approver to review the red order."

	return {"text": text, "details": details, "next_action": action}


def evaluate_signal_result(facts, limits=None, workflow_state="Draft"):
	"""Run the shared signal rules and return a presentation-ready server result."""
	reasons = evaluate_signal(facts, limits)
	merged_limits = dict(DEFAULT_LIMITS)
	for key, value in (limits or {}).items():
		if value is not None:
			merged_limits[key] = value
	findings = [_explain_reason(reason, facts, merged_limits) for reason in reasons]
	colour = signal_colour(reasons)
	if workflow_state == "Pending Approval":
		next_action = "A permitted Fleet Approver may approve or reject this order with a reason."
	elif colour == "Red":
		next_action = "A Fleet User may reject this order or send it to a permitted Fleet Approver with an explanation."
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
