frappe.query_reports["Asset Performance"] = {
	filters: [
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Fleet Asset",
			reqd: 1,
		},
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
	],
};
