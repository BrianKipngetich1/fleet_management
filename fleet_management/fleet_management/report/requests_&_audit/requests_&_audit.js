frappe.query_reports["Requests & Audit"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Link",
			options: "Fleet Location",
		},
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Fleet Asset",
		},
		{
			fieldname: "fuel_type",
			label: __("Fuel Type"),
			fieldtype: "Link",
			options: "Fuel Type",
		},
		{
			fieldname: "station",
			label: __("Station"),
			fieldtype: "Link",
			options: "Fuel Station",
		},
	],
};
