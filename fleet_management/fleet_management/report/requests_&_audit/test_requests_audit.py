import csv
from datetime import datetime
from importlib import import_module
from io import StringIO
from typing import ClassVar

import frappe
from frappe.desk.query_report import _export_query, run
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import getdate

from fleet_management.fleet_management.doctype.fueling_discrepancy.test_fueling_discrepancy import (
	FuelingDiscrepancyFixture,
)
from fleet_management.history import stage_cancel_reason

_build_rows = import_module(
	"fleet_management.fleet_management.report.requests_&_audit.requests_&_audit"
)._build_rows
_filter_rows = import_module(
	"fleet_management.fleet_management.report.requests_&_audit.requests_&_audit"
)._filter_rows


class TestRequestsAuditRows(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirements 3.1, 3.2, 3.3, and 3.4."""

	def test_withdrawal_keeps_its_reason_actor_warning_and_event_date(self):
		day = getdate("2026-10-03")
		event_time = datetime(2026, 10, 3, 10, 0)
		order = frappe._dict(
			{
				"name": "FO-TEST",
				"location": "Nairobi",
				"asset": "VH-TEST",
				"fuel_type": "Diesel",
				"station": "ST-TEST",
				"requester": "Person-TEST",
				"request_datetime": event_time,
				"approved_on": None,
				"rejected_on": event_time,
				"docstatus": 0,
				"workflow_state": "Rejected",
				"decision_action": "Withdraw",
				"decision_reason": "The requester corrected the entry.",
				"rejected_by": "requester@example.com",
				"signal": "Red",
				"signal_reasons": "Meter reading requires review.",
				"valid_until": None,
				"has_submitted_transaction": 0,
			}
		)

		rows = _build_rows([order], [], day, day)
		decision = next(row for row in rows if row["activity"] == "Fuel request decision")
		self.assertEqual(decision["activity_date"], event_time)
		self.assertEqual(decision["request_status"], "Withdrawn")
		self.assertEqual(decision["decision_action"], "Withdraw")
		self.assertEqual(decision["decision_reason"], "The requester corrected the entry.")
		self.assertEqual(decision["decision_by"], "requester@example.com")
		self.assertEqual(decision["warning_status"], "Red")
		self.assertEqual(decision["warning_reasons"], "Meter reading requires review.")

	def test_missing_discrepancy_is_described_as_not_recorded(self):
		day = getdate("2026-10-03")
		transaction = frappe._dict(
			{
				"name": "FT-TEST",
				"docstatus": 1,
				"fuel_order": "FO-TEST",
				"actual_fueling_datetime": datetime(2026, 10, 3, 11, 0),
				"location": "Nairobi",
				"asset": "VH-TEST",
				"fuel_type": "Diesel",
				"station": "ST-TEST",
				"delivered_litres": 20,
				"requester": "Person-TEST",
				"discrepancy": None,
			}
		)

		row = _build_rows([], [transaction], day, day)[0]
		self.assertEqual(row["discrepancy_status"], "No discrepancy was recorded")
		self.assertIsNone(row["fueling_discrepancy"])

	def test_review_sections_keep_their_rows_and_all_audit_keeps_cancellations(self):
		rows = [
			{
				"activity": "Fuel request",
				"warning_status": "Red",
				"warning_reasons": "Review the meter reading.",
				"fuel_order": "FO-RED",
			},
			{
				"activity": "Fuel request decision",
				"warning_status": "Red",
				"fuel_order": "FO-RED",
				"fueling_transaction": "FT-RED",
				"warning_reasons": "Review the meter reading.",
				"request_status": "Approved",
			},
			{
				"activity": "Fuel request",
				"warning_status": "Green",
				"warning_reasons": None,
				"fuel_order": "FO-CLEAR",
			},
			{"activity": "Recorded fueling discrepancy", "fueling_discrepancy": "FD-1"},
			{"activity": "Cancelled fueling transaction", "fueling_status": "Cancelled"},
		]

		self.assertEqual(len(_filter_rows(rows, "Approvals")), 3)
		flags = _filter_rows(rows, "Flag Reports")
		self.assertEqual(len(flags), 2)
		self.assertEqual(flags[1]["request_status"], "Approved")
		self.assertEqual(flags[1]["warning_reasons"], "Review the meter reading.")
		self.assertEqual(flags[1]["fueling_transaction"], "FT-RED")
		self.assertEqual(_filter_rows(rows, "Discrepancy Reports"), [rows[3]])
		self.assertEqual(_filter_rows(rows, "All Audit"), rows)


class TestRequestsAudit(FuelingDiscrepancyFixture, IntegrationTestCase):
	"""Integration checks for spec 008-overseer-reports Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.2."""

	date_filters: ClassVar[dict[str, str]] = {"from_date": "2000-01-01", "to_date": "2099-12-31"}

	def setUp(self):
		super().setUp()
		self.rejected_order = self._make_rejected_order("Nairobi")

	def _run_report(self, filters=None):
		return run("Requests & Audit", filters or self.date_filters)

	def _export_csv(self, filters):
		name, extension, content = _export_query(
			frappe._dict(
				report_name="Requests & Audit",
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
		self.assertTrue(name.startswith("Requests & Audit"))
		return list(csv.DictReader(StringIO(content.decode("utf-8"))))

	def test_decisions_warnings_discrepancies_filters_and_export_match_sources(self):
		transaction = self._submit_transaction("Nairobi")
		with self.set_user(self.users["Nairobi"]):
			discrepancy = self._insert_discrepancy(transaction)

		order = frappe.get_doc("Fuel Order", self.orders["Nairobi"].name)
		rejected = frappe.get_doc("Fuel Order", self.rejected_order.name)
		filters = {
			"from_date": getdate(transaction.actual_fueling_datetime),
			"to_date": getdate(transaction.actual_fueling_datetime),
			"location": self.locations["Nairobi"].name,
			"asset": self.assets["Nairobi"].name,
			"fuel_type": self.fuel_type.name,
			"station": self.stations["Nairobi"].name,
		}
		with self.set_user(self.approvers["Nairobi"]):
			with self.assertRaises(frappe.ValidationError) as error:
				self._run_report({**filters, "from_date": "2099-12-31", "to_date": "2000-01-01"})
			self.assertIn("From Date cannot be later than To Date.", str(error.exception))

			result = self._run_report(filters)
			rows = result["result"]
			self.assertTrue(rows)
			self.assertEqual({row["location"] for row in rows}, {self.locations["Nairobi"].name})
			self.assertTrue(all(row["asset"] == filters["asset"] for row in rows))
			self.assertTrue(all(row["fuel_type"] == filters["fuel_type"] for row in rows))
			self.assertTrue(all(row["station"] == filters["station"] for row in rows))

			request = next(
				row
				for row in rows
				if row.get("fuel_order") == order.name and row["activity"] == "Fuel request"
			)
			approval = next(
				row
				for row in rows
				if row.get("fuel_order") == order.name and row["activity"] == "Fuel request decision"
			)
			self.assertEqual(request["request_status"], "Approved")
			self.assertEqual(request["fulfillment_status"], "Completed")
			self.assertEqual(request["warning_status"], order.signal)
			self.assertEqual(request["warning_reasons"], order.signal_reasons)
			self.assertEqual(approval["decision_action"], "Approve")
			self.assertEqual(approval["decision_by"], order.approved_by)
			self.assertEqual(approval["activity_date"], order.approved_on)

			rejection = next(
				row
				for row in rows
				if row.get("fuel_order") == rejected.name and row["activity"] == "Fuel request decision"
			)
			self.assertEqual(rejection["decision_action"], "Reject")
			self.assertEqual(rejection["decision_reason"], rejected.decision_reason)
			self.assertEqual(rejection["decision_by"], rejected.rejected_by)
			self.assertEqual(rejection["activity_date"], rejected.rejected_on)

			approvals = self._run_report({**filters, "section": "Approvals"})["result"]
			self.assertTrue(approvals)
			self.assertTrue(
				all(row["activity"] in ("Fuel request", "Fuel request decision") for row in approvals)
			)

			flags = self._run_report({**filters, "section": "Flag Reports"})["result"]
			self.assertTrue(flags)
			self.assertTrue(all(row["warning_status"] in ("Green", "Red") for row in flags))
			self.assertTrue(all(row["warning_reasons"] for row in flags))
			flagged_rejection = next(row for row in flags if row.get("fuel_order") == rejected.name)
			self.assertEqual(flagged_rejection["request_status"], "Rejected")

			discrepancy_rows = self._run_report({**filters, "section": "Discrepancy Reports"})["result"]
			self.assertEqual({row["fueling_discrepancy"] for row in discrepancy_rows}, {discrepancy.name})

			audit = next(
				row
				for row in rows
				if row.get("fueling_transaction") == transaction.name
				and row["activity"] == "Recorded fueling discrepancy"
			)
			self.assertEqual(audit["fueling_status"], "Submitted")
			self.assertEqual(audit["discrepancy_status"], "Recorded")
			self.assertEqual(audit["fueling_discrepancy"], discrepancy.name)
			self.assertEqual(audit["discrepancy_type"], discrepancy.discrepancy_type)
			self.assertEqual(audit["discrepancy_details"], discrepancy.details)
			self.assertEqual(audit["discrepancy_reason"], discrepancy.reason)
			self.assertEqual(audit["recorded_by"], discrepancy.recorded_by)
			self.assertEqual(audit["recorded_on"], discrepancy.recorded_on)

			csv_rows = self._export_csv(filters)
			self.assertEqual({row["Activity"] for row in csv_rows}, {row["activity"] for row in rows})
			self.assertEqual(
				{row["Fueling Transaction"] for row in csv_rows if row["Fueling Transaction"]},
				{row["fueling_transaction"] for row in rows if row.get("fueling_transaction")},
			)

	def test_missing_discrepancy_is_clear_and_scope_cannot_be_widened(self):
		transaction = self._submit_transaction("Mombasa")
		filters = {
			**self.date_filters,
			"location": self.locations["Mombasa"].name,
			"asset": self.assets["Mombasa"].name,
		}
		with self.set_user(self.approvers["Mombasa"]):
			rows = self._run_report(filters)["result"]
			audit = next(
				row
				for row in rows
				if row.get("fueling_transaction") == transaction.name
				and row["activity"] == "Fueling transaction"
			)
			self.assertEqual(audit["discrepancy_status"], "No discrepancy was recorded")
			self.assertNotIn("no issue occurred", audit["discrepancy_status"].lower())

		with self.set_user(self.approvers["Nairobi"]):
			rows = self._run_report(self.date_filters)["result"]
			self.assertEqual({row["location"] for row in rows}, {self.locations["Nairobi"].name})
			with self.assertRaises(frappe.PermissionError):
				self._run_report({**self.date_filters, "location": self.locations["Mombasa"].name})

		with self.set_user(self.users["Nairobi"]), self.assertRaises(frappe.PermissionError):
			self._run_report(self.date_filters)

	def test_cancelled_transaction_stays_in_audit_and_out_of_summary_and_performance(self):
		transaction = self._submit_transaction("Nairobi")
		with self.set_user("Administrator"):
			stage_cancel_reason("Fueling Transaction", transaction.name, "Duplicate test fueling transaction")
			frappe.get_doc("Fueling Transaction", transaction.name).cancel()

		day = getdate(transaction.actual_fueling_datetime)
		filters = {
			"from_date": day,
			"to_date": day,
			"location": self.locations["Nairobi"].name,
			"asset": self.assets["Nairobi"].name,
			"fuel_type": self.fuel_type.name,
			"station": self.stations["Nairobi"].name,
		}
		with self.set_user(self.approvers["Nairobi"]):
			audit_rows = self._run_report(filters)["result"]
			cancelled = next(
				row
				for row in audit_rows
				if row.get("fueling_transaction") == transaction.name
				and row["activity"] == "Cancelled fueling transaction"
			)
			self.assertEqual(cancelled["activity"], "Cancelled fueling transaction")
			self.assertEqual(cancelled["fueling_status"], "Cancelled")

			summary_rows = run("Fueling Summary", filters)["result"]
			self.assertFalse(
				any(
					row.get("name") == transaction.name or row.get("row_type") == "Monthly total"
					for row in summary_rows
				)
			)

			performance_rows = run("Asset Performance", filters)["result"]
			self.assertNotIn(
				transaction.name,
				{row.get("fueling_transaction") for row in performance_rows},
			)
			monthly = [row for row in performance_rows if row.get("record_type") == "Monthly total"]
			self.assertEqual(sum(row.get("fueling_count", 0) or 0 for row in monthly), 0)
			self.assertEqual(sum(row.get("delivered_litres", 0) or 0 for row in monthly), 0)
