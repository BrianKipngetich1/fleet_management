frappe.query_reports["Fueling Summary"] = {
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
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (data?.row_type === __("Monthly total")) {
			return `<strong>${formatted}</strong>`;
		}
		const color = {
			Green: "34, 197, 94",
			Red: "239, 68, 68",
		}[data?.warning_status];
		if (data?.row_type === __("Fueling transaction") && data.warning_reasons && color) {
			return `<div style="box-sizing:border-box;height:100%;margin:-8px;padding:8px;background:linear-gradient(90deg,rgba(${color},0.22),rgba(${color},0.06))">${formatted}</div>`;
		}
		return formatted;
	},
};
