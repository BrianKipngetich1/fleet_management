"""Fixed sample data for the dedicated test site.

Run on the test site only:

    bench --site fleet_management-test.localhost execute fleet_management.sample_data.reset_and_seed

``reset_and_seed`` removes every fleet record (and the files, versions, comments, notices, and
User Permissions that belong to them), then loads the company's real fleet from
``fleet_management.master_data`` (spec 006): Kabete and Kanha, Ecoflame Limited serving both, and
15 vehicles and a generator, each held by its real holder.

Phyllis (Fleet User) enters every order, names the vehicle's holder as driver and requester, and
approves the green ones herself; red ones go to Vishal (Fleet Approver) with her explanation. Both
cover Kabete and Kanha. A test-only Kanha approver sees Kanha alone, so the checks can prove one
company's orders stay hidden from the other. There is no fuelling history until Phyllis's real
September 2026 fill-ups are copied into ``HISTORY`` (spec 006 Phase 5); history rows run through
the real document rules and are then dated back. Users are created without passwords and keep any
password already set; ``CREDENTIALS.md`` is the password inventory.
"""

from datetime import timedelta
from io import BytesIO

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, get_datetime, now_datetime

from fleet_management import master_data
from fleet_management.fleet_management.doctype.fuel_order.fuel_order import record_decision_reason

TEST_SITE = "fleet_management-test.localhost"
PRINT_FORMAT = "Fuel Order Approval Slip"

# Written reasons recorded before a workflow decision (spec 002 D-10, D-11).
SEND_UP_EXPLANATION = "Long-distance delivery run; mileage confirmed with the driver."
APPROVAL_REASON = "Explanation checked; approved."

FLEET_DOCTYPES = (
	"Fueling Transaction",
	"Fuel Order",
	"Asset Assignment",
	"Fleet Asset",
	"Vehicle Model",
	"Fuel Station",
	"Fuel Station Location",
	"Fleet Person",
	"Fleet Location",
	"Fuel Type",
)

PHYLLIS = "phyllis.test@example.com"
VISHAL = "vishal.test@example.com"
KANHA_APPROVER = "kanha.approver.test@example.com"
FLEET_ADMIN = "test.fleet.admin@example.com"
ADMIN = "Administrator"

BOTH_COMPANIES = [master_data.KABETE, master_data.KANHA]
USERS = (
	# email, first name, roles, permitted Fleet Locations
	(PHYLLIS, "Phyllis", ["Fleet User"], BOTH_COMPANIES),
	(VISHAL, "Vishal", ["Fleet Approver"], BOTH_COMPANIES),
	(KANHA_APPROVER, "Kanha Approver", ["Fleet Approver"], [master_data.KANHA]),
	(FLEET_ADMIN, "Test Fleet Admin", ["Fleet Admin"], []),  # sees every location
)
# The Fleet People who sign in on the test site.
PEOPLE_USERS = {master_data.PHYLLIS: PHYLLIS, master_data.VISHAL: VISHAL}

INVOICE_PREFIX = {master_data.ECOFLAME: "ECO"}

# Synthetic company heading (002 D-13: site data, never real values).
LETTER_HEAD = "Krystalline Salt Fuel Order Slip"
LETTER_HEAD_CONTENT = (
	'<div class="company-heading">'
	"<p><strong>KRYSTALLINE SALT LIMITED</strong><br><strong>PIN NO. P000000000T</strong></p>"
	"<p>P.O Box 00000-00100<br>NAIROBI.<br>Tel: 020-0000000<br>Email: fuel.test@example.com</p>"
	"</div>"
)

# The most a generator order may authorise, in litres (owner, 07/10/2026; spec 006 D-11).
GENERATOR_MAX_LITRES = {"KLW-Generator": 100}

# Completed fuelling history, oldest first. Each row: days ago, request meter reading (odometer km
# for vehicles, hour meter for generators), request gauge % (vehicles only), invoice litres, full
# tank (vehicles only), station. Empty until Phyllis's September 2026 fill-ups are copied in.
HISTORY = {}

ATTENDANTS = ("Brian Ouma", "Mercy Atieno", "Kevin Njoroge", "Esther Wambui")


def reset_and_seed():
	reset()
	seed()


def reset():
	"""Remove every fleet record and the framework records that belong to them."""
	_assert_test_site()
	frappe.set_user(ADMIN)

	files = frappe.get_all(
		"File",
		filters={"is_folder": 0},
		or_filters=[
			["attached_to_doctype", "in", FLEET_DOCTYPES],
			["attached_to_doctype", "is", "not set"],
		],
		pluck="name",
	)
	for name in files:
		frappe.delete_doc("File", name, force=True, ignore_permissions=True)

	for doctype, field in (
		("Version", "ref_doctype"),
		("Comment", "reference_doctype"),
		("Notification Log", "document_type"),
		("Workflow Action", "reference_doctype"),
		("Activity Log", "reference_doctype"),
		("Email Queue", "reference_doctype"),
		("ToDo", "reference_type"),
		("Deleted Document", "deleted_doctype"),
	):
		frappe.db.delete(doctype, {field: ("in", FLEET_DOCTYPES)})

	addresses = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": ("in", FLEET_DOCTYPES)},
		pluck="parent",
	)
	for name in set(addresses):
		frappe.delete_doc("Address", name, force=True, ignore_permissions=True)
	frappe.db.delete("Letter Head", {"name": LETTER_HEAD})

	frappe.db.delete("User Permission", {"allow": ("in", FLEET_DOCTYPES)})
	for doctype in FLEET_DOCTYPES:
		frappe.db.delete(doctype)
	# Restart order and transaction numbering so every reseed gives the same document names.
	frappe.db.sql("DELETE FROM `tabSeries` WHERE name LIKE 'FO-%%' OR name LIKE 'FT-%%'")

	settings = frappe.get_single("Fleet Management Settings")
	settings.update(
		{
			"default_tolerance_percent": 2,
			"orange_band_percent": 10,
			"red_band_percent": 20,
			"default_validity_days": 3,
			"print_instruction": "Do not dispense after the valid-until timestamp.",
			"transaction_entry_sla_hours": 48,
			"mileage_margin_percent": 15,
			"litres_excess_percent": 10,
			"gauge_limit_percent": 75,
			"min_hours_between_fuelings": 24,
		}
	)
	settings.save(ignore_permissions=True)
	frappe.db.commit()


def seed():
	_assert_test_site()
	frappe.set_user(ADMIN)
	if frappe.db.count("Fuel Order") or frappe.db.count("Fleet Asset"):
		frappe.throw("Fleet data already exists. Run reset_and_seed to start again from empty.")

	_seed_users()
	_seed_masters()
	_seed_location_access()
	frappe.db.commit()

	sequence = iter(range(1, 10_000))
	for asset, rows in HISTORY.items():
		for days_ago, odometer, gauge, litres, full, station in rows:
			_completed_cycle(
				asset,
				days_ago,
				odometer,
				gauge,
				litres,
				full,
				station,
				next(sequence),
				hours_ago=8 if days_ago == 0 else None,
			)
	frappe.set_user(ADMIN)
	frappe.db.commit()


def _assert_test_site():
	if frappe.local.site != TEST_SITE or not frappe.conf.allow_tests:
		frappe.throw(f"Sample data may only be loaded on {TEST_SITE}.")


def _seed_users():
	for email, first_name, roles, _locations in USERS:
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.new_doc("User")
			user.email = email
			user.send_welcome_email = 0
		user.update({"first_name": first_name, "last_name": None, "enabled": 1, "user_type": "System User"})
		user.set("roles", [{"role": role} for role in roles])
		user.save(ignore_permissions=True)


def _seed_location_access():
	for email, _first_name, _roles, locations in USERS:
		for location in locations:
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": email,
					"allow": "Fleet Location",
					"for_value": location,
					"apply_to_all_doctypes": 1,
				}
			).insert(ignore_permissions=True)


def _seed_masters():
	master_data.load(PEOPLE_USERS)
	_insert(
		"Letter Head",
		letter_head_name=LETTER_HEAD,
		source="HTML",
		content=LETTER_HEAD_CONTENT,
		is_default=1,
	)
	# Letter Head.before_insert switches a new letter head to "Image"; keep the sample one HTML-based.
	frappe.db.set_value("Letter Head", LETTER_HEAD, "source", "HTML")


def _insert(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _people(asset):
	location = _home_location(asset)
	assignment = frappe.get_all(
		"Asset Assignment",
		filters={"parent": asset, "effective_until": ("is", "not set")},
		fields=["custodian", "primary_driver"],
		limit=1,
	)[0]
	return location, assignment.custodian, assignment.primary_driver


def _home_location(asset):
	return frappe.get_all(
		"Asset Assignment",
		filters={"parent": asset, "effective_until": ("is", "not set")},
		pluck="assigned_location",
		limit=1,
	)[0]


def _actors(location):
	# Phyllis enters and Vishal signs off red orders, for Kabete and Kanha alike.
	return PHYLLIS, VISHAL


def _is_generator(asset):
	return frappe.db.get_value("Fleet Asset", asset, "asset_type") == "Generator"


def _new_order(asset, meter, gauge, station, partial_litres=None, driver=None):
	location, custodian, _usual_driver = _people(asset)
	if _is_generator(asset):
		partial_litres = GENERATOR_MAX_LITRES[asset]
	order = frappe.get_doc(
		{
			"doctype": "Fuel Order",
			"request_datetime": now_datetime(),
			"asset": asset,
			# The holder requests the fuel and drives (spec 006 D-9).
			"actual_requester": custodian,
			"driver": driver or custodian,
			"custodian": custodian,
			"company_representative": master_data.REPRESENTATIVE[location],
			"operational_location": location,
			"planned_station": station,
			"fuel_type": frappe.db.get_value("Fleet Asset", asset, "fuel_type"),
			"request_meter_reading": meter,
			"request_gauge_percent": gauge,
			"quantity_authorization": "Partial" if partial_litres else "Full",
			"authorized_quantity_litres": partial_litres,
		}
	)
	entered_by, _approver = _actors(location)
	frappe.set_user(entered_by)
	order.insert()
	# Phyllis photographs the meter and, for a vehicle, the gauge (spec 002 D-6).
	generator = _is_generator(asset)
	photos = {
		"meter_photo": _evidence(
			f"{order.name}-meter.png",
			["METER PHOTO", f"{'Hour meter' if generator else 'Odometer'} {meter}", f"Asset {asset}"],
		)
	}
	if not generator:
		photos["gauge_photo"] = _evidence(
			f"{order.name}-gauge.png", ["GAUGE PHOTO", f"Fuel gauge {gauge}%", f"Asset {asset}"]
		)
	order.update(photos)
	order.save()
	return order


def _send_up(order, explanation=SEND_UP_EXPLANATION):
	"""As the entering user, record the explanation for a red order and send it for sign-off."""
	entered_by, _approver = _actors(order.operational_location)
	frappe.set_user(entered_by)
	record_decision_reason(order.name, "Submit for Approval", explanation)
	return apply_workflow(frappe.get_doc("Fuel Order", order.name), "Submit for Approval")


def _submit_and_approve(order):
	# The colour decides the route: green is approved by whoever entered it; red is explained, sent
	# up, and approved with a written reason. The slip is printed by the user who approved.
	entered_by, approver = _actors(order.operational_location)
	order = frappe.get_doc("Fuel Order", order.name)
	if order.signal == "Green":
		frappe.set_user(entered_by)
		order = apply_workflow(order, "Approve")
	else:
		_send_up(order)
		frappe.set_user(approver)
		record_decision_reason(order.name, "Approve", APPROVAL_REASON)
		order = apply_workflow(frappe.get_doc("Fuel Order", order.name), "Approve")
	frappe.get_print("Fuel Order", order.name, print_format=PRINT_FORMAT, no_letterhead=1)
	return frappe.get_doc("Fuel Order", order.name)


def _completed_cycle(asset, days_ago, meter, gauge, litres, full, station, sequence, hours_ago=None):
	generator = _is_generator(asset)
	order = _new_order(asset, meter, gauge, station, partial_litres=None if full else litres)
	order = _submit_and_approve(order)
	entered_by, _approver = _actors(order.operational_location)

	frappe.set_user(entered_by)
	transaction = frappe.get_doc({"doctype": "Fueling Transaction", "fuel_order": order.name}).insert()
	invoice_number = f"{INVOICE_PREFIX[station]}-{sequence:06d}"
	transaction.update(
		{
			"actual_station": station,
			"fuel_type": order.fuel_type,
			"invoice_number": invoice_number,
			"cu_number": f"0110{sequence:015d}",
			"actual_fueling_datetime": get_datetime(order.approved_on) + timedelta(minutes=1),
			"fueling_time_source": "Printed on invoice",
			# A vehicle drives a few kilometres to the station; a generator's hours do not move.
			**({"hour_meter": meter} if generator else {"vehicle_odometer": meter + 4}),
			"invoice_litres": litres,
			# Synthetic values for the disposable site; real old transactions are never backfilled.
			"invoice_amount": round(litres * 185, 2),
			"printed_unit_price": 185,
			"full_tank_confirmed": full,
			"attendant_name": ATTENDANTS[sequence % len(ATTENDANTS)],
		}
	)
	transaction.save()
	invoice = _evidence(
		f"{invoice_number}.png",
		[station, f"Invoice {invoice_number}", f"{order.fuel_type} {litres:.2f} L", f"Vehicle {asset}"],
	)
	signed = _evidence(
		f"{order.name}-signed.png",
		[
			"FUEL ORDER SLIP (signed)",
			order.name,
			f"{'Generator' if generator else 'Reg No'} {asset}",
			f"{'Hour meter' if generator else 'Speedometer'} {meter}",
		],
	)
	transaction.update({"signed_invoice": invoice, "signed_order": signed})
	transaction.save()
	transaction.submit()

	_date_back(order, transaction, days_ago, hours_ago)


def _evidence(file_name, lines):
	from PIL import Image, ImageDraw

	image = Image.new("RGB", (640, 360), "white")
	draw = ImageDraw.Draw(image)
	draw.text((24, 20), "SAMPLE DATA - TEST SITE", fill=(160, 0, 0))
	for index, line in enumerate(lines):
		draw.text((24, 70 + index * 40), line, fill=(0, 0, 0))
	buffer = BytesIO()
	image.save(buffer, format="PNG")
	previous_user = frappe.session.user
	frappe.set_user(ADMIN)
	file_doc = _insert("File", file_name=file_name, content=buffer.getvalue(), is_private=1)
	frappe.set_user(previous_user)
	return file_doc.file_url


def _date_back(order, transaction, days_ago, hours_ago=None):
	"""Move a finished cycle to a realistic past working day, keeping its validity window intact."""
	requested = get_datetime(add_days(now_datetime().date(), -days_ago)).replace(hour=8, minute=15)
	if hours_ago is not None:
		# Earlier today: requested this many hours before the script runs, fuelled 2 h 40 min later.
		requested = now_datetime() - timedelta(hours=hours_ago)
	approved = requested + timedelta(minutes=40)
	validity_days = frappe.db.get_single_value("Fleet Management Settings", "default_validity_days") or 3
	valid_until = approved + timedelta(days=validity_days)
	delta = requested - get_datetime(order.creation)

	frappe.db.set_value(
		"Fuel Order",
		order.name,
		{
			"request_datetime": requested,
			"submitted_on": requested + timedelta(minutes=5) if order.submitted_by else None,
			"approved_on": approved,
			"valid_until": valid_until,
			"last_slip_printed_on": approved + timedelta(minutes=5),
			"creation": requested,
			"modified": approved + timedelta(minutes=5),
		},
		update_modified=False,
	)
	if transaction:
		fuelled = approved + timedelta(hours=2)
		frappe.db.set_value(
			"Fueling Transaction",
			transaction.name,
			{
				"approved_on": approved,
				"valid_until": valid_until,
				"actual_fueling_datetime": fuelled,
				"submitted_on": fuelled + timedelta(hours=4),
				"creation": fuelled + timedelta(hours=3),
				"modified": fuelled + timedelta(hours=4),
			},
			update_modified=False,
		)

	names = [order.name] + ([transaction.name] if transaction else [])
	seconds = int(delta.total_seconds())
	for doctype, field in (
		("Version", "docname"),
		("Comment", "reference_name"),
		("Notification Log", "document_name"),
		("Workflow Action", "reference_name"),
		("File", "attached_to_name"),
	):
		frappe.db.sql(
			f"""UPDATE `tab{doctype}`
			SET creation = DATE_ADD(creation, INTERVAL %(seconds)s SECOND),
				modified = DATE_ADD(modified, INTERVAL %(seconds)s SECOND)
			WHERE `{field}` IN %(names)s""",
			{"seconds": seconds, "names": names},
		)
