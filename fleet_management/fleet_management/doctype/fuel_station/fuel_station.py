from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class FuelStation(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.drop_repeated_locations()

	def drop_repeated_locations(self):
		"""Keep each extra location once and never repeat the operational location (spec 006 D-7)."""
		seen = {self.operational_location}
		rows = []
		for row in self.also_serves:
			if row.fleet_location and row.fleet_location not in seen:
				seen.add(row.fleet_location)
				rows.append(row)
		self.also_serves = rows
