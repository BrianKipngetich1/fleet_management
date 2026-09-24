# Progress

One row per specification. Detail lives in the specification and its phase records —
this file is a pointer, never a journal. Overwrite the rows; do not append to them.
Status history is git's job.

| Specification | Status | Phases | Next action |
|---|---|---|---|
| [001 — Fleet and Fuel Management](specs/001-fleet-fuel-management/spec.md) | In progress — Phases 0 and 0.5 complete (PR #2: independent review by Claude Opus 5.5, final review by Rishabh Vyas); Phase 1 in progress on `feature/001-phase-1` | Phase 0 ✅ AC-01, 03, 04, 05, 06, 19 · Phase 0.5 ✅ D-14–D-16 · Phases 1–9 AC-02, 07–18, 20–28, each record stating built / partly built / not built | Phase 1 (location access, AC-02): add tests for asset and station choice (rows 5–6), rerun rows 1–7 on MariaDB, walk through Desk |

Record execution order here when it is not phase-id order.

A specification may be **parked** so another takes priority. Parked is not abandoned and
not cleared: its phase records and open findings stay exactly as they are, and it resumes
at the phase named in its status.

## Environment

| | |
|---|---|
| Bench root | /home/kayadmin/frappe-bench |
| Development site | fleet_management.localhost — MariaDB `fleet_mgmt_dev`, own DB user; tests disabled (SQLite history archived) |
| Test site | fleet_management-test.localhost — MariaDB `fleet_mgmt_test`, own DB user; bench default site; only site allowing tests (SQLite history archived) |
| Required backend | MariaDB for both sites and all new acceptance evidence |
| Services | systemd user units under `frappe-bench.target` (linger on; start at boot, restart on failure): apt Redis :13000/:11000, `bench serve` :8000, socketio, worker, scheduler, watch. Manage with `systemctl --user`; do not run `bench start` while the target is active. MariaDB is the system service. |
| Backups | `~/Backups` (outside the repo; README and checksum manifest there). `bench backup` prunes a site's own backups older than 23 hours, so copy sets out after taking them. |
| Base branch | main (release branch) |
| Integration/default branch | develop |

## Phase records

Every phase has exactly one record under `specs/<NNN-name>/verification/phase-NN-<slug>.md`,
written to `specs/TEMPLATE-verification.md`. A record states the current position; it is
not a chronicle.
