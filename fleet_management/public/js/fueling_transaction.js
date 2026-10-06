function orderContextValue(value) {
	return frappe.utils.escape_html(value === null || value === undefined || value === "" ? "—" : String(value));
}

function orderContextDate(value) {
	return value ? frappe.datetime.str_to_user(value) : __("Not available");
}

function renderFuelOrderContext(context) {
	const asset = [context.asset_identifier, context.asset_type, context.vehicle_model]
		.filter(Boolean)
		.join(" · ");
	const authorization =
		context.quantity_authorization === "Full"
			? __("Full tank")
			: context.quantity_authorization === "Partial"
				? __("Partial authorization")
				: context.quantity_authorization;
	const fields = [
		[__("Fuel Order"), context.order_number],
		[__("Approval status"), context.workflow_state],
		[__("Asset"), asset],
		[__("Location"), context.location],
		[__("Authorized station"), context.station],
		[__("Fuel type"), context.fuel_type],
		[__("Quantity authorization"), authorization],
		[__("Authorized litres"), context.authorized_quantity_litres],
		[__("Estimated litres"), context.estimated_litres],
		[__("Approved on"), orderContextDate(context.approved_on)],
		[__("Valid until"), orderContextDate(context.valid_until)],
		[__("Driver"), context.driver],
		[__("Company representative"), context.company_representative],
	];
	const rows = fields
		.map(
			([label, value]) =>
				`<div class="col-sm-6 col-md-4 mb-3"><div class="text-muted small">${orderContextValue(label)}</div><div>${orderContextValue(value)}</div></div>`
		)
		.join("");

	return `<div class="frappe-card"><div class="row">${rows}</div></div>`;
}

function renderLitreVariance(context, actualValue) {
	if (!(["Vehicle", "Generator"].includes(context.asset_type))) {
		return `<span class="indicator-pill gray">${orderContextValue(__("No comparison available"))}</span>`;
	}

	const isVehicle = context.asset_type === "Vehicle";
	const baselineLabel = isVehicle ? __("Estimated litres") : __("Approved litres");
	const baseline = Number(isVehicle ? context.estimated_litres : context.authorized_quantity_litres);
	if (!Number.isFinite(baseline) || baseline <= 0) {
		return `<span class="indicator-pill gray">${orderContextValue(__("No comparison available"))}</span>`;
	}

	const actual = Number(actualValue);
	if (!Number.isFinite(actual) || actual <= 0) {
		return `<span class="indicator-pill gray">${orderContextValue(__("Enter invoice litres to compare"))}</span>`;
	}

	let color = "green";
	let label = __("Within baseline");
	const variancePercent = ((actual - baseline) / baseline) * 100;
	if (actual > baseline) {
		color = variancePercent <= 15 ? "orange" : "red";
		label = color === "orange" ? __("Within 15% tolerance") : __("Overrun");
	}
	const details = `${__("Actual")}: ${actual.toFixed(2)} L · ${baselineLabel}: ${baseline.toFixed(2)} L${
		variancePercent > 0 ? ` · ${variancePercent.toFixed(1)}% ${__("over")}` : ""
	}`;
	return `<span class="indicator-pill ${color}">${orderContextValue(label)}</span><div class="text-muted small mt-1">${orderContextValue(details)}</div>`;
}

function updateLitreVariance(frm) {
	const field = frm.get_field("litre_variance_status");
	if (!field) return;
	field.$wrapper.html(
		frm._fuel_order_context
			? renderLitreVariance(frm._fuel_order_context, frm.doc.invoice_litres)
			: ""
	);
}

async function loadFuelOrderContext(frm, { forceDefaults = false } = {}) {
	const field = frm.get_field("approved_order_context");
	if (!field) return;
	toggleAssetMeter(frm);

	const orderName = frm.doc.fuel_order;
	if (!orderName) {
		frm._fuel_order_context = null;
		field.$wrapper.empty();
		updateLitreVariance(frm);
		return;
	}

	field.$wrapper.html(`<div class="text-muted">${orderContextValue(__("Loading approved order details…"))}</div>`);
	try {
		const response = await frappe.call({
			method: "fleet_management.fleet_management.doctype.fueling_transaction.fueling_transaction.get_fuel_order_context",
			args: { fuel_order: orderName },
		});
		if (frm.doc.fuel_order !== orderName) return;
		if (!response.message) {
			frm._fuel_order_context = null;
			field.$wrapper.empty();
			updateLitreVariance(frm);
			return;
		}
		const context = response.message;
		frm._fuel_order_context = context;
		toggleAssetMeter(frm, context.asset_type);
		if (frm.doc.docstatus === 0) {
			const values = {};
			if (context.station_link && (forceDefaults || !frm.doc.actual_station)) {
				values.actual_station = context.station_link;
			}
			if (context.fuel_type_link && (forceDefaults || !frm.doc.fuel_type)) {
				values.fuel_type = context.fuel_type_link;
			}
			if (Object.keys(values).length) await frm.set_value(values);
		}
		field.$wrapper.html(renderFuelOrderContext(context));
		updateLitreVariance(frm);
	} catch {
		if (frm.doc.fuel_order !== orderName) return;
		field.$wrapper.html(
			`<div class="text-muted">${orderContextValue(__("Fuel Order details are unavailable."))}</div>`
		);
		frm._fuel_order_context = null;
		updateLitreVariance(frm);
	}
}

function toggleAssetMeter(frm, assetType) {
	frm.toggle_display("vehicle_odometer", assetType === "Vehicle");
	frm.toggle_display("hour_meter", assetType === "Generator");
}

frappe.ui.form.on("Fueling Transaction", {
	refresh(frm) {
		loadFuelOrderContext(frm);
	},
	fuel_order(frm) {
		frm._fuel_order_context = null;
		updateLitreVariance(frm);
		if (!frm.doc.fuel_order && frm.doc.docstatus === 0) {
			frm.set_value({ actual_station: null, fuel_type: null });
		}
		loadFuelOrderContext(frm, { forceDefaults: Boolean(frm.doc.fuel_order) });
	},
	invoice_litres(frm) {
		updateLitreVariance(frm);
	},
});
