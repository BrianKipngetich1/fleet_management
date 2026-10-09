import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FuelOrderHistoryEvent(Document):
	def before_insert(self):
		if not self.flags.get("from_history_service"):
			frappe.throw(
				frappe._("Fuel Order history can only be written by the server."),
				frappe.PermissionError,
			)
		self.event_datetime = now_datetime()
		self.actor = frappe.session.user

	def validate(self):
		if not self.is_new():
			frappe.throw(
				frappe._("Fuel Order history events cannot be changed."),
				frappe.PermissionError,
			)

	def on_trash(self):
		frappe.throw(
			frappe._("Fuel Order history events cannot be deleted."),
			frappe.PermissionError,
		)

	def before_rename(self, old, new, merge=False):
		frappe.throw(
			frappe._("Fuel Order history events cannot be renamed."),
			frappe.PermissionError,
		)
