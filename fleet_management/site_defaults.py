import frappe

# Every site running this app shows and accepts dates as day/month/year. The value is one of
# Frappe's own System Settings date formats; the setup wizard overwrites it from the chosen
# country, so it is re-asserted after install, after the wizard, and after every migrate.
DATE_FORMAT = "dd/mm/yyyy"


def ensure_date_format(*args, **kwargs):
	settings = frappe.get_single("System Settings")
	if settings.date_format == DATE_FORMAT:
		return
	if not frappe.is_setup_complete():
		# A fresh install has no language or time zone until the setup wizard runs, so a full save
		# fails validation. Write the value directly; the wizard hook re-asserts it afterwards.
		frappe.db.set_single_value("System Settings", "date_format", DATE_FORMAT)
		frappe.db.set_default("date_format", DATE_FORMAT)
		return
	settings.date_format = DATE_FORMAT
	# Saving (not set_single_value) also refreshes the site default that Desk boots from.
	settings.save(ignore_permissions=True)


# Station addresses (spec 002 D-13): a Fleet Admin maintains them, approvers and clerks read them.
# Frappe's Role Permission Manager API copies Address's standard rules into Custom DocPerm first.
ADDRESS_PERMISSIONS = {
	"Fleet Admin": ("read", "write", "create"),
	"Fleet Approver": ("read",),
	"Fleet User": ("read",),
}


def ensure_address_permissions(*args, **kwargs):
	from frappe.permissions import add_permission, update_permission_property

	for role, rights in ADDRESS_PERMISSIONS.items():
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists(
			"Custom DocPerm", {"parent": "Address", "role": role, "permlevel": 0, "if_owner": 0}
		):
			add_permission("Address", role)
		for right in rights:
			update_permission_property("Address", role, 0, right, 1, validate=False)
	frappe.clear_cache(doctype="Address")


# Frappe renders an address through the Address Template for its country, else the default one, and
# throws when neither exists; without ERPNext nothing creates one. Frappe's built-in layout is used.
def ensure_address_template(*args, **kwargs):
	if frappe.db.exists("Address Template", {"is_default": 1}):
		return
	country = frappe.db.get_single_value("System Settings", "country")
	if not country:
		# Before the setup wizard the site has no country; the wizard hook runs this again.
		return
	if frappe.db.exists("Address Template", country):
		frappe.db.set_value("Address Template", country, "is_default", 1)
		return
	frappe.get_doc({"doctype": "Address Template", "country": country, "is_default": 1}).insert(
		ignore_permissions=True
	)
