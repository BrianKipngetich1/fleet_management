import csv
from io import StringIO

import frappe
from frappe import _dict
from frappe.desk.query_report import _export_query, run
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, flt, getdate

from fleet_management.fleet_management.report.asset_performance.asset_performance import (
	_fueling_source_key,
	_fulfillment_status,
	_get_optional_date_range,
	_monthly_efficiency,
	_rate_efficiency,
	_request_status,
	_target_history_state,
	_vehicle_efficiency_columns,
)
from fleet_management.fleet_management.report.fueling_summary.fueling_summary import _get_date_range
from fleet_management.tests.report_history import ReportHistoryFixture


class TestAssetPerformanceStatuses(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirement 2.1."""

	def test_reversed_period_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "From Date cannot be later than To Date"):
			_get_date_range(_dict(from_date="2026-10-02", to_date="2026-10-01"))

	def test_asset_period_is_optional_and_accepts_one_sided_bounds(self):
		self.assertEqual(_get_optional_date_range(_dict()), (None, None))
		self.assertEqual(
			_get_optional_date_range(_dict(from_date="2026-10-02")), (getdate("2026-10-02"), None)
		)
		self.assertEqual(
			_get_optional_date_range(_dict(to_date="2026-10-03")), (None, getdate("2026-10-03"))
		)
		with self.assertRaisesRegex(frappe.ValidationError, "From Date cannot be later than To Date"):
			_get_optional_date_range(_dict(from_date="2026-10-02", to_date="2026-10-01"))

	def test_request_status_distinguishes_pending_approval_rejection_withdrawal_and_cancellation(self):
		self.assertEqual(_request_status(_dict(docstatus=0, workflow_state="Pending Approval")), "Pending")
		self.assertEqual(_request_status(_dict(docstatus=1, workflow_state="Approved")), "Approved")
		self.assertEqual(
			_request_status(_dict(docstatus=1, workflow_state="Rejected", decision_action="Reject")),
			"Rejected",
		)
		self.assertEqual(
			_request_status(_dict(docstatus=1, workflow_state="Rejected", decision_action="Withdraw")),
			"Withdrawn",
		)
		self.assertEqual(_request_status(_dict(docstatus=2, workflow_state="Approved")), "Cancelled")

	def test_fulfillment_status_reports_awaiting_completed_expired_and_cancelled(self):
		self.assertEqual(
			_fulfillment_status(
				_dict(docstatus=1, workflow_state="Approved", has_submitted_transaction=0, valid_until=None)
			),
			"Awaiting fueling",
		)
		self.assertEqual(
			_fulfillment_status(_dict(docstatus=1, workflow_state="Approved", has_submitted_transaction=1)),
			"Completed",
		)
		self.assertEqual(
			_fulfillment_status(
				_dict(
					docstatus=1,
					workflow_state="Approved",
					has_submitted_transaction=0,
					valid_until="2026-10-01 00:00:00",
				),
				now="2026-10-02 00:00:00",
			),
			"Expired",
		)
		self.assertEqual(_fulfillment_status(_dict(docstatus=2, workflow_state="Approved")), "Cancelled")


class TestAssetPerformanceEfficiency(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirements 2.2, 2.3, and 2.4."""

	def test_rating_bands_are_inclusive_above_and_below_target(self):
		self.assertEqual(_rate_efficiency(11, 10), "Green")
		self.assertEqual(_rate_efficiency(9, 10), "Green")
		self.assertEqual(_rate_efficiency(12, 10), "Orange")
		self.assertEqual(_rate_efficiency(8, 10), "Orange")
		self.assertEqual(_rate_efficiency(12.01, 10), "Red")
		self.assertEqual(_rate_efficiency(7.99, 10), "Red")
		self.assertIsNone(_rate_efficiency(10, 0))

	def test_target_history_detects_changes_and_missing_snapshots(self):
		self.assertEqual(_target_history_state(10, [10, 10.0]), "stable")
		self.assertEqual(_target_history_state(10, [10, 12]), "changed")
		self.assertEqual(_target_history_state(10, [10, None]), "unknown")

	def test_changed_target_keeps_efficiency_but_withholds_rating(self):
		transaction = _dict(
			name="FT-CLOSE",
			closing_full_fill="FT-CLOSE",
			previous_full_fill="FT-OPEN",
			distance_km=500,
			qualifying_litres=50,
			km_per_litre=10,
			asset_target_km_per_litre_snapshot=10,
		)
		columns = _vehicle_efficiency_columns(transaction, {"FT-CLOSE": "changed"})
		self.assertEqual(columns["efficiency_km_per_litre"], 10)
		self.assertIsNone(columns["efficiency_rating"])
		self.assertIn("target changed", columns["efficiency_status"].lower())

	def test_non_closing_transaction_shows_efficiency_unavailable(self):
		columns = _vehicle_efficiency_columns(_dict(name="FT-PARTIAL"), {})
		self.assertEqual(columns["efficiency_status"], "Unavailable")

	def test_full_fill_ties_use_actual_fueling_time_then_name(self):
		opening = _dict(name="FT-0001", actual_fueling_datetime="2026-10-01 08:00:00")
		closing = _dict(name="FT-0002", actual_fueling_datetime="2026-10-01 08:00:00")
		self.assertLess(_fueling_source_key(opening), _fueling_source_key(closing))

	def test_month_efficiency_weights_only_valid_intervals_by_qualifying_litres(self):
		rows = [
			{"distance_km": 400, "qualifying_litres": 40},
			{"distance_km": 300, "qualifying_litres": 20},
			{"efficiency_status": "Unavailable"},
		]
		self.assertEqual(_monthly_efficiency(rows), 11.6667)
		self.assertIsNone(_monthly_efficiency([{"efficiency_status": "Unavailable"}]))


class TestAssetPerformanceReport(ReportHistoryFixture, IntegrationTestCase):
	"""Source-row checks for spec 008-overseer-reports Requirements 2.1, 2.2, 2.3, and 2.4."""

	date_filters = {"from_date": "2000-01-01", "to_date": "2099-12-31"}

	def _run_report(self, filters):
		return run("Asset Performance", filters)

	def _details(self, result):
		return [row for row in result["result"] if row.get("record_type") != "Monthly total"]

	def _transaction_rows(self, result):
		return [row for row in self._details(result) if row.get("fueling_transaction")]

	def _interval_with_partial_fill(self, asset):
		transactions = frappe.get_all(
			"Fueling Transaction",
			filters={"asset": asset, "docstatus": 1},
			fields=[
				"name",
				"actual_fueling_datetime",
				"previous_full_fill",
				"closing_full_fill",
				"full_tank_confirmed",
				"invoice_litres",
				"qualifying_litres",
				"km_per_litre",
				"distance_km",
				"asset_target_km_per_litre_snapshot",
			],
			order_by="actual_fueling_datetime asc, name asc",
		)
		by_name = {row.name: row for row in transactions}
		for closing in transactions:
			if closing.closing_full_fill != closing.name or not closing.previous_full_fill:
				continue
			opening = by_name.get(closing.previous_full_fill)
			if not opening:
				continue
			partial = next(
				(
					row
					for row in transactions
					if not row.full_tank_confirmed
					and _fueling_source_key(opening)
					< _fueling_source_key(row)
					<= _fueling_source_key(closing)
				),
				None,
			)
			if partial:
				return opening, partial, closing
		self.fail(f"No full-to-full interval with a partial fill was found for {asset}.")

	def _export_csv(self, filters):
		name, extension, content = _export_query(
			frappe._dict(
				report_name="Asset Performance",
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
		self.assertTrue(name.startswith("Asset Performance"))
		return list(csv.DictReader(StringIO(content.decode("utf-8"))))

	def test_statuses_and_links_match_source_fuel_orders_and_transactions(self):
		seen_requests = set()
		seen_fulfillment = set()
		with self.set_user(self.admin):
			for asset in (*self.vehicles.values(), self.generator):
				filters = {**self.date_filters, "asset": asset}
				rows = self._details(self._run_report(filters))
				for row in rows:
					if row.get("fuel_order"):
						order = frappe.get_doc("Fuel Order", row["fuel_order"])
						self.assertTrue(frappe.has_permission("Fuel Order", "read", doc=order))
						self.assertEqual(row["request_status"], _request_status(order))
						self.assertEqual(row["request_date"], order.request_datetime)
						self.assertEqual(row["decision_date"], order.approved_on or order.rejected_on)
						self.assertEqual(row["fuel_type"], order.fuel_type)
						self.assertEqual(row["requester"], order.actual_requester)
						seen_requests.add(row["request_status"])
						seen_fulfillment.add(row["fulfillment_status"])
					if row.get("fueling_transaction"):
						transaction = frappe.get_doc("Fueling Transaction", row["fueling_transaction"])
						self.assertEqual(transaction.docstatus, 1)
						self.assertTrue(frappe.has_permission("Fueling Transaction", "read", doc=transaction))
						self.assertEqual(row["delivered_litres"], transaction.invoice_litres)
						self.assertEqual(row["station"], transaction.actual_station)
						self.assertEqual(row["fueling_transaction"], transaction.name)
						self.assertEqual(row["fulfillment_status"], "Completed")
						self.assertEqual(row["request_status"], "Approved")
						seen_fulfillment.add(row["fulfillment_status"])

		self.assertTrue({"Pending", "Rejected", "Approved"}.issubset(seen_requests))
		self.assertTrue({"Awaiting fueling", "Completed", "Expired"}.issubset(seen_fulfillment))

	def test_unbounded_asset_history_and_monthly_efficiency_match_valid_intervals(self):
		asset = self.vehicles[self.north]
		transactions = frappe.get_all(
			"Fueling Transaction",
			filters={"asset": asset, "docstatus": 1},
			fields=["name", "actual_fueling_datetime", "distance_km", "qualifying_litres"],
			order_by="actual_fueling_datetime asc, name asc",
		)
		self.assertTrue(transactions)
		with self.set_user(self.admin):
			result = self._run_report({"asset": asset})
			rows = self._transaction_rows(result)
			self.assertEqual({row["fueling_transaction"] for row in rows}, {row.name for row in transactions})
			monthly = {
				row["month"]: row
				for row in result["result"]
				if row.get("record_type") == "Monthly total"
			}
			valid_by_month = {}
			for transaction in transactions:
				if flt(transaction.distance_km) > 0 and flt(transaction.qualifying_litres) > 0:
					month = getdate(transaction.actual_fueling_datetime).strftime("%Y-%m")
					valid_by_month.setdefault(month, []).append(transaction)
			for month, total in monthly.items():
				intervals = valid_by_month.get(month, [])
				if intervals:
					expected = sum(flt(row.distance_km) for row in intervals) / sum(
						flt(row.qualifying_litres) for row in intervals
					)
					self.assertAlmostEqual(total["efficiency_km_per_litre"], expected, places=4)
				else:
					self.assertIsNone(total["efficiency_km_per_litre"])
			self.assertEqual(result["chart"]["data"]["labels"], sorted(monthly))

			start = getdate(transactions[len(transactions) // 2].actual_fueling_datetime)
			from_only = self._transaction_rows(self._run_report({"asset": asset, "from_date": start}))
			self.assertTrue(all(getdate(row["activity_date"]) >= start for row in from_only))
			end = getdate(transactions[0].actual_fueling_datetime)
			to_only = self._transaction_rows(self._run_report({"asset": asset, "to_date": end}))
			self.assertTrue(all(getdate(row["activity_date"]) <= end for row in to_only))

	def test_vehicle_period_keeps_boundary_activity_and_uses_out_of_period_full_fill(self):
		asset = self.vehicles[self.north]
		opening, partial, closing = self._interval_with_partial_fill(asset)
		from_date = getdate(partial.actual_fueling_datetime)
		to_date = getdate(closing.actual_fueling_datetime)
		self.assertLess(getdate(opening.actual_fueling_datetime), from_date)
		transactions = frappe.get_all(
			"Fueling Transaction",
			filters={"asset": asset, "docstatus": 1},
			fields=["name", "actual_fueling_datetime", "invoice_litres"],
		)
		interval_litres = sum(
			flt(row.invoice_litres)
			for row in transactions
			if _fueling_source_key(opening) < _fueling_source_key(row) <= _fueling_source_key(closing)
		)
		self.assertEqual(interval_litres, flt(closing.qualifying_litres))

		filters = {
			"asset": asset,
			"from_date": from_date,
			"to_date": to_date,
			"location": self.north,
		}
		with self.set_user(self.admin):
			result = self._run_report(filters)
			rows = self._transaction_rows(result)
			row_by_name = {row["fueling_transaction"]: row for row in rows}
			self.assertIn(partial.name, row_by_name)
			self.assertIn(closing.name, row_by_name)
			self.assertNotIn(opening.name, row_by_name)
			closing_row = row_by_name[closing.name]
			self.assertEqual(closing_row["qualifying_litres"], flt(closing.qualifying_litres))
			self.assertEqual(closing_row["efficiency_km_per_litre"], flt(closing.km_per_litre))
			self.assertEqual(
				closing_row["efficiency_rating"],
				_rate_efficiency(closing.km_per_litre, closing.asset_target_km_per_litre_snapshot),
			)
			self.assertTrue(all(from_date <= getdate(row["activity_date"]) <= to_date for row in rows))

			later_start = self._run_report({**filters, "from_date": add_days(from_date, 1)})
			later_start_rows = {
				row["fueling_transaction"]: row for row in self._transaction_rows(later_start)
			}
			self.assertNotIn(partial.name, later_start_rows)
			self.assertIn(closing.name, later_start_rows)
			self.assertEqual(
				later_start_rows[closing.name]["efficiency_km_per_litre"],
				flt(closing.km_per_litre),
			)

			before_closing = self._run_report({**filters, "to_date": add_days(to_date, -1)})
			self.assertNotIn(
				closing.name,
				{row.get("fueling_transaction") for row in self._transaction_rows(before_closing)},
			)

	def test_target_change_inside_interval_withholds_rating_but_keeps_efficiency(self):
		asset = self.vehicles[self.north]
		opening, partial, closing = self._interval_with_partial_fill(asset)
		filters = {
			"asset": asset,
			"from_date": getdate(partial.actual_fueling_datetime),
			"to_date": getdate(closing.actual_fueling_datetime),
		}
		self.assertLess(getdate(opening.actual_fueling_datetime), filters["from_date"])
		frappe.db.savepoint("asset_performance_target_change")
		try:
			frappe.db.set_value(
				"Fueling Transaction",
				partial.name,
				"asset_target_km_per_litre_snapshot",
				flt(partial.asset_target_km_per_litre_snapshot) + 1,
				update_modified=False,
			)
			with self.set_user(self.admin):
				row = next(
					row
					for row in self._transaction_rows(self._run_report(filters))
					if row["fueling_transaction"] == closing.name
				)
				self.assertEqual(row["efficiency_km_per_litre"], flt(closing.km_per_litre))
				self.assertIsNone(row["efficiency_rating"])
				self.assertEqual(row["efficiency_status"], "Target changed within interval; not rated")
		finally:
			frappe.db.rollback(save_point="asset_performance_target_change")

	def test_generator_shows_hour_meter_and_delivered_litres_only(self):
		asset = self.generator
		transaction = frappe.get_all(
			"Fueling Transaction",
			filters={"asset": asset, "docstatus": 1},
			fields=["name", "actual_fueling_datetime", "hour_meter", "invoice_litres"],
			order_by="actual_fueling_datetime desc",
			limit=1,
		)[0]
		day = getdate(transaction.actual_fueling_datetime)
		with self.set_user(self.admin):
			result = self._run_report({"asset": asset, "from_date": day, "to_date": day})
			row = next(
				row
				for row in self._transaction_rows(result)
				if row["fueling_transaction"] == transaction.name
			)
			self.assertEqual(row["hour_meter"], flt(transaction.hour_meter))
			self.assertEqual(row["delivered_litres"], flt(transaction.invoice_litres))
			self.assertIsNone(row.get("vehicle_odometer"))
			self.assertTrue(any(column["label"] == "Hour Meter" for column in result["columns"]))
			self.assertFalse(any("consumed" in column["label"].lower() for column in result["columns"]))

	def test_filters_trend_export_and_location_permissions_match(self):
		asset = self.vehicles[self.north]
		source = frappe.get_all(
			"Fueling Transaction",
			filters={"asset": asset, "docstatus": 1},
			fields=["name", "actual_fueling_datetime", "fuel_type", "actual_station"],
			order_by="actual_fueling_datetime asc",
			limit=1,
		)[0]
		day = getdate(source.actual_fueling_datetime)
		filters = {
			"asset": asset,
			"from_date": day,
			"to_date": day,
			"location": self.north,
			"fuel_type": source.fuel_type,
			"station": source.actual_station,
		}
		with self.set_user(self.approvers[self.north]):
			result = self._run_report(filters)
			details = self._details(result)
			transactions = self._transaction_rows(result)
			self.assertIn(source.name, {row["fueling_transaction"] for row in transactions})
			self.assertTrue(all(row["location"] == self.north for row in details))
			self.assertTrue(all(row["asset"] == asset for row in details))
			self.assertTrue(all(row["fuel_type"] == source.fuel_type for row in details))
			self.assertTrue(all(row["station"] == source.actual_station for row in details))
			self.assertEqual(result["chart"]["data"]["labels"], [day.strftime("%Y-%m")])
			month_total = next(row for row in result["result"] if row.get("record_type") == "Monthly total")
			self.assertEqual(month_total["fueling_count"], len(transactions))
			self.assertAlmostEqual(
				month_total["delivered_litres"], sum(flt(row["delivered_litres"]) for row in transactions)
			)
			self.assertEqual(
				result["chart"]["data"]["datasets"][0]["values"], [month_total["delivered_litres"]]
			)
			self.assertTrue(frappe.permissions.can_export("Fueling Transaction"))
			csv_rows = self._export_csv(filters)
			csv_transactions = [
				row["Fueling Transaction"] for row in csv_rows if row["Activity"] == "Fueling Transaction"
			]
			self.assertEqual(set(csv_transactions), {row["fueling_transaction"] for row in transactions})
			csv_orders = {row["Fuel Order"] for row in csv_rows if row["Activity"].startswith("Fuel Order")}
			self.assertEqual(csv_orders, {row["fuel_order"] for row in details if row.get("fuel_order")})

			before_day = self._run_report(
				{**filters, "from_date": add_days(day, 1), "to_date": add_days(day, 1)}
			)
			self.assertNotIn(
				source.name, {row.get("fueling_transaction") for row in self._transaction_rows(before_day)}
			)
			with self.assertRaises(frappe.PermissionError):
				self._run_report({**filters, "location": self.south})
