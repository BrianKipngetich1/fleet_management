import frappe

# Every site running this app shows and accepts dates as day/month/year. The value is one of
# Frappe's own System Settings date formats; the setup wizard overwrites it from the chosen
# country, so it is re-asserted after install, after the wizard, and after every migrate.
DATE_FORMAT = "dd/mm/yyyy"


def ensure_date_format(*args, **kwargs):
	settings = frappe.get_single("System Settings")
	if settings.date_format == DATE_FORMAT:
		return
	settings.date_format = DATE_FORMAT
	# Saving (not set_single_value) also refreshes the site default that Desk boots from.
	settings.save(ignore_permissions=True)
