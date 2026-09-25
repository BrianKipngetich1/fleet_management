"""Shared helpers for fleet_management tests."""

import frappe

PNG_CONTENT = bytes.fromhex("89504e470d0a1a0a0000000d49484452")
PDF_CONTENT = b"%PDF-1.4\n"


def make_photo(extension="png", private=True):
	"""A File that stands in for an uploaded photo; PNG content by default."""
	content = {"png": PNG_CONTENT, "pdf": PDF_CONTENT}.get(extension, b"plain text")
	content += frappe.generate_hash(length=8).encode()
	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"photo-{frappe.generate_hash(length=8)}.{extension}",
			"content": content,
			"is_private": int(private),
		}
	).insert(ignore_permissions=True)


def attach_request_photos(order, extension="png", private=True):
	"""Attach a meter photo, and a gauge photo for a vehicle, to a saved draft Fuel Order."""
	order.meter_photo = make_photo(extension, private).file_url
	if order.asset_type == "Vehicle":
		order.gauge_photo = make_photo(extension, private).file_url
	order.save()
	return order
