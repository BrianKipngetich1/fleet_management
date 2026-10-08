"""Append-only Fuel Order history events and their permission-checked reader."""

import json
import re
from hashlib import sha256

import frappe
from frappe.utils import now_datetime

HISTORY_EVENT_DOCTYPE = "Fuel Order History Event"
SIGNAL_HISTORY_EVENT_TYPES = ("Signal Issue", "Signal Resolved")
CANCELLABLE_DOCTYPES = frozenset({"Fuel Order", "Fueling Transaction"})
ORDER_EVIDENCE_FIELDS = ("meter_photo", "gauge_photo")
TRANSACTION_EVIDENCE_FIELDS = ("signed_invoice", "signed_order")
ORDER_SOURCE_FIELDS = (
	"asset",
	"request_datetime",
	"request_meter_reading",
	"request_gauge_percent",
	"previous_entry_source",
	"previous_meter_reading",
	"previous_entry_date",
	"asset_tank_capacity_snapshot",
	"asset_target_km_per_litre_snapshot",
	"quantity_authorization",
	"authorized_quantity_litres",
	"partial_authorization_reason",
	"signal",
	"signal_reasons",
	"signal_details_json",
	"workflow_state",
	"send_up_explanation",
	"decision_action",
	"decision_reason",
	"decision_reason_by",
	"submitted_by",
	"submitted_on",
	"approved_by",
	"approved_on",
	"rejected_by",
	"rejected_on",
	"valid_until",
	"slip_revision",
	"printed_slip_revision",
)
TRANSACTION_SOURCE_FIELDS = (
	"fuel_order",
	"fuel_order_slip_revision",
	"asset",
	"actual_station",
	"fuel_type",
	"actual_fueling_datetime",
	"fueling_time_source",
	"fueling_time_explanation",
	"vehicle_odometer",
	"hour_meter",
	"invoice_litres",
	"full_tank_confirmed",
	"invoice_number",
	"cu_number",
	"attendant_name",
	"submitted_by",
	"submitted_on",
	"docstatus",
)


def _json(value):
	return json.dumps(value, default=str, separators=(",", ":"))


def _snapshot(doc, fieldnames):
	return {fieldname: doc.get(fieldname) for fieldname in fieldnames}


def _evidence_references(doc, fieldnames):
	references = []
	for fieldname in fieldnames:
		url = doc.get(fieldname)
		if not url:
			continue
		file_doc = frappe.db.get_value(
			"File",
			{
				"file_url": url.split("?", 1)[0],
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"attached_to_field": fieldname,
				"is_folder": 0,
			},
			["name", "file_name", "file_url", "is_private"],
			as_dict=True,
		)
		references.append(
			{
				"fieldname": fieldname,
				"file": file_doc.name if file_doc else None,
				"file_name": file_doc.file_name if file_doc else None,
				"file_url": file_doc.file_url if file_doc else url,
				"is_private": bool(file_doc.is_private) if file_doc else None,
			}
		)
	return references


def capture_order_facts(order):
	facts = _snapshot(order, ORDER_SOURCE_FIELDS)
	if facts.get("signal_details_json"):
		try:
			facts["signal_details"] = json.loads(facts["signal_details_json"])
		except (TypeError, ValueError):
			facts["signal_details"] = facts["signal_details_json"]
	return facts


def capture_transaction_facts(transaction):
	return _snapshot(transaction, TRANSACTION_SOURCE_FIELDS)


def capture_evidence_references(doc):
	fields = ORDER_EVIDENCE_FIELDS if doc.doctype == "Fuel Order" else TRANSACTION_EVIDENCE_FIELDS
	return _evidence_references(doc, fields)


def record_history_event(
	fuel_order,
	event_type,
	summary,
	*,
	reason=None,
	fueling_transaction=None,
	source_facts=None,
	evidence_references=None,
	issue_key=None,
	related_event=None,
	slip_revision=None,
):
	"""Insert a server-stamped history record; events cannot be edited or removed."""
	event = frappe.get_doc(
		{
			"doctype": HISTORY_EVENT_DOCTYPE,
			"fuel_order": fuel_order,
			"fueling_transaction": fueling_transaction,
			"event_type": event_type,
			"summary": str(summary or "")[:140],
			"reason": reason,
			"issue_key": issue_key,
			"related_event": related_event,
			"slip_revision": slip_revision,
			"source_facts_json": _json(source_facts or {}),
			"evidence_references_json": _json(evidence_references or []),
		}
	)
	event.flags.from_history_service = True
	event.insert(ignore_permissions=True)
	return event.name


def _read_source_facts(event):
	try:
		value = json.loads(event.source_facts_json or "{}")
	except (TypeError, ValueError):
		return {}
	return value if isinstance(value, dict) else {}


def latest_signal_history_event(fuel_order):
	"""Return the newest issue or resolution event for an order, if any."""
	events = frappe.get_all(
		HISTORY_EVENT_DOCTYPE,
		filters={"fuel_order": fuel_order, "event_type": ["in", SIGNAL_HISTORY_EVENT_TYPES]},
		fields=["name", "event_type", "issue_key", "related_event", "source_facts_json"],
		order_by="event_datetime desc, creation desc",
		limit=1,
	)
	return events[0] if events else None


def _issue_fingerprint(signal_result):
	"""Fingerprint the active explanations and their displayed source facts.

	Elapsed time naturally changes between saves. That alone does not make a new
	issue snapshot while the same early-fueling issue remains open.
	"""
	reasons = []
	has_timing_reason = False
	for reason in signal_result.get("reasons") or []:
		text = str(reason.get("text") or "")
		if text.startswith("Too soon since the last fueling:"):
			has_timing_reason = True
			text = re.sub(
				r"^(Too soon since the last fueling: )[^;]+",
				r"\1elapsed time below the configured minimum",
				text,
			)
		details = [
			detail
			for detail in (reason.get("details") or [])
			if not str(detail).startswith("Hours since last fueling:")
		]
		reasons.append({"text": text, "details": details})

	inputs = signal_result.get("signal_inputs") or {}
	captured = {"signal": signal_result.get("signal"), "reasons": reasons}
	if has_timing_reason:
		captured["last_fueling"] = inputs.get("last_fueling")
		captured["minimum_hours"] = (inputs.get("limits") or {}).get("min_hours_between_fuelings")
	encoded = _json(captured).encode()
	return sha256(encoded).hexdigest()


def record_signal_issue_state(order):
	"""Append a changed red issue snapshot or the resolution of its open issue."""
	if not order.name:
		return None
	try:
		signal_result = json.loads(order.signal_details_json or "{}")
	except (TypeError, ValueError):
		return None
	if not isinstance(signal_result, dict) or signal_result.get("status") == "waiting":
		return None

	previous = latest_signal_history_event(order.name)
	if signal_result.get("signal") == "Red":
		fingerprint = _issue_fingerprint(signal_result)
		previous_facts = _read_source_facts(previous) if previous else {}
		if (
			previous
			and previous.event_type == "Signal Issue"
			and previous_facts.get("issue_fingerprint") == fingerprint
		):
			return previous.name

		issue_key = (
			previous.issue_key
			if previous and previous.event_type == "Signal Issue" and previous.issue_key
			else frappe.generate_hash(length=20)
		)
		return record_history_event(
			order.name,
			"Signal Issue",
			"Saved signal reports review issues.",
			issue_key=issue_key,
			related_event=previous.name if previous else None,
			source_facts={
				"issue_fingerprint": fingerprint,
				"signal_result": signal_result,
				"order": capture_order_facts(order),
			},
			evidence_references=capture_evidence_references(order),
		)

	if signal_result.get("signal") == "Green" and previous and previous.event_type == "Signal Issue":
		previous_facts = _read_source_facts(previous)
		return record_history_event(
			order.name,
			"Signal Resolved",
			"A later saved signal cleared the open issue.",
			issue_key=previous.issue_key,
			related_event=previous.name,
			source_facts={
				"resolved_issue_fingerprint": previous_facts.get("issue_fingerprint"),
				"resolved_issue_event": previous.name,
				"signal_result": signal_result,
				"order": capture_order_facts(order),
			},
			evidence_references=capture_evidence_references(order),
		)
	return None


def _cancel_reason_cache_key(doctype, name, user=None):
	user = user or frappe.session.user
	digest = sha256(f"{user}\0{doctype}\0{name}".encode()).hexdigest()
	return f"fuel-order-cancel-reason:{digest}"


@frappe.whitelist(methods=["POST"])
def stage_cancel_reason(doctype, name, reason):
	"""Keep a short-lived reason for the next native cancel request."""
	if doctype not in CANCELLABLE_DOCTYPES:
		frappe.throw(frappe._("This record cannot be cancelled from this action."), frappe.ValidationError)
	reason = str(reason or "").strip()
	if not reason:
		frappe.throw(frappe._("A written cancellation reason is required."), frappe.ValidationError)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("cancel")
	frappe.cache().set_value(_cancel_reason_cache_key(doctype, name), reason, expires_in_sec=300, shared=True)
	return {"staged": True}


def take_cancel_reason(doctype, name):
	key = _cancel_reason_cache_key(doctype, name)
	reason = frappe.cache().get_value(key, shared=True, use_local_cache=False)
	if isinstance(reason, bytes):
		reason = reason.decode()
	reason = str(reason or "").strip()
	if not reason:
		frappe.throw(
			frappe._("A written cancellation reason is required before this record can be cancelled."),
			frappe.ValidationError,
		)
	return reason


def clear_cancel_reason(doctype, name):
	frappe.cache().delete_value(_cancel_reason_cache_key(doctype, name), shared=True)


@frappe.whitelist(methods=["POST"])
def get_order_history(name):
	"""Return events only after checking the linked order's ordinary read permission."""
	order = frappe.get_doc("Fuel Order", name)
	order.check_permission("read")
	events = frappe.get_all(
		HISTORY_EVENT_DOCTYPE,
		filters={"fuel_order": name},
		fields=[
			"name",
			"event_type",
			"event_datetime",
			"actor",
			"summary",
			"reason",
			"fueling_transaction",
			"issue_key",
			"related_event",
			"slip_revision",
			"source_facts_json",
			"evidence_references_json",
		],
		order_by="event_datetime asc, creation asc",
	)
	return events
