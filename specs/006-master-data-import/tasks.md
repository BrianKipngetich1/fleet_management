<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->

# Import the fleet's master lists and load the company's real fleet: tasks

## Phase 1: Import the master lists

**Tracer:** An administrator saves a Data Import for Fleet Location, downloads its blank Excel
template, and imports a filled one.

- [x] 1.1 Show the refusal today: saving a Data Import for Fleet Location fails
  - _Requirements: 1.1_
- [x] 1.2 Set `allow_import` on the six master DocTypes; migrate the main site
  - _Requirements: 1.1_
- [x] 1.3 Test Property 1: import open for the six, refused for orders and fuellings
  - _Requirements: 1.1, 2.2_
- [x] 1.4 Test Property 2: an asset with an assignment row imports; a bad row is reported
  - _Requirements: 1.2, 1.3_
- [ ] 1.5 Confirm Fleet Admin, Fleet User, and Fleet Approver still cannot open the import tool, and the suites still pass (run with the pre-PR checks)
  - _Requirements: 2.1, 2.3_

## Phase 2: Ecoflame serves both companies

**Tracer:** On the test site, a fleet admin adds a second company to a station's "also serves"
list, and an order for a vehicle at that second company accepts the station.

- [x] 2.1 Add the `Fuel Station Location` child DocType and `Fuel Station.also_serves`; migrate the main site
  - _Requirements: 4.2_
- [x] 2.2 Serve the whole set: `get_served_locations`, `_validate_station`, `get_request_facts`, and a whitelisted `station_query` used by the order form
  - _Requirements: 4.1, 2.4_
- [x] 2.3 Scope stations by the whole set in `permissions.py`
  - _Requirements: 5.3_
- [x] 2.4 Test Property 5 (accepted when served, refused when not, suggestion and search agree) and Property 6 (shared station visible, other company's orders and vehicles refused)
  - _Requirements: 4.1, 4.2, 2.4, 5.3_

## Phase 3: The real fleet on the test site

**Tracer:** After `bench fleet-test-site up --replace`, Phyllis signs in, opens KAY222A, and
raises an order to Ecoflame with Mrs. Danbhai Kanji as driver; Vishal signs off a red one.

- [x] 3.1 Write `fleet_management/master_data.py` from the templates with the D-10 and D-11 corrections, and `load(people_users)` that only adds
  - _Requirements: 3.1, 3.3, 3.4_
- [x] 3.2 Rewrite `sample_data.py` to load the real fleet with the D-8 logins and company access, Ecoflame's address, and an empty history
  - _Requirements: 3.2, 5.1, 5.2_
- [x] 3.3 Test Property 3 (the listed fleet, every time) and Property 4 (only adds, keeps edits)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
- [x] 3.4 Test Property 7 (Phyllis's orders with the holder as driver, green and red routes to Vishal, Ecoflame on the slip)
  - _Requirements: 5.1, 5.2, 5.4, 2.5, 4.3_
- [x] 3.5 Update the browser-test facts (`e2e/fixtures.ts`, `e2e/setup.ts`) and the project notes that name the old people and places
  - _Requirements: 5.3, 2.3_

## Phase 4: The same fleet on the main site

**Tracer:** On the main site, signed in as `fleet.user@example.com`, Phyllis sees all 15
vehicles at Kabete and Kanha and Ecoflame as their station.

- [ ] 4.1 Add `load_main`, which links Phyllis and Vishal to the main-site logins and adds their company access
  - _Requirements: 3.3, 5.1, 5.2_
- [ ] 4.2 Run `load_main` once on the main site and confirm a second run adds nothing
  - _Requirements: 3.1, 3.3, 3.5_

## Phase 5: September's history becomes the test history (later)

**Tracer:** After Phyllis has entered 01/09/2026–30/09/2026 on the main site, a rebuilt test
site shows the same fill-ups for each vehicle.

- [ ] 5.1 Copy September's completed fill-ups into the sample-data history (separate approval when the data exists)
  - _Requirements: 3.2_

## Progress log

- `30/09/2026`: Requirements and design written. Next: approval, then 1.1.
- `30/09/2026`: Approved. 1.1 refusal shown for all eight Fleet lists; 1.2 import switched on for
  the six master lists and the main site migrated (orders and fuellings still refused). Next: 1.3.
- `30/09/2026`: 1.3 and 1.4 tests added and passing on the test site (migrated, not rebuilt: this
  branch reads the login file from its old place). Next: 1.5.
- `30/09/2026`: Migrating from this branch alone removed the Fleet home page from both sites;
  merged `fix/005-fleet-desk-page` in, migrated the main site, rebuilt the test site (five logins
  checked). Next: 1.5 with the full suites before the pull request.
- `07/10/2026`: Scope widened (Heavy): the company's real fleet becomes the starting data on both
  sites, Ecoflame serves Kabete and Kanha, Phyllis and Vishal replace Philip and Vikas.
  Requirements and design approved by Mukesh Singh. Test-site logins renamed in the login file
  (old file backed up in `~/Backups/fleet_management/`). Next: 2.1.
- `07/10/2026`: 2.1 Stations gained an "Also Serves" list (new child table of locations; repeats and the
  station's own location are dropped on save). Main site migrated; Locale unchanged; the Fleet home
  page is back. Next: 2.2.
- `07/10/2026`: 2.2 Orders accept any station serving their location (own or Also Serves); the vehicle's
  station suggestion and the order form's station search use the same rule (new `station_query`).
  Refusal now reads "Planned station must serve the operational location." Main site migrated. Next: 2.3.
- `07/10/2026`: 2.3 A Fleet User or Approver sees a station wherever it serves (own location or Also
  Serves), in lists and when opening it. The station's location links no longer go through Frappe's
  own User Permission filter (as Fuel Order already does), so the app's location scope alone decides.
  Main site migrated. Next: 2.4.
- `07/10/2026`: 2.4 `tests/test_shared_station.py` (Properties 5 and 6) passes 4/4 on a rebuilt MariaDB test
  site; the station-related modules still pass (permissions 13, fuel order 26, signal 9, import 3). The
  test site was built with the backed-up old login file, since its sample data still creates Philip,
  Vikas, and Amina until 3.2; then taken down. Part 1 complete. Next: 3.1.
- `07/10/2026`: 3.1 `fleet_management/master_data.py` holds the real fleet (2 companies, 2 fuel types, 14
  models, 12 people, Ecoflame serving both, 15 assets) and `load`, which only adds. Cross-checked against
  the owner's templates: every asset and model matches after the D-10/D-11 corrections; only the
  generator's and crane's tanks differ (blank in the template, 100 L by the owner). Not yet run on a
  site (3.2 and 3.3). Next: 3.2.
- `07/10/2026`: 3.2 The test site now loads the real fleet: Phyllis and Vishal (both companies), the
  Kanha-only test approver, and the test Fleet Admin; the holder requests and drives; no history or
  open orders. Rebuilt on MariaDB: 2 companies, 2 fuel types, 14 models, 12 people, Ecoflame (Kabete,
  also Kanha, address on file), 15 assets; Phyllis and Vishal see 15 vehicles, the Kanha approver 10;
  all three see Ecoflame; dd/mm/yyyy; 5 logins checked. Sample-data, shared-station, and permission
  tests pass. Test site left up for a look. Next: 3.3.
- `07/10/2026`: 3.3 `tests/test_master_data.py` (Properties 3 and 4) passes 5/5 on the rebuilt MariaDB test
  site, which keeps its data afterwards. The app folder had been switched to 010 and then 008 by a paused
  session (008 now merges 009 and migrated the main site at 13:01, removing this branch's station table
  there; no records exist on the main site). Owner: switch back after this work. Main-site migrations
  skipped from here until Phase 4. Next: 3.4.
- `07/10/2026`: 3.4 `tests/test_real_fleet_routes.py` (Property 7) passes 3/3 on the MariaDB test site: Phyllis
  orders for a Kabete and a Kanha vehicle with the holder driving and herself as representative, approves
  green, sends red with a reason to Vishal, who signs off; the slip shows Ecoflame's address and email.
  Each test uses its own vehicles (an earlier test's open order would turn the next red). Next: 3.5.
- `07/10/2026`: 3.5 Browser-test facts and CLAUDE.md now describe the real fleet (Phyllis, Vishal, the Kanha-only
  approver, Ecoflame, KAY222A); setup checks each user's companies as an exact set. Playwright 24/24 on a
  rebuilt test site, confirmed by an independent verifier (PASS). Known limitation: the tenancy list check
  cannot tell users apart now that Phyllis holds both companies; the acceptance spec proves the split.
  Part 2 complete. Next: 4.1.
