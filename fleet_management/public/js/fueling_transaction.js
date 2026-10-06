function orderContextValue(value) {
	return frappe.utils.escape_html(value === null || value === undefined || value === "" ? "—" : String(value));
}

function orderContextDate(value) {
	return value ? frappe.datetime.str_to_user(value) : __("Not available");
}

function applyFuelingTransactionLayout(frm) {
	if (!document.getElementById("fueling-transaction-layout-styles")) {
		const style = document.createElement("style");
		style.id = "fueling-transaction-layout-styles";
		style.textContent = `
			.form-section.fueling-transaction-layout > .section-body {
				display: grid !important;
				grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
				column-gap: 24px;
			}
			.form-section.fueling-transaction-layout > .section-body > .form-column {
				width: auto !important;
				max-width: none !important;
				min-width: 0;
				padding-left: 0;
				padding-right: 0;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column > form {
				display: grid;
				grid-template-columns: repeat(6, minmax(0, 1fr));
				column-gap: 10px;
				align-items: start;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column {
				border-left: 1px solid var(--border-color);
				padding-left: 16px !important;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column .frappe-control {
				grid-column: span 3;
				min-width: 0;
				margin-bottom: 4px;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column .help-box:not(.hide) {
				display: none !important;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column .form-group {
				margin-bottom: 4px !important;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column .control-label {
				font-size: 12px;
				line-height: 1.2;
				margin-bottom: 2px !important;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column input.form-control,
			.form-section.fueling-transaction-layout .fueling-invoice-column .like-disabled-input {
				min-height: 28px !important;
				padding: 3px 6px !important;
				font-size: 12px;
				line-height: 1.25;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="actual_fueling_datetime"],
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="fueling_time_source"],
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="fueling_time_explanation"] {
				grid-column: 1 / -1;
			}
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="pre_tax_amount"],
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="tax_amount"],
			.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="invoice_total"] {
				grid-column: span 2;
			}
			.form-section.fueling-transaction-layout .fuel-order-context-grid {
				display: grid;
				grid-template-columns: repeat(2, minmax(0, 1fr));
				gap: 4px 8px;
			}
			.form-section.fueling-transaction-layout .fuel-order-context-fact {
				min-width: 0;
				padding: 2px 0;
				border-bottom: 1px solid var(--border-color);
			}
			.form-section.fueling-transaction-layout .fuel-order-context-label {
				color: var(--text-muted);
				font-size: 11px;
				line-height: 1.2;
			}
			.form-section.fueling-transaction-layout .fuel-order-context-value {
				font-size: 12px;
				line-height: 1.25;
				overflow-wrap: anywhere;
			}
			.form-section.fueling-transaction-layout .fuel-order-slip-link {
				display: block;
				margin-top: 6px;
			}
			.form-section.fueling-summary-section .fueling-summary-grid {
				display: grid;
				grid-template-columns: repeat(4, minmax(0, 1fr));
				gap: 8px;
			}
			.form-section.fueling-summary-section .fueling-summary-item {
				min-width: 0;
			}
			.form-section.fueling-summary-section .fueling-summary-label {
				color: var(--text-muted);
				font-size: 11px;
			}
			.form-section.fueling-summary-section .fueling-summary-value {
				font-size: 13px;
				line-height: 1.25;
			}
			.form-section.fueling-summary-section .frappe-control[data-fieldname="litre_variance_status"] .frappe-card {
				padding: 8px !important;
			}
			@media (max-width: 767px) {
				.form-section.fueling-transaction-layout > .section-body {
					grid-template-columns: minmax(0, 1fr);
					row-gap: 12px;
				}
				.form-section.fueling-transaction-layout .fueling-invoice-column {
					border-left: 0;
					padding-left: 0 !important;
				}
				.form-section.fueling-transaction-layout .fuel-order-context-grid {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}
				.form-section.fueling-transaction-layout .fueling-invoice-column > form {
					grid-template-columns: minmax(0, 1fr);
				}
				.form-section.fueling-transaction-layout .fueling-invoice-column .frappe-control {
					grid-column: auto;
				}
				.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="actual_fueling_datetime"],
				.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="fueling_time_source"],
				.form-section.fueling-transaction-layout .fueling-invoice-column [data-fieldname="fueling_time_explanation"] {
					grid-column: auto;
				}
				.form-section.fueling-transaction-layout .fueling-invoice-column .help-box:not(.hide) {
					display: block !important;
				}
				.form-section.fueling-summary-section .fueling-summary-grid {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}
			}
		`;
		document.head.appendChild(style);
	}

	const $layoutSection = frm.fields_dict.fuel_order?.$wrapper?.closest(".form-section");
	$layoutSection?.addClass("fueling-transaction-layout");
	const $invoiceColumn = frm.fields_dict.actual_station?.$wrapper?.closest(".form-column");
	$invoiceColumn?.addClass("fueling-invoice-column");
	[
		"actual_fueling_datetime",
		"fueling_time_source",
		"fueling_time_explanation",
		"vehicle_odometer",
		"hour_meter",
		"invoice_litres",
		"full_tank_confirmed",
		"attendant_name",
		"pre_tax_amount",
		"signed_invoice",
		"signed_order",
	].forEach((fieldname) => {
		const field = frm.fields_dict[fieldname];
		const label = field?.$wrapper?.find(".control-label");
		if (field?.df.description && label?.length) {
			label.attr("title", `${label.text().trim()}: ${field.df.description}`);
		}
	});

	const $formLayout = $layoutSection?.closest(".form-layout");
	const $summaryField = $formLayout?.find('.frappe-control[data-fieldname="litre_variance_status"]');
	const $summarySection = $formLayout?.find(
		'.form-section[data-fieldname="section_break_transaction_summary"]'
	);
	if ($summaryField?.length && $summarySection?.length) {
		const placeSummary = () => {
			let $summaryForm = $summarySection.find(".form-column form").first();
			if (!$summaryForm.length) {
				$summarySection
					.find(".section-body")
					.append('<div class="form-column col-sm-12"><form></form></div>');
				$summaryForm = $summarySection.find(".form-column form").first();
			}
			$summaryField.appendTo($summaryForm);
			$summarySection
				.insertAfter($layoutSection)
				.removeClass("empty-section")
				.addClass("visible-section fueling-summary-section");
		};
		placeSummary();
		window.requestAnimationFrame(placeSummary);
	}
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
				`<div class="fuel-order-context-fact"><div class="fuel-order-context-label">${orderContextValue(label)}</div><div class="fuel-order-context-value">${orderContextValue(value)}</div></div>`
		)
		.join("");
	const slipLink = context.can_print_slip
		? `<a class="fuel-order-slip-link" href="${orderContextValue(
				frappe.urllib.get_full_url(
					`/printview?doctype=Fuel%20Order&name=${encodeURIComponent(context.order_number)}&format=Fuel%20Order%20Approval%20Slip&no_letterhead=1`
				)
			)}" target="_blank" rel="noopener noreferrer">${orderContextValue(__("Open authorization slip"))}</a>`
		: "";

	return `<div class="frappe-card p-2"><div class="fuel-order-context-grid">${rows}</div>${slipLink}</div>`;
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
	return `<div class="frappe-card p-2"><div class="fueling-summary-grid">
		<div class="fueling-summary-item"><div class="fueling-summary-label">${orderContextValue(baselineLabel)}</div><div class="fueling-summary-value">${orderContextValue(value(baseline, hasBaseline))}</div></div>
		<div class="fueling-summary-item"><div class="fueling-summary-label">${orderContextValue(__("Invoice litres"))}</div><div class="fueling-summary-value">${orderContextValue(value(actual, hasActual))}</div></div>
		<div class="fueling-summary-item"><div class="fueling-summary-label">${orderContextValue(__("Litre status"))}</div><div class="fueling-summary-value"><span class="indicator-pill ${color}">${orderContextValue(status)}</span></div></div>
		<div class="fueling-summary-item"><div class="fueling-summary-label">${orderContextValue(__("Efficiency"))}</div><div class="fueling-summary-value">${orderContextValue(efficiency)}</div></div>
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
		?.off(".fuelTransactionSummary")
		?.on("input.fuelTransactionSummary", () => {
			updateTransactionSummary(frm, litresField.get_value());
		});

	const amountField = frm.fields_dict.pre_tax_amount;
	amountField?.$input
		?.off(".fuelInvoiceAmounts")
		?.on("input.fuelInvoiceAmounts", () => updateInvoiceAmounts(frm, amountField.get_value()));
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
		applyFuelingTransactionLayout(frm);
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
