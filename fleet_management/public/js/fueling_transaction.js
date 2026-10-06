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
				`<div class="col-12 col-lg-6 mb-3"><div class="text-muted small">${orderContextValue(label)}</div><div>${orderContextValue(value)}</div></div>`
		)
		.join("");
	const slipLink = context.can_print_slip
		? `<div class="col-12"><a href="${orderContextValue(
				frappe.urllib.get_full_url(
					`/printview?doctype=Fuel%20Order&name=${encodeURIComponent(context.order_number)}&format=Fuel%20Order%20Approval%20Slip&no_letterhead=1`
				)
			)}" target="_blank" rel="noopener noreferrer">${orderContextValue(__("Open authorization slip"))}</a></div>`
		: "";

	return `<div class="frappe-card"><div class="row">${rows}${slipLink}</div></div>`;
}

function renderTransactionSummary(context, doc, invoiceLitres, generatorEfficiency) {
	const assetType = context?.asset_type;
	const isVehicle = assetType === "Vehicle";
	const baselineLabel = isVehicle ? __("Estimated litres") : __("Approved litres");
	const baseline = Number(isVehicle ? context?.estimated_litres : context?.authorized_quantity_litres);
	const actual = Number(invoiceLitres);
	const hasBaseline = Number.isFinite(baseline) && baseline > 0;
	const hasActual = Number.isFinite(actual) && actual > 0;
	let color = "gray";
	let status = assetType ? __("Enter invoice litres to compare") : __("No comparison available");

	if (hasBaseline && hasActual) {
		color = "green";
		status = __("Within baseline");
		const variancePercent = ((actual - baseline) / baseline) * 100;
		if (variancePercent > 0 && variancePercent <= 15) {
			color = "orange";
			status = __("Within 15% tolerance");
		} else if (variancePercent > 15) {
			color = "red";
			status = __("Overrun");
		}
	} else if (assetType && !hasBaseline) {
		status = __("No comparison available");
	}

	let efficiency = __("Efficiency is not yet available.");
	if (isVehicle && doc.docstatus === 1 && doc.full_tank_confirmed && !doc.is_efficiency_baseline) {
		const kmPerLitre = Number(doc.km_per_litre);
		if (Number.isFinite(kmPerLitre) && kmPerLitre > 0) {
			efficiency = `${kmPerLitre.toFixed(2)} km/L`;
		}
	} else if (
		assetType === "Generator" &&
		Number.isFinite(Number(generatorEfficiency)) &&
		Number(generatorEfficiency) > 0
	) {
		efficiency = `${Number(generatorEfficiency).toFixed(2)} L/hour`;
	}

	const value = (number, available) => (available ? `${number.toFixed(2)} L` : __("Not entered"));
	return `<div class="frappe-card p-3"><div class="row">
		<div class="col-sm-4 mb-3"><div class="text-muted small">${orderContextValue(baselineLabel)}</div><div>${orderContextValue(value(baseline, hasBaseline))}</div></div>
		<div class="col-sm-4 mb-3"><div class="text-muted small">${orderContextValue(__("Invoice litres"))}</div><div>${orderContextValue(value(actual, hasActual))}</div></div>
		<div class="col-sm-4 mb-3"><div class="text-muted small">${orderContextValue(__("Litre status"))}</div><div><span class="indicator-pill ${color}">${orderContextValue(status)}</span></div></div>
		<div class="col-12"><div class="text-muted small">${orderContextValue(__("Efficiency"))}</div><div>${orderContextValue(efficiency)}</div></div>
	</div></div>`;
}

function updateTransactionSummary(frm, invoiceLitres = frm.doc.invoice_litres) {
	const field = frm.get_field("litre_variance_status");
	if (field) {
		field.$wrapper.html(
			renderTransactionSummary(
				frm._fuel_order_context,
				frm.doc,
				invoiceLitres,
				frm._generator_efficiency
			)
		);
	}
}

function bindLiveInvoiceInputs(frm) {
	const litresField = frm.fields_dict.invoice_litres;
	litresField?.$input
		.off(".fuelTransactionSummary")
		.on("input.fuelTransactionSummary", () => {
			updateTransactionSummary(frm, litresField.get_value());
		});

	const amountField = frm.fields_dict.pre_tax_amount;
	amountField?.$input
		.off(".fuelInvoiceAmounts")
		.on("input.fuelInvoiceAmounts", () => updateInvoiceAmounts(frm, amountField.get_value()));
}

function loadGeneratorEfficiency(frm) {
	const context = frm._fuel_order_context;
	frm._efficiency_request_id = (frm._efficiency_request_id || 0) + 1;
	if (!context || context.asset_type !== "Generator" || frm.doc.docstatus !== 1) {
		frm._generator_efficiency = null;
		updateTransactionSummary(frm);
		return;
	}

	const transactionName = frm.doc.name;
	const requestId = frm._efficiency_request_id;
	frm._generator_efficiency = null;
	updateTransactionSummary(frm);
	frappe.call({
		method: "fleet_management.fleet_management.doctype.fueling_transaction.fueling_transaction.get_generator_efficiency",
		args: { transaction_name: transactionName },
		type: "GET",
	}).then((response) => {
		if (frm.doc.name !== transactionName || frm._efficiency_request_id !== requestId) return;
		frm._generator_efficiency = response.message;
		updateTransactionSummary(frm);
	}).catch(() => {
		if (frm.doc.name !== transactionName || frm._efficiency_request_id !== requestId) return;
		frm._generator_efficiency = null;
		updateTransactionSummary(frm);
	});
}

function updateInvoiceAmounts(frm, enteredAmount = frm.doc.pre_tax_amount) {
	const preTaxAmount = flt(enteredAmount, 2);
	const taxAmount = flt(preTaxAmount * 0.08, 2);
	frm.set_value({ tax_amount: taxAmount, invoice_total: flt(preTaxAmount + taxAmount, 2) });
}

async function loadFuelOrderContext(frm, { forceDefaults = false } = {}) {
	const field = frm.get_field("approved_order_context");
	if (!field) return;
	toggleAssetMeter(frm);

	const orderName = frm.doc.fuel_order;
	if (!orderName) {
		frm._fuel_order_context = null;
		frm._generator_efficiency = null;
		field.$wrapper.empty();
		updateTransactionSummary(frm);
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
			updateTransactionSummary(frm);
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
		loadGeneratorEfficiency(frm);
	} catch {
		if (frm.doc.fuel_order !== orderName) return;
		field.$wrapper.html(
			`<div class="text-muted">${orderContextValue(__("Fuel Order details are unavailable."))}</div>`
		);
		frm._fuel_order_context = null;
		updateTransactionSummary(frm);
	}
}

function toggleAssetMeter(frm, assetType) {
	frm.toggle_display("vehicle_odometer", assetType === "Vehicle");
	frm.toggle_display("hour_meter", assetType === "Generator");
}

frappe.ui.form.on("Fueling Transaction", {
	refresh(frm) {
		bindLiveInvoiceInputs(frm);
		loadFuelOrderContext(frm);
	},
	fuel_order(frm) {
		frm._fuel_order_context = null;
		frm._generator_efficiency = null;
		updateTransactionSummary(frm);
		if (!frm.doc.fuel_order && frm.doc.docstatus === 0) {
			frm.set_value({ actual_station: null, fuel_type: null });
		}
		loadFuelOrderContext(frm, { forceDefaults: Boolean(frm.doc.fuel_order) });
	},
	invoice_litres(frm) {
		updateTransactionSummary(frm);
	},
	pre_tax_amount(frm) {
		updateInvoiceAmounts(frm);
	},
});
