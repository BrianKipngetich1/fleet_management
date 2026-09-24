from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from .fleet_asset import FleetAsset, get_effective_assignment


class TestFleetAsset(UnitTestCase):
	def make_asset(self, *assignments):
		asset = object.__new__(FleetAsset)
		asset.assignments = [frappe._dict(assignment) for assignment in assignments]
		return asset

	def test_non_overlapping_assignment_periods_are_accepted(self):
		asset = self.make_asset(
			{"effective_from": "2026-01-01", "effective_until": "2026-01-31", "idx": 1},
			{"effective_from": "2026-02-01", "effective_until": None, "idx": 2},
		)

		asset.validate_assignments()

	def test_overlapping_assignment_periods_are_rejected(self):
		asset = self.make_asset(
			{"effective_from": "2026-01-01", "effective_until": None, "idx": 1},
			{"effective_from": "2026-01-01", "effective_until": "2026-01-31", "idx": 2},
		)

		with patch.object(frappe, "_", side_effect=lambda message: message), patch.object(
			frappe, "throw", side_effect=frappe.ValidationError
		):
			with self.assertRaises(frappe.ValidationError):
				asset.validate_assignments()

	def test_effective_assignment_uses_the_requested_date(self):
		asset = self.make_asset(
			{
				"assigned_location": "Nairobi",
				"effective_from": "2026-01-01",
				"effective_until": "2026-01-31",
				"idx": 1,
			},
			{
				"assigned_location": "Mombasa",
				"effective_from": "2026-02-01",
				"effective_until": None,
				"idx": 2,
			},
		)

		self.assertEqual(get_effective_assignment(asset, "2026-01-15").assigned_location, "Nairobi")
		self.assertEqual(get_effective_assignment(asset, "2026-02-15").assigned_location, "Mombasa")
		self.assertIsNone(get_effective_assignment(asset, "2025-12-31"))
