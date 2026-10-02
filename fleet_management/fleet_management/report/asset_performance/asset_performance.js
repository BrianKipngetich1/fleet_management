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
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname !== "efficiency_rating" || !data?.efficiency_rating) {
			return formatted;
		}
		const colors = {
			[__("Green")]: "green",
			[__("Orange")]: "orange",
			[__("Red")]: "red",
		};
		const color = colors[data.efficiency_rating];
		return color ? `<span class="indicator-pill ${color}">${formatted}</span>` : formatted;
	},
};
