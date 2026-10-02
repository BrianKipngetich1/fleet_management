from frappe import _dict
from frappe.tests import UnitTestCase

from fleet_management.fleet_management.report.asset_performance.asset_performance import (
	_fulfillment_status,
	_request_status,
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
