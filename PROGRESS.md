# Progress

One row per specification. Detail lives in the specification and its phase records —
this file is a pointer, never a journal. Overwrite the rows; do not append to them.
Status history is git's job.

| Specification | Status | Phases | Next action |
|---|---|---|---|
| [001 — Fleet and Fuel Management](specs/001-fleet-fuel-management/spec.md) | **Parked** at Phase 1 for 002 (owner, 2026-09-25) — Phases 0 and 0.5 complete (PR #2: independent review by Claude Opus 5.5, final review by Rishabh Vyas); Phase 1 work in progress, partly merged in PR #3 | Phase 0 ✅ AC-01, 03, 04, 05, 06, 19 · Phase 0.5 ✅ D-14–D-16 · Phases 1–9 AC-02, 07–18, 20–28, each record stating built / partly built / not built | After 002 closes, resume Phase 1 (location access, AC-02): add tests for asset and station choice (rows 5–6), rerun rows 1–7 on MariaDB, walk through Desk |
| [002 — Fuel Order request, signal, and slip](specs/002-fuel-order-request-slip/spec.md) | Implementing on `feature/002-fuel-order-request-slip` (spec approved in PR #4, `3c37dbb`) — all four phases built and verified on MariaDB (backend, Playwright, Desk), none yet reviewed | Phases 0–3 verified, awaiting independent review: Phase 0 slip AC-01–03 · Phase 1 vehicle-first request AC-04–07 · Phase 2 green and red signal AC-08–11 · Phase 3 Philip decides, Vikas signs off red AC-12–15 | Independent review of each phase, then push the branch and hand over the pull request |
| [005 — Fleet home page and a test site that copies the main site](specs/005-fleet-desk-page/bugfix.md) | Spec written on `fix/005-fleet-desk-page`, awaiting approval | Phase 1 Fleet home page · Phase 2 test site copies main setup, checks logins | Owner approves, then 1.1 |

Record execution order here when it is not phase-id order.

- 2026-09-25 — 002 runs before 001 resumes; 001 is parked at Phase 1 (002 D-2).
- 2026-09-25 — 002's four phases are built in turn on one branch, tested together once all are
  built, and delivered in one pull request; each keeps its own record, review, and closure (owner).

A specification may be **parked** so another takes priority. Parked is not abandoned and
not cleared: its phase records and open findings stay exactly as they are, and it resumes
at the phase named in its status.

## Environment

| | |
|---|---|
| Bench root | /home/kayadmin/frappe-bench |
| Main site | fleet_management.localhost (`http://fleet_management.localhost:8000`) — MariaDB `fleet_mgmt_dev`, own DB user; tests disabled; never receives test records (SQLite history archived) |
| Test site | fleet_management-test.localhost (`http://fleet_management-test.localhost:8000`) — **disposable**: built for each test session with `bench fleet-test-site up` (MariaDB `fleet_mgmt_test`, own DB user, fixed sample data from `fleet_management/sample_data.py`, logins from the 001 `CREDENTIALS.md`) and removed with `bench fleet-test-site down`; the only site allowing tests. History before 2026-09-25 is in `~/Backups` |
| Required backend | MariaDB for both sites and all new acceptance evidence |
| Regional settings | Both sites: Kenya, Africa/Nairobi, KES, dd/mm/yyyy (set 2026-09-26); the test site copies country, time zone, language, and currency from the main site at every build |
| PDF | The fuel order slip uses Frappe's Chrome PDF generator; the bench's `common_site_config.json` sets `chromium_path` to `/usr/bin/google-chrome`. wkhtmltopdf is not installed |
| Services | systemd user units under `frappe-bench.target` (linger on; start at boot, restart on failure): apt Redis :13000/:11000, `bench serve` :8000, socketio, worker, scheduler, watch. Manage with `systemctl --user`; do not run `bench start` while the target is active. MariaDB is the system service. |
| Backups | `~/Backups` (outside the repo; README and checksum manifest there). `bench backup` prunes a site's own backups older than 23 hours, so copy sets out after taking them. |
| Base branch | main (release branch) |
| Integration/default branch | develop |

## Phase records

Every phase has exactly one record under `specs/<NNN-name>/verification/phase-NN-<slug>.md`,
written to `specs/TEMPLATE-verification.md`. A record states the current position; it is
not a chronicle.
