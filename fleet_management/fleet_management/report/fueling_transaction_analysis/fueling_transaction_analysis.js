frappe.query_reports["Fueling Transaction Analysis"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "asset", label: __("Asset"), fieldtype: "Link", options: "Fleet Asset" },
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Fleet Location" },
		{ fieldname: "fuel_type", label: __("Fuel Type"), fieldtype: "Link", options: "Fuel Type" },
		{ fieldname: "station", label: __("Station"), fieldtype: "Link", options: "Fuel Station" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname !== "variance_status" || !value) {
			return default_formatter(value, row, column, data);
		}

		const colors = {
			"Within baseline": "green",
			"Above baseline (0–15%)": "orange",
			"Overrun (>15%)": "red",
			"No comparison available": "gray",
		};
		const formatted = default_formatter(value, row, column, data);
		return `<span class="indicator-pill ${colors[value] || "gray"}">${formatted}</span>`;
	},
};
