function set_meter_label(frm) {
	const label =
		frm.doc.asset_type === "Vehicle"
			? __("Odometer")
			: frm.doc.asset_type === "Generator"
				? __("Hour Meter")
				: __("Meter Reading");
	frm.set_df_property("request_meter_reading", "label", label);
}

function escape_panel_text(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function summary_value(value, unit) {
	if (value === null || value === undefined || value === "") return __("Not available");
	const shown =
		typeof value === "number" && Number.isFinite(value)
			? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
			: String(value);
	return unit ? shown + " " + unit : shown;
}

function summary_row(label, value, unit) {
	return (
		'<div class="fuel-order-summary-row"><span class="text-muted">' +
		escape_panel_text(label) +
		'</span><strong>' +
		escape_panel_text(summary_value(value, unit)) +
		'</strong></div>'
	);
}

function summary_card(title, rows) {
	return (
		'<div class="fuel-order-summary-card"><div class="fuel-order-summary-title">' +
		escape_panel_text(title) +
		'</div>' +
		rows.map((row) => summary_row(row[0], row[1], row[2])).join("") +
		'</div>'
	);
}

function render_vehicle_summary(frm) {
	const section = frm.layout?.sections_dict?.section_break_vehicle_order?.wrapper;
	const page = frm.layout?.page;
	if (!section || !page) return;

	let summary = page.children(".fuel-order-summary-block");
	if (!summary.length) {
		summary = $('<div class="fuel-order-summary-block"></div>').insertAfter(section);
	}
	if (!frm.doc.asset) {
		summary.html(
			'<div class="text-muted">' +
				escape_panel_text(
					__("Select an asset to see its vehicle, assignment, previous-entry, and estimate summary.")
				) +
			'</div>'
		);
		return;
	}

	const vehicle = frm.doc.asset_type === "Vehicle";
	const requestSummary = frm._fuel_order_request_summary || {};
	const meter_unit = vehicle ? "km" : frm.doc.asset_type === "Generator" ? "h" : "";
	const vehicle_rows = [
		[__("Asset"), frm.doc.asset],
		[__("Make and model"), frm.doc.vehicle_model],
		[__("Asset type"), frm.doc.asset_type],
		[__("Fuel type"), frm.doc.fuel_type],
	];
	if (vehicle) {
		vehicle_rows.push(
			[__("Tank size"), frm.doc.asset_tank_capacity_snapshot, "L"],
			[__("Vehicle target fuel economy"), frm.doc.asset_target_km_per_litre_snapshot, "km/L"]
		);
	}

	const assignment_rows = [
		[__("Selected driver"), frm.doc.driver],
		[__("Assigned custodian"), frm.doc.custodian],
		[__("Home location"), frm.doc.assigned_location_snapshot],
	];
	const noPreviousEntry = frm.doc.previous_entry_source === "none";
	const previous_date = !noPreviousEntry && frm.doc.previous_entry_date
		? frappe.datetime.str_to_user(frm.doc.previous_entry_date)
		: null;
	const history_rows = [
		[
			__("Previous entry"),
			noPreviousEntry
				? __("No previous entry")
				: frm.doc.previous_entry_source || __("Not recorded"),
		],
		[
			vehicle ? __("Previous Odometer") : __("Previous Hour Meter"),
			noPreviousEntry ? null : frm.doc.previous_meter_reading,
			meter_unit,
		],
		[__("Recorded on"), previous_date],
	];
	if (vehicle) {
		history_rows.push([__("Estimated litres to fill"), frm.doc.estimated_litres, "L"]);
		if (requestSummary.recent_observed_average_km_per_litre != null) {
			history_rows.push([
				__("Recent observed full-to-full average"),
				requestSummary.recent_observed_average_km_per_litre,
				"km/L",
			]);
		}
		const economySource = requestSummary.applicable_fuel_economy_source;
		const sourceLabel =
			economySource === "recent_average"
				? __("recent weighted average")
				: economySource === "vehicle_target"
					? __("vehicle target")
					: __("source not recorded");
		history_rows.push([
			`${__("Applicable fuel economy")} (${sourceLabel})`,
			requestSummary.average_km_per_litre ?? frm.doc.average_km_per_litre,
			"km/L",
		]);
	}

	const cards = [
		[__("Vehicle"), vehicle_rows],
		[__("Assignment"), assignment_rows],
		[__("Previous Entry and Estimate"), history_rows],
	];
	summary.html(
		'<div class="fuel-order-summary-heading">' +
			escape_panel_text(__("Selected Asset Summary")) +
		'</div><div class="row fuel-order-summary">' +
			cards
				.map(
					(card) =>
						'<div class="col-12 col-md-6 col-xl-4 mb-3">' +
						summary_card(card[0], card[1]) +
						'</div>'
				)
				.join("") +
			'</div>'
	);
}

function apply_fuel_order_layout(frm) {
	if (!frm.layout) return;
	frm.layout.page?.addClass("fuel-order-workspace");
	frm.layout.sections_dict?.section_break_system_details?.wrapper?.addClass(
		"fuel-order-system-details"
	);
}

function render_order_history(frm, events, error) {
	const field = frm.fields_dict.history_html;
	if (!field) return;
	if (error) {
		field.set_value('<p class="text-muted">' + escape_panel_text(error) + '</p>');
		return;
	}
	if (!events || !events.length) {
		field.set_value('<p class="text-muted">' + __("No saved history events yet.") + '</p>');
		return;
	}
	const events_by_name = new Map(events.map((event) => [event.name, event]));
	const rows = events
		.map((event) => {
			const related_event = event.related_event ? events_by_name.get(event.related_event) : null;
			let facts = event.source_facts_json || "";
			let evidence = [];
			try {
				facts = JSON.stringify(JSON.parse(facts), null, 2);
			} catch (error) {
				// Older events can retain a plain source value.
			}
			try {
				evidence = JSON.parse(event.evidence_references_json || "[]");
			} catch (error) {
				evidence = [];
			}
			const evidenceHtml = evidence
				.map((reference) => {
					const label = escape_panel_text(reference.file_name || reference.fieldname || reference.file);
					const url = String(reference.file_url || "");
					return url.startsWith("/private/files/")
						? '<li><a href="' + escape_panel_text(url) + '">' + label + '</a></li>'
						: '<li>' + label + '</li>';
				})
				.join("");
			const capturedFacts = facts
				? '<details><summary>' + __("Captured facts") + '</summary><pre>' + escape_panel_text(facts) + '</pre></details>'
				: "";
			const evidenceList = evidenceHtml
				? '<p>' + __("Evidence") + '</p><ul>' + evidenceHtml + '</ul>'
				: "";
			const relatedEventHtml = related_event
				? '<p class="text-muted">' +
					__("Related to:") +
					' ' +
					escape_panel_text(related_event.event_type) +
					' — ' +
					escape_panel_text(related_event.summary) +
					'</p>'
				: "";
			return (
				'<li class="fuel-order-history-event"><strong>' +
				escape_panel_text(event.event_type) +
				':</strong> ' +
				escape_panel_text(event.summary) +
				'<p class="text-muted">' +
				escape_panel_text(event.actor) +
				' · ' +
				escape_panel_text(event.event_datetime) +
				'</p>' +
				(event.reason
					? '<p><strong>' + __("Reason or explanation:") + '</strong> ' + escape_panel_text(event.reason) + '</p>'
					: "") +
				(event.fueling_transaction
					? '<p>' + __("Fueling Transaction:") + ' ' + escape_panel_text(event.fueling_transaction) + '</p>'
					: "") +
				relatedEventHtml +
				capturedFacts +
				evidenceList +
				'</li>'
			);
		})
		.join("");
	field.set_value('<ol class="fuel-order-history">' + rows + '</ol>');
}

function load_order_history(frm) {
	if (frm.is_new() || !frm.doc.name) {
		render_order_history(frm, []);
		return;
	}
	frappe.call({
		method: "fleet_management.history.get_order_history",
		args: { name: frm.doc.name },
	})
		.then(({ message }) => render_order_history(frm, message || []))
		.catch((error) =>
			render_order_history(frm, null, error.message || __("History could not be loaded."))
		);
}

function prompt_cancel_reason(frm, doctype) {
	frappe.dom.unfreeze();
	return new Promise((resolve, reject) => {
		frappe.prompt(
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Cancellation reason"), reqd: 1 },
			({ reason }) =>
				frappe
					.call({
						method: "fleet_management.history.stage_cancel_reason",
						args: { doctype, name: frm.doc.name, reason },
					})
					.then(resolve, reject),
			__("Cancel document"),
			__("Continue")
		);
	});
}

function render_signal_panel(frm, result) {
	const field = frm.fields_dict.signal_panel_html;
	if (!field) return;

	if (result.status === "waiting") {
		const readings = (result.waiting_for || []).map(escape_panel_text).join(", ");
		field.set_value(`
			<div class="alert alert-warning" role="status">
				<strong>${__("Signal preview waiting")}</strong>
				<p>${__("Enter the following before the signal can be calculated:")} ${readings}</p>
				<p>${escape_panel_text(result.next_action)}</p>
			</div>
		`);
		return;
	}

	if (result.status === "unavailable") {
		field.set_value(`
			<div class="alert alert-warning" role="status">
				<strong>${__("Signal preview unavailable")}</strong>
				<p>${escape_panel_text(result.message)}</p>
				<p>${__("This is a preview error, not a Red signal. Normal validation and permissions still apply.")}</p>
			</div>
		`);
		return;
	}

	const red = result.signal === "Red";
	const findings = (result.reasons || [])
		.map((reason) => {
			const details = (reason.details || [])
				.map((detail) => `<li>${escape_panel_text(detail)}</li>`)
				.join("");
			return `
				<li>
					<strong>${escape_panel_text(reason.text)}</strong>
					${details ? `<ul>${details}</ul>` : ""}
					<p><strong>${__("Check next:")}</strong> ${escape_panel_text(reason.next_action)}</p>
				</li>
			`;
		})
		.join("");
	const summary = red
		? `<strong>${__("Red signal — review needed")}</strong>`
		: `<strong>${__("Green signal — every check passed")}</strong>`;
	const baseline = result.signal_inputs && result.signal_inputs.mileage_baseline;
	const baselineTime = baseline && baseline.timestamp ? frappe.datetime.str_to_user(baseline.timestamp) : "";
	const baselineDetails = baseline
		? [
				`${escape_panel_text(baseline.label)} — ${escape_panel_text(baseline.reference)}`,
				`${__("Baseline Odometer:")} ${escape_panel_text(baseline.vehicle_odometer)} km`,
				baselineTime ? `${__("Baseline date and time:")} ${escape_panel_text(baselineTime)}` : "",
				baseline.fuel_order ? `${__("Fuel Order:")} ${escape_panel_text(baseline.fuel_order)}` : "",
			]
				.filter(Boolean)
				.join("; ")
		: "";
	const baselineSummary = baseline
		? `<p><strong>${__("Mileage baseline used:")}</strong> ${baselineDetails}</p>`
		: "";
	const mileageCheck = result.signal_inputs && result.signal_inputs.full_tank_mileage_check;
	let mileageSummary = "";
	if (mileageCheck && mileageCheck.status === "pass") {
		const observedAverage = mileageCheck.average_source === "recent_average";
		const average = Number(mileageCheck.average_km_per_litre);
		let economy = `${escape_panel_text(average)} km/L (${__("vehicle target")})`;
		if (observedAverage) {
			const equivalents = [
				`${(1 / average).toFixed(3)} L/km`,
				`${(100 / average).toFixed(1)} L/100 km`,
			].join("; ");
			economy = `${escape_panel_text(average)} km/L (${__("recent weighted average")}; ${__("observed full-to-full equivalents")}: ${equivalents})`;
		}
		const comparison = [
			`${__("Odometer distance travelled:")} ${escape_panel_text(mileageCheck.distance_km)} km`,
			`${__("Expected distance:")} ${escape_panel_text(Number(mileageCheck.expected_distance_km).toFixed(1))} km`,
			`${__("Estimated fuel used:")} ${escape_panel_text(mileageCheck.estimated_consumed_litres)} L`,
			`${__("Applicable fuel economy:")} ${economy}`,
			`${__("Allowed mileage margin:")} ±${escape_panel_text(mileageCheck.margin_percent)}%`,
		].join("; ");
		mileageSummary = `<p><strong>${__("Mileage comparison:")}</strong> ${comparison}.</p>`;
	}
	field.set_value(`
		<div class="alert ${red ? "alert-danger" : "alert-success"}" role="status">
			${summary}
			${baselineSummary}
			${mileageSummary}
			${findings ? `<ul>${findings}</ul>` : ""}
			<p><strong>${__("What happens next:")}</strong> ${escape_panel_text(result.next_action)}</p>
			<p>${escape_panel_text(result.note)}</p>
		</div>
	`);
}

function show_saved_signal_panel(frm) {
	if (frm.doc.signal_details_json) {
		try {
			render_signal_panel(frm, JSON.parse(frm.doc.signal_details_json));
			return;
		} catch (error) {
			// Older records do not have the structured server result yet.
		}
	}

	if (!frm.doc.signal) {
		render_signal_panel(frm, {
			status: "waiting",
			waiting_for: [__("Asset")],
			next_action: __("Choose an asset to refresh the signal preview."),
		});
		return;
	}

	render_signal_panel(frm, {
		status: "complete",
		signal: frm.doc.signal,
		reasons: (frm.doc.signal_reasons || "")
			.split("\n")
			.filter(Boolean)
			.map((text) => ({ text, details: [], next_action: "Review the saved order." })),
		next_action:
			frm.doc.signal === "Red"
				? __("A Fleet User may reject this order or send it to a permitted Fleet Approver with an explanation.")
				: __("A Fleet User may approve this green order."),
		note: __("A signal is review information; evidence, permissions, and required-field checks still apply."),
	});
}

function update_request_summary(frm, result) {
	const summary = result && result.request_summary;
	if (!summary) return;
	frm._fuel_order_request_summary = summary;
	frm.set_value({
		estimated_litres: summary.estimated_litres ?? null,
		average_km_per_litre: summary.average_km_per_litre ?? null,
	}).then(() => render_vehicle_summary(frm));
}

function queue_signal_preview(frm) {
	window.clearTimeout(frm._signalPreviewTimer);
	const requestId = (frm._signalPreviewId || 0) + 1;
	frm._signalPreviewId = requestId;

	if (frm.doc.docstatus === 1 || !frm.has_perm("write")) {
		show_saved_signal_panel(frm);
		return;
	}

	render_signal_panel(frm, {
		status: "waiting",
		waiting_for: [__("Updated readings")],
		next_action: __("Refreshing the server-calculated signal preview…"),
	});

	frm._signalPreviewTimer = window.setTimeout(async () => {
		const args = {
			name: frm.is_new() ? undefined : frm.doc.name,
			asset: frm.doc.asset || null,
			request_meter_reading: frm.doc.request_meter_reading ?? null,
			request_gauge_percent: frm.doc.request_gauge_percent ?? null,
			quantity_authorization: frm.doc.quantity_authorization || "Full",
			authorized_quantity_litres: frm.doc.authorized_quantity_litres ?? null,
			operational_location: frm.doc.operational_location || null,
			driver: frm.doc.driver || null,
		};
		try {
			const { message } = await frappe.call({
				method: "fleet_management.fleet_management.doctype.fuel_order.fuel_order.preview_signal",
				type: "POST",
				args,
			});
			if (requestId === frm._signalPreviewId) {
				update_request_summary(frm, message);
				render_signal_panel(frm, message);
			}
		} catch (error) {
			if (requestId !== frm._signalPreviewId) return;
			render_signal_panel(frm, {
				status: "unavailable",
				message: error.message || __("The server could not calculate a preview."),
			});
		}
	}, 200);
}

async function clear_asset_specific_values(frm) {
	frm._fuel_order_request_summary = null;
	await frm.set_value({
		asset_type: null,
		vehicle_model: null,
		fuel_type: null,
		custodian: null,
		assigned_location_snapshot: null,
		asset_tank_capacity_snapshot: null,
		asset_target_km_per_litre_snapshot: null,
		previous_entry_source: null,
		previous_meter_reading: null,
		previous_entry_date: null,
		estimated_litres: null,
		average_km_per_litre: null,
		request_meter_reading: null,
		request_gauge_percent: null,
		meter_photo: null,
		gauge_photo: null,
		driver: null,
		actual_requester: null,
		operational_location: null,
		planned_station: null,
	});
	render_vehicle_summary(frm);
	set_meter_label(frm);
}

function queue_asset_specific_clear(frm) {
	const previous = frm._fuel_order_asset_clear || Promise.resolve();
	const current = previous.catch(() => {}).then(() => clear_asset_specific_values(frm));
	frm._fuel_order_asset_clear = current;
	return current;
}

frappe.ui.form.on("Fuel Order", {
	setup(frm) {
		frm.set_query("operational_location", () => {
			const permissions = frappe.defaults.get_user_permissions()["Fleet Location"] || [];
			const locations = permissions.map((permission) => permission.doc).filter(Boolean);
			return locations.length ? { filters: { name: ["in", locations] } } : {};
		});
		frm.set_query("planned_station", () => ({
			filters: {
				operational_location: frm.doc.operational_location,
				active: 1,
				approved: 1,
			},
		}));
	},
	operational_location(frm) {
		if (frm.doc.planned_station) frm.set_value("planned_station", null);
		queue_signal_preview(frm);
	},
	async asset(frm) {
		const requestId = (frm._fuel_order_asset_request_id || 0) + 1;
		frm._fuel_order_asset_request_id = requestId;
		if (!frm.doc.asset) {
			await queue_asset_specific_clear(frm);
			if (requestId !== frm._fuel_order_asset_request_id) return;
			queue_signal_preview(frm);
			return;
		}
		await queue_asset_specific_clear(frm);
		if (requestId !== frm._fuel_order_asset_request_id || !frm.doc.asset) return;
		const selectedAsset = frm.doc.asset;
		try {
			const { message: facts } = await frappe.call({
				method: "fleet_management.fleet_management.doctype.fuel_order.fuel_order.get_request_facts",
				args: { asset: selectedAsset },
			});
			if (
				!facts ||
				requestId !== frm._fuel_order_asset_request_id ||
				frm.doc.asset !== selectedAsset
			)
				return;
			// The server fills review facts; it recomputes them again on save and preview.
			await frm.set_value({
				asset_type: facts.asset_type,
				vehicle_model: facts.vehicle_model,
				fuel_type: facts.fuel_type,
				custodian: facts.custodian,
				assigned_location_snapshot: facts.assigned_location_snapshot,
				asset_tank_capacity_snapshot: facts.asset_tank_capacity_snapshot,
				asset_target_km_per_litre_snapshot: facts.asset_target_km_per_litre_snapshot,
				previous_entry_source: facts.previous_entry_source,
				previous_meter_reading: facts.previous_meter_reading,
				previous_entry_date: facts.previous_entry_date,
			});
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			await frm.set_value({
				driver: facts.custodian || null,
				actual_requester: facts.custodian || null,
			});
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			if (facts.assigned_location_snapshot) {
				await frm.set_value("operational_location", facts.assigned_location_snapshot);
			}
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			if (facts.suggested_station) {
				await frm.set_value("planned_station", facts.suggested_station);
			}
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			if (facts.asset_type === "Generator") {
				await frm.set_value({ request_gauge_percent: null, gauge_photo: null, estimated_litres: null });
			}
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			render_vehicle_summary(frm);
			set_meter_label(frm);
			queue_signal_preview(frm);
		} catch (error) {
			if (requestId !== frm._fuel_order_asset_request_id || frm.doc.asset !== selectedAsset) return;
			render_signal_panel(frm, {
				status: "unavailable",
				message: error.message || __("The asset summary could not be loaded."),
			});
		}
	},
	request_meter_reading: queue_signal_preview,
	request_gauge_percent: queue_signal_preview,
	driver(frm) {
		render_vehicle_summary(frm);
		queue_signal_preview(frm);
	},
	quantity_authorization: queue_signal_preview,
	authorized_quantity_litres: queue_signal_preview,
	before_cancel(frm) {
		return prompt_cancel_reason(frm, "Fuel Order");
	},
	before_workflow_action(frm) {
		// The workflow reloads the order before it moves, so a reason typed into the form would be lost:
		// ask for it here and record it on the server first (spec 002 D-10, D-11).
		const action = frm.selected_workflow_action;
		const needs_reason = ["Submit for Approval", "Approve", "Reject", "Withdraw"].includes(
			action
		);
		if (!needs_reason || (action === "Approve" && frm.doc.workflow_state === "Draft")) return;
		frappe.dom.unfreeze();
		const label =
			action === "Submit for Approval" ? __("Why is this red order genuine?") : __("Reason");
		return new Promise((resolve, reject) => {
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label, reqd: 1 },
				({ reason }) =>
					frappe
						.call({
							method: "fleet_management.fleet_management.doctype.fuel_order.fuel_order.record_decision_reason",
							args: { name: frm.doc.name, action, reason },
						})
						.then(resolve, reject),
				__(action),
				__(action)
			);
		});
	},
	refresh(frm) {
		apply_fuel_order_layout(frm);
		frm._fuel_order_request_summary = null;
		if (frm.doc.signal_details_json) {
			try {
				const savedSignal = JSON.parse(frm.doc.signal_details_json);
				const savedSummary = savedSignal.request_summary || null;
				if (savedSummary) {
					savedSummary.applicable_fuel_economy_source =
						savedSummary.applicable_fuel_economy_source || savedSignal.signal_inputs?.average_source;
					if (
						savedSummary.recent_observed_average_km_per_litre == null &&
						savedSummary.applicable_fuel_economy_source === "recent_average"
					) {
						savedSummary.recent_observed_average_km_per_litre = savedSummary.average_km_per_litre;
					}
				}
				frm._fuel_order_request_summary = savedSummary;
			} catch (error) {
				// A summary from an older saved snapshot is not required to render the form.
			}
		}
		render_vehicle_summary(frm);
		set_meter_label(frm);
		show_saved_signal_panel(frm);
		load_order_history(frm);
		if (frm.doc.docstatus !== 1 && frm.has_perm("write")) queue_signal_preview(frm);

		if (
			frm.is_new() ||
			frm.doc.workflow_state !== "Approved" ||
			(!frappe.user.has_role("Fleet Approver") && !frappe.user.has_role("Fleet Admin")) ||
			!frm.has_perm("write")
		)
			return;

		frm.add_custom_button(
			__("Extend Validity"),
			() => {
				const dialog = new frappe.ui.Dialog({
					title: __("Extend Fuel Order Validity"),
					fields: [
						{
							fieldname: "new_valid_until",
							fieldtype: "Datetime",
							label: __("New Valid Until"),
							reqd: 1,
						},
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Reason"),
							reqd: 1,
						},
					],
					primary_action_label: __("Extend"),
					primary_action(values) {
						frm.call("extend_validity", values).then(() => {
							dialog.hide();
							frm.reload_doc();
						});
					},
				});
				dialog.show();
			},
			__("Actions")
		);
	},
});


frappe.ui.form.on("Fueling Transaction", {
	before_cancel(frm) {
		return prompt_cancel_reason(frm, "Fueling Transaction");
	},
});
