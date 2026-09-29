import tempfile
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import click
import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from fleet_management import sample_data
from fleet_management.commands import DB_NAME, DB_USER, TEST_SITE, _read_credentials

INVENTORY = f"""# Logins — private, never committed (mode 0600)

| Site | Username | Role | Password |
|---|---|---|---|
| fleet_management.localhost | fleet.user@example.com | Fleet User | mainOnlyValue1 |
| fleet_management.localhost | Administrator | Administrator | mainAdminValue |
| {TEST_SITE} | Administrator | Administrator | adminValue |
| {TEST_SITE} | philip.test@example.com | Fleet User | testPhilipValue |
| {TEST_SITE} | vikas.test@example.com | Fleet Approver | testVikasValue |

## Database

| Site | Database | Database user | Password |
|---|---|---|---|
| fleet_management.localhost | fleet_mgmt_dev | fleet_mgmt_dev | mainDatabaseValue |
| {TEST_SITE} | {DB_NAME} | {DB_USER} | testDatabaseValue |
"""


class TestTestSiteCredentials(UnitTestCase):
	def _read(self, text):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory, "CREDENTIALS.md")
			path.write_text(text)
			return _read_credentials(path)

	def _refused(self, text, *names):
		with self.assertRaises(click.ClickException) as raised:
			self._read(text)
		message = str(raised.exception.message)
		for name in names:
			self.assertIn(name, message)
		for password in ("adminValue", "testDatabaseValue", "testPhilipValue", "testVikasValue"):
			self.assertNotIn(password, message)

	def test_returns_only_test_site_logins(self):
		secrets = self._read(INVENTORY)
		self.assertEqual(
			secrets["users"],
			{"philip.test@example.com": "testPhilipValue", "vikas.test@example.com": "testVikasValue"},
		)

	def test_main_site_rows_are_ignored(self):
		secrets = self._read(INVENTORY)
		self.assertNotIn("fleet.user@example.com", secrets["users"])
		self.assertNotEqual(secrets["admin_password"], "mainAdminValue")
		self.assertNotEqual(secrets["db_password"], "mainDatabaseValue")

	def test_administrator_row_gives_the_admin_password(self):
		secrets = self._read(INVENTORY)
		self.assertEqual(secrets["admin_password"], "adminValue")
		self.assertNotIn("Administrator", secrets["users"])

	def test_database_table_gives_the_db_password(self):
		self.assertEqual(self._read(INVENTORY)["db_password"], "testDatabaseValue")

	def test_missing_administrator_password_is_refused(self):
		text = INVENTORY.replace(f"| {TEST_SITE} | Administrator | Administrator | adminValue |\n", "")
		self._refused(text, "Administrator")

	def test_missing_database_password_is_refused(self):
		text = INVENTORY.replace(f"| {TEST_SITE} | {DB_NAME} | {DB_USER} | testDatabaseValue |\n", "")
		self._refused(text, f"{DB_USER} database password")

	def test_missing_test_logins_are_refused(self):
		text = "\n".join(line for line in INVENTORY.splitlines() if ".test@" not in line)
		self._refused(text, "test-site logins")

	def test_a_test_login_without_the_word_test_is_refused(self):
		self._refused(INVENTORY.replace("testVikasValue", "vikasValue"), "vikas.test@example.com")


class TestSampleHistory(UnitTestCase):
	"""Keep the fixed history realistic when someone edits it."""

	assets: ClassVar[dict] = {row[0]: row for row in sample_data.ASSETS}

	def test_every_history_asset_is_defined_with_a_requester(self):
		for asset in sample_data.HISTORY:
			self.assertIn(asset, self.assets)
			self.assertIn(asset, sample_data.REQUESTERS)

	def test_vehicle_intervals_stay_within_ten_percent_of_target(self):
		for asset, rows in sample_data.HISTORY.items():
			_registration, asset_type, _active, _fuel, _model, target, _assignments = self.assets[asset]
			if asset_type != "Vehicle":
				continue
			previous_full, litres = None, 0.0
			for _days, odometer, gauge, invoice_litres, full, _station in rows:
				self.assertTrue(0 <= gauge <= 100, asset)
				litres += invoice_litres
				if not full:
					continue
				if previous_full is not None:
					km_per_litre = (odometer - previous_full) / litres
					self.assertAlmostEqual(km_per_litre, target, delta=target * 0.1, msg=asset)
				previous_full, litres = odometer, 0.0

	def test_generator_rows_have_rising_hours_and_stay_within_the_maximum(self):
		for asset, rows in sample_data.HISTORY.items():
			if self.assets[asset][1] != "Generator":
				continue
			hours = [row[1] for row in rows]
			self.assertEqual(hours, sorted(hours), asset)
			for _days, _hours, gauge, invoice_litres, full, _station in rows:
				self.assertIsNone(gauge)
				self.assertFalse(full)
				self.assertLessEqual(invoice_litres, sample_data.GENERATOR_MAX_LITRES[asset])

	def test_days_ago_run_oldest_first(self):
		for asset, rows in sample_data.HISTORY.items():
			days = [row[0] for row in rows]
			self.assertEqual(days, sorted(days, reverse=True), asset)


class TestSampleDataGuards(IntegrationTestCase):
	def test_loading_is_refused_on_any_other_site(self):
		with patch.object(frappe.local, "site", "fleet_management.localhost"):
			with self.assertRaises(frappe.ValidationError):
				sample_data.reset()
			with self.assertRaises(frappe.ValidationError):
				sample_data.seed()

	def test_seeding_over_existing_fleet_data_is_refused(self):
		self.addCleanup(frappe.set_user, frappe.session.user)
		if not frappe.db.count("Fleet Asset"):
			fuel_type = frappe.get_doc(
				{"doctype": "Fuel Type", "fuel_type_name": f"Guard {frappe.generate_hash(length=6)}"}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Fleet Asset",
					"asset_identifier": f"Guard Generator {frappe.generate_hash(length=6)}",
					"asset_type": "Generator",
					"fuel_type": fuel_type.name,
					"target_km_per_litre": 1,
				}
			).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			sample_data.seed()
