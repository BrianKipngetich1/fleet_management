frappe.ui.form.on("Fuel Order", {
	setup(frm) {
		frm.set_query("operational_location", () => {
			const permissions = frappe.defaults.get_user_permissions()["Fleet Location"] || [];
			const locations = permissions.map((permission) => permission.doc).filter(Boolean);
			return locations.length ? { filters: { name: ["in", locations] } } : {};
		});
	},
	refresh(frm) {
		if (
			frm.is_new() ||
			frm.doc.workflow_state !== "Approved" ||
			(!frappe.user.has_role("Fleet Approver") && !frappe.user.has_role("Fleet Admin")) ||
			!frm.has_perm("write")
		) return;

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
			__("Actions"),
		);
	},
});
