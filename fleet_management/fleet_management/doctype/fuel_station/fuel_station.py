import frappe
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


def get_served_locations(station):
	"""The station's operational location plus every Also Serves location (spec 006 D-7)."""
	operational_location = frappe.db.get_value("Fuel Station", station, "operational_location")
	if not operational_location:
		return set()
	extra = frappe.get_all(
		"Fuel Station Location",
		filters={"parent": station, "parenttype": "Fuel Station", "parentfield": "also_serves"},
		pluck="fleet_location",
	)
	return {operational_location, *extra}


def get_stations_serving(location, txt=None):
	"""Names of active, approved stations that serve the location, optionally matching `txt`."""
	if not location:
		return []
	extra = frappe.get_all(
		"Fuel Station Location",
		filters={"fleet_location": location, "parenttype": "Fuel Station", "parentfield": "also_serves"},
		pluck="parent",
	)
	filters = {"active": 1, "approved": 1}
	if txt:
		filters["name"] = ["like", f"%{txt}%"]
	return frappe.get_all(
		"Fuel Station",
		filters=filters,
		or_filters={"operational_location": location, "name": ["in", extra or [""]]},
		pluck="name",
		order_by="name asc",
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def station_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link search for a Fuel Order's planned station: stations serving the order's location."""
	names = get_stations_serving((filters or {}).get("operational_location"), txt)
	visible = set(frappe.get_list("Fuel Station", filters={"name": ["in", names or [""]]}, pluck="name"))
	return [(name,) for name in names if name in visible][int(start) : int(start) + int(page_len)]
