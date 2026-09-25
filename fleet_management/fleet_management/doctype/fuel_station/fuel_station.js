frappe.ui.form.on("Fuel Station", {
	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Fuel Station" };
		frm.toggle_display("address_section", !frm.is_new());
		if (frm.is_new()) {
			frappe.contacts.clear_address_and_contact(frm);
		} else {
			frappe.contacts.render_address_and_contact(frm);
		}
	},
});
