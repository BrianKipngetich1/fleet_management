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

async function loadFuelOrderContext(frm, { forceDefaults = false } = {}) {
	const field = frm.get_field("approved_order_context");
	if (!field) return;
	toggleAssetMeter(frm);

	const orderName = frm.doc.fuel_order;
	if (!orderName) {
		field.$wrapper.empty();
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
			field.$wrapper.empty();
			return;
		}
		const context = response.message;
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
	} catch {
		if (frm.doc.fuel_order !== orderName) return;
		field.$wrapper.html(
			`<div class="text-muted">${orderContextValue(__("Fuel Order details are unavailable."))}</div>`
		);
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
		if (!frm.doc.fuel_order && frm.doc.docstatus === 0) {
			frm.set_value({ actual_station: null, fuel_type: null });
		}
		loadFuelOrderContext(frm, { forceDefaults: Boolean(frm.doc.fuel_order) });
	},
});
