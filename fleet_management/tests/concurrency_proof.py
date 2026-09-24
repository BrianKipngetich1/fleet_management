"""AC-07 row-lock proof for a disposable MariaDB/PostgreSQL test site.

Run with:
FLEET_RUN_CONCURRENCY_PROOF=1 bench --site fleet_management-concurrency-test.localhost \
    run-tests --module fleet_management.fleet_management.doctype.fueling_transaction.test_fueling_transaction \
    --test test_concurrent_submissions_wait_for_order_lock
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import frappe


CONCURRENCY_SITE = "fleet_management-concurrency-test.localhost"
CONCURRENCY_OPT_IN = "FLEET_RUN_CONCURRENCY_PROOF"
EXPECTED_UNIQUE_INDEXES = {
	"unique_fueling_invoice_station",
	"unique_fueling_cu_number",
	"unique_active_fueling_order",
}


def concurrency_proof_enabled():
	return os.environ.get(CONCURRENCY_OPT_IN) == "1"


def assert_concurrency_site():
	if not concurrency_proof_enabled():
		raise RuntimeError(f"Set {CONCURRENCY_OPT_IN}=1 to run the concurrency proof.")
	if frappe.local.site != CONCURRENCY_SITE:
		raise RuntimeError(f"Run this proof only on {CONCURRENCY_SITE}.")
	if frappe.db.db_type not in {"mariadb", "postgres"}:
		raise RuntimeError("AC-07 overlap proof requires MariaDB or PostgreSQL row locks.")
	return frappe.db.db_type


def unique_index_names():
	if frappe.db.db_type == "mariadb":
		rows = frappe.db.sql("SHOW INDEX FROM `tabFueling Transaction`", as_dict=True)
		return {row["Key_name"] for row in rows if int(row["Non_unique"]) == 0}
	if frappe.db.db_type == "postgres":
		rows = frappe.db.sql(
			"""
			SELECT index_class.relname AS index_name
			FROM pg_class AS table_class
			JOIN pg_index AS index_meta ON table_class.oid = index_meta.indrelid
			JOIN pg_class AS index_class ON index_class.oid = index_meta.indexrelid
			JOIN pg_namespace AS schema_meta ON schema_meta.oid = table_class.relnamespace
			WHERE table_class.relname = %s
				AND schema_meta.nspname = current_schema()
				AND index_meta.indisunique
			""",
			("tabFueling Transaction",),
			as_dict=True,
		)
		return {row["index_name"] for row in rows}
	raise RuntimeError("AC-07 overlap proof requires MariaDB or PostgreSQL row locks.")


def _touch(path):
	Path(path).touch()


def _wait_for_file(path, timeout):
	deadline = time.monotonic() + timeout
	while time.monotonic() < deadline:
		if Path(path).exists():
			return True
		time.sleep(0.02)
	return Path(path).exists()


def submit_worker(transaction_name, user, worker_id, state_dir, hold_after_lock=0):
	"""Submit one draft in a fresh bench process and expose the order-lock point."""
	assert_concurrency_site()
	from fleet_management.fleet_management.doctype.fueling_transaction.fueling_transaction import (
		FuelingTransaction,
	)

	state_dir = Path(state_dir)
	original_get_order = FuelingTransaction._get_order
	outcome_path = state_dir / f"{worker_id}-outcome.json"
	outcome = None

	def observed_get_order(self, for_update=False):
		is_submission_lock = for_update and self.name == transaction_name
		if is_submission_lock:
			_touch(state_dir / f"{worker_id}-attempting")
		order = original_get_order(self, for_update=for_update)
		if is_submission_lock:
			_touch(state_dir / f"{worker_id}-acquired")
			if hold_after_lock and not _wait_for_file(state_dir / "release-a", 30):
				raise TimeoutError("Timed out waiting to release worker A's order lock.")
		return order

	try:
		FuelingTransaction._get_order = observed_get_order
		frappe.set_user(user)
		frappe.get_doc("Fueling Transaction", transaction_name).submit()
		frappe.db.commit()
		outcome = {"result": "submitted"}
	except frappe.ValidationError as error:
		frappe.db.rollback()
		outcome = {
			"result": "validation",
			"exception": type(error).__name__,
			"message": str(error),
		}
	except Exception as error:
		frappe.db.rollback()
		outcome = {"result": "error", "exception": type(error).__name__}
	finally:
		FuelingTransaction._get_order = original_get_order
		outcome_path.write_text(json.dumps(outcome), encoding="utf-8")


def _start_worker(site, transaction_name, user, worker_id, state_dir, hold_after_lock):
	kwargs = json.dumps(
		{
			"transaction_name": transaction_name,
			"user": user,
			"worker_id": worker_id,
			"state_dir": str(state_dir),
			"hold_after_lock": int(hold_after_lock),
		}
	)
	bench_root = Path(frappe.get_site_path()).parent.parent
	return subprocess.Popen(
		[
			"bench",
			"--site",
			site,
			"execute",
			"fleet_management.tests.concurrency_proof.submit_worker",
			"--kwargs",
			kwargs,
		],
		cwd=bench_root,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)


def _wait_for_marker(path, process, label, timeout=30):
	if _wait_for_file(path, timeout):
		return
	if process.poll() is not None:
		raise AssertionError(f"Worker {label} exited with code {process.returncode} before {path.name}.")
	raise AssertionError(f"Timed out waiting for worker {label} to reach {path.name}.")


def _assert_worker_waits_for_order_lock(path, process, timeout=1):
	deadline = time.monotonic() + timeout
	while time.monotonic() < deadline:
		if Path(path).exists():
			raise AssertionError("Worker B acquired the Fuel Order before worker A committed.")
		if process.poll() is not None:
			raise AssertionError(f"Worker B exited while worker A held the Fuel Order lock ({process.returncode}).")
		time.sleep(0.02)
	if Path(path).exists():
		raise AssertionError("Worker B acquired the Fuel Order before worker A committed.")


def _wait_for_outcome(path, process, label):
	_wait_for_marker(path, process, f"{label} outcome")
	try:
		return json.loads(Path(path).read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as error:
		raise AssertionError(f"Worker {label} did not write a readable outcome.") from error


def _stop_worker(process):
	if process is None or process.poll() is not None:
		return
	process.terminate()
	try:
		process.wait(timeout=5)
	except subprocess.TimeoutExpired:
		process.kill()
		process.wait(timeout=5)


def run_locked_order_overlap(order_name, transaction_a, transaction_b, user):
	"""Prove worker B waits for A's order lock, then receives business validation."""
	site = frappe.local.site
	assert_concurrency_site()

	with tempfile.TemporaryDirectory(prefix="fleet-concurrency-") as directory:
		state_dir = Path(directory)
		worker_a = worker_b = None
		try:
			worker_a = _start_worker(
				site, transaction_a, user, "a", state_dir, hold_after_lock=True
			)
			_wait_for_marker(state_dir / "a-acquired", worker_a, "A lock")

			worker_b = _start_worker(
				site, transaction_b, user, "b", state_dir, hold_after_lock=False
			)
			_wait_for_marker(state_dir / "b-attempting", worker_b, "B lock attempt")
			_assert_worker_waits_for_order_lock(state_dir / "b-acquired", worker_b)
			_touch(state_dir / "release-a")

			outcome_a = _wait_for_outcome(state_dir / "a-outcome.json", worker_a, "A")
			outcome_b = _wait_for_outcome(state_dir / "b-outcome.json", worker_b, "B")
			worker_a.wait(timeout=30)
			worker_b.wait(timeout=30)
			if worker_a.returncode or worker_b.returncode:
				raise AssertionError("A concurrency worker exited unsuccessfully.")

			if outcome_a.get("result") != "submitted":
				raise AssertionError(f"Worker A did not submit successfully: {outcome_a.get('exception', 'unknown error')}.")
			if (
				outcome_b.get("result") != "validation"
				or outcome_b.get("exception") != "ValidationError"
				or "already has an active Fueling Transaction" not in outcome_b.get("message", "")
			):
				raise AssertionError(
					"Worker B did not receive the controlled active-order validation error "
					f"(result={outcome_b.get('result')}, exception={outcome_b.get('exception', 'none')})."
				)

			active_rows = frappe.get_all(
				"Fueling Transaction",
				filters={"fuel_order": order_name, "active_fuel_order": order_name},
				fields=["name", "docstatus"],
			)
			if len(active_rows) != 1 or active_rows[0].name != transaction_a or active_rows[0].docstatus != 1:
				raise AssertionError("Expected exactly one submitted row to retain the active Fuel Order key.")
			if frappe.db.count("Fueling Transaction", {"fuel_order": order_name, "docstatus": 1}) != 1:
				raise AssertionError("Expected exactly one submitted Fueling Transaction for the Fuel Order.")
			return {"winner": transaction_a, "loser": transaction_b}
		finally:
			_touch(state_dir / "release-a")
			_stop_worker(worker_b)
			_stop_worker(worker_a)
