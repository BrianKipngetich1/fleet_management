"""The company's real fleet: the starting data of the main site and of every rebuilt test site.

Copied on 07/10/2026 from the owner's filled import templates (files 1-6), with the owner's
corrections applied (spec 006 D-10, D-11): one Dennis Kamau; "Lexus" and "Urban Cruiser";
KBR136G uses the model template's ELF-PB-NPR81AN; KLW and Athi_MV were sites, not people, so the
generator and the mobile crane are held by Phyllis at Kabete and Kanha; the template's 0.1
tolerance is Excel's 10%. KSL-Westlands holds no vehicles and is left out.

``load`` creates each record that is missing, by its name, and never changes one that exists, so
corrections made by hand on the main site survive a second run (spec 006 D-4).
"""

import frappe

MAIN_SITE = "fleet_management.localhost"

KABETE = "Kabete"
KANHA = "Kanha"
LOCATIONS = (
	(KABETE, "Kabete company vehicles"),
	(KANHA, "Kanha company vehicles"),
)

FUEL_TYPES = ("Diesel", "Petrol")

VEHICLE_MODELS = (
	# make, model, tank litres, engine cc
	("Isuzu", "NMR", 75, 2999),
	("Isuzu", "ELF-PB-NPR81AN", 75, 4770),
	("Lexus", "LX600-3BA-VJA310W", 80, 3445),
	("Toyota", "Axio", 42, 1490),
	("Toyota", "Fortuner", 80, 2986),
	("Toyota", "Hilux", 80, 2393),
	("Toyota", "Rav4", 60, 1987),
	("Toyota", "Starlet", 38, 1373),
	("Toyota", "Urban Cruiser", 48, 1462),
	("Toyota", "ZSA42R", 60, 1987),
	("Toyota", "Avensis", 60, 1998),
	("Toyota", "Land Cruiser", 96, 4164),  # listed by the owner; no vehicle uses it
	("GEN", "45KVA/36KW", 100, None),  # 100 L set by the owner, to be confirmed
	("Locatel", "KZL284", 100, None),  # mobile crane; 100 L set by the owner, to be confirmed
)

PHYLLIS = "Phyllis"  # Fleet User: enters orders, company representative for Kabete and Kanha
VISHAL = "Vishal"  # Fleet Approver: signs off Phyllis's red orders
HOLDERS = (
	"Mrs. Danbhai Kanji",
	"Dennis Kamau",
	"Amrat Deepak Patel",
	"Deepak Kanji Patel",
	"Joseph Wakhungu",
	"Harish Kumar",
	"Vinu Pindoria",
	"Mukesh Singh",
	"Sanjeev Modi",
	"Mr. Kanji K. Patel",
)
PEOPLE = (PHYLLIS, VISHAL, *HOLDERS)
REPRESENTATIVE = {KABETE: PHYLLIS, KANHA: PHYLLIS}

ECOFLAME = "Ecoflame Limited"
STATIONS = (
	# name, operational location, also serves
	(ECOFLAME, KABETE, (KANHA,)),
)
STATION_ADDRESSES = {
	# station: P.O. Box, postal code, town, email
	ECOFLAME: ("P.O Box 818", "00606", "Nairobi", "ecoflamelimited@gmail.com"),
}

HELD_FROM = "2026-09-01"
TOLERANCE_PERCENT = 10
ASSETS = (
	# identifier, type, fuel, vehicle model, target km/L, holder, company
	("KAY222A", "Vehicle", "Petrol", "Toyota - Avensis", 8, "Mrs. Danbhai Kanji", KABETE),
	("KBD159W", "Vehicle", "Petrol", "Toyota - Fortuner", 6, "Dennis Kamau", KANHA),
	("KBR136G", "Vehicle", "Diesel", "Isuzu - ELF-PB-NPR81AN", 6, "Dennis Kamau", KANHA),
	("KBX093J", "Vehicle", "Petrol", "Toyota - ZSA42R", 7, "Amrat Deepak Patel", KABETE),
	("KCL225R", "Vehicle", "Petrol", "Toyota - Rav4", 7, "Deepak Kanji Patel", KABETE),
	("KCL966X", "Vehicle", "Petrol", "Toyota - Axio", 10, "Joseph Wakhungu", KANHA),
	("KCV927J", "Vehicle", "Petrol", "Toyota - Axio", 10, "Dennis Kamau", KANHA),
	("KDD516Z", "Vehicle", "Diesel", "Toyota - Hilux", 7, "Harish Kumar", KANHA),
	("KDE169V", "Vehicle", "Petrol", "Toyota - Starlet", 10, "Vinu Pindoria", KANHA),
	("KDE189V", "Vehicle", "Petrol", "Toyota - Starlet", 10, "Mukesh Singh", KANHA),
	("KDG173X", "Vehicle", "Petrol", "Toyota - Urban Cruiser", 10, "Sanjeev Modi", KANHA),
	("KDK039L", "Vehicle", "Diesel", "Isuzu - NMR", 6, "Dennis Kamau", KANHA),
	("KDQ111J", "Vehicle", "Petrol", "Lexus - LX600-3BA-VJA310W", 7, "Mr. Kanji K. Patel", KABETE),
	# The target is required by the form but unused for a generator (spec 006 D-11).
	("KLW-Generator", "Generator", "Diesel", "GEN - 45KVA/36KW", 1, PHYLLIS, KABETE),
	# 2 km/L is an estimate (no official record found), to be corrected from its fuelling history.
	("MobileCrane", "Vehicle", "Diesel", "Locatel - KZL284", 2, PHYLLIS, KANHA),
)


def load(people_users=None):
	"""Create every listed record that is missing and return how many of each were created.

	``people_users`` maps a Fleet Person name to the login it is linked to when it is created.
	"""
	_assert_allowed_site()
	people_users = people_users or {}
	created = {}

	def add(doctype, name, **values):
		if frappe.db.exists(doctype, name):
			return False
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
		created[doctype] = created.get(doctype, 0) + 1
		return True

	for name, description in LOCATIONS:
		add("Fleet Location", name, location_name=name, description=description, active=1)
	for name in FUEL_TYPES:
		add("Fuel Type", name, fuel_type_name=name, active=1)
	for make, model, tank, engine_cc in VEHICLE_MODELS:
		add(
			"Vehicle Model",
			f"{make} - {model}",
			make=make,
			model=model,
			tank_capacity_litres=tank,
			engine_capacity_cc=engine_cc,
		)
	for name in PEOPLE:
		add("Fleet Person", name, person_name=name, user=people_users.get(name), active=1)
	for name, location, also_serves in STATIONS:
		add(
			"Fuel Station",
			name,
			station_name=name,
			operational_location=location,
			also_serves=[{"fleet_location": extra} for extra in also_serves],
			active=1,
			approved=1,
		)
	for station, (box, postal_code, town, email) in STATION_ADDRESSES.items():
		if not _has_address(station):
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": station,
					"address_type": "Postal",
					"address_line1": box,
					"pincode": postal_code,
					"city": town,
					"country": "Kenya",
					"email_id": email,
					"is_primary_address": 1,
					"links": [{"link_doctype": "Fuel Station", "link_name": station}],
				}
			).insert(ignore_permissions=True)
			created["Address"] = created.get("Address", 0) + 1
	for identifier, asset_type, fuel, model, target, holder, location in ASSETS:
		add(
			"Fleet Asset",
			identifier,
			asset_identifier=identifier,
			asset_type=asset_type,
			active=1,
			fuel_type=fuel,
			vehicle_model=model,
			target_km_per_litre=target,
			tolerance_percent=TOLERANCE_PERCENT,
			assignments=[
				{
					"custodian": holder,
					"assigned_location": location,
					"effective_from": HELD_FROM,
					"reason": "Fleet allocation",
				}
			],
		)
	return created


def _has_address(station):
	return bool(
		frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Address", "link_doctype": "Fuel Station", "link_name": station},
			limit=1,
		)
	)


def _assert_allowed_site():
	if frappe.local.site != MAIN_SITE and not frappe.conf.allow_tests:
		frappe.throw(f"The starting data may only be loaded on {MAIN_SITE} or a test site.")
