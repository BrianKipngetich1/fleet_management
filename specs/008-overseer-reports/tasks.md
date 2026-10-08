<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property check also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->

# Fleet Oversight Reports: tasks

## Phase 1: Fueling summary and recorded spend

**Tracer:** an overseer can review monthly litres, transaction counts, and recorded KES spend, inspect each fueling and its invoice prices, and export the same filtered rows.

- [x] 1.1 Add invoice total and optional printed unit price to new Fueling Transactions; require a positive total on submission while leaving existing submitted transactions unchanged.
  - _Requirements: 1.4, 5.1_
- [x] 1.2 Build Fueling Summary with inclusive date filters, monthly litres/counts/spend, recorded and unavailable amount handling, calculated and printed prices, detail rows, monthly trend, and standard export; cap the implementation at three reports.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 3.4_
- [x] 1.3 Restrict report roles, location filter choices, report rows, linked records, and exports to the existing Fleet Approver and Fleet Admin access rules.
  - _Requirements: 4.1, 4.2_
- [x] 1.4 Check the summary against source transactions from two locations, including a legacy row with no amount and a cancelled transaction.
  - _Requirements: 1.3, 1.4, 1.5, 3.4, 4.1, 4.2_

## Phase 2: Asset performance and history

**Tracer:** an overseer can follow one asset's requests and fueling history, inspect vehicle efficiency across a selected period, and see generator litres as delivered fuel with its hour-meter readings.

- [x] 2.1 Build Asset Performance with asset and period filters, linked Fuel Orders and Fueling Transactions, people, fuel, station, quantities, and every requested status.
  - _Requirements: 2.1_
- [x] 2.2 Use the existing full-to-full interval facts for vehicle efficiency, include partial fills and a prior full fill outside the display period, apply the required rating bands, and show generator delivered litres and operating hours.
  - _Requirements: 2.2, 2.3, 2.4_
- [x] 2.3 Apply date, location, asset, fuel type, and station filters consistently and preserve location access in links and exports.
  - _Requirements: 1.1, 1.5, 4.1, 4.2_
- [x] 2.4 Check request status, boundary dates, interval edge cases, changed targets, and generator labels against the source records.
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

## Phase 3: Requests, discrepancies, and audit

**Tracer:** an overseer can review decisions, warnings, recorded discrepancies, and cancelled fuelings with their reasons, actors, dates, and source links.

- [x] 3.1 Add location-scoped Fueling Discrepancy records with type, details, reason, server-set recorder and date, and a link to the unchanged Fueling Transaction.
  - _Requirements: 3.3, 4.1, 5.1_
- [x] 3.2 Build Requests & Audit for decisions, withdrawals, warnings, fulfillment status, discrepancies, and cancelled transactions, with source links and standard export.
  - _Requirements: 1.1, 1.5, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2_
- [x] 3.3 Add the Fleet Oversight Workspace linking the three reports and visible to Fleet Approver and Fleet Admin.
  - _Requirements: 1.6, 4.1_
- [x] 3.4 Check that canceled transactions appear in Requests & Audit but are absent from summary and performance totals, and that current request and fueling workflows still enforce their existing rules.
  - _Requirements: 3.4, 5.1_
- [x] 3.5 Show Green and Red warning statuses in their matching flag colours on Requests & Audit while preserving the status text and export values.
  - _Requirements: 3.2_

## Phase 4: Report sections and vehicle trends

**Tracer:** an overseer can open focused approvals, flags, and discrepancy sections; identify warning status directly in fueling rows; and review a selected vehicle's full history and monthly trends.

- [x] 4.1 Add distinct Approvals, Flag Reports, and Discrepancy Reports sections to Requests & Audit; show every flagged request's status, reason, and source links.
  - _Requirements: 3.5, 3.6, 4.1, 4.2_
- [x] 4.2 Apply a full-row Green/Red warning gradient to linked Fueling Summary transaction rows; leave unflagged rows, monthly totals, status text, and exports unchanged.
  - _Requirements: 1.5, 1.7, 4.1, 4.2_
- [x] 4.3 Extend Asset Performance to default to all retained asset history with optional date filters and graph monthly delivered litres alongside valid-interval km/L efficiency for vehicles.
  - _Requirements: 2.1, 2.2, 2.5, 4.1, 4.2_
- [ ] 4.4 Verify section contents and filters, approved and non-approved flagged requests, row colors, asset history, trend calculations, and existing exports and access rules.
  - _Requirements: 1.5, 1.7, 2.1, 2.5, 3.5, 3.6, 4.1, 4.2, 5.1_

## Progress log

- `08/10/2026`: Task 4.3 complete. Asset Performance now defaults to all retained history for the selected asset; either date bound can be set independently. Monthly vehicle efficiency is the weighted distance/qualifying-litre ratio across valid full-to-full intervals closing that month, and a separate km/L chart appears only for months with valid intervals; the delivered-litres chart remains. On the disposable test site, 2 unit tests and 2 integration tests passed for optional bounds, unbounded history, weighted intervals, and prior full-fill boundaries. Main and test-site migrations passed with Locale matched; JSON validity, Python compilation, JavaScript syntax, diff checks, and spec-check passed. Ruff is unavailable. No test records were created on the main site. Next: task 4.4 verification.

- `08/10/2026`: Task 4.2 complete. Fueling Summary carries linked Fuel Order warning status and reasons as non-column row metadata. Its formatter shades every cell of warned transaction rows with a Green/Red gradient; Green rows without a warning reason and monthly totals stay neutral, and export columns are unchanged. On the disposable site, the warning metadata unit test and existing filter/export integration test passed. Main and test-site migrations passed with Locale matched; JSON validity, Python compilation, JavaScript syntax, diff checks, and spec-check passed. Ruff is unavailable. No test records were created on the main site. Next: task 4.3.

- `08/10/2026`: Task 4.1 complete. Added section buttons and a shared Section filter for Approvals, Flag Reports, Discrepancy Reports, and All Audit; the selected rows remain the standard export source, and All Audit retains cancellation rows. Flag Reports include Green/Red requests only when a warning reason exists, with request/decision status and any linked fueling transaction. The disposable test site passed all 3 Requests & Audit unit and 3 integration tests, including section filters, reasons, linked transactions, discrepancy-only rows, exports, and cancellation status. Main and test-site migrations passed with Locale matched; JSON validity, Python compilation, JavaScript syntax, diff checks, and spec-check passed. Ruff is unavailable. No test records were created on the main site. Next: task 4.2.

- `03/10/2026`: Task 3.5 complete. Requests & Audit formats Green statuses with the green flag color and Red statuses with the red flag color while preserving status and export values. Main and disposable test-site migrations exited successfully; JS syntax, all 30 JSON files, diff checks, and spec-check passed (spec-check retains its existing test-naming warnings). Ruff/pre-commit were unavailable. A Desk walkthrough was skipped because agent-browser could not create its socket under read-only `/run/user/1000/agent-browser`; its diagnostic check passed. No test records were created on the main site.

- `02/10/2026`: The requester approved the requirements earlier and the current design in this conversation; approval attribution awaits confirmation of the full name. Phase 1 is in progress.
- `02/10/2026`: Task 1.1 complete. Added optional KES invoice fields, positive-total submission validation, submitted-value immutability, and positive synthetic sample invoices. The test-site migration and Fueling Transaction tests passed (31 integration tests, 2 unit tests; 1 concurrency test skipped). JSON validation, Python compilation, diff checks, and spec-check passed; lint was skipped because Ruff and pre-commit are unavailable. Next: task 1.2.
- `02/10/2026`: Task 1.2 complete. Added the Fueling Summary Script Report with inclusive date filters, month totals, recorded-only spend and calculated prices, separate printed prices, unavailable legacy amounts, detail rows, a monthly recorded-spend trend, and the standard export result. The query uses the existing location scope and excludes non-submitted transactions. Test-site migration and 2 report unit checks passed; live report runs included the 30/09/2026 boundary and returned only Mombasa rows for a Mombasa filter. JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed; lint was skipped because Ruff and pre-commit are unavailable. Next: task 1.3.
- `02/10/2026`: Task 1.3 complete. Limited the report to Fleet Approver and Fleet Admin, enabled the approver's existing source-record export permission, and verified location scoping for report rows, linked records, and standard CSV exports. The disposable test site passed 2 report unit tests and 4 access/filter integration tests, including access for both permitted locations and denial of an out-of-scope location. JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed; Ruff/pre-commit and the main-site migration were skipped. Next: task 1.4.
- `02/10/2026`: Task 1.4 complete. Compared report details and monthly count/litre totals with submitted source rows from Nairobi and Mombasa. The disposable test temporarily cancelled an unreferenced source transaction, confirmed it disappeared from report totals, verified a legacy row shows an unavailable amount, and rolled back the cancellation. Test-site migration and the report suite passed (2 unit, 5 integration); JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed. Ruff/pre-commit were skipped because the tools are unavailable. After Phase 1, the main-site migration also passed and Locale matches; no test records were added there. Phase 1 is complete; Phases 2–3 are not started.
- `02/10/2026`: Task 2.1 complete. Added Asset Performance with asset/date filters, in-period Fuel Order and submitted Fueling Transaction rows, source links, people, fuel/station, requested/authorized/delivered quantities, and request/fulfillment/cancellation statuses. Main-site migration, JSON validity, Python compilation, diff checks, and spec-check passed; Ruff was unavailable. Test-site report verification and edge-case checks remain for task 2.4. No test records were created on the main site. Next: task 2.2.
- `02/10/2026`: Task 2.2 complete. Added stored full-to-full efficiency and qualifying-litre facts, target-change detection using interval snapshots, inclusive green/orange/red bands, unavailable states, and distinct vehicle odometer/generator hour-meter columns. Main-site migration, report JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed; Ruff and pre-commit were unavailable. Test-site interval and generator checks remain for task 2.4. No test records were created on the main site. Next: task 2.3.
- `02/10/2026`: Task 2.3 complete. Added location, fuel type, and station filters to the asset/date filters; the monthly delivered-litres trend, monthly figures, detail rows, and standard export now derive from the same filtered data. Existing Fuel Order and Fueling Transaction location query helpers and location-filter validation protect report rows and source links. Main-site migration, JSON validity, Python compilation, JavaScript syntax, diff checks, and spec-check passed; Ruff was unavailable. Test-site access/filter/export checks remain for task 2.4. No test records were created on the main site. Next: task 2.4.
- `02/10/2026`: Task 2.4 complete. On the disposable MariaDB test site, all 8 Asset Performance unit tests and 5 integration tests passed against seeded source records, covering statuses and links, inclusive activity boundaries, a prior full fill and partial fill, changed-target rating suppression, generator labels, filters, location access, trends, and CSV export. Main-site migration completed with Locale matched; Python compilation, report JSON, JavaScript syntax, diff checks, and spec-check passed; Ruff and pre-commit were unavailable. The test-site build seeded its data but hit a MariaDB concurrent-update error at final scheduler activation; a test-site migration resynced report metadata and the report suite then passed. Desk walkthrough was skipped because `scripts/ab-login.sh` cannot resolve the extensionless `./target` import in `e2e/sid.ts`; the attempted browser page was empty. No test records were created on the main site. Phase 2 is complete; next: draft the Phase 3 prompt.
- `03/10/2026`: Task 3.1 complete. Added location-scoped Fueling Discrepancy records with required type, details, reason, and server-set recorder/date; the linked transaction remains unchanged. Main-site migration and the existing disposable test site's migration passed. The test-site rebuild was blocked because the configured Phase 001 `CREDENTIALS.md` is absent, so the existing disposable MariaDB site was migrated instead. Both discrepancy integration checks passed with records created by the tests on that site. JSON validity, Python compilation, and spec-check passed; Ruff and pre-commit are unavailable. No test records were created on the main site. Next: task 3.2.
- `03/10/2026`: Task 3.2 complete. Added Requests & Audit with separate request, decision, fueling, and discrepancy rows; event-date, location, asset, fuel, and station filters; request and fulfillment statuses; decision/warning reasons; discrepancy detail and server audit fields; cancelled status; source links; and standard CSV export from the same result. Existing location conditions and fulfillment-status logic are reused. Main-site migration passed with Locale matched; the existing disposable MariaDB test site was migrated because a fresh rebuild still lacks the configured Phase 001 `CREDENTIALS.md`. Two unit and two integration tests passed, covering request/rejection decisions, warning details, discrepancy links, filters, location scope, no-discrepancy wording, and CSV export. JSON, Python, JavaScript syntax, diff checks, and spec-check passed; Ruff and pre-commit are unavailable. No test records were created on the main site. Next: task 3.3.
- `03/10/2026`: Task 3.3 complete. Added the Fleet Oversight Workspace with links to Fueling Summary, Asset Performance, and Requests & Audit. Its role list and all three report role lists contain only Fleet Approver and Fleet Admin. The disposable MariaDB test site confirmed the workspace appears for both roles and not Fleet User; exactly three report links are present. Main-site migration passed with Locale matched; the existing test site was migrated because the credential inventory needed for a fresh build is absent. JSON validity, Python compilation, spec-check, and the workspace integration check passed; Ruff and pre-commit are unavailable. No test records were created on the main site. Next: task 3.4.
- `03/10/2026`: Task 3.4 complete. On the disposable MariaDB test site, Requests & Audit rejected a reversed date range and returned valid results after correction; the cancellation regression confirmed a cancelled transaction remains visible with `Cancelled` status and contributes no summary or performance row or total. Requests & Audit (2 unit, 3 integration), Asset Performance (8 unit, 5 integration), Fuel Order request/decision/warning (43 integration), Fueling Transaction (2 unit, 31 integration; one concurrency check skipped), discrepancy (2 integration), and Workspace (1 integration) test modules passed. One separate Fueling Summary integration assertion failed because it expects a seeded legacy transaction without an invoice amount, and the current seed has no such row; the cancellation regression itself passed. Main and test migrations passed with Locale matched; the existing test site was used because the credential inventory required for a fresh rebuild is absent. MariaDB and `dd/mm/yyyy` were confirmed. JSON validity (18 files), Python compilation, JavaScript syntax, diff checks, and spec-check passed; Ruff and pre-commit are unavailable. No test records were created on the main site. The full app suite, Desk walkthrough, and pre-PR pipeline were not run. Automatic review blocked deleting the disposable test site's database while the credential inventory is missing, so the existing test site remains. Phase 3 is complete; await a request to publish.
