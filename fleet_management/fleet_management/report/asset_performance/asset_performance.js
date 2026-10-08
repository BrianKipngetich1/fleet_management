let efficiencyChartData;

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
			description: __("Leave both dates blank to view all retained history."),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Link",
			options: "Fleet Location",
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
		if (data?.record_type === __("Monthly total")) {
			return `<strong>${formatted}</strong>`;
		}
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
	get_chart_data(columns, result) {
		const monthly = result.filter((row) => row.record_type === __("Monthly total"));
		if (!monthly.length) return;

		const is_vehicle = monthly.some((row) => row.asset_type === "Vehicle");
		const valid_efficiency_months = monthly.filter(
			(row) => row.efficiency_km_per_litre != null
		);
		efficiencyChartData =
			is_vehicle && valid_efficiency_months.length
				? {
						labels: valid_efficiency_months.map((row) => row.month),
						values: valid_efficiency_months.map((row) => row.efficiency_km_per_litre),
				  }
				: null;

		return {
			data: {
				labels: monthly.map((row) => row.month),
				datasets: [
					{
						name: __("Delivered Litres"),
						values: monthly.map((row) => row.delivered_litres || 0),
					},
				],
			},
			type: "line",
		};
	},
	after_datatable_render() {
		if (!efficiencyChartData) return;

		const report = frappe.query_report;
		const wrapper = $("<div class='asset-efficiency-chart'>").appendTo(report.$chart);
		$("<h4 class='text-muted'>")
			.text(__("Monthly Vehicle Efficiency (km/L)"))
			.appendTo(wrapper);
		const chart = $("<div>").appendTo(wrapper);
		new frappe.Chart(chart[0], {
			data: {
				labels: efficiencyChartData.labels,
				datasets: [{ name: __("Efficiency (km/L)"), values: efficiencyChartData.values }],
			},
			type: "line",
			height: 280,
			colors: ["#2563eb"],
		});
	},
};
