# Fueling Transaction layout and fuel analysis: tasks

## Phase 1: Transaction entry and read-only order context

**Tracer:** Staff can enter and review one Fueling Transaction with its approved LPO context,
without modifying the LPO or looking up a physical document.

- [x] 1.1 Show the approved LPO details needed for transaction entry as a read-only context panel
  on the existing Fueling Transaction.
  - _Requirements: 1.1, 1.2, 1.3_
- [x] 1.2 Reorganize the existing transaction fields into a clear entry sequence, fill station
  and fuel from the selected LPO, show only the correct meter for the linked asset, and retain
  the existing time, evidence, and transaction validations.
  - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.8_
- [x] 1.3 Show a live litre variance status against the vehicle's LPO estimated litres or the
  generator's approved LPO litres, and include the same status in transaction review.
  - _Requirements: 1.7_
- [x] 1.4 Verify the transaction reads LPO context without writing to or changing any LPO data,
  and preserves existing role, location, order-link, validity, station, and evidence checks.
  - _Requirements: 1.2, 1.8_
- [x] 1.5 Link the read-only order context to the existing authorization slip when the user can
  print the linked order; leave the Fuel Order and slip unchanged.
  - _Requirements: 1.1, 1.2, 1.3_

## Phase 2: Fuel cost and analysis

**Tracer:** Reviewers can analyze fuel usage, litre variances, efficiency, and pre-tax fuel
spend from permission-filtered transaction records.

- [x] 2.1 Record the fuel-only pre-tax amount in KES, require both litres and pre-tax amount
  before saving a new transaction, calculate tax at 8% and the invoice total, and leave
  historical amounts unfilled.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.8, 2.9_
- [ ] 2.2 Provide filtered analysis of actual and applicable LPO baseline litres, variance status,
  pre-tax spend, cost per litre, vehicle efficiency, generator litres per operating hour, and full-tank
  exceptions, with export under existing permissions.
  - _Requirements: 1.7, 2.4, 2.5, 2.6, 2.7, 2.8, 2.10_
- [ ] 2.3 Verify save is blocked when either litres or pre-tax amount is missing; check tax and
  total calculations, cost analysis, vehicle and generator
  efficiency, litre variance thresholds, missing LPO baselines, report filters, historical
  records without costs, export permissions, and existing transaction controls.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

## Progress log

One line per finished task or phase, newest last.

- `06/10/2026`: Added a permission-checked, read-only LPO context panel to Fueling Transaction;
  the focused MariaDB integration test and main-site migration passed. The first main migration
  removed the empty orphan `Fueling Discrepancy` DocType, three orphan standard reports, and the
  legacy `Fleet Oversight` workspace before failing on missing report-module metadata. Whether to
  restore those legacy records remains an unrelated follow-up.
- `06/10/2026`: Reorganized the transaction entry fields, populated station and fuel from the
  selected LPO, and showed only the linked asset's meter. The Fueling Transaction module passed
  31 MariaDB integration tests and 2 unit tests (1 opt-in concurrency test skipped); the Desk
  walkthrough passed for a vehicle and generator order. JSON, JavaScript syntax, spec, and
  whitespace checks passed. Ruff is not installed. A fresh test-site rebuild was blocked because
  the local ignored `specs/001-fleet-fuel-management/verification/CREDENTIALS.md` is missing; a
  test-site-only migration loaded the layout, and its orphan cleanup affected only the disposable
  test site. No task 1.2 migration ran on the main site; wait for the user's decision on the
  retired legacy reports/workspace before migrating it.
- `06/10/2026`: Added a live litre status beside invoice litres. Vehicles compare with estimated
  LPO litres; generators compare with approved LPO litres. The threshold cases, JSON, JavaScript
  syntax, spec check, and disposable test-site migration passed. Next: task 1.4 verification.
- `06/10/2026`: The Fueling Transaction suite passed 31 MariaDB integration tests and 2 unit
  tests; the opt-in concurrency test was skipped. The read-only context test confirmed the LPO
  stayed unchanged and other-location orders remained inaccessible. Existing approval, validity,
  station, and evidence checks passed. The Desk walkthrough needs the missing local test credentials.
  Next: resolve the earlier legacy-record cleanup decision before Phase 2.
- `06/10/2026`: Added a required pre-tax fuel amount in KES, live 8% tax and invoice total, and
  server-side checks requiring positive litres and amount on new transactions. Existing records
  received no estimated costs. On the test site, 33 transaction integration tests, 2 unit tests,
  26 Fuel Order tests, and 5 notification tests passed; one opt-in concurrency test was skipped.
  Migration, JSON, JavaScript, Python compilation, live calculation, and spec checks passed. Ruff
  is unavailable; Desk login still needs the missing local credentials file. Next: task 2.2.
- `06/10/2026`: Added a permission-gated link from the transaction's read-only order context to
  the linked Fuel Order's existing authorization slip. The link opens the existing print preview
  in a new tab; the Fuel Order and slip are unchanged. The focused suite passed 33 integration
  tests and 2 unit tests (one opt-in concurrency test skipped). JavaScript syntax and rendering
  smoke checks, spec check, and whitespace check passed. Ruff is unavailable. No migration ran.
