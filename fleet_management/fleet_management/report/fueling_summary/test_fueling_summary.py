import frappe
from frappe.tests import UnitTestCase

from fleet_management.fleet_management.report.fueling_summary.fueling_summary import (
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
