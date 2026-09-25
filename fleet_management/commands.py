"""Bench commands for the disposable test site.

    bench fleet-test-site up        # build a fresh test site from the sample data
    bench fleet-test-site down      # throw it away
    bench fleet-test-site up --replace

`up` builds the test site from the current code, copies the main site's regional System
Settings so the two behave alike, loads `fleet_management.sample_data`, and gives every test-site
login the password recorded in the local credential inventory — so each rebuild has the same users
with the same credentials. `down` drops the database and the site folder.

No MariaDB root access is needed: the site's own database user holds every privilege on its one
database and rebuilds it through Frappe's `--no-setup-db` install path. Passwords are read from the
gitignored credential inventory and never printed or passed on a command line.
"""

import os
import shutil
from pathlib import Path

import click

TEST_SITE = "fleet_management-test.localhost"
MAIN_SITE = "fleet_management.localhost"
DB_NAME = "fleet_mgmt_test"
DB_USER = "fleet_mgmt_test"
DB_SOCKET = "/run/mysqld/mysqld.sock"
SETUP_USER = "test@erpnext.com"
DEFAULT_CREDENTIALS = (
	Path(__file__).resolve().parents[1]
	/ "specs/001-fleet-fuel-management/verification/CREDENTIALS.md"
)
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
	help="Local credential inventory holding the test-site passwords.",
)
def up(replace, credentials):
	"""Build a fresh test site from the sample data."""
	secrets = _read_credentials(credentials)
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


def _read_credentials(path):
	"""Return the test-site passwords from the credential inventory's markdown tables."""
	section = None
	users, db_password, admin_password = {}, None, None
	for line in path.read_text().splitlines():
		if line.startswith("## "):
			section = line
			continue
		if not line.startswith("| ") or line.startswith("|---"):
			continue
		cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
		if section and section.startswith("## Test site") and len(cells) >= 3 and "@" in cells[1]:
			users[cells[1]] = cells[2]
		elif cells[:3] == [TEST_SITE, DB_NAME, DB_USER] and len(cells) >= 4:
			db_password = cells[3]
		elif cells[:2] == [TEST_SITE, "Administrator"] and len(cells) >= 3:
			admin_password = cells[2]

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


def _main_site_settings():
	import frappe

	frappe.init(MAIN_SITE)
	frappe.connect()
	try:
		return {key: frappe.db.get_single_value("System Settings", key) for key in REGIONAL_SETTINGS}
	finally:
		frappe.destroy()


def _connect_as_site_user(password):
	import pymysql

	return pymysql.connect(unix_socket=DB_SOCKET, user=DB_USER, password=password, autocommit=True)


def _recreate_database(password):
	connection = _connect_as_site_user(password)
	try:
		with connection.cursor() as cursor:
			cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
			cursor.execute(
				f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
			)
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
		for user, password in secrets["users"].items():
			if frappe.db.exists("User", user):
				update_password(user, password)
			else:
				click.secho(f"Skipped {user}: the sample data does not create it.", fg="yellow")
		enable_scheduler()
		frappe.db.commit()
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
