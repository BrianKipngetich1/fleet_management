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
	field.set_value(`
		<div class="alert ${red ? "alert-danger" : "alert-success"}" role="status">
			${summary}
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
	frm.set_value({
		estimated_litres: summary.estimated_litres ?? null,
		average_km_per_litre: summary.average_km_per_litre ?? null,
	});
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

frappe.ui.form.on("Fuel Order", {
	setup(frm) {
		frm._selected_asset_for_form = frm.doc.asset;
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
		const assetChanged =
			frm._selected_asset_for_form && frm._selected_asset_for_form !== frm.doc.asset;
		frm._selected_asset_for_form = frm.doc.asset;
		if (!frm.doc.asset) {
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
				meter_photo: null,
				gauge_photo: null,
				request_gauge_percent: null,
			});
			set_meter_label(frm);
			queue_signal_preview(frm);
			return;
		}
		if (assetChanged) {
			await frm.set_value({
				meter_photo: null,
				gauge_photo: null,
				request_gauge_percent: null,
				estimated_litres: null,
				average_km_per_litre: null,
			});
		}
		const selectedAsset = frm.doc.asset;
		try {
			const { message: facts } = await frappe.call({
				method: "fleet_management.fleet_management.doctype.fuel_order.fuel_order.get_request_facts",
				args: { asset: selectedAsset },
			});
			if (!facts || frm.doc.asset !== selectedAsset) return;
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
			if (facts.primary_driver) await frm.set_value("driver", facts.primary_driver);
			if (facts.assigned_location_snapshot) {
				await frm.set_value("operational_location", facts.assigned_location_snapshot);
			}
			if (facts.suggested_station) {
				await frm.set_value("planned_station", facts.suggested_station);
			}
			if (facts.asset_type === "Generator") {
				await frm.set_value({ request_gauge_percent: null, gauge_photo: null, estimated_litres: null });
			}
			set_meter_label(frm);
			queue_signal_preview(frm);
		} catch (error) {
			render_signal_panel(frm, {
				status: "unavailable",
				message: error.message || __("The asset summary could not be loaded."),
			});
		}
	},
	request_meter_reading: queue_signal_preview,
	request_gauge_percent: queue_signal_preview,
	driver: queue_signal_preview,
	quantity_authorization: queue_signal_preview,
	authorized_quantity_litres: queue_signal_preview,
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
		set_meter_label(frm);
		show_saved_signal_panel(frm);
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
