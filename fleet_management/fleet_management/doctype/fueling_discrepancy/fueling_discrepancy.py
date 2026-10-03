import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class FuelingDiscrepancy(Document):
	def before_insert(self):
		self._validate_transaction_access()
		self.recorded_by = frappe.session.user
		self.recorded_on = now_datetime()

	def validate(self):
		self._validate_transaction_access()
		for fieldname in ("discrepancy_type", "details", "reason"):
			if not (self.get(fieldname) or "").strip():
				frappe.throw(_("{0} is required.").format(self.meta.get_label(fieldname)), frappe.ValidationError)

	def _validate_transaction_access(self):
		if not self.fueling_transaction:
			frappe.throw(_("Fueling Transaction is required."), frappe.ValidationError)

		transaction = frappe.get_doc("Fueling Transaction", self.fueling_transaction)
		if not frappe.has_permission("Fueling Transaction", "read", doc=transaction):
			frappe.throw(_("You do not have access to the linked Fueling Transaction."), frappe.PermissionError)
