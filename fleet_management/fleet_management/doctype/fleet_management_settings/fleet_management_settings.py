import frappe
from frappe.model.document import Document


class FleetManagementSettings(Document):
	def validate(self):
		# At 100% the tank has no room left, so the mileage check could not be worked out (spec 002 D-8).
		if self.gauge_limit_percent is not None and self.gauge_limit_percent >= 100:
			frappe.throw(frappe._("Gauge Limit must be below 100%."), frappe.ValidationError)
