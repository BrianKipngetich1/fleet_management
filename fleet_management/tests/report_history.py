"""Throwaway fuelling history for the oversight-report tests (spec 008).

The reports read real orders and fuellings, so these tests build their own instead of reading the
test site's sample data (which holds no history since spec 006): two locations, each with a
station, a Fleet User, a Fleet Approver, and a vehicle; a generator at the first location; a Fleet
Admin; fill-ups on past days, including a full, partial, full interval; one fill-up recorded
without an invoice amount, as legacy records were; and one order in each other state (pending,
rejected, approved and awaiting fuelling, expired). Everything is rolled back with the test class.
"""

from datetime import timedelta

import frappe
from frappe.utils import add_days, get_datetime, now_datetime

from fleet_management.tests.utils import attach_request_photos, decide, make_photo, send_up

PRINT_FORMAT = "Fuel Order Approval Slip"
VALIDITY_DAYS = 3
SETTINGS = {
	"gauge_limit_percent": 30,
	"mileage_margin_percent": 15,
	"litres_excess_percent": 10,
	"min_hours_between_fuelings": 24,
	"default_validity_days": VALIDITY_DAYS,
}
GREEN_GAUGE = 20
RED_GAUGE = 90  # above the gauge limit, so the order needs an approver's sign-off


class ReportHistoryFixture:
	"""Builds the history once per test class; the class rollback removes it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		try:
			cls._build_history()
		finally:
			frappe.set_user("Administrator")

	@classmethod
	def _build_history(cls):
		suffix = frappe.generate_hash(length=8)
		settings = frappe.get_single("Fleet Management Settings")
		settings.update(SETTINGS)
		settings.save(ignore_permissions=True)

		cls.north = _insert("Fleet Location", location_name=f"R008 North {suffix}").name
		cls.south = _insert("Fleet Location", location_name=f"R008 South {suffix}").name
		cls.fuel_type = _insert("Fuel Type", fuel_type_name=f"R008 Diesel {suffix}").name
		model = _insert(
			"Vehicle Model", make=f"R008 Make {suffix}", model=f"R008 Model {suffix}", tank_capacity_litres=80
		).name
		cls.person = _insert("Fleet Person", person_name=f"R008 Person {suffix}").name
		cls.admin = _user("Fleet Admin")
		cls.users, cls.approvers, cls.stations, cls.vehicles = {}, {}, {}, {}
		for location in (cls.north, cls.south):
			cls.users[location] = _user("Fleet User", location)
			cls.approvers[location] = _user("Fleet Approver", location)
			cls.stations[location] = _insert(
				"Fuel Station",
				station_name=f"R008 Station {location}",
				operational_location=location,
				active=1,
				approved=1,
			).name
			cls.vehicles[location] = cls._asset(f"R008 Vehicle {location}", "Vehicle", model, location, 10)
		cls.generator = cls._asset(f"R008 Generator {suffix}", "Generator", model, cls.north, 1)

		# North vehicle: full (20 days ago), partial (15), full (10), full (4). The middle three make
		# a full-to-full interval with a partial fill inside it.
		for days_ago, meter, litres, full in (
			(20, 10000, 60, 1),
			(15, 10250, 20, 0),
			(10, 10500, 30, 1),
			(4, 10800, 35, 1),
		):
			cls._fill_up(cls.vehicles[cls.north], cls.north, days_ago, meter, litres, full)
		cls._fill_up(cls.generator, cls.north, 8, 500, 80, 1)
		# South vehicle: two full fill-ups, the second recorded without an invoice amount.
		cls._fill_up(cls.vehicles[cls.south], cls.south, 12, 20000, 50, 1)
		legacy = cls._fill_up(cls.vehicles[cls.south], cls.south, 6, 20400, 45, 1)
		frappe.db.set_value(
			"Fueling Transaction",
			legacy,
			{"invoice_amount": 0, "printed_unit_price": 0},
			update_modified=False,
		)

		# One order in each remaining state, on the south vehicle.
		south = cls.vehicles[cls.south]
		expired = cls._approved_order(south, cls.south, 20500, GREEN_GAUGE)
		_date_back(expired, None, VALIDITY_DAYS + 2)
		rejected = cls._order(south, cls.south, 20510, RED_GAUGE)
		cls._as(cls.users[cls.south], send_up, rejected)
		cls._as(cls.approvers[cls.south], decide, rejected, "Reject", "The tank was nearly full.")
		cls._approved_order(south, cls.south, 20520, GREEN_GAUGE)
		pending = cls._order(south, cls.south, 20530, RED_GAUGE)
		cls._as(cls.users[cls.south], send_up, pending)

	@classmethod
	def _asset(cls, identifier, asset_type, model, location, target):
		return _insert(
			"Fleet Asset",
			asset_identifier=identifier,
			asset_type=asset_type,
			fuel_type=cls.fuel_type,
			vehicle_model=model,
			target_km_per_litre=target,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": cls.person,
					"assigned_location": location,
					"effective_from": "2026-01-01",
				}
			],
		).name

	@classmethod
	def _as(cls, user, function, *args):
		frappe.set_user(user)
		try:
			return function(*args)
		finally:
			frappe.set_user("Administrator")

	@classmethod
	def _order(cls, asset, location, meter, gauge):
		is_vehicle = frappe.db.get_value("Fleet Asset", asset, "asset_type") == "Vehicle"

		def insert():
			order = frappe.get_doc(
				{
					"doctype": "Fuel Order",
					"actual_requester": cls.person,
					"driver": cls.person,
					"custodian": cls.person,
					"company_representative": cls.person,
					"asset": asset,
					"operational_location": location,
					"planned_station": cls.stations[location],
					"request_meter_reading": meter,
					"request_gauge_percent": gauge if is_vehicle else None,
				}
			).insert()
			return attach_request_photos(order)

		return cls._as(cls.users[location], insert)

	@classmethod
	def _approved_order(cls, asset, location, meter, gauge):
		order = cls._order(asset, location, meter, gauge)
		if order.signal == "Green":
			return cls._as(cls.users[location], decide, order, "Approve")
		cls._as(cls.users[location], send_up, order)
		return cls._as(cls.approvers[location], decide, order, "Approve")

	@classmethod
	def _fill_up(cls, asset, location, days_ago, meter, litres, full):
		order = cls._approved_order(asset, location, meter, GREEN_GAUGE)
		is_vehicle = frappe.db.get_value("Fleet Asset", asset, "asset_type") == "Vehicle"

		def record():
			frappe.get_print("Fuel Order", order.name, print_format=PRINT_FORMAT, no_letterhead=1)
			transaction = frappe.get_doc(
				{"doctype": "Fueling Transaction", "fuel_order": order.name}
			).insert()
			transaction.update(
				{
					"actual_station": order.planned_station,
					"fuel_type": order.fuel_type,
					"actual_fueling_datetime": now_datetime(),
					"fueling_time_source": "Printed on invoice",
					"attendant_name": "R008 Attendant",
					"invoice_litres": litres,
					"invoice_amount": round(litres * 185, 2),
					"printed_unit_price": 185,
					"full_tank_confirmed": full,
					"invoice_number": f"R008-INV-{frappe.generate_hash(length=8)}",
					"cu_number": f"R008-CU-{frappe.generate_hash(length=8)}",
					**({"vehicle_odometer": meter} if is_vehicle else {"hour_meter": meter}),
					"signed_invoice": make_photo("pdf").file_url,
					"signed_order": make_photo("pdf").file_url,
				}
			)
			transaction.save()
			transaction.submit()
			return transaction

		transaction = cls._as(cls.users[location], record)
		_date_back(frappe.get_doc("Fuel Order", order.name), transaction, days_ago)
		return transaction.name


def _insert(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _user(role, location=None):
	user = _insert(
		"User",
		email=f"r008-{frappe.generate_hash(length=8)}@example.com",
		first_name="R008",
		send_welcome_email=0,
		roles=[{"doctype": "Has Role", "role": role}],
	).name
	if location:
		_insert("User Permission", user=user, allow="Fleet Location", for_value=location)
	frappe.clear_cache(user=user)
	return user


def _date_back(order, transaction, days_ago):
	"""Move a finished order (and its fuelling) to 08:15 on a past day, keeping its validity window."""
	requested = get_datetime(add_days(now_datetime().date(), -days_ago)).replace(hour=8, minute=15)
	approved = requested + timedelta(minutes=40)
	valid_until = approved + timedelta(days=VALIDITY_DAYS)
	frappe.db.set_value(
		"Fuel Order",
		order.name,
		{
			"request_datetime": requested,
			"approved_on": approved,
			"valid_until": valid_until,
			"creation": requested,
		},
		update_modified=False,
	)
	if transaction:
		fuelled = approved + timedelta(hours=2)
		frappe.db.set_value(
			"Fueling Transaction",
			transaction.name,
			{
				"approved_on": approved,
				"valid_until": valid_until,
				"actual_fueling_datetime": fuelled,
				"submitted_on": fuelled + timedelta(hours=4),
				"creation": fuelled + timedelta(hours=3),
			},
			update_modified=False,
		)
