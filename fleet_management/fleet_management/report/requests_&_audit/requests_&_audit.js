frappe.query_reports["Requests & Audit"] = {
	onload(report) {
		[
			[__("All Audit"), "All Audit"],
			[__("Approvals"), "Approvals"],
			[__("Flag Reports"), "Flag Reports"],
			[__("Discrepancy Reports"), "Discrepancy Reports"],
		].forEach(([label, section]) => {
			report.page.add_inner_button(
				label,
				() => report.set_filter_value("section", section),
				__("Sections")
			);
		});
	},
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname !== "warning_status") {
			return formatted;
		}

		const color = { Green: "green", Red: "red" }[value];
		return color ? `<span class="indicator-pill ${color}">${formatted}</span>` : formatted;
	},
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
		{
			fieldname: "section",
			label: __("Section"),
			fieldtype: "Select",
			options: [
				__("All Audit"),
				__("Approvals"),
				__("Flag Reports"),
				__("Discrepancy Reports"),
			],
			default: __("All Audit"),
		},
	],
};
