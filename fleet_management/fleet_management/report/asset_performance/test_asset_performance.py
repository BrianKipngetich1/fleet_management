from frappe import _dict
from frappe.tests import UnitTestCase

from fleet_management.fleet_management.report.asset_performance.asset_performance import (
	_fulfillment_status,
	_rate_efficiency,
	_request_status,
	_target_history_state,
	_vehicle_efficiency_columns,
)


class TestAssetPerformanceStatuses(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirement 2.1."""

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
			_fulfillment_status(
				_dict(docstatus=1, workflow_state="Approved", has_submitted_transaction=1)
			),
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
		self.assertEqual(
			_fulfillment_status(_dict(docstatus=2, workflow_state="Approved")), "Cancelled"
		)


class TestAssetPerformanceEfficiency(UnitTestCase):
	"""Pure checks for spec 008-overseer-reports Requirements 2.2, 2.3, and 2.4."""

	def test_rating_bands_are_inclusive_above_and_below_target(self):
		self.assertEqual(_rate_efficiency(11, 10), "Green")
		self.assertEqual(_rate_efficiency(8, 10), "Green")
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
