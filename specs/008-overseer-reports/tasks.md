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

- [ ] 2.1 Build Asset Performance with asset and period filters, linked Fuel Orders and Fueling Transactions, people, fuel, station, quantities, and every requested status.
  - _Requirements: 2.1_
- [ ] 2.2 Use the existing full-to-full interval facts for vehicle efficiency, include partial fills and a prior full fill outside the display period, apply the required rating bands, and show generator delivered litres and operating hours.
  - _Requirements: 2.2, 2.3, 2.4_
- [ ] 2.3 Apply date, location, asset, fuel type, and station filters consistently and preserve location access in links and exports.
  - _Requirements: 1.1, 1.5, 4.1, 4.2_
- [ ] 2.4 Check request status, boundary dates, interval edge cases, changed targets, and generator labels against the source records.
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

## Phase 3: Requests, discrepancies, and audit

**Tracer:** an overseer can review decisions, warnings, recorded discrepancies, and cancelled fuelings with their reasons, actors, dates, and source links.

- [ ] 3.1 Add location-scoped Fueling Discrepancy records with type, details, reason, server-set recorder and date, and a link to the unchanged Fueling Transaction.
  - _Requirements: 3.3, 4.1, 5.1_
- [ ] 3.2 Build Requests & Audit for decisions, withdrawals, warnings, fulfillment status, discrepancies, and cancelled transactions, with source links and standard export.
  - _Requirements: 1.1, 1.5, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2_
- [ ] 3.3 Add the Fleet Oversight Workspace linking the three reports and visible to Fleet Approver and Fleet Admin.
  - _Requirements: 1.6, 4.1_
- [ ] 3.4 Check that canceled transactions appear in Requests & Audit but are absent from summary and performance totals, and that current request and fueling workflows still enforce their existing rules.
  - _Requirements: 3.4, 5.1_

## Progress log

- `02/10/2026`: The requester approved the requirements earlier and the current design in this conversation; approval attribution awaits confirmation of the full name. Phase 1 is in progress.
- `02/10/2026`: Task 1.1 complete. Added optional KES invoice fields, positive-total submission validation, submitted-value immutability, and positive synthetic sample invoices. The test-site migration and Fueling Transaction tests passed (31 integration tests, 2 unit tests; 1 concurrency test skipped). JSON validation, Python compilation, diff checks, and spec-check passed; lint was skipped because Ruff and pre-commit are unavailable. Next: task 1.2.
- `02/10/2026`: Task 1.2 complete. Added the Fueling Summary Script Report with inclusive date filters, month totals, recorded-only spend and calculated prices, separate printed prices, unavailable legacy amounts, detail rows, a monthly recorded-spend trend, and the standard export result. The query uses the existing location scope and excludes non-submitted transactions. Test-site migration and 2 report unit checks passed; live report runs included the 30/09/2026 boundary and returned only Mombasa rows for a Mombasa filter. JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed; lint was skipped because Ruff and pre-commit are unavailable. Next: task 1.3.
- `02/10/2026`: Task 1.3 complete. Limited the report to Fleet Approver and Fleet Admin, enabled the approver's existing source-record export permission, and verified location scoping for report rows, linked records, and standard CSV exports. The disposable test site passed 2 report unit tests and 4 access/filter integration tests, including access for both permitted locations and denial of an out-of-scope location. JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed; Ruff/pre-commit and the main-site migration were skipped. Next: task 1.4.
- `02/10/2026`: Task 1.4 complete. Compared report details and monthly count/litre totals with submitted source rows from Nairobi and Mombasa. The disposable test temporarily cancelled an unreferenced source transaction, confirmed it disappeared from report totals, verified a legacy row shows an unavailable amount, and rolled back the cancellation. Test-site migration and the report suite passed (2 unit, 5 integration); JSON, Python compilation, JavaScript syntax, diff checks, and spec-check passed. Ruff/pre-commit and main-site migration were skipped. Phase 1 is complete; Phases 2–3 are not started.
