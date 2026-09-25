import json
from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, now_datetime

from fleet_management.fleet_management.doctype.fleet_asset.fleet_asset import (
	get_assignment_snapshot,
)
from fleet_management.permissions import get_permitted_location_names
from fleet_management.notifications import notify_fuel_order


APPROVAL_TRANSITION_STATES = {"Approved", "Rejected"}
AUDIT_FIELDS = (
	"submitted_by",
	"submitted_on",
	"approved_by",
	"approved_on",
	"valid_until",
	"rejected_by",
	"rejected_on",
	"reprint_required",
	"slip_revision",
	"printed_slip_revision",
	"last_slip_printed_on",
	"validity_extension_history",
)
EXTENSION_FIELDS = frozenset(
	{"valid_until", "reprint_required", "slip_revision", "validity_extension_history"}
)
EXTENSION_ROLES = frozenset({"Fleet Admin", "Fleet Approver"})
SNAPSHOT_FIELDS = (
	"assigned_location_snapshot",
	"assigned_custodian_snapshot",
	"assignment_effective_from",
	"assignment_effective_until",
	"asset_fuel_type_snapshot",
	"asset_tank_capacity_snapshot",
	"asset_target_km_per_litre_snapshot",
	"asset_tolerance_percent_snapshot",
)


class FuelOrder(Document):
	@property
	def fulfillment_status(self):
		"""Derived fulfillment condition of an approved order; never stored (spec D-6)."""
		if self.is_new() or self.docstatus != 1 or self.workflow_state != "Approved":
			return None
		if frappe.db.exists("Fueling Transaction", {"fuel_order": self.name, "docstatus": 1}):
			return "Completed"
		if self.valid_until and now_datetime() > get_datetime(self.valid_until):
			return "Expired"
		return "Awaiting Transaction"

	def on_update(self):
		previous_state = self._previous_workflow_state()
		event = {
			("Draft", "Pending Approval"): "pending_approval",
			("Pending Approval", "Approved"): "approved",
			("Pending Approval", "Rejected"): "rejected",
		}.get((previous_state, self.workflow_state))
		if event:
			notify_fuel_order(self, event)

	def before_validate(self):
		self._set_asset_assignment_snapshot()
		if self.asset and not self.fuel_type:
			self.fuel_type = frappe.db.get_value("Fleet Asset", self.asset, "fuel_type")
		if not self.quantity_authorization:
			self.quantity_authorization = "Full"
		self._set_estimated_litres()
		if self.is_new():
			self.reprint_required = 0
			self.slip_revision = self.slip_revision or 1
			self.printed_slip_revision = self.printed_slip_revision or 0
			self.validity_extension_history = "[]"

	def validate(self):
		self._validate_approval_actor()
		self._record_approval_audit()
		self._restore_audit_fields()
		self._validate_immutable_snapshots()
		self._validate_assignment_snapshot()
		self._validate_asset_fuel_type()
		self._validate_quantity_authorization()
		self._validate_request_gauge()

		for fieldname, label in (
			("actual_requester", "Actual requester"),
			("driver", "Driver"),
			("custodian", "Custodian"),
			("company_representative", "Company representative"),
		):
			self._validate_active_reference("Fleet Person", fieldname, label)

		self._validate_active_reference("Fleet Asset", "asset", "Asset")
		self._validate_asset_permission()
		self._validate_active_reference("Fleet Location", "operational_location", "Operational location")
		self._validate_active_reference("Fuel Type", "fuel_type", "Fuel type")
		self._validate_station()

	def _validate_asset_permission(self):
		if self.flags.ignore_permissions or not self.asset:
			return

		asset = frappe.get_doc("Fleet Asset", self.asset)
		if not frappe.has_permission("Fleet Asset", "read", asset):
			frappe.throw(
				frappe._("You do not have permission to use this asset."), frappe.PermissionError
			)

	def _set_asset_assignment_snapshot(self):
		if not self.asset:
			return
		# Approved orders are historical authorization records. Their assignment
		# snapshot must never follow a later master-data change.
		if self.docstatus == 1 and self.workflow_state == "Approved":
			return

		snapshot = get_assignment_snapshot(self.asset, self.request_datetime)
		if not snapshot:
			frappe.throw(
				frappe._("Asset must have exactly one effective assignment at request time."),
				frappe.ValidationError,
			)
		for fieldname, value in snapshot.items():
			self.set(fieldname, value)

	def _asset_type(self):
		return frappe.db.get_value("Fleet Asset", self.asset, "asset_type") if self.asset else None

	def _set_estimated_litres(self):
		# The request-time estimate is part of the approved snapshot; an approved
		# order keeps the value it was approved with.
		if self.docstatus == 1:
			return
		if self._asset_type() != "Vehicle" or self.request_gauge_percent in (None, ""):
			self.estimated_litres = None
			return
		gauge = min(max(int(self.request_gauge_percent), 0), 100)
		self.estimated_litres = flt(
			flt(self.asset_tank_capacity_snapshot) * (100 - gauge) / 100, 2
		)

	def _validate_request_gauge(self):
		if self._asset_type() != "Vehicle":
			if self.request_gauge_percent not in (None, "", 0):
				frappe.throw(
					frappe._("Request gauge applies to vehicles only."), frappe.ValidationError
				)
			return
		if self.request_gauge_percent in (None, ""):
			frappe.throw(
				frappe._("Request gauge is required for a vehicle Fuel Order."), frappe.ValidationError
			)
		if not 0 <= int(self.request_gauge_percent) <= 100:
			frappe.throw(
				frappe._("Request gauge must be a whole-number percent from 0 to 100."),
				frappe.ValidationError,
			)

	def _validate_assignment_snapshot(self):
		asset_type = self._asset_type()
		missing = [
			fieldname
			for fieldname in SNAPSHOT_FIELDS
			if fieldname != "assignment_effective_until"
			and (fieldname != "asset_tank_capacity_snapshot" or asset_type == "Vehicle")
			and self.get(fieldname) in (None, "")
		]
		if missing:
			frappe.throw(
				frappe._("Fuel Order assignment and asset snapshots are required."),
				frappe.ValidationError,
			)

		self._validate_active_reference(
			"Fleet Location", "assigned_location_snapshot", "Assigned location snapshot"
		)
		self._validate_active_reference(
			"Fleet Person", "assigned_custodian_snapshot", "Assigned custodian snapshot"
		)

	def _validate_asset_fuel_type(self):
		if self.asset and self.fuel_type:
			asset_fuel_type = frappe.db.get_value("Fleet Asset", self.asset, "fuel_type")
			if asset_fuel_type and self.fuel_type != asset_fuel_type:
				frappe.throw(
					frappe._("Fuel type must match the Fleet Asset master."), frappe.ValidationError
				)
		if self.asset_fuel_type_snapshot and self.fuel_type != self.asset_fuel_type_snapshot:
			frappe.throw(
				frappe._("Fuel type must match the approved asset snapshot."), frappe.ValidationError
			)

	def _validate_immutable_snapshots(self):
		previous = getattr(self, "_doc_before_save", None)
		if not previous or previous.docstatus != 1:
			return

		for fieldname in SNAPSHOT_FIELDS:
			if self.get(fieldname) != previous.get(fieldname):
				frappe.throw(
					frappe._("Approved Fuel Order snapshots cannot be changed."),
					frappe.ValidationError,
				)

	def _validate_approval_actor(self):
		previous = getattr(self, "_doc_before_save", None)
		previous_state = previous.get("workflow_state") if previous else None
		if previous_state != "Pending Approval" or self.workflow_state not in APPROVAL_TRANSITION_STATES:
			return

		roles = set(frappe.get_roles())
		if not EXTENSION_ROLES.intersection(roles):
			frappe.throw(frappe._("Only Fleet Approvers can approve or reject Fuel Orders."), frappe.PermissionError)
		if "Fleet Admin" not in roles and self.assigned_location_snapshot not in get_permitted_location_names():
			frappe.throw(
				frappe._("The approver is not assigned to the asset's effective location."),
				frappe.PermissionError,
			)

		requester_user = frappe.db.get_value("Fleet Person", previous.get("actual_requester"), "user")
		if frappe.session.user in {
			previous.get("owner"),
			previous.get("submitted_by"),
			requester_user,
		}:
			frappe.throw(frappe._("Self approval is not allowed"), frappe.ValidationError)

	def _record_approval_audit(self):
		previous_state = self._previous_workflow_state()
		if previous_state == "Draft" and self.workflow_state == "Pending Approval":
			self.submitted_by = frappe.session.user
			self.submitted_on = now_datetime()
		elif previous_state == "Pending Approval" and self.workflow_state == "Approved":
			self.approved_by = frappe.session.user
			self.approved_on = now_datetime()
			validity_days = frappe.db.get_single_value(
				"Fleet Management Settings", "default_validity_days"
			)
			if validity_days is None:
				validity_days = 3
			self.valid_until = self.approved_on + timedelta(days=int(validity_days))
		elif previous_state == "Pending Approval" and self.workflow_state == "Rejected":
			self.rejected_by = frappe.session.user
			self.rejected_on = now_datetime()

	def _restore_audit_fields(self):
		previous = getattr(self, "_doc_before_save", None)
		if not previous:
			return

		for fieldname in AUDIT_FIELDS:
			if not self._is_audit_transition(fieldname):
				self.set(fieldname, previous.get(fieldname))

	def _is_audit_transition(self, fieldname):
		if self.flags.get("validity_extension") and fieldname in EXTENSION_FIELDS:
			return True

		previous_state = self._previous_workflow_state()
		return (
			previous_state == "Draft"
			and self.workflow_state == "Pending Approval"
			and fieldname in {"submitted_by", "submitted_on"}
		) or (
			previous_state == "Pending Approval"
			and self.workflow_state == "Approved"
			and fieldname in {"approved_by", "approved_on", "valid_until"}
		) or (
			previous_state == "Pending Approval"
			and self.workflow_state == "Rejected"
			and fieldname in {"rejected_by", "rejected_on"}
		)

	@frappe.whitelist(methods=["POST"])
	def extend_validity(self, new_valid_until: str | datetime | None, reason: str | None):
		self._validate_extension_actor()

		# Reload under a row lock so the action cannot extend a stale order or race
		# a Fueling Transaction submission.
		self.flags.for_update = True
		self.reload()
		self._validate_extension_actor()

		if self.docstatus != 1 or self.workflow_state != "Approved":
			frappe.throw(
				frappe._("Only approved Fuel Orders can have their validity extended."),
				frappe.ValidationError,
			)

		reason = str(reason or "").strip()
		if not reason:
			frappe.throw(frappe._("A reason is required to extend Fuel Order validity."), frappe.ValidationError)

		try:
			current_valid_until = get_datetime(self.valid_until)
			new_valid_until = get_datetime(new_valid_until)
		except (TypeError, ValueError) as error:
			raise frappe.ValidationError(frappe._("Validity timestamps must be real datetimes.")) from error

		if not current_valid_until or not new_valid_until:
			frappe.throw(frappe._("Validity timestamps must be real datetimes."), frappe.ValidationError)
		if now_datetime() >= current_valid_until:
			frappe.throw(
				frappe._("Expired Fuel Orders cannot be extended retroactively."),
				frappe.ValidationError,
			)
		if new_valid_until <= current_valid_until:
			frappe.throw(
				frappe._("New validity must extend the existing valid-until timestamp."),
				frappe.ValidationError,
			)
		if self._has_fueling_started():
			frappe.throw(
				frappe._("Fuel Order validity cannot be extended after fueling has started."),
				frappe.ValidationError,
			)

		extended_on = now_datetime()
		extension = {
			"old_valid_until": str(current_valid_until),
			"new_valid_until": str(new_valid_until),
			"actor": frappe.session.user,
			"timestamp": str(extended_on),
			"reason": reason,
		}
		history = self._get_extension_history()
		history.append(extension)

		self.valid_until = new_valid_until
		self.slip_revision = int(self.slip_revision or 1) + 1
		self.reprint_required = 1
		self.validity_extension_history = json.dumps(history, separators=(",", ":"))
		self.flags.validity_extension = True
		self.save()
		notify_fuel_order(self, "extended")
		self.flags.validity_extension = False
		return {
			"valid_until": str(self.valid_until),
			"reprint_required": self.reprint_required,
			"extension": extension,
		}

	def _validate_extension_actor(self):
		if not EXTENSION_ROLES.intersection(frappe.get_roles()):
			frappe.throw(
				frappe._("Only Fleet Approvers and Fleet Admins can extend Fuel Order validity."),
				frappe.PermissionError,
			)
		self.check_permission("write")

	def _get_extension_history(self):
		value = self.validity_extension_history or "[]"
		if isinstance(value, str):
			try:
				value = json.loads(value)
			except (TypeError, ValueError) as error:
				raise frappe.ValidationError(frappe._("Validity extension history is invalid.")) from error

		if not isinstance(value, list):
			frappe.throw(frappe._("Validity extension history is invalid."), frappe.ValidationError)
		return value

	def _has_fueling_started(self):
		return bool(
			frappe.db.exists(
				"Fueling Transaction", {"fuel_order": self.name, "docstatus": 1}
			)
			or frappe.db.exists(
				"Fueling Transaction",
				{"fuel_order": self.name, "actual_fueling_datetime": ["is", "set"]},
			)
		)

	def _previous_workflow_state(self):
		previous = getattr(self, "_doc_before_save", None)
		return previous.get("workflow_state") if previous else None

	def _validate_active_reference(self, doctype, fieldname, label):
		name = self.get(fieldname)
		if not name:
			return

		record = frappe.db.get_value(doctype, name, ["name", "active"], as_dict=True)
		if not record or not record.active:
			frappe.throw(
				frappe._("{0} must reference an existing active record.").format(label),
				frappe.ValidationError,
			)

	def _validate_station(self):
		if not self.planned_station:
			return

		station = frappe.db.get_value(
			"Fuel Station",
			self.planned_station,
			["name", "active", "approved", "operational_location"],
			as_dict=True,
		)
		if not station or not station.active or not station.approved:
			frappe.throw(
				frappe._("Planned station must reference an existing active, approved Fuel Station."),
				frappe.ValidationError,
			)
		if self.operational_location and station.operational_location != self.operational_location:
			frappe.throw(
				frappe._("Planned station must belong to the operational location."),
				frappe.ValidationError,
			)

	def _validate_quantity_authorization(self):
		if self.quantity_authorization not in {"Full", "Partial"}:
			frappe.throw(
				frappe._("Quantity authorization must be Full or Partial."), frappe.ValidationError
			)

		if self.quantity_authorization == "Partial" and (self.authorized_quantity_litres or 0) <= 0:
			frappe.throw(
				frappe._("Partial authorization requires a positive authorized quantity in litres."),
				frappe.ValidationError,
			)

	def before_print(self, print_settings=None):
		if not ({"Fleet Admin", "Fleet Approver", "System Manager"} & set(frappe.get_roles())):
			frappe.throw(
				frappe._("Only Fleet Approvers and Fleet Admins can print Fuel Orders."),
				frappe.PermissionError,
			)
		if self.workflow_state != "Approved" or self.docstatus != 1 or not self.valid_until:
			frappe.throw(
				frappe._("Only approved Fuel Orders can be printed as approval slips."),
				frappe.PermissionError,
			)

		# Rendering the current slip is the server-side completion of a required
		# reprint. This gives transaction submission a current revision to check;
		# stale physical slips cannot satisfy an extension by themselves.
		slip_revision = int(self.slip_revision or 1)
		if int(self.printed_slip_revision or 0) != slip_revision or self.reprint_required:
			printed_on = now_datetime()
			updates = {
				"printed_slip_revision": slip_revision,
				"last_slip_printed_on": printed_on,
				"reprint_required": 0,
			}
			frappe.db.set_value(self.doctype, self.name, updates, update_modified=False)
			self.update(updates)
			# Desk/printview is a GET request, so Frappe otherwise rolls back this
			# intentional print-completion write at request end. Keep unit and
			# integration tests inside their existing transaction boundary.
			if getattr(frappe.local, "request", None):
				frappe.db.commit()
