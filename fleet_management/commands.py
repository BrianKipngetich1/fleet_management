"""Bench commands for the disposable test site.

    bench fleet-test-site up        # build a fresh test site from the sample data
    bench fleet-test-site down      # throw it away
    bench fleet-test-site up --replace

`up` builds the test site from the current code, copies the main site's regional System
Settings, date format and set Fleet Management Settings so the two behave alike, loads
`fleet_management.sample_data`, and gives every test-site login the password recorded in the local
credential inventory — so each rebuild has the same users with the same credentials. It stops before
changing anything when a sample person has no test login, and afterwards checks that every login
signs in. `down` drops the database and the site folder.

No MariaDB root access is needed: the site's own database user holds every privilege on its one
database and rebuilds it through Frappe's `--no-setup-db` install path. Passwords are read from the
gitignored credential inventory and never printed or passed on a command line.
"""

import os
import shutil
from pathlib import Path

import click
from frappe.commands import get_site, pass_context

TEST_SITE = "fleet_management-test.localhost"
MAIN_SITE = "fleet_management.localhost"
DB_NAME = "fleet_mgmt_test"
DB_USER = "fleet_mgmt_test"
DB_SOCKET = "/run/mysqld/mysqld.sock"
SETUP_USER = "test@erpnext.com"
DEFAULT_CREDENTIALS = Path(__file__).resolve().parents[1] / "CREDENTIALS.md"
REGIONAL_SETTINGS = ("country", "time_zone", "language", "currency")


@click.group("fleet-test-site")
def fleet_test_site():
	"""Build or throw away the disposable test site."""


@fleet_test_site.command("up")
@click.option("--replace", is_flag=True, help="Throw away an existing test site first.")
@click.option(
	"--credentials",
	type=click.Path(exists=True, dir_okay=False, path_type=Path),
	default=DEFAULT_CREDENTIALS,
	show_default=True,
	help="Repository-root CREDENTIALS.md holding the test-site passwords.",
)
def up(replace, credentials):
	"""Build a fresh test site from the sample data."""
	secrets = _read_credentials(credentials)
	missing = _missing_test_logins(secrets["users"])
	if missing:
		raise click.ClickException(f"The login file has no test login for: {', '.join(missing)}.")
	if os.path.exists(TEST_SITE):
		if not replace:
			raise click.ClickException(f"{TEST_SITE} already exists; pass --replace or run down first.")
		_down()

	regional = _main_site_settings()
	_recreate_database(secrets["db_password"])
	_install(secrets)
	_setup_and_seed(regional, secrets)
	click.secho(f"{TEST_SITE} is ready with sample data and {len(secrets['users'])} test logins.", fg="green")


@fleet_test_site.command("down")
def down():
	"""Throw away the test site: its database and its site folder."""
	if not os.path.exists(TEST_SITE):
		raise click.ClickException(f"{TEST_SITE} does not exist.")
	_down()
	click.secho(f"{TEST_SITE} removed.", fg="green")


@fleet_test_site.command("session")
@click.argument("email")
@pass_context
def session(context, email):
	"""Print `?sid=<sid>` for a logged-in session of EMAIL; test site with developer_mode only."""
	import frappe
	from frappe.auth import CookieManager, LoginManager

	site = get_site(context, raise_err=False)
	if site != TEST_SITE:
		raise click.ClickException(f"Only {TEST_SITE} with developer_mode can mint a session.")
	frappe.init(site)
	try:
		if not frappe.conf.developer_mode:
			raise click.ClickException(f"Only {TEST_SITE} with developer_mode can mint a session.")
		frappe.connect()
		if not email or email == "Guest" or not frappe.db.exists("User", email):
			raise click.ClickException(f"{email or '<empty>'} is not a user that can be given a session.")
		frappe.utils.set_request(path="/")
		frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(email)
		frappe.db.commit()
		# Print the sid that was saved: read back the newest stored session, not the in-memory one.
		saved = frappe.db.get_value("Sessions", {"user": email}, "sid", order_by="lastupdate desc")
		if not saved:
			raise click.ClickException(f"No session was saved for {email}.")
		click.echo(f"?sid={saved}")
	finally:
		frappe.destroy()


def _read_credentials(path):
	"""Return the test-site passwords from the login file's markdown tables, told apart by header."""
	table = None
	users, db_password, admin_password = {}, None, None
	for line in path.read_text().splitlines():
		if not line.startswith("| ") or line.startswith("|---"):
			continue
		cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
		if cells[0] == "Site":
			table = "database" if cells[:2] == ["Site", "Database"] else "login"
		elif len(cells) < 4 or cells[0] != TEST_SITE:
			continue
		elif table == "database" and cells[1:3] == [DB_NAME, DB_USER]:
			db_password = cells[3]
		elif table == "login" and cells[1] == "Administrator":
			admin_password = cells[3]
		elif table == "login":
			users[cells[1]] = cells[3]

	missing = [
		label
		for label, value in (
			("test-site logins", users),
			(f"{DB_USER} database password", db_password),
			("test-site Administrator password", admin_password),
		)
		if not value
	]
	if missing:
		raise click.ClickException(f"{path} is missing: {', '.join(missing)}.")
	bad = [user for user, password in users.items() if "test" not in user or "test" not in password]
	if bad:
		raise click.ClickException(f"Test usernames and passwords must contain 'test': {', '.join(bad)}.")
	return {"users": users, "db_password": db_password, "admin_password": admin_password}


def _missing_test_logins(users):
	"""Return the sample people, in sample order, that have no test login in `users`."""
	from fleet_management import sample_data

	return [email for email, *_rest in sample_data.USERS if email not in users]


def _merge_settings(main, sample):
	"""Per field, the main site's value when it is set, else the sample value; "0" counts as set."""
	merged = dict(sample)
	for field, value in main.items():
		if value is not None and str(value).strip() != "":
			merged[field] = value
	return merged


def _main_site_settings():
	import frappe

	frappe.init(MAIN_SITE)
	frappe.connect()
	try:
		settings = {key: frappe.db.get_single_value("System Settings", key) for key in REGIONAL_SETTINGS}
		settings["date_format"] = frappe.db.get_single_value("System Settings", "date_format")
		# Raw rows, so a blank number stays blank instead of reading as 0; absent rows are blank too.
		fields = _settings_fields()
		rows = frappe.db.sql(
			"SELECT field, value FROM tabSingles WHERE doctype=%s", "Fleet Management Settings"
		)
		settings["fleet_settings"] = {
			field: value
			for field, value in rows
			if field in fields and value is not None and str(value).strip() != ""
		}
		return settings
	finally:
		frappe.destroy()


def _settings_fields():
	"""Return the Fleet Management Settings fieldnames and types that hold a value."""
	import frappe
	from frappe.model import no_value_fields

	return {
		df.fieldname: df.fieldtype
		for df in frappe.get_meta("Fleet Management Settings").fields
		if df.fieldtype not in no_value_fields
	}


def _apply_main_settings(regional):
	"""Put the main site's date format and set Fleet Management Settings over the seeded ones."""
	import frappe
	from frappe.utils import cint, flt

	if regional.get("date_format"):
		frappe.db.set_single_value("System Settings", "date_format", regional["date_format"])
	fields = _settings_fields()
	settings = frappe.get_single("Fleet Management Settings")
	merged = _merge_settings(regional.get("fleet_settings") or {}, {})
	for field, value in merged.items():
		fieldtype = fields.get(field)
		if fieldtype in ("Int", "Check"):
			value = cint(value)
		elif fieldtype in ("Float", "Currency", "Percent"):
			value = flt(value)
		settings.set(field, value)
	settings.save(ignore_permissions=True)


def _failing_logins(users):
	"""Return the users in `users` that exist on the site but do not sign in with their password."""
	import frappe
	from frappe.utils.password import check_password

	failing = []
	for user, password in users.items():
		if not frappe.db.exists("User", user):
			continue
		try:
			check_password(user, password)
		except frappe.AuthenticationError:
			failing.append(user)
	return failing


def _connect_as_site_user(password):
	import pymysql

	return pymysql.connect(unix_socket=DB_SOCKET, user=DB_USER, password=password, autocommit=True)


def _recreate_database(password):
	connection = _connect_as_site_user(password)
	try:
		with connection.cursor() as cursor:
			cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
			cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
	finally:
		connection.close()


def _install(secrets):
	import frappe
	from frappe.installer import _new_site
	from frappe.utils import CallbackManager

	frappe.init(TEST_SITE, new_site=True)
	try:
		_new_site(
			DB_NAME,
			TEST_SITE,
			admin_password=secrets["admin_password"],
			install_apps=["fleet_management"],
			db_password=secrets["db_password"],
			db_type="mariadb",
			db_socket=DB_SOCKET,
			db_user=DB_USER,
			setup_db=False,
			rollback_callback=CallbackManager(),
		)
	finally:
		frappe.destroy()


def _setup_and_seed(regional, secrets):
	import frappe
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
	from frappe.installer import update_site_config
	from frappe.utils.password import update_password
	from frappe.utils.scheduler import enable_scheduler

	from fleet_management import sample_data

	frappe.init(TEST_SITE)
	# developer_mode lets `bench browse --user` mint sessions; allow_tests enables the test runner.
	update_site_config("developer_mode", 1)
	update_site_config("allow_tests", True)
	frappe.destroy()

	frappe.init(TEST_SITE)
	frappe.connect()
	try:
		frappe.set_user("Administrator")
		setup_complete(
			{
				"language": regional["language"] or "en",
				"country": regional["country"],
				"timezone": regional["time_zone"],
				"currency": regional["currency"],
				"email": SETUP_USER,
				"full_name": "Test User",
				"password": secrets["users"].get(SETUP_USER, "test"),
			}
		)
		frappe.set_user("Administrator")
		sample_data.seed()
		_apply_main_settings(regional)
		for user, password in secrets["users"].items():
			if frappe.db.exists("User", user):
				update_password(user, password)
			else:
				click.secho(f"Skipped {user}: the sample data does not create it.", fg="yellow")
		enable_scheduler()
		frappe.db.commit()
		failing = _failing_logins(secrets["users"])
		if failing:
			raise click.ClickException(f"These test logins do not sign in: {', '.join(failing)}.")
		frappe.clear_cache()
	finally:
		frappe.destroy()


def _down():
	import frappe

	frappe.init(TEST_SITE)
	password = frappe.conf.db_password
	if frappe.conf.db_name != DB_NAME:
		raise click.ClickException(f"{TEST_SITE} does not use {DB_NAME}; refusing to drop it.")
	try:
		frappe.connect()
		# Redis keys are prefixed with the database name, which the next build reuses.
		frappe.clear_cache()
	finally:
		frappe.destroy()

	connection = _connect_as_site_user(password)
	try:
		with connection.cursor() as cursor:
			cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
	finally:
		connection.close()
	shutil.rmtree(TEST_SITE)


commands = [fleet_test_site]
