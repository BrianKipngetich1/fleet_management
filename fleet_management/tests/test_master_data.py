from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from fleet_management import master_data


class TestStartingDataIsTheListedFleet(IntegrationTestCase):
	"""Loading gives exactly the company's listed fleet, on an empty site or a seeded one."""

	def setUp(self):
		super().setUp()
		master_data.load()

	def test_master_lists_match_the_listed_fleet(self):
		"""006-master-data-import: Requirements 3.1, 3.2; Property 3. Every listed record exists with
		its listed values."""
		for name, _description in master_data.LOCATIONS:
			self.assertTrue(frappe.db.get_value("Fleet Location", name, "active"), name)
		for name in master_data.FUEL_TYPES:
			self.assertTrue(frappe.db.get_value("Fuel Type", name, "active"), name)
		for make, model, tank, engine_cc in master_data.VEHICLE_MODELS:
			values = frappe.db.get_value(
				"Vehicle Model",
				f"{make} - {model}",
				["tank_capacity_litres", "engine_capacity_cc"],
				as_dict=True,
			)
			self.assertEqual(
				(values.tank_capacity_litres, values.engine_capacity_cc or None), (tank, engine_cc)
			)
		for name in master_data.PEOPLE:
			self.assertTrue(frappe.db.get_value("Fleet Person", name, "active"), name)

		station = frappe.get_doc("Fuel Station", master_data.ECOFLAME)
		self.assertEqual(station.operational_location, master_data.KABETE)
		self.assertEqual([row.fleet_location for row in station.also_serves], [master_data.KANHA])
		self.assertTrue(station.active and station.approved)
		address = frappe.get_all(
			"Address",
			filters=[["Dynamic Link", "link_name", "=", master_data.ECOFLAME]],
			fields=["address_line1", "pincode", "city", "email_id"],
		)
		self.assertEqual(
			[(row.address_line1, row.pincode, row.city, row.email_id) for row in address],
			[master_data.STATION_ADDRESSES[master_data.ECOFLAME]],
		)

		for identifier, asset_type, fuel, model, target, holder, location in master_data.ASSETS:
			asset = frappe.get_doc("Fleet Asset", identifier)
			self.assertEqual(
				(asset.asset_type, asset.fuel_type, asset.vehicle_model, asset.target_km_per_litre),
				(asset_type, fuel, model, target),
				identifier,
			)
			self.assertEqual(asset.tolerance_percent, 10, identifier)
			self.assertTrue(asset.active, identifier)
			self.assertEqual(
				[
					(row.custodian, row.assigned_location, str(row.effective_from))
					for row in asset.assignments
				],
				[(holder, location, "2026-09-01")],
				identifier,
			)

	def test_the_owners_corrections_are_applied(self):
		"""006-master-data-import: Requirements 3.4; Property 3. No record carries the templates'
		mistakes."""
		self.assertEqual(len(master_data.ASSETS), 15)
		self.assertEqual(len(master_data.VEHICLE_MODELS), 14)
		for wrong in ("Lexas - LX600-3BA-VJA310W", "Toyota - Urban Crushar", "Isuzu - PB-NPR81AN"):
			self.assertFalse(frappe.db.exists("Vehicle Model", wrong), wrong)
		for not_a_person in ("KLW", "Athi_MV"):
			self.assertFalse(frappe.db.exists("Fleet Person", not_a_person), not_a_person)
		self.assertEqual(frappe.db.count("Fleet Person", {"person_name": "Dennis Kamau"}), 1)
		self.assertFalse(frappe.db.exists("Fleet Location", "KSL-Westlands"))
		self.assertEqual(
			frappe.db.get_value("Fleet Asset", "KBR136G", "vehicle_model"), "Isuzu - ELF-PB-NPR81AN"
		)
		self.assertEqual(frappe.db.get_value("Fleet Asset", "KLW-Generator", "asset_type"), "Generator")
		crane = frappe.get_doc("Fleet Asset", "MobileCrane")
		self.assertEqual((crane.asset_type, crane.target_km_per_litre), ("Vehicle", 2))
		self.assertEqual(
			[(row.custodian, row.assigned_location) for row in crane.assignments],
			[(master_data.PHYLLIS, master_data.KANHA)],
		)
		for model in ("GEN - 45KVA/36KW", "Locatel - KZL284"):
			self.assertEqual(frappe.db.get_value("Vehicle Model", model, "tank_capacity_litres"), 100, model)

	def test_loading_again_adds_nothing(self):
		"""006-master-data-import: Requirements 3.2, 3.3; Property 3. A second load is a no-op."""
		self.assertEqual(master_data.load(), {})


class TestStartingDataOnlyAdds(IntegrationTestCase):
	def test_hand_corrections_survive_and_missing_records_return(self):
		"""006-master-data-import: Requirements 3.3, 3.5; Property 4. Loading keeps a corrected
		vehicle as it is and recreates only what is missing."""
		master_data.load()
		self.addCleanup(master_data.load)
		self.addCleanup(
			frappe.db.set_value,
			"Fleet Asset",
			"KAY222A",
			{"tolerance_percent": 10, "target_km_per_litre": 8},
		)
		frappe.db.set_value("Fleet Asset", "KAY222A", {"tolerance_percent": 12, "target_km_per_litre": 9})
		frappe.db.set_value("Vehicle Model", "Toyota - Avensis", "tank_capacity_litres", 61)
		self.addCleanup(frappe.db.set_value, "Vehicle Model", "Toyota - Avensis", "tank_capacity_litres", 60)
		# The Land Cruiser model is listed but no vehicle uses it, so it can be removed and come back.
		frappe.delete_doc("Vehicle Model", "Toyota - Land Cruiser", ignore_permissions=True, force=True)

		self.assertEqual(master_data.load(), {"Vehicle Model": 1})

		asset = frappe.db.get_value(
			"Fleet Asset", "KAY222A", ["tolerance_percent", "target_km_per_litre"], as_dict=True
		)
		self.assertEqual((asset.tolerance_percent, asset.target_km_per_litre), (12, 9))
		self.assertEqual(frappe.db.get_value("Vehicle Model", "Toyota - Avensis", "tank_capacity_litres"), 61)
		self.assertTrue(frappe.db.exists("Vehicle Model", "Toyota - Land Cruiser"))

	def test_loading_is_refused_on_any_other_site(self):
		"""006-master-data-import: Requirements 3.3. Only the main site or a test site loads."""
		with patch.object(frappe.local, "site", "elsewhere.localhost"):
			with patch.dict(frappe.local.conf, {"allow_tests": False}):
				with self.assertRaises(frappe.ValidationError):
					master_data.load()


class TestMainSiteAccess(IntegrationTestCase):
	"""Linking people to their logins and giving those logins both companies only adds."""

	def setUp(self):
		super().setUp()
		master_data.load()

	def _user(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"s006-access-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "S006",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.db.delete, "User Permission", {"user": user.name})
		return user.name

	def _person(self, user=None):
		person = frappe.get_doc(
			{
				"doctype": "Fleet Person",
				"person_name": f"S006 Access {frappe.generate_hash(length=8)}",
				"user": user,
				"active": 1,
			}
		).insert(ignore_permissions=True)
		return person.name

	def _companies(self, user):
		return set(
			frappe.get_all(
				"User Permission",
				filters={"user": user, "allow": "Fleet Location", "apply_to_all_doctypes": 1},
				pluck="for_value",
			)
		)

	def test_missing_links_and_permissions_are_added_once(self):
		"""006-master-data-import: Requirements 3.3, 5.1, 5.2; Property 4. A person without a login
		is linked, both logins get Kabete and Kanha, and a second call adds nothing."""
		first_user, second_user = self._user(), self._user()
		unlinked = self._person()
		people_users = {unlinked: first_user, self._person(): second_user}
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": second_user,
				"allow": "Fleet Location",
				"for_value": master_data.KABETE,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

		added = master_data.grant_access(people_users)

		self.assertEqual(added["User Permission"], 3)
		self.assertIn(unlinked, added["Fleet Person linked"])
		self.assertEqual(frappe.db.get_value("Fleet Person", unlinked, "user"), first_user)
		for user in (first_user, second_user):
			self.assertEqual(self._companies(user), {master_data.KABETE, master_data.KANHA}, user)
		self.assertEqual(master_data.grant_access(people_users), {})
		self.assertEqual(frappe.db.count("User Permission", {"user": second_user}), 2)

	def test_an_existing_link_is_not_overwritten(self):
		"""006-master-data-import: Requirements 3.3, 5.1, 5.2; Property 4. A person already linked
		to another login keeps that link."""
		kept_user, other_user = self._user(), self._user()
		person = self._person(kept_user)

		added = master_data.grant_access({person: other_user})

		self.assertNotIn("Fleet Person linked", added)
		self.assertEqual(frappe.db.get_value("Fleet Person", person, "user"), kept_user)
		self.assertEqual(self._companies(other_user), {master_data.KABETE, master_data.KANHA})

	def test_a_missing_user_is_skipped_and_named(self):
		"""006-master-data-import: Requirements 3.3, 5.1, 5.2; Property 4. A login that does not exist
		is named and nothing is added for it."""
		missing = f"s006-missing-{frappe.generate_hash(length=8)}@example.com"
		person = self._person()

		self.assertEqual(master_data.grant_access({person: missing}), {"Skipped users": [missing]})
		self.assertFalse(frappe.db.get_value("Fleet Person", person, "user"))
		self.assertFalse(frappe.db.exists("User Permission", {"user": missing}))

	def test_loading_the_main_site_is_refused_on_the_test_site(self):
		"""006-master-data-import: Requirements 3.3, 5.1, 5.2; Property 4. ``load_main`` runs only on
		the main site, even where tests are allowed."""
		self.assertNotEqual(frappe.local.site, master_data.MAIN_SITE)
		with self.assertRaises(frappe.ValidationError):
			master_data.load_main()
