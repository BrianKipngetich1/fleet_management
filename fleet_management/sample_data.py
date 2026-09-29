"""Fixed sample data for the dedicated test site.

Run on the test site only:

    bench --site fleet_management-test.localhost execute fleet_management.sample_data.reset_and_seed

``reset_and_seed`` removes every fleet record (and the files, versions, comments, notices, and
User Permissions that belong to them), then creates the same sample fleet every time: four
Krystalline Salt locations, real vehicle models with their real tank sizes, a Nairobi fleet with
about two months of fuelling history, and a few open orders in each workflow state.

The fleet includes vehicles and standby generators. Philip (Fleet User) enters every Nairobi order
and approves the green ones himself; red ones go to Vikas (Fleet Approver) with his explanation.
Amina (Fleet Approver) covers Mombasa, whose orders are entered by Administrator. History runs
through the real document rules and is then dated back, so each vehicle shows realistic
kilometres per litre. Dates are relative to the day the script runs. Users are created without
passwords and keep any password already set; the root `CREDENTIALS.md` is the password inventory.
Philip's drafts include one red example of each signal check a Nairobi-scoped user can meet
(every check but away from home) and one green one.
"""

from datetime import timedelta
from io import BytesIO

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, get_datetime, now_datetime

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import record_decision_reason

TEST_SITE = "fleet_management-test.localhost"
PRINT_FORMAT = "Fuel Order Approval Slip"

# Written reasons recorded before a workflow decision (spec 002 D-10, D-11).
SEND_UP_EXPLANATION = "Long-distance delivery run; mileage confirmed with the driver."
COVER_DRIVER_EXPLANATION = "Usual driver on leave; {} is covering the route."
APPROVAL_REASON = "Explanation checked; approved."
REJECTION_REASON = "Tank still 70% full; refuel after the Thika delivery run."

FLEET_DOCTYPES = (
	"Fueling Transaction",
	"Fuel Order",
	"Asset Assignment",
	"Fleet Asset",
	"Vehicle Model",
	"Fuel Station",
	"Fleet Person",
	"Fleet Location",
	"Fuel Type",
)

PHILIP = "philip.test@example.com"
VIKAS = "vikas.test@example.com"
AMINA = "amina.test@example.com"
FLEET_ADMIN = "test.fleet.admin@example.com"
ADMIN = "Administrator"

USERS = (
	# email, first name, roles, permitted Fleet Locations
	(PHILIP, "Philip", ["Fleet User"], ["Nairobi"]),
	(VIKAS, "Vikas", ["Fleet Approver"], ["Nairobi"]),
	(AMINA, "Amina", ["Fleet Approver"], ["Mombasa"]),
	(FLEET_ADMIN, "Test Fleet Admin", ["Fleet Admin"], []),  # sees every location
)

LOCATIONS = (
	("Nairobi", "Head office and Nairobi distribution, Industrial Area"),
	("Mombasa", "Mombasa depot, Changamwe"),
	("Gongoni", "Gongoni salt works, Malindi"),
	("Marereni", "Marereni salt works, Magarini"),
)

FUEL_TYPES = ("Diesel", "Petrol")

STATIONS = (
	# name, location, approved, invoice prefix
	("Mombasa Road Service Station", "Nairobi", 1, "MRS"),
	("Industrial Area Fuel Centre", "Nairobi", 1, "IAF"),
	("Githurai Roadside Kiosk", "Nairobi", 0, "GRK"),
	("Changamwe Service Station", "Mombasa", 1, "CSS"),
	("Gongoni Fuel Point", "Gongoni", 1, "GFP"),
	("Marereni Service Station", "Marereni", 1, "MSS"),
)
INVOICE_PREFIX = {name: prefix for name, _location, _approved, prefix in STATIONS}

# Synthetic company heading and station postal addresses (002 D-13: site data, never real values).
LETTER_HEAD = "Krystalline Salt Fuel Order Slip"
LETTER_HEAD_CONTENT = (
	'<div class="company-heading">'
	"<p><strong>KRYSTALLINE SALT LIMITED</strong><br><strong>PIN NO. P000000000T</strong></p>"
	"<p>P.O Box 00000-00100<br>NAIROBI.<br>Tel: 020-0000000<br>Email: fuel.test@example.com</p>"
	"</div>"
)
STATION_ADDRESSES = {
	# station: P.O. Box, postal code, town, email
	"Mombasa Road Service Station": ("P.O Box 10001", "00100", "Nairobi", "mombasa-road.test@example.com"),
	"Industrial Area Fuel Centre": ("P.O Box 10002", "00500", "Nairobi", "industrial-area.test@example.com"),
	"Githurai Roadside Kiosk": ("P.O Box 10003", "00609", "Nairobi", "githurai.test@example.com"),
	"Changamwe Service Station": ("P.O Box 20001", "80100", "Mombasa", "changamwe.test@example.com"),
	"Gongoni Fuel Point": ("P.O Box 30001", "80200", "Malindi", "gongoni.test@example.com"),
	"Marereni Service Station": ("P.O Box 30002", "80207", "Marereni", "marereni.test@example.com"),
}

VEHICLE_MODELS = (
	# make, model, engine cc, tank litres
	("Toyota", "Hilux Double Cab 2.4 GD-6", 2393, 80),
	("Toyota", "Land Cruiser Prado 2.8 D-4D", 2755, 87),
	("Toyota", "Probox 1.5", 1496, 50),
	("Isuzu", "D-Max 3.0 Double Cab", 2999, 76),
	("Isuzu", "NQR 4.6 Truck", 4570, 100),
	("Isuzu", "FVZ Tipper", 7790, 200),
	("Mitsubishi Fuso", "Fighter FK 7.5", 7545, 200),
	("Toyota", "Land Cruiser 79 Pick-up 4.5 V8", 4461, 130),
)

PEOPLE = (
	# name, linked user, active
	("Philip", PHILIP, 1),
	("Vikas", VIKAS, 1),
	("Amina", AMINA, 1),
	("Grace Wanjiku", None, 1),  # Nairobi admin and logistics, custodian
	("Daniel Kiptoo", None, 1),  # Nairobi sales manager, custodian
	("Lucy Njeri", None, 1),  # Nairobi accounts, company representative
	("John Mwangi", None, 1),
	("Peter Otieno", None, 1),
	("Samuel Kiprono", None, 1),
	("Joseph Mutua", None, 1),
	("Fatuma Abdalla", None, 1),  # Mombasa custodian
	("Hassan Omar", None, 1),
	("James Karisa", None, 1),  # Gongoni custodian
	("Ali Bakari", None, 1),
	("Kazungu Charo", None, 1),  # Marereni custodian
	("Said Mwarimbo", None, 1),
	("Michael Onyango", None, 0),  # former driver, left the company
)


def _assignment(custodian, location, start, driver=None, until=None, reason="Fleet allocation"):
	return {
		"custodian": custodian,
		"assigned_location": location,
		"effective_from": start,
		"effective_until": until,
		"primary_driver": driver,
		"reason": reason,
	}


ASSETS = (
	# registration, type, active, fuel, model, target km/L, assignments
	(
		"KDA 412M",
		"Vehicle",
		1,
		"Diesel",
		"Toyota - Hilux Double Cab 2.4 GD-6",
		10,
		[_assignment("Grace Wanjiku", "Nairobi", "2026-01-05", "John Mwangi")],
	),
	(
		"KCZ 908T",
		"Vehicle",
		1,
		"Diesel",
		"Toyota - Land Cruiser Prado 2.8 D-4D",
		9,
		[
			_assignment("Grace Wanjiku", "Nairobi", "2025-06-02", "Peter Otieno", "2026-03-31"),
			_assignment(
				"Daniel Kiptoo",
				"Nairobi",
				"2026-04-01",
				"Peter Otieno",
				reason="Reassigned to the sales manager",
			),
		],
	),
	(
		"KDB 551Q",
		"Vehicle",
		1,
		"Petrol",
		"Toyota - Probox 1.5",
		14,
		[_assignment("Grace Wanjiku", "Nairobi", "2026-02-02", "Joseph Mutua")],
	),
	(
		"KCY 230L",
		"Vehicle",
		1,
		"Diesel",
		"Isuzu - NQR 4.6 Truck",
		6,
		[_assignment("Grace Wanjiku", "Nairobi", "2025-11-10", "Samuel Kiprono")],
	),
	(
		# Nairobi pool vehicle delivered this month: no fuelling history yet. The Playwright suite
		# creates its generic orders on it, so the realistic histories above stay untouched.
		"KDH 201A",
		"Vehicle",
		1,
		"Diesel",
		"Isuzu - D-Max 3.0 Double Cab",
		10,
		[_assignment("Grace Wanjiku", "Nairobi", "2026-09-01", "Joseph Mutua", reason="New pool vehicle")],
	),
	# Two Nairobi pick-ups kept for the signal examples: KDG 118X was fuelled a few hours before
	# the script runs; KDJ 507K's last interval is well off its own average.
	(
		"KDG 118X",
		"Vehicle",
		1,
		"Diesel",
		"Toyota - Hilux Double Cab 2.4 GD-6",
		10,
		[_assignment("Grace Wanjiku", "Nairobi", "2026-01-05", "John Mwangi")],
	),
	(
		"KDJ 507K",
		"Vehicle",
		1,
		"Diesel",
		"Toyota - Hilux Double Cab 2.4 GD-6",
		10,
		[_assignment("Grace Wanjiku", "Nairobi", "2026-01-05", "Samuel Kiprono")],
	),
	(
		"KBZ 615J",
		"Vehicle",
		0,
		"Diesel",
		"Isuzu - D-Max 3.0 Double Cab",
		10,
		[_assignment("Grace Wanjiku", "Nairobi", "2024-03-01", "Michael Onyango", "2026-06-30")],
	),
	(
		"KDE 774H",
		"Vehicle",
		1,
		"Diesel",
		"Mitsubishi Fuso - Fighter FK 7.5",
		4,
		[_assignment("Fatuma Abdalla", "Mombasa", "2025-09-01", "Hassan Omar")],
	),
	(
		"KDC 339F",
		"Vehicle",
		1,
		"Diesel",
		"Isuzu - FVZ Tipper",
		3.5,
		[_assignment("James Karisa", "Gongoni", "2025-08-18", "Ali Bakari")],
	),
	(
		"KCX 102P",
		"Vehicle",
		1,
		"Diesel",
		"Toyota - Land Cruiser 79 Pick-up 4.5 V8",
		7,
		[_assignment("Kazungu Charo", "Marereni", "2025-10-06", "Said Mwarimbo")],
	),
	# Generators carry no vehicle model; the target field is required but unused for them. The
	# driver is whoever collects fuel for the set.
	(
		"GEN-NRB-01 Cummins 100 kVA",
		"Generator",
		1,
		"Diesel",
		None,
		1,
		[
			_assignment(
				"Grace Wanjiku", "Nairobi", "2025-11-10", "Samuel Kiprono", reason="Head office standby power"
			)
		],
	),
	(
		"GEN-GON-01 Perkins 250 kVA",
		"Generator",
		1,
		"Diesel",
		None,
		1,
		[_assignment("James Karisa", "Gongoni", "2025-08-18", "Ali Bakari", reason="Salt works brine pumps")],
	),
)

# The most a generator order may authorise, in litres (D-2 of 001: generators get a maximum).
GENERATOR_MAX_LITRES = {"GEN-NRB-01 Cummins 100 kVA": 200, "GEN-GON-01 Perkins 250 kVA": 1200}

# Completed fuelling history, oldest first. Each row: days ago, request meter reading (odometer km
# for vehicles, hour meter for generators), request gauge % (vehicles only), invoice litres, full
# tank (vehicles only), station. Vehicle rows give realistic km/L for each model; the standby
# generator runs about 10 hours a fortnight at about 16 litres an hour. A row 0 days ago is dated
# a few hours before the script runs.
HISTORY = {
	"KDA 412M": [
		(58, 48210, 20, 64.2, 1, "Mombasa Road Service Station"),
		(50, 48850, 22, 63.1, 1, "Mombasa Road Service Station"),
		(42, 49455, 25, 61.0, 1, "Industrial Area Fuel Centre"),
		(33, 50120, 18, 66.5, 1, "Mombasa Road Service Station"),
		(24, 50730, 24, 62.0, 1, "Mombasa Road Service Station"),
		(15, 51395, 20, 65.8, 1, "Industrial Area Fuel Centre"),
		(6, 52020, 22, 63.0, 1, "Mombasa Road Service Station"),
	],
	"KCZ 908T": [
		(55, 31500, 15, 74.0, 1, "Industrial Area Fuel Centre"),
		(45, 32140, 20, 70.5, 1, "Industrial Area Fuel Centre"),
		(35, 32790, 17, 72.8, 1, "Mombasa Road Service Station"),
		(25, 33400, 22, 68.0, 1, "Industrial Area Fuel Centre"),
		(12, 34020, 20, 69.4, 1, "Industrial Area Fuel Centre"),
	],
	"KDB 551Q": [
		(52, 102300, 20, 40.1, 1, "Mombasa Road Service Station"),
		(45, 102860, 18, 40.8, 1, "Mombasa Road Service Station"),
		(38, 103420, 20, 39.5, 1, "Industrial Area Fuel Centre"),
		(30, 103700, 55, 20.0, 0, "Mombasa Road Service Station"),  # authorised partial fill
		(26, 104010, 25, 22.5, 1, "Mombasa Road Service Station"),
		(18, 104580, 20, 41.0, 1, "Industrial Area Fuel Centre"),
		(9, 105150, 18, 41.5, 1, "Mombasa Road Service Station"),
	],
	"KCY 230L": [
		(50, 215400, 20, 80.5, 1, "Industrial Area Fuel Centre"),
		(40, 215880, 18, 81.0, 1, "Industrial Area Fuel Centre"),
		(30, 216350, 22, 78.0, 1, "Industrial Area Fuel Centre"),
		(19, 216820, 20, 79.5, 1, "Industrial Area Fuel Centre"),
		(8, 217290, 25, 76.5, 1, "Industrial Area Fuel Centre"),
	],
	"KDE 774H": [
		(40, 388100, 25, 150.0, 1, "Changamwe Service Station"),
		(20, 388700, 20, 152.0, 1, "Changamwe Service Station"),
	],
	"GEN-NRB-01 Cummins 100 kVA": [
		(56, 1240.0, None, 160.0, 0, "Mombasa Road Service Station"),
		(42, 1251.0, None, 172.0, 0, "Mombasa Road Service Station"),
		(28, 1260.5, None, 150.0, 0, "Industrial Area Fuel Centre"),
		(14, 1271.0, None, 168.0, 0, "Mombasa Road Service Station"),
	],
	"KDG 118X": [
		(30, 70000, 20, 64.0, 1, "Industrial Area Fuel Centre"),
		(20, 70640, 22, 63.0, 1, "Mombasa Road Service Station"),
		(10, 71265, 21, 62.5, 1, "Industrial Area Fuel Centre"),
		(0, 71900, 20, 64.0, 1, "Mombasa Road Service Station"),
	],
	"KDJ 507K": [
		(52, 60000, 20, 64.0, 1, "Industrial Area Fuel Centre"),
		(42, 60600, 18, 66.0, 1, "Industrial Area Fuel Centre"),
		(32, 61205, 20, 66.5, 1, "Mombasa Road Service Station"),
		(22, 61800, 19, 65.5, 1, "Industrial Area Fuel Centre"),
		(12, 62400, 17, 66.0, 1, "Industrial Area Fuel Centre"),
		(3, 62672, 68, 25.0, 1, "Mombasa Road Service Station"),  # 10.9 km/L against about 9.1
	],
}

REQUESTERS = {
	"KDA 412M": "John Mwangi",
	"KCZ 908T": "Daniel Kiptoo",
	"KDB 551Q": "Joseph Mutua",
	"KCY 230L": "Samuel Kiprono",
	"KDE 774H": "Hassan Omar",
	"KDG 118X": "Grace Wanjiku",
	"KDJ 507K": "Daniel Kiptoo",
	"GEN-NRB-01 Cummins 100 kVA": "Grace Wanjiku",
	"GEN-GON-01 Perkins 250 kVA": "James Karisa",
}
REPRESENTATIVE = {"Nairobi": "Lucy Njeri", "Mombasa": "Fatuma Abdalla"}
ATTENDANTS = ("Brian Ouma", "Mercy Atieno", "Kevin Njoroge", "Esther Wambui")


def reset_and_seed():
	reset()
	seed()


def reset():
	"""Remove every fleet record and the framework records that belong to them."""
	_assert_test_site()
	frappe.set_user(ADMIN)

	files = frappe.get_all(
		"File",
		filters={"is_folder": 0},
		or_filters=[
			["attached_to_doctype", "in", FLEET_DOCTYPES],
			["attached_to_doctype", "is", "not set"],
		],
		pluck="name",
	)
	for name in files:
		frappe.delete_doc("File", name, force=True, ignore_permissions=True)

	for doctype, field in (
		("Version", "ref_doctype"),
		("Comment", "reference_doctype"),
		("Notification Log", "document_type"),
		("Workflow Action", "reference_doctype"),
		("Activity Log", "reference_doctype"),
		("Email Queue", "reference_doctype"),
		("ToDo", "reference_type"),
		("Deleted Document", "deleted_doctype"),
	):
		frappe.db.delete(doctype, {field: ("in", FLEET_DOCTYPES)})

	addresses = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": ("in", FLEET_DOCTYPES)},
		pluck="parent",
	)
	for name in set(addresses):
		frappe.delete_doc("Address", name, force=True, ignore_permissions=True)
	frappe.db.delete("Letter Head", {"name": LETTER_HEAD})

	frappe.db.delete("User Permission", {"allow": ("in", FLEET_DOCTYPES)})
	for doctype in FLEET_DOCTYPES:
		frappe.db.delete(doctype)
	# Restart order and transaction numbering so every reseed gives the same document names.
	frappe.db.sql("DELETE FROM `tabSeries` WHERE name LIKE 'FO-%%' OR name LIKE 'FT-%%'")

	settings = frappe.get_single("Fleet Management Settings")
	settings.update(
		{
			"default_tolerance_percent": 2,
			"orange_band_percent": 10,
			"red_band_percent": 20,
			"default_validity_days": 3,
			"print_instruction": "Do not dispense after the valid-until timestamp.",
			"transaction_entry_sla_hours": 48,
			"mileage_margin_percent": 15,
			"litres_excess_percent": 10,
			"gauge_limit_percent": 75,
			"min_hours_between_fuelings": 24,
		}
	)
	settings.save(ignore_permissions=True)
	frappe.db.commit()


def seed():
	_assert_test_site()
	frappe.set_user(ADMIN)
	if frappe.db.count("Fuel Order") or frappe.db.count("Fleet Asset"):
		frappe.throw("Fleet data already exists. Run reset_and_seed to start again from empty.")

	_seed_users()
	_seed_masters()
	_seed_location_access()
	frappe.db.commit()

	sequence = iter(range(1, 10_000))
	for asset, rows in HISTORY.items():
		for days_ago, odometer, gauge, litres, full, station in rows:
			_completed_cycle(
				asset,
				days_ago,
				odometer,
				gauge,
				litres,
				full,
				station,
				next(sequence),
				hours_ago=8 if days_ago == 0 else None,
			)
	_open_orders()
	frappe.set_user(ADMIN)
	frappe.db.commit()


def _assert_test_site():
	if frappe.local.site != TEST_SITE or not frappe.conf.allow_tests:
		frappe.throw(f"Sample data may only be loaded on {TEST_SITE}.")


def _seed_users():
	for email, first_name, roles, _locations in USERS:
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.new_doc("User")
			user.email = email
			user.send_welcome_email = 0
		user.update({"first_name": first_name, "last_name": None, "enabled": 1, "user_type": "System User"})
		user.set("roles", [{"role": role} for role in roles])
		user.save(ignore_permissions=True)


def _seed_location_access():
	for email, _first_name, _roles, locations in USERS:
		for location in locations:
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "Fleet Location",
					"for_value": location,
					"apply_to_all_doctypes": 1,
				}
			).insert(ignore_permissions=True)


def _seed_masters():
	for name, description in LOCATIONS:
		_insert("Fleet Location", location_name=name, description=description, active=1)
	for name in FUEL_TYPES:
		_insert("Fuel Type", fuel_type_name=name, active=1)
	for name, location, approved, _prefix in STATIONS:
		_insert("Fuel Station", station_name=name, operational_location=location, active=1, approved=approved)
	for station, (box, postal_code, town, email) in STATION_ADDRESSES.items():
		_insert(
			"Address",
			address_title=station,
			address_type="Postal",
			address_line1=box,
			pincode=postal_code,
			city=town,
			country="Kenya",
			email_id=email,
			is_primary_address=1,
			links=[{"link_doctype": "Fuel Station", "link_name": station}],
		)
	_insert(
		"Letter Head",
		letter_head_name=LETTER_HEAD,
		source="HTML",
		content=LETTER_HEAD_CONTENT,
		is_default=1,
	)
	# Letter Head.before_insert switches a new letter head to "Image"; keep the sample one HTML-based.
	frappe.db.set_value("Letter Head", LETTER_HEAD, "source", "HTML")
	for make, model, engine_cc, tank in VEHICLE_MODELS:
		_insert(
			"Vehicle Model", make=make, model=model, engine_capacity_cc=engine_cc, tank_capacity_litres=tank
		)
	for name, user, active in PEOPLE:
		_insert("Fleet Person", person_name=name, user=user, active=active)
	for registration, asset_type, active, fuel, model, target, assignments in ASSETS:
		_insert(
			"Fleet Asset",
			asset_identifier=registration,
			asset_type=asset_type,
			active=active,
			fuel_type=fuel,
			vehicle_model=model,
			target_km_per_litre=target,
			assignments=assignments,
		)


def _insert(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _people(asset):
	location = _home_location(asset)
	assignment = frappe.get_all(
		"Asset Assignment",
		filters={"parent": asset, "effective_until": ("is", "not set")},
		fields=["custodian", "primary_driver"],
		limit=1,
	)[0]
	return location, assignment.custodian, assignment.primary_driver


def _home_location(asset):
	return frappe.get_all(
		"Asset Assignment",
		filters={"parent": asset, "effective_until": ("is", "not set")},
		pluck="assigned_location",
		limit=1,
	)[0]


def _actors(location):
	# Nairobi: Philip enters, Vikas signs off red orders. Mombasa: Administrator enters, Amina signs off.
	return (PHILIP, VIKAS) if location == "Nairobi" else (ADMIN, AMINA)


def _is_generator(asset):
	return frappe.db.get_value("Fleet Asset", asset, "asset_type") == "Generator"


def _new_order(asset, meter, gauge, station, partial_litres=None, driver=None):
	location, custodian, usual_driver = _people(asset)
	if _is_generator(asset):
		partial_litres = GENERATOR_MAX_LITRES[asset]
	order = frappe.get_doc(
		{
			"doctype": "Fuel Order",
			"request_datetime": now_datetime(),
			"asset": asset,
			"actual_requester": REQUESTERS[asset],
			"driver": driver or usual_driver,
			"custodian": custodian,
			"company_representative": REPRESENTATIVE[location],
			"operational_location": location,
			"planned_station": station,
			"fuel_type": frappe.db.get_value("Fleet Asset", asset, "fuel_type"),
			"request_meter_reading": meter,
			"request_gauge_percent": gauge,
			"quantity_authorization": "Partial" if partial_litres else "Full",
			"authorized_quantity_litres": partial_litres,
		}
	)
	entered_by, _approver = _actors(location)
	frappe.set_user(entered_by)
	order.insert()
	# Philip photographs the meter and, for a vehicle, the gauge (spec 002 D-6).
	generator = _is_generator(asset)
	photos = {
		"meter_photo": _evidence(
			f"{order.name}-meter.png",
			["METER PHOTO", f"{'Hour meter' if generator else 'Odometer'} {meter}", f"Asset {asset}"],
		)
	}
	if not generator:
		photos["gauge_photo"] = _evidence(
			f"{order.name}-gauge.png", ["GAUGE PHOTO", f"Fuel gauge {gauge}%", f"Asset {asset}"]
		)
	order.update(photos)
	order.save()
	return order


def _send_up(order, explanation=SEND_UP_EXPLANATION):
	"""As the entering user, record the explanation for a red order and send it for sign-off."""
	entered_by, _approver = _actors(order.operational_location)
	frappe.set_user(entered_by)
	record_decision_reason(order.name, "Submit for Approval", explanation)
	return apply_workflow(frappe.get_doc("Fuel Order", order.name), "Submit for Approval")


def _submit_and_approve(order):
	# The colour decides the route: green is approved by whoever entered it; red is explained, sent
	# up, and approved with a written reason. The slip is printed by the user who approved.
	entered_by, approver = _actors(order.operational_location)
	order = frappe.get_doc("Fuel Order", order.name)
	if order.signal == "Green":
		frappe.set_user(entered_by)
		order = apply_workflow(order, "Approve")
	else:
		_send_up(order)
		frappe.set_user(approver)
		record_decision_reason(order.name, "Approve", APPROVAL_REASON)
		order = apply_workflow(frappe.get_doc("Fuel Order", order.name), "Approve")
	frappe.get_print("Fuel Order", order.name, print_format=PRINT_FORMAT, no_letterhead=1)
	return frappe.get_doc("Fuel Order", order.name)


def _completed_cycle(asset, days_ago, meter, gauge, litres, full, station, sequence, hours_ago=None):
	generator = _is_generator(asset)
	order = _new_order(asset, meter, gauge, station, partial_litres=None if full else litres)
	order = _submit_and_approve(order)
	entered_by, _approver = _actors(order.operational_location)

	frappe.set_user(entered_by)
	transaction = frappe.get_doc({"doctype": "Fueling Transaction", "fuel_order": order.name}).insert()
	invoice_number = f"{INVOICE_PREFIX[station]}-{sequence:06d}"
	transaction.update(
		{
			"actual_station": station,
			"fuel_type": order.fuel_type,
			"invoice_number": invoice_number,
			"cu_number": f"0110{sequence:015d}",
			"actual_fueling_datetime": get_datetime(order.approved_on) + timedelta(minutes=1),
			"fueling_time_source": "Printed on invoice",
			# A vehicle drives a few kilometres to the station; a generator's hours do not move.
			**({"hour_meter": meter} if generator else {"vehicle_odometer": meter + 4}),
			"invoice_litres": litres,
			"full_tank_confirmed": full,
			"attendant_name": ATTENDANTS[sequence % len(ATTENDANTS)],
		}
	)
	transaction.save()
	invoice = _evidence(
		f"{invoice_number}.png",
		[station, f"Invoice {invoice_number}", f"{order.fuel_type} {litres:.2f} L", f"Vehicle {asset}"],
	)
	signed = _evidence(
		f"{order.name}-signed.png",
		[
			"FUEL ORDER SLIP (signed)",
			order.name,
			f"{'Generator' if generator else 'Reg No'} {asset}",
			f"{'Hour meter' if generator else 'Speedometer'} {meter}",
		],
	)
	transaction.update({"signed_invoice": invoice, "signed_order": signed})
	transaction.save()
	transaction.submit()

	_date_back(order, transaction, days_ago, hours_ago)


def _evidence(file_name, lines):
	from PIL import Image, ImageDraw

	image = Image.new("RGB", (640, 360), "white")
	draw = ImageDraw.Draw(image)
	draw.text((24, 20), "SAMPLE DATA - TEST SITE", fill=(160, 0, 0))
	for index, line in enumerate(lines):
		draw.text((24, 70 + index * 40), line, fill=(0, 0, 0))
	buffer = BytesIO()
	image.save(buffer, format="PNG")
	previous_user = frappe.session.user
	frappe.set_user(ADMIN)
	file_doc = _insert("File", file_name=file_name, content=buffer.getvalue(), is_private=1)
	frappe.set_user(previous_user)
	return file_doc.file_url


def _date_back(order, transaction, days_ago, hours_ago=None):
	"""Move a finished cycle to a realistic past working day, keeping its validity window intact."""
	requested = get_datetime(add_days(now_datetime().date(), -days_ago)).replace(hour=8, minute=15)
	if hours_ago is not None:
		# Earlier today: requested this many hours before the script runs, fuelled 2 h 40 min later.
		requested = now_datetime() - timedelta(hours=hours_ago)
	approved = requested + timedelta(minutes=40)
	validity_days = frappe.db.get_single_value("Fleet Management Settings", "default_validity_days") or 3
	valid_until = approved + timedelta(days=validity_days)
	delta = requested - get_datetime(order.creation)

	frappe.db.set_value(
		"Fuel Order",
		order.name,
		{
			"request_datetime": requested,
			"submitted_on": requested + timedelta(minutes=5) if order.submitted_by else None,
			"approved_on": approved,
			"valid_until": valid_until,
			"last_slip_printed_on": approved + timedelta(minutes=5),
			"creation": requested,
			"modified": approved + timedelta(minutes=5),
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
				"modified": fuelled + timedelta(hours=4),
			},
			update_modified=False,
		)

	names = [order.name] + ([transaction.name] if transaction else [])
	seconds = int(delta.total_seconds())
	for doctype, field in (
		("Version", "docname"),
		("Comment", "reference_name"),
		("Notification Log", "document_name"),
		("Workflow Action", "reference_name"),
		("File", "attached_to_name"),
	):
		frappe.db.sql(
			f"""UPDATE `tab{doctype}`
			SET creation = DATE_ADD(creation, INTERVAL %(seconds)s SECOND),
				modified = DATE_ADD(modified, INTERVAL %(seconds)s SECOND)
			WHERE `{field}` IN %(names)s""",
			{"seconds": seconds, "names": names},
		)


def _open_orders():
	"""Orders in each state Philip, Vikas, and Amina meet today."""
	# Approved this morning, slip printed, not yet fuelled.
	_submit_and_approve(_new_order("KDA 412M", 52650, 21, "Mombasa Road Service Station"))

	# Approved five days ago and never fuelled: validity has lapsed.
	expired = _submit_and_approve(_new_order("KCZ 908T", 34580, 24, "Industrial Area Fuel Centre"))
	_date_back(expired, None, 5)

	# Waiting for Vikas: Joseph Mutua covers Samuel Kiprono's truck, which turns the order red.
	pending = _new_order("KCY 230L", 217760, 20, "Industrial Area Fuel Centre", driver="Joseph Mutua")
	_send_up(pending, COVER_DRIVER_EXPLANATION.format("Joseph Mutua"))

	# Rejected by Philip: tank still 70% full; refuel after the Thika delivery run.
	rejected = _new_order("KDB 551Q", 105300, 70, "Mombasa Road Service Station")
	frappe.set_user(PHILIP)
	record_decision_reason(rejected.name, "Reject", REJECTION_REASON)
	apply_workflow(frappe.get_doc("Fuel Order", rejected.name), "Reject")

	# Philip's draft, not yet sent.
	_new_order("KCZ 908T", 34650, 23, "Industrial Area Fuel Centre")

	# Head office generator: approved for up to 200 litres after a long outage, not yet fuelled.
	_submit_and_approve(
		_new_order("GEN-NRB-01 Cummins 100 kVA", 1283.5, None, "Mombasa Road Service Station")
	)

	# Mombasa order waiting for Amina; Philip and Vikas cannot see it. Fatuma Abdalla covers
	# Hassan Omar's truck, which turns the order red.
	pending_mombasa = _new_order("KDE 774H", 389310, 22, "Changamwe Service Station", driver="Fatuma Abdalla")
	_send_up(pending_mombasa, COVER_DRIVER_EXPLANATION.format("Fatuma Abdalla"))

	_signal_cases()


def _signal_cases():
	"""Philip's drafts that each fail one signal check (spec 002 D-8, AC-08), and one that is green.

	Last fuelled at, average km/L, tank: KCZ 908T 34,024 km, 8.98, 87 L; KDA 412M 52,024 km, 9.96,
	80 L; KDG 118X 71,904 km, 10.03, 80 L; KDJ 507K 62,676 km, 9.25, 80 L. Away from home cannot
	be shown: Philip may use only Nairobi vehicles at Nairobi.
	"""
	station = "Industrial Area Fuel Centre"

	# Green: 606 km on 66.99 L of room is within 1% of the 602 km expected.
	_new_order("KCZ 908T", 34630, 23, station)

	# Check 1, "Mileage does not add up": 876 km against 586 km expected.
	_new_order("KCZ 908T", 34900, 25, station)

	# Check 2, "More litres than the tank has room for": 80 L against 65.25 L of room plus 8.7 L.
	_new_order("KCZ 908T", 34610, 25, station, partial_litres=80)

	# Check 3, "Tank nearly full": gauge 80%; 156 km matches the 17.4 L of room.
	_new_order("KCZ 908T", 34180, 80, station)

	# Check 4, "Open order exists": its approved order at 52,650 km still awaits fuel.
	_new_order("KDA 412M", 52655, 21, "Mombasa Road Service Station")

	# Check 5, "Too soon since the last fueling": filled about five hours before the script ran;
	# 241 km matches the 24 L of room.
	_new_order("KDG 118X", 72145, 70, station)

	# Check 7, "Not the usual driver": John Mwangi drives Peter Otieno's vehicle.
	_new_order("KCZ 908T", 34634, 22, station, driver="John Mwangi")

	# Check 8, "Mileage off its own trend": last interval 10.88 km/L against 9.25 (18% off);
	# 558 km matches the 60 L of room.
	_new_order("KDJ 507K", 63234, 25, station)
