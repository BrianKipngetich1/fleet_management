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
