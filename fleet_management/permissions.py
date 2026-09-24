"""Location-scoped permissions for fleet records.

Fleet User and Fleet Approver receive location access through standard Frappe
User Permission records whose ``allow`` value is ``Fleet Location``.  The
query hook filters lists, while the controller hook protects direct reads,
prints, reports, and document actions.
"""

import frappe
from frappe.permissions import get_roles, get_user_permissions
from frappe.utils import today

from fleet_management.fleet_management.doctype.fleet_asset.fleet_asset import get_effective_assignment


LOCATION_DOCTYPE = "Fleet Location"
LOCATION_ROLES = frozenset({"Fleet User", "Fleet Approver"})
SCOPED_DOCTYPES = frozenset(
	{
		"Fleet Location",
		"Fuel Station",
		"Fleet Asset",
		"Asset Assignment",
		"Fuel Order",
		"Fueling Transaction",
	}
)

LOCATION_FIELDS = {
	"Fuel Station": ("operational_location",),
	"Asset Assignment": ("assigned_location",),
	"Fuel Order": ("assigned_location_snapshot",),
	"Fueling Transaction": ("assigned_location_snapshot",),
}

ASSET_LINK_FIELDS = {
	"Fuel Order": ("fleet_asset", "asset", "vehicle"),
	"Fueling Transaction": ("fleet_asset", "asset", "vehicle"),
}


def _user(user=None):
	return user or frappe.session.user


def _is_unrestricted(user):
	return user == "Administrator" or "Fleet Admin" in get_roles(user)


def _is_location_scoped(user):
	return bool(LOCATION_ROLES.intersection(get_roles(user)))


def get_permitted_location_names(user=None):
	"""Return Fleet Locations granted to the user by User Permission."""
	user = _user(user)
	return {
		str(permission.get("doc"))
		for permission in get_user_permissions(user).get(LOCATION_DOCTYPE, [])
		if permission.get("doc")
	}


def _escaped_locations(locations):
	return ", ".join(frappe.db.escape(location, percent=False) for location in sorted(locations))


def _table(doctype):
	return f"`tab{doctype}`"


def _meta_fieldnames(doctype):
	try:
		return {field.fieldname for field in frappe.get_meta(doctype).fields}
	except frappe.DoesNotExistError:
		return set()


def _query_location_fields(doctype):
	fields = LOCATION_FIELDS.get(doctype, ())
	if doctype not in {"Fuel Order", "Fueling Transaction"}:
		return fields

	available = _meta_fieldnames(doctype)
	return tuple(field for field in fields if field in available)


def _location_values(doc, doctype):
	for field in LOCATION_FIELDS.get(doctype, ()):
		value = doc.get(field)
		if value:
			# Assigned location is the authoritative scope when both snapshots exist.
			return {str(value)}
	return set()


def _asset_assignment_locations(asset):
	assignment = get_effective_assignment(asset, today())
	return {str(assignment.assigned_location)} if assignment and assignment.assigned_location else set()


def _linked_asset_locations(doc, doctype):
	for field in ASSET_LINK_FIELDS.get(doctype, ()):
		asset_name = doc.get(field)
		if asset_name:
			try:
				return _asset_assignment_locations(frappe.get_doc("Fleet Asset", asset_name))
			except frappe.DoesNotExistError:
				return set()
	return set()


def _document_location_names(doc):
	doctype = doc.get("doctype")
	if doctype == "Fleet Location":
		return {str(doc.get("name"))} if doc.get("name") else set()
	if doctype == "Fleet Asset":
		return _asset_assignment_locations(doc)
	if doctype == "Fuel Order":
		location = doc.get("assigned_location_snapshot")
		if location:
			return {str(location)}
		if doc.get("asset"):
			assignment = get_effective_assignment(doc.get("asset"), doc.get("request_datetime"))
			return {str(assignment.assigned_location)} if assignment and assignment.assigned_location else set()
	if doctype == "Fueling Transaction":
		location = doc.get("assigned_location_snapshot")
		if location:
			return {str(location)}
		if doc.get("fuel_order"):
			location = frappe.db.get_value(
				"Fuel Order", doc.get("fuel_order"), "assigned_location_snapshot"
			)
			return {str(location)} if location else set()

	locations = _location_values(doc, doctype)
	return locations or _linked_asset_locations(doc, doctype)


def _assignment_exists_condition(parent_expression, locations):
	today_value = frappe.db.escape(today(), percent=False)
	return (
		"EXISTS ("
		"SELECT 1 FROM `tabAsset Assignment` aa "
		f"WHERE aa.parent = {parent_expression} "
		"AND aa.parenttype = 'Fleet Asset' "
		f"AND aa.assigned_location IN ({_escaped_locations(locations)}) "
		f"AND aa.effective_from <= {today_value} "
		f"AND (aa.effective_until IS NULL OR aa.effective_until >= {today_value})"
		")"
	)


def _query_condition(doctype, locations):
	if doctype == "Fleet Location":
		return f"{_table(doctype)}.`name` IN ({_escaped_locations(locations)})"

	if doctype == "Fleet Asset":
		return _assignment_exists_condition(f"{_table(doctype)}.`name`", locations)

	if doctype == "Asset Assignment":
		today_value = frappe.db.escape(today(), percent=False)
		return (
			f"{_table(doctype)}.`assigned_location` IN ({_escaped_locations(locations)}) "
			f"AND {_table(doctype)}.`effective_from` <= {today_value} "
			f"AND ({_table(doctype)}.`effective_until` IS NULL "
			f"OR {_table(doctype)}.`effective_until` >= {today_value})"
		)

	parts = [
		f"{_table(doctype)}.`{field}` IN ({_escaped_locations(locations)})"
		for field in _query_location_fields(doctype)
	]
	if doctype == "Fueling Transaction":
		parts.append(
			"EXISTS (SELECT 1 FROM `tabFuel Order` fo "
			f"WHERE fo.name = {_table(doctype)}.`fuel_order` "
			f"AND fo.assigned_location_snapshot IN ({_escaped_locations(locations)}))"
		)

	for field in ASSET_LINK_FIELDS.get(doctype, ()):
		if field in _meta_fieldnames(doctype) and doctype not in {"Fuel Order", "Fueling Transaction"}:
			parts.append(_assignment_exists_condition(f"{_table(doctype)}.`{field}`", locations))
			break

	return "(" + " OR ".join(parts) + ")" if parts else "1=0"


def get_permission_query_conditions(user=None, doctype=None):
	"""Return the reusable SQL scope used by list and report queries."""
	user = _user(user)
	if _is_unrestricted(user) or not _is_location_scoped(user) or doctype not in SCOPED_DOCTYPES:
		return ""

	locations = get_permitted_location_names(user)
	return _query_condition(doctype, locations) if locations else "1=0"


def get_report_query_conditions(doctype, user=None):
	"""Return the same location condition for Query/Script Report SQL."""
	return get_permission_query_conditions(user=user, doctype=doctype)


def has_permission(doc, ptype=None, user=None, debug=False):
	"""Deny direct, print, report, and action access outside the location scope."""
	user = _user(user)
	if not doc or _is_unrestricted(user) or not _is_location_scoped(user):
		return True

	if doc.get("doctype") not in SCOPED_DOCTYPES:
		return True

	return bool(_document_location_names(doc) & get_permitted_location_names(user))
