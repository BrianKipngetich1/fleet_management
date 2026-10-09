import csv
import io

import frappe
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.tests import IntegrationTestCase

MASTER_DOCTYPES = (
	"Fleet Location",
	"Fuel Type",
	"Vehicle Model",
	"Fleet Person",
	"Fuel Station",
	"Fleet Asset",
)
WORKFLOW_DOCTYPES = ("Fuel Order", "Fueling Transaction")
FLEET_ROLES = ("Fleet Admin", "Fleet Approver", "Fleet User")


def new_import(doctype, file_url=None):
	return frappe.get_doc(
		{
			"doctype": "Data Import",
			"reference_doctype": doctype,
			"import_type": "Insert New Records",
			"import_file": file_url,
		}
	)


class TestMasterDataImportScope(IntegrationTestCase):
	def test_import_is_open_for_master_lists_only(self):
		"""006-master-data-import: Requirements 1.1, 2.2; Property 1. Import opens for the six master
		lists and stays refused for orders and fuellings."""
		for doctype in MASTER_DOCTYPES:
			with self.subTest(doctype=doctype):
				new_import(doctype).validate_doctype()
		for doctype in WORKFLOW_DOCTYPES:
			with self.subTest(doctype=doctype):
				with self.assertRaisesRegex(frappe.ValidationError, "Data Import is not allowed"):
					new_import(doctype).validate_doctype()

	def test_fleet_roles_cannot_open_the_import_tool(self):
		"""006-master-data-import: Requirements 2.1. Only a system administrator imports."""
		for role in FLEET_ROLES:
			with self.subTest(role=role):
				user = frappe.get_doc(
					{
						"doctype": "User",
						"email": f"import.{frappe.scrub(role)}.{frappe.generate_hash(length=6)}@example.com",
						"first_name": role,
						"send_welcome_email": 0,
						"roles": [{"role": role}],
					}
				).insert(ignore_permissions=True)
				self.assertFalse(frappe.has_permission("Data Import", "create", user=user.name))
				self.assertFalse(frappe.has_permission("Data Import", "read", user=user.name))


class TestFleetAssetImport(IntegrationTestCase):
	"""The import commits row by row, so every record made here is removed explicitly."""

	def setUp(self):
		suffix = frappe.generate_hash(length=6)
		self.created = []
		self.location = self._make({"doctype": "Fleet Location", "location_name": f"Import Depot {suffix}"})
		self.fuel_type = self._make({"doctype": "Fuel Type", "fuel_type_name": f"Import Diesel {suffix}"})
		self.model = self._make(
			{"doctype": "Vehicle Model", "make": "Import", "model": suffix, "tank_capacity_litres": 80}
		)
		self.first_holder = self._make(
			{"doctype": "Fleet Person", "person_name": f"Import Holder A {suffix}"}
		)
		self.second_holder = self._make(
			{"doctype": "Fleet Person", "person_name": f"Import Holder B {suffix}"}
		)
		self.good = f"KIM {suffix} A"
		self.bad = f"KIM {suffix} B"
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()
		for doctype in ("Data Import Log", "Data Import"):
			for name in frappe.get_all(doctype, filters={"name": ("in", self._imports())}, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		for name in (self.good, self.bad):
			if frappe.db.exists("Fleet Asset", name):
				frappe.delete_doc("Fleet Asset", name, force=True, ignore_permissions=True)
		for doctype, name in reversed(self.created):
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _make(self, values):
		doc = frappe.get_doc(values).insert(ignore_permissions=True)
		self.created.append((doc.doctype, doc.name))
		return doc

	def _imports(self):
		return [name for doctype, name in self.created if doctype == "Data Import"] or [""]

	def _template_header(self):
		# The same columns the Download Template dialog offers for a vehicle and its holders.
		exporter = Exporter(
			"Fleet Asset",
			export_fields={
				"Fleet Asset": [
					"asset_identifier",
					"asset_type",
					"active",
					"fuel_type",
					"vehicle_model",
					"target_km_per_litre",
				],
				"assignments": [
					"custodian",
					"assigned_location",
					"effective_from",
					"effective_until",
					"reason",
				],
			},
			export_data=False,
			file_type="CSV",
		)
		return exporter.get_csv_array()[0]

	def test_filled_template_imports_holders_and_reports_refused_rows(self):
		"""006-master-data-import: Requirements 1.2, 1.3; Property 2. A filled template creates the
		vehicle with its holder history and reports the row that breaks a rule."""
		header = self._template_header()
		column = {label: index for index, label in enumerate(header)}

		def row(**values):
			cells = [""] * len(header)
			for label, value in values.items():
				cells[column[label]] = value
			return cells

		loc = self.location.name
		rows = [
			row(
				**{
					"Asset Identifier": self.good,
					"Asset Type": "Vehicle",
					"Active": 1,
					"Fuel Type": self.fuel_type.name,
					"Vehicle Model": self.model.name,
					"Target (km/L)": 10,
					"Custodian (Assignment History)": self.first_holder.name,
					"Assigned Location (Assignment History)": loc,
					"Effective From (Assignment History)": "15/01/2026",
					"Effective Until (Assignment History)": "30/06/2026",
					"Reason (Assignment History)": "First holder",
				}
			),
			row(
				**{
					"Custodian (Assignment History)": self.second_holder.name,
					"Assigned Location (Assignment History)": loc,
					"Effective From (Assignment History)": "01/07/2026",
					"Reason (Assignment History)": "Handed over",
				}
			),
			# A vehicle with no model breaks the same rule as when typed by hand.
			row(
				**{
					"Asset Identifier": self.bad,
					"Asset Type": "Vehicle",
					"Active": 1,
					"Fuel Type": self.fuel_type.name,
					"Target (km/L)": 10,
					"Custodian (Assignment History)": self.first_holder.name,
					"Assigned Location (Assignment History)": loc,
					"Effective From (Assignment History)": "15/01/2026",
				}
			),
		]
		content = io.StringIO()
		csv.writer(content).writerows([header, *rows])
		file = self._make(
			{
				"doctype": "File",
				"file_name": f"{self.good}.csv",
				"content": content.getvalue(),
				"is_private": 1,
			}
		)
		data_import = self._make(new_import("Fleet Asset", file.file_url).as_dict())
		frappe.db.commit()

		data_import.start_import()

		asset = frappe.get_doc("Fleet Asset", self.good)
		self.assertEqual(
			[
				(a.custodian, str(a.effective_from), a.effective_until and str(a.effective_until))
				for a in asset.assignments
			],
			[
				(self.first_holder.name, "2026-01-15", "2026-06-30"),
				(self.second_holder.name, "2026-07-01", None),
			],
		)
		self.assertFalse(frappe.db.exists("Fleet Asset", self.bad))
		logs = frappe.get_all(
			"Data Import Log",
			filters={"data_import": data_import.name, "success": 0},
			fields=["row_indexes", "messages"],
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(frappe.parse_json(logs[0].row_indexes), [4])
		self.assertIn("Vehicle Model", logs[0].messages)
