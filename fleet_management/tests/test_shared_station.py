import frappe
from frappe.tests import IntegrationTestCase

from fleet_management.fleet_management.doctype.fuel_order.fuel_order import get_request_facts
from fleet_management.fleet_management.doctype.fuel_station.fuel_station import station_query
from fleet_management.permissions import has_permission


class TestSharedStation(IntegrationTestCase):
	"""A station serving two companies, as Ecoflame serves Kabete and Kanha (spec 006 D-7)."""

	def setUp(self):
		super().setUp()
		suffix = frappe.generate_hash(length=8)
		self.kabete = self._insert("Fleet Location", location_name=f"S006 Kabete {suffix}")
		self.kanha = self._insert("Fleet Location", location_name=f"S006 Kanha {suffix}")
		self.elsewhere = self._insert("Fleet Location", location_name=f"S006 Elsewhere {suffix}")
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"S006 Petrol {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model", make=f"S006 Make {suffix}", model=f"S006 Model {suffix}", tank_capacity_litres=60
		)
		self.person = self._insert("Fleet Person", person_name=f"S006 Holder {suffix}")
		self.shared = self._insert(
			"Fuel Station",
			station_name=f"S006 Ecoflame {suffix}",
			operational_location=self.kabete.name,
			also_serves=[{"fleet_location": self.kanha.name}],
		)
		self.kabete_only = self._insert(
			"Fuel Station",
			station_name=f"S006 Kabete Only {suffix}",
			operational_location=self.kabete.name,
		)
		self.kabete_asset = self._insert_asset(f"S006 KAB {suffix}", self.kabete.name)
		self.kanha_asset = self._insert_asset(f"S006 KAN {suffix}", self.kanha.name)
		self.kabete_order = self._insert_order(self.kabete, self.shared, self.kabete_asset)
		self.kanha_order = self._insert_order(self.kanha, self.shared, self.kanha_asset)

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _insert_asset(self, identifier, location):
		return self._insert(
			"Fleet Asset",
			asset_identifier=identifier,
			asset_type="Vehicle",
			fuel_type=self.fuel_type.name,
			vehicle_model=self.vehicle_model.name,
			target_km_per_litre=10,
			assignments=[
				{
					"doctype": "Asset Assignment",
					"custodian": self.person.name,
					"assigned_location": location,
					"effective_from": "2026-01-01",
				}
			],
		)

	def _insert_order(self, location, station, asset):
		return frappe.get_doc(
			{
				"doctype": "Fuel Order",
				"request_datetime": "2026-01-01 10:00:00",
				"actual_requester": self.person.name,
				"driver": self.person.name,
				"custodian": self.person.name,
				"company_representative": self.person.name,
				"asset": asset.name,
				"operational_location": location.name,
				"planned_station": station.name,
				"request_meter_reading": 1000,
				"request_gauge_percent": 40,
			}
		).insert(ignore_permissions=True)

	def _user(self, role, *locations):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"s006-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "S006",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": role}],
			}
		).insert(ignore_permissions=True)
		for location in locations:
			self._insert("User Permission", user=user.name, allow="Fleet Location", for_value=location.name)
		frappe.clear_cache(user=user.name)
		return user.name

	def _search(self, location, txt=""):
		rows = station_query("Fuel Station", txt, "name", 0, 20, {"operational_location": location.name})
		return {row[0] for row in rows}

	def test_order_accepts_a_station_serving_its_location(self):
		"""006-master-data-import: Requirements 4.1, 2.4; Property 5. A Kanha order may use the
		shared station; a station serving only Kabete is still refused."""
		self.assertEqual(self.kanha_order.planned_station, self.shared.name)
		self.assertEqual(self.kabete_order.planned_station, self.shared.name)
		with self.assertRaisesRegex(
			frappe.ValidationError, r"Planned station must serve the operational location\."
		):
			self._insert_order(self.kanha, self.kabete_only, self.kanha_asset)
		with self.assertRaisesRegex(
			frappe.ValidationError, r"Planned station must serve the operational location\."
		):
			self._insert_order(self.elsewhere, self.shared, self.kanha_asset)

	def test_suggestion_and_search_follow_the_served_locations(self):
		"""006-master-data-import: Requirements 4.1, 4.2; Property 5. The vehicle's suggestion and the
		order form's station search list every station serving the location, and no other."""
		self.assertEqual(get_request_facts(self.kanha_asset.name)["suggested_station"], self.shared.name)
		# Two stations serve Kabete, so none is suggested.
		self.assertIsNone(get_request_facts(self.kabete_asset.name)["suggested_station"])

		self.assertEqual(self._search(self.kanha), {self.shared.name})
		self.assertEqual(self._search(self.kabete), {self.shared.name, self.kabete_only.name})
		self.assertEqual(self._search(self.kabete, "Only"), {self.kabete_only.name})
		self.assertEqual(self._search(self.elsewhere), set())

		self.shared.append("also_serves", {"fleet_location": self.elsewhere.name})
		self.shared.save(ignore_permissions=True)
		self.assertEqual(self._search(self.elsewhere), {self.shared.name})

	def test_station_keeps_each_extra_location_once(self):
		"""006-master-data-import: Requirements 4.2; Property 5. Repeats and the station's own
		location are dropped from Also Serves on save."""
		self.shared.append("also_serves", {"fleet_location": self.kanha.name})
		self.shared.append("also_serves", {"fleet_location": self.kabete.name})
		self.shared.save(ignore_permissions=True)
		self.assertEqual([row.fleet_location for row in self.shared.also_serves], [self.kanha.name])

	def test_kanha_only_user_sees_the_shared_station_but_not_kabete(self):
		"""006-master-data-import: Requirements 5.3; Property 6. The shared station is visible to
		either company; Kabete's vehicles and orders stay hidden from a Kanha-only approver."""
		kanha_approver = self._user("Fleet Approver", self.kanha)
		with self.set_user(kanha_approver):
			stations = set(frappe.get_list("Fuel Station", pluck="name"))
			self.assertIn(self.shared.name, stations)
			self.assertNotIn(self.kabete_only.name, stations)
			self.assertTrue(frappe.has_permission("Fuel Station", "read", self.shared))
			self.assertTrue(frappe.has_permission("Fuel Station", "print", self.shared))
			self.assertFalse(frappe.has_permission("Fuel Station", "read", self.kabete_only))
			self.assertEqual(self._search(self.kanha), {self.shared.name})

			orders = set(frappe.get_list("Fuel Order", pluck="name"))
			self.assertIn(self.kanha_order.name, orders)
			self.assertNotIn(self.kabete_order.name, orders)
			self.assertTrue(frappe.has_permission("Fuel Order", "read", self.kanha_order))
			self.assertFalse(frappe.has_permission("Fuel Order", "read", self.kabete_order))

			assets = set(frappe.get_list("Fleet Asset", pluck="name"))
			self.assertIn(self.kanha_asset.name, assets)
			self.assertNotIn(self.kabete_asset.name, assets)
			self.assertFalse(frappe.has_permission("Fleet Asset", "read", self.kabete_asset))

		# A record without its rows (as some framework paths pass it) is read from the station.
		partial = frappe._dict(doctype="Fuel Station", name=self.shared.name)
		self.assertTrue(has_permission(partial, ptype="read", user=kanha_approver))

		kabete_user = self._user("Fleet User", self.kabete)
		with self.set_user(kabete_user):
			stations = set(frappe.get_list("Fuel Station", pluck="name"))
			self.assertIn(self.shared.name, stations)
			self.assertIn(self.kabete_only.name, stations)
			self.assertTrue(frappe.has_permission("Fuel Station", "read", self.shared))
