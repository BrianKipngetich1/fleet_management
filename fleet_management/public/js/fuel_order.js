frappe.ui.form.on("Fuel Order", {
	setup(frm) {
		frm.set_query("operational_location", () => {
			const permissions = frappe.defaults.get_user_permissions()["Fleet Location"] || [];
			const locations = permissions.map((permission) => permission.doc).filter(Boolean);
			return locations.length ? { filters: { name: ["in", locations] } } : {};
		});
		// Stations serving the order's location, including through Also Serves (spec 006 D-7).
		frm.set_query("planned_station", () => ({
			query: "fleet_management.fleet_management.doctype.fuel_station.fuel_station.station_query",
			filters: { operational_location: frm.doc.operational_location },
		}));
	},
	operational_location(frm) {
		if (frm.doc.planned_station) frm.set_value("planned_station", null);
	},
	async asset(frm) {
		if (!frm.doc.asset) return;
		const { message: facts } = await frappe.call({
			method: "fleet_management.fleet_management.doctype.fuel_order.fuel_order.get_request_facts",
			args: { asset: frm.doc.asset },
		});
		if (!facts) return;
		// What the system holds about the vehicle is shown read-only; the server sets it again on save.
		await frm.set_value({
			custodian: facts.custodian,
			assigned_location_snapshot: facts.assigned_location_snapshot,
			asset_tank_capacity_snapshot: facts.asset_tank_capacity_snapshot,
			asset_target_km_per_litre_snapshot: facts.asset_target_km_per_litre_snapshot,
			previous_entry_source: facts.previous_entry_source,
			previous_meter_reading: facts.previous_meter_reading,
			previous_entry_date: facts.previous_entry_date,
		});
		// Suggestions the user may change (spec 002 D-4). The station is set after the location,
		// whose handler clears it.
		if (facts.primary_driver) await frm.set_value("driver", facts.primary_driver);
		if (facts.assigned_location_snapshot) {
			await frm.set_value("operational_location", facts.assigned_location_snapshot);
		}
		if (facts.suggested_station)
			await frm.set_value("planned_station", facts.suggested_station);
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
		// The colour is the server's (spec 002 D-8); show it, with every reason, where the order starts.
		if (frm.doc.signal) {
			const reasons = (frm.doc.signal_reasons || "").split("\n").filter(Boolean);
			const red = frm.doc.signal === "Red";
			frm.set_intro(
				red
					? `<strong>${__("Red")}</strong><br>${reasons
							.map((r) => frappe.utils.escape_html(r))
							.join("<br>")}`
					: `<strong>${__("Green")}</strong>: ${__("every check passed.")}`,
				red ? "red" : "green"
			);
		} else {
			frm.set_intro("");
		}

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
