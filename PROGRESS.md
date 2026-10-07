# Progress

One row per specification. Detail lives in the specification and its phase records —
this file is a pointer, never a journal. Overwrite the rows; do not append to them.
Status history is git's job.

| Specification | Status | Phases | Next action |
|---|---|---|---|
| [001 — Fleet and Fuel Management](specs/001-fleet-fuel-management/spec.md) | **Parked** at Phase 1 for 002 (owner, 2026-09-25) — Phases 0 and 0.5 complete (PR #2: independent review by Claude Opus 5.5, final review by Rishabh Vyas); Phase 1 work in progress, partly merged in PR #3 | Phase 0 ✅ AC-01, 03, 04, 05, 06, 19 · Phase 0.5 ✅ D-14–D-16 · Phases 1–9 AC-02, 07–18, 20–28, each record stating built / partly built / not built | After 002 closes, resume Phase 1 (location access, AC-02): add tests for asset and station choice (rows 5–6), rerun rows 1–7 on MariaDB, walk through Desk |
| [002 — Fuel Order request, signal, and slip](specs/002-fuel-order-request-slip/spec.md) | Implementing on `feature/002-fuel-order-request-slip` (spec approved in PR #4, `3c37dbb`) — all four phases built and verified on MariaDB (backend, Playwright, Desk), none yet reviewed | Phases 0–3 verified, awaiting independent review: Phase 0 slip AC-01–03 · Phase 1 vehicle-first request AC-04–07 · Phase 2 green and red signal AC-08–11 · Phase 3 Philip decides, Vikas signs off red AC-12–15 | Independent review of each phase, then push the branch and hand over the pull request |
| [004 — Test-site rebuild, regional settings, and pull-request checks](specs/004-test-site-locale/bugfix.md) | **Closed** 29/09/2026 — fix in PR #7 and PR #8 (CI green), record in PR #9 | Phase 1 ✅ 1.1–1.5 · Phase 2 ✅ 2.1–2.4 · Desk walkthrough moved to 005 (owner) | None |
| [005 — Fleet home page, one login file, and a test site that copies the main site](specs/005-fleet-desk-page/bugfix.md) | Bugfix (`ecd7510`) and design (`6d8acf1`) approved on `fix/005-fleet-desk-page`; all three phases built and verified, not yet reviewed | Phase 1 one login file, working sign-in ✅ · Phase 2 Fleet home page ✅ (drift: setup links on an admin-only page) · Phase 3 test site copies main setup, checks logins ✅ | Independent review, then the pull request when the owner asks |
| [006 — Import the master lists and load the company's real fleet](specs/006-master-data-import/requirements.md) | Building on `feature/006-master-data-import` (Heavy since 07/10/2026; requirements `0da72f4` and design `cd585e5` approved by Mukesh Singh) | Phase 1 import ✅ 1.1–1.4 (1.5 with pre-PR checks) · Phase 2 Ecoflame serves both companies ✅ 2.1–2.4 · Phase 3 real fleet on the test site · Phase 4 same fleet on the main site · Phase 5 September history (later) | Task 3.1 |
| [008 — Fleet Oversight Reports](specs/008-overseer-reports/requirements.md) | Implementing on `feature/008-overseer-reports` — Phases 1–3 complete; Phase 3 backend verification recorded | Phase 1: 1.1–1.4 ✅ · Phase 2: 2.1–2.4 ✅ · Phase 3: 3.1–3.5 ✅ | Await a request to publish; pre-PR pipeline has not started |
| [009 — Fuel Order experience](specs/009-fuel-order-ux/requirements.md) | Integrated into `feature/008-overseer-reports` from local `feature/009-fuel-order-ux-brian`; four implementation phases built. Phase 1's final visual recheck and Phase 4.4 action-history walkthrough remain open. | System Details is in the far-right fourth column and collapsed by default; responsive layouts, borders, signal explanations, full-tank comparison, and event history are implemented. Earlier focused runs recorded 146 passed and one existing concurrency test skipped by its environment guard; no full suite was run. | Complete the pending visual recheck and Phase 4.4 walkthrough before publication. |

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
| Test site | fleet_management-test.localhost (`http://fleet_management-test.localhost:8000`) — **disposable**: built for each test session with `bench fleet-test-site up` (MariaDB `fleet_mgmt_test`, own DB user, fixed sample data from `fleet_management/sample_data.py`, logins from the root `CREDENTIALS.md`) and removed with `bench fleet-test-site down`; the only site allowing tests. History before 2026-09-25 is in `~/Backups` |
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
