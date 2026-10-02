import csv
from collections import defaultdict
from io import StringIO

import frappe
from frappe.desk.query_report import _export_query, run
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import flt, getdate

from fleet_management.sample_data import AMINA, FLEET_ADMIN, PHILIP, VIKAS

from fleet_management.fleet_management.report.fueling_summary.fueling_summary import (
	LOCATION_EXPRESSION,
	_build_report_rows,
	_get_date_range,
)


class TestFuelingSummary(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirements 1.2, 1.3, and 1.4."""

	def test_rejects_a_reversed_date_range(self):
		with self.assertRaisesRegex(frappe.ValidationError, "From Date cannot be later than To Date"):
			_get_date_range(frappe._dict(from_date="2026-10-02", to_date="2026-10-01"))

	def test_month_rows_keep_years_separate_and_mark_empty_amounts_unavailable(self):
		data, chart = _build_report_rows(
			[
				{
					"name": "FT-2025-0001",
					"location": "Nairobi",
					"asset": "VH-1",
					"fuel_type": "Diesel",
					"station": "Station 1",
					"fueling_datetime": "2025-12-31 23:00:00",
					"delivered_litres": 20,
					"invoice_amount": 4000,
					"printed_unit_price": 200,
				},
				{
					"name": "FT-2025-0002",
					"location": "Mombasa",
					"asset": "VH-2",
					"fuel_type": "Diesel",
					"station": "Station 2",
					"fueling_datetime": "2025-12-31 23:30:00",
					"delivered_litres": 10,
					"invoice_amount": 0,
					"printed_unit_price": 0,
				},
				{
					"name": "FT-2026-0001",
					"location": "Mombasa",
					"asset": "VH-2",
					"fuel_type": "Diesel",
					"station": "Station 2",
					"fueling_datetime": "2026-01-01 01:00:00",
					"delivered_litres": 10,
					"invoice_amount": 0,
					"printed_unit_price": 0,
				},
			]
		)

		monthly = [row for row in data if row["row_type"] == "Monthly total"]
		self.assertEqual([row["month"] for row in monthly], ["2025-12", "2026-01"])
		self.assertEqual(monthly[0]["delivered_litres"], 30)
		self.assertEqual(monthly[0]["transaction_count"], 2)
		self.assertEqual(monthly[0]["recorded_spend"], 4000)
		self.assertEqual(monthly[0]["calculated_price_per_litre"], 200)
		self.assertIn("1 recorded; 1 unavailable", monthly[0]["amount_status"])
		self.assertEqual(data[1]["calculated_price_per_litre"], 200)
		self.assertEqual(data[1]["printed_unit_price"], 200)
		self.assertEqual(data[2]["amount_status"], "Unavailable")
		self.assertIsNone(data[2]["recorded_spend"])
		self.assertIsNone(monthly[1]["recorded_spend"])
		self.assertIn("unavailable", monthly[1]["amount_status"])
		self.assertEqual(data[4]["amount_status"], "Unavailable")
		self.assertIsNone(data[4]["printed_unit_price"])
		self.assertEqual(chart["data"]["labels"], ["2025-12", "2026-01"])
		self.assertEqual(chart["data"]["datasets"][0]["values"], [4000, 0])


class TestFuelingSummaryPermissions(IntegrationTestCase):
	"""Exercise spec 008-overseer-reports Requirements 1.3, 1.4, 1.5, 3.4, 4.1, and 4.2."""

	date_filters = {"from_date": "2000-01-01", "to_date": "2099-12-31"}

	def _run_report(self, filters=None):
		return run("Fueling Summary", filters or self.date_filters)

	def _details(self, result):
		return [row for row in result["result"] if row.get("row_type") == "Fueling transaction"]

	def _export_csv(self, filters):
		name, extension, content = _export_query(
			frappe._dict(
				report_name="Fueling Summary",
				file_format_type="CSV",
				custom_columns="[]",
				include_indentation=0,
				include_filters=0,
				visible_idx=[],
				ignore_visible_idx=1,
				include_hidden_columns=0,
				filters=filters,
				applied_filters=filters,
			),
			{"delimiter": ",", "quoting": csv.QUOTE_NONNUMERIC, "decimal_sep": "."},
			populate_response=False,
		)
		self.assertEqual(extension, "csv")
		self.assertTrue(name.startswith("Fueling Summary"))
		return list(csv.DictReader(StringIO(content.decode("utf-8"))))

	def test_approvers_see_only_permitted_locations_and_linked_records(self):
		for user, expected_location in ((VIKAS, "Nairobi"), (AMINA, "Mombasa")):
			with self.subTest(user=user), self.set_user(user):
				location_choices = {
					row.name for row in frappe.get_list("Fleet Location", fields=["name"], limit=100)
				}
				self.assertEqual(location_choices, {expected_location})

				result = self._run_report()
				details = self._details(result)
				self.assertTrue(details)
				self.assertEqual({row["location"] for row in details}, {expected_location})
				for row in details:
					doc = frappe.get_doc("Fueling Transaction", row["name"])
					self.assertTrue(frappe.has_permission("Fueling Transaction", "read", doc=doc))

				self.assertTrue(frappe.permissions.can_export("Fueling Transaction"))
				csv_rows = self._export_csv(self.date_filters)
				csv_details = [row for row in csv_rows if row["Row Type"] == "Fueling transaction"]
				self.assertEqual({row["Location"] for row in csv_details}, {expected_location})
				self.assertEqual(
					{row["Fueling Transaction"] for row in csv_details},
					{row["name"] for row in details},
				)

	def test_filters_match_source_totals_trend_details_and_export(self):
		with self.set_user(VIKAS):
			source = frappe.get_list(
				"Fueling Transaction",
				filters={"docstatus": 1},
				fields=[
					"name",
					"asset",
					"fuel_type",
					"actual_station",
					"actual_fueling_datetime",
				],
				order_by="actual_fueling_datetime asc, name asc",
				limit=1,
			)[0]
			fueling_date = getdate(source.actual_fueling_datetime)
			filters = {
				"from_date": fueling_date,
				"to_date": fueling_date,
				"location": "Nairobi",
				"asset": source.asset,
				"fuel_type": source.fuel_type,
				"station": source.actual_station,
			}
			source_rows = frappe.get_list(
				"Fueling Transaction",
				filters={
					"docstatus": 1,
					"actual_fueling_datetime": [
						"between",
						[f"{fueling_date} 00:00:00", f"{fueling_date} 23:59:59"],
					],
					"asset": source.asset,
					"fuel_type": source.fuel_type,
					"actual_station": source.actual_station,
				},
				fields=["name", "invoice_litres"],
				limit=1000,
			)
			report = self._run_report(filters)
			details = self._details(report)
			self.assertTrue(details)
			self.assertEqual({row["name"] for row in details}, {row.name for row in source_rows})
			self.assertTrue(all(row["location"] == "Nairobi" for row in details))
			self.assertTrue(all(row["asset"] == source.asset for row in details))
			self.assertTrue(all(row["fuel_type"] == source.fuel_type for row in details))
			self.assertTrue(all(row["station"] == source.actual_station for row in details))

			monthly = [row for row in report["result"] if row.get("row_type") == "Monthly total"]
			self.assertEqual([row["month"] for row in monthly], [fueling_date.strftime("%Y-%m")])
			self.assertEqual(monthly[0]["transaction_count"], len(details))
			self.assertEqual(
				monthly[0]["delivered_litres"], sum(flt(row.invoice_litres) for row in source_rows)
			)
			self.assertEqual(report["chart"]["data"]["labels"], [fueling_date.strftime("%Y-%m")])
			csv_rows = self._export_csv(filters)
			csv_details = [row for row in csv_rows if row["Row Type"] == "Fueling transaction"]
			self.assertEqual(
				{row["Fueling Transaction"] for row in csv_details},
				{row["name"] for row in details},
			)

	def test_approver_cannot_select_another_location_and_user_cannot_open_report(self):
		with self.set_user(VIKAS), self.assertRaises(frappe.PermissionError):
			self._run_report({**self.date_filters, "location": "Mombasa"})

		with self.set_user(PHILIP), self.assertRaises(frappe.PermissionError):
			self._run_report()

	def test_fleet_admin_retains_all_location_access(self):
		with self.set_user(FLEET_ADMIN):
			details = self._details(self._run_report())
			self.assertTrue({"Nairobi", "Mombasa"}.issubset({row["location"] for row in details}))

	def test_report_matches_two_location_source_and_excludes_cancelled_legacy_rows(self):
		def source_rows(docstatus):
			return frappe.db.sql(
				f"""
				SELECT
					`tabFueling Transaction`.name,
					{LOCATION_EXPRESSION} AS location,
					`tabFueling Transaction`.actual_fueling_datetime AS fueling_datetime,
					`tabFueling Transaction`.invoice_litres AS delivered_litres,
					`tabFueling Transaction`.invoice_amount AS invoice_amount
				FROM `tabFueling Transaction`
				LEFT JOIN `tabFuel Order`
					ON `tabFuel Order`.name = `tabFueling Transaction`.fuel_order
				WHERE `tabFueling Transaction`.docstatus = %(docstatus)s
				ORDER BY `tabFueling Transaction`.actual_fueling_datetime, `tabFueling Transaction`.name
				""",
				{"docstatus": docstatus},
				as_dict=True,
			)

		frappe.db.savepoint("fueling_summary_source_check")
		try:
			with self.set_user(FLEET_ADMIN):
				before = source_rows(1)
				self.assertTrue({"Nairobi", "Mombasa"}.issubset({row.location for row in before}))
				legacy = next((row for row in before if flt(row.invoice_amount) <= 0), None)
				self.assertIsNotNone(
					legacy,
					"The disposable source data should include a legacy transaction without an amount.",
				)

				to_cancel = next(
					row
					for row in before
					if row.location == "Nairobi"
					and not any(
						frappe.db.exists(
							"Fueling Transaction",
							{fieldname: row.name, "name": ["!=", row.name]},
						)
						for fieldname in ("previous_full_fill", "closing_full_fill")
					)
				)
				frappe.get_doc("Fueling Transaction", to_cancel.name).cancel()
				active = source_rows(1)
				cancelled = source_rows(2)
				self.assertIn(to_cancel.name, {row.name for row in cancelled})
				self.assertNotIn(to_cancel.name, {row.name for row in active})

				report = self._run_report()
				details = self._details(report)
				self.assertEqual({row["name"] for row in details}, {row.name for row in active})
				self.assertEqual({row["location"] for row in details}, {"Nairobi", "Mombasa"})
				self.assertNotIn(to_cancel.name, {row["name"] for row in details})
				self.assertIn("Monthly spend totals include only recorded invoice amounts", report["message"])

				legacy_detail = next(row for row in details if row["name"] == legacy.name)
				self.assertEqual(legacy_detail["amount_status"], "Unavailable")
				self.assertIsNone(legacy_detail["recorded_spend"])

				monthly_source = defaultdict(
					lambda: {
						"count": 0,
						"litres": 0.0,
						"spend": 0.0,
						"priced_litres": 0.0,
						"unavailable": 0,
					}
				)
			for row in active:
				month = getdate(row.fueling_datetime).strftime("%Y-%m")
				bucket = monthly_source[month]
				bucket["count"] += 1
				bucket["litres"] += flt(row.delivered_litres)
				if flt(row.invoice_amount) > 0:
					bucket["spend"] += flt(row.invoice_amount)
					bucket["priced_litres"] += flt(row.delivered_litres)
				else:
					bucket["unavailable"] += 1

			monthly_report = {
				row["month"]: row for row in report["result"] if row.get("row_type") == "Monthly total"
			}
			self.assertEqual(set(monthly_report), set(monthly_source))
			for month, source in monthly_source.items():
				total = monthly_report[month]
				self.assertEqual(total["transaction_count"], source["count"])
				self.assertAlmostEqual(total["delivered_litres"], source["litres"], places=2)
				if source["spend"]:
					self.assertAlmostEqual(total["recorded_spend"], source["spend"], places=2)
					self.assertAlmostEqual(
						total["calculated_price_per_litre"], source["spend"] / source["priced_litres"], places=4
					)
				else:
					self.assertIsNone(total["recorded_spend"])
				self.assertIn(f"{source['unavailable']} unavailable", total["amount_status"])
		finally:
			frappe.db.rollback(save_point="fueling_summary_source_check")
