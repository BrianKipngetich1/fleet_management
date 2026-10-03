import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from fleet_management.tests.utils import attach_request_photos, decide, send_up


class TestFuelingDiscrepancy(IntegrationTestCase):
	"""Integration checks for spec 008-overseer-reports Requirements 3.3 and 4.1."""

	def setUp(self):
		super().setUp()
		suffix = frappe.generate_hash(length=8)
		self.locations = {
			"Nairobi": self._insert("Fleet Location", location_name=f"AC08 Nairobi {suffix}"),
			"Mombasa": self._insert("Fleet Location", location_name=f"AC08 Mombasa {suffix}"),
		}
		self.fuel_type = self._insert("Fuel Type", fuel_type_name=f"AC08 Diesel {suffix}")
		self.vehicle_model = self._insert(
			"Vehicle Model",
			make=f"AC08 Make {suffix}",
			model=f"AC08 Model {suffix}",
			tank_capacity_litres=60,
		)
		self.person = self._insert("Fleet Person", person_name=f"AC08 Person {suffix}")
		self.users = {}
		self.transactions = {}
		for name, location in self.locations.items():
			station = self._insert(
				"Fuel Station",
				station_name=f"AC08 {name} Station {suffix}",
				operational_location=location.name,
				active=1,
				approved=1,
			)
			asset = self._insert(
				"Fleet Asset",
				asset_identifier=f"AC08 {name} Asset {suffix}",
				asset_type="Vehicle",
				fuel_type=self.fuel_type.name,
				vehicle_model=self.vehicle_model.name,
				target_km_per_litre=10,
				assignments=[
					{
						"doctype": "Asset Assignment",
						"custodian": self.person.name,
						"assigned_location": location.name,
						"effective_from": "2026-01-01",
					}
				],
			)
			requester = self._user("Fleet User", location.name)
			approver = self._user("Fleet Approver", location.name)
			self.users[name] = requester
			order = self._make_approved_order(location, station, asset, requester, approver)
			with self.set_user(requester):
				self.transactions[name] = frappe.get_doc(
					{"doctype": "Fueling Transaction", "fuel_order": order.name}
				).insert()

	def _insert(self, doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)

	def _user(self, role, location):
		user = self._insert(
			"User",
			email=f"ac08-{frappe.generate_hash(length=8)}@example.com",
			first_name="AC08",
			send_welcome_email=0,
			roles=[{"doctype": "Has Role", "role": role}],
		)
		self._insert("User Permission", user=user.name, allow="Fleet Location", for_value=location)
		frappe.clear_cache(user=user.name)
		return user.name

	def _make_approved_order(self, location, station, asset, requester, approver):
		with self.set_user(requester):
			order = frappe.get_doc(
				{
					"doctype": "Fuel Order",
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
			).insert()
			order = attach_request_photos(order)
			if order.signal != "Green":
				order = send_up(order)
				decision_maker = approver
			else:
				decision_maker = requester

		with self.set_user(decision_maker):
			return decide(order, "Approve")

	def _insert_discrepancy(self, transaction, **values):
		return frappe.get_doc(
			{
				"doctype": "Fueling Discrepancy",
				"fueling_transaction": transaction.name,
				"discrepancy_type": "Invoice mismatch",
				"details": "The invoice litres differ from the recorded delivery.",
				"reason": "The attendant reported a difference during reconciliation.",
				**values,
			}
		).insert()

	def test_recorder_and_date_are_server_set_and_source_transaction_is_unchanged(self):
		transaction = self.transactions["Nairobi"]
		before = frappe.db.get_value(
			"Fueling Transaction", transaction.name, ["docstatus", "modified"], as_dict=True
		)
		with self.set_user(self.users["Nairobi"]):
			discrepancy = self._insert_discrepancy(
				transaction,
				recorded_by="Administrator",
				recorded_on="2000-01-01 00:00:00",
			)

		self.assertEqual(discrepancy.recorded_by, self.users["Nairobi"])
		self.assertNotEqual(str(discrepancy.recorded_on), "2000-01-01 00:00:00")
		self.assertLessEqual(str(discrepancy.recorded_on), str(now_datetime()))
		self.assertEqual(
			frappe.db.get_value("Fueling Transaction", transaction.name, ["docstatus", "modified"], as_dict=True),
			before,
		)

	def test_creation_and_list_access_follow_transaction_location(self):
		with self.set_user(self.users["Nairobi"]):
			nairobi = self._insert_discrepancy(self.transactions["Nairobi"])
		with self.set_user(self.users["Mombasa"]):
			mombasa = self._insert_discrepancy(self.transactions["Mombasa"])

		with self.set_user(self.users["Nairobi"]):
			visible = frappe.get_list(
				"Fueling Discrepancy",
				filters={"name": ["in", [nairobi.name, mombasa.name]]},
				fields=["name"],
			)
			self.assertEqual({row.name for row in visible}, {nairobi.name})
			self.assertTrue(frappe.has_permission("Fueling Discrepancy", "read", doc=nairobi))
			self.assertFalse(frappe.has_permission("Fueling Discrepancy", "read", doc=mombasa))
			with self.assertRaises(frappe.PermissionError):
				self._insert_discrepancy(self.transactions["Mombasa"])
