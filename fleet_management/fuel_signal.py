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
			f"Away from home: fuelling at {operational_location}, but its home location is "
			f"{home_location}."
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


def signal_colour(reasons):
	return "Red" if reasons else "Green"
