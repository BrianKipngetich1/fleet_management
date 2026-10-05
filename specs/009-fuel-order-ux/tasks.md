# Fuel Order experience: tasks

## Phase 1: Entry form

**Tracer:** a Fleet User enters an order in four clear sections, sees the selected vehicle's read-only facts, and records a partial quantity and its reason only when choosing Partial authorization.

- [x] 1.1 Arrange the four sections, wide-screen columns, narrow-screen stacking, asset summary, meter labels, vehicle-only gauge fields, native image preview, and collapsible system details.
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 1.8_
- [x] 1.2 Add the conditional partial-authorization reason and server validation before an order leaves Draft, while keeping the current quantity and approval rules.
  - _Requirements: 1.4, 3.3_
- [x] 1.3 Cover the entry form and partial-authorization cases with focused tests.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 3.3_
- [x] 1.4 Walk through the entry form as a Fleet User at wide and narrow sizes, with a vehicle, a generator, a request photo, and both quantity choices.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_
- [x] 1.5 Refine the entry layout for three/two/one responsive columns, a read-only asset summary, and a dedicated quantity/approval area with the single flagged-reasons panel using existing fields.
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.8_
- [x] 1.6 Keep request date and time server-supplied, and refresh or clear asset-dependent readings, evidence, assignment suggestions, and station selection when Asset changes; test defaults, read-only snapshots, and allowed edits.
  - _Requirements: 1.2, 1.6, 3.1_

## Phase 2: Signal panel

**Tracer:** a person entering an order sees one current server-backed explanation after the readings and quantity inputs that affect it, including what is missing and what action is available.

- [x] 2.1 Use one server calculation for save, approval, and unsaved preview; return detailed reasons with their readings, comparison, limit, economy source, and next action; remove the repeated form alert.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2_
- [x] 2.2 Add focused checks for incomplete previews, matching preview/save results, reason explanations, and server authority over client-supplied signal values.
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3_
- [x] 2.3 Walk through green and red orders as the Fleet User and the sent-up order as a permitted Fleet Approver; record the observed panel behavior.
  - _Requirements: 2.1, 2.2, 2.3, 2.6, 3.3_
- [x] 2.4 Distinguish vehicle target fuel economy from a recent observed average, explain the own-trend direction and equivalent units, and make both distance-only explanations explicit about sources and estimates without changing their rules.
  - _Requirements: 2.4, 2.5, 3.1, 3.2_

## Phase 3: Full-tank mileage check

**Tracer:** a vehicle order shows a separate comparison preferring the latest submitted fueling linked to a Full-authorized order, falling back to the existing Previous Entry when needed, and leaving that existing check unchanged.

- [x] 3.1 Select the latest submitted, non-cancelled vehicle Fueling Transaction linked to a Full-authorized Fuel Order and capture its transaction and order names, actual odometer, and fueling date/time in the server signal snapshot; do not use the prior gauge or the transaction's Full Tank Confirmed field to select the baseline.
  - _Requirements: 3.1, 3.2, 4.1, 4.3, 4.5, 4.6_
- [x] 3.2 Add the separate distance comparison, reason explanation, and approved freeze using the agreed current-gauge estimate; prefer the Full baseline, fall back to and identify Previous Entry, skip only when neither source exists, and show a red cannot-calculate reason for unusable inputs, unavailable economy, or zero estimated consumption.
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
- [x] 3.3 Test no partial fueling, later partial fuelings, a newer Full-authorized fueling, fallback to Previous Entry when no Full baseline exists, no baseline at all, cancelled transactions, exact and beyond-margin values, and differing old/new results; prove the existing “Mileage does not add up” result and comparator remain unchanged; cover generators, unavailable economy, the answered invalid-input cases, and approved snapshot freezing.
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
- [x] 3.4 Walk through a red full-tank comparison and a generator order on the disposable test site; confirm the source and result shown to the person match the saved server result.
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 4.5, 4.6_

## Phase 4: Issue and action history

**Tracer:** a permitted reviewer can follow each saved issue, explanation, decision, cancellation, extension, slip print, and actual fueling without losing the original facts.

- [x] 4.1 Add append-only issue and action history records, including signal facts, explanations, decisions, partial-authorization reasons, actors, times, and evidence references, with reads limited by the linked order's existing permissions.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.5_
- [x] 4.2 Require a written reason through the existing cancel action for permitted cancellations, and record each extension, slip print or reprint, and submitted or cancelled actual fueling with its source facts and evidence links.
  - _Requirements: 3.3, 3.4, 5.2, 5.3, 5.4, 5.5_
- [x] 4.3 Test issue snapshot timing and deduplication, resolution, immutable earlier events, all action links, current cancellation permissions, and location-scoped history access.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5_
- [ ] 4.4 Walk through one resolved signal issue, one cancellation, one extension and reprint, and one completed fueling; confirm each appears once with its original facts.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5_

## Progress log

- 2026-10-02 — 1.1: reordered the DocType into four primary sections with responsive columns, a read-only asset summary, dynamic meter wording, vehicle-only gauge fields, and collapsible system details. Test-site DocType metadata checks pass; Desk walkthrough awaits the test account inventory.
- 2026-10-02 — 1.2: added the conditional Partial reason and server enforcement before leaving Draft; existing partial slip test now supplies its reason. The focused order integration tests pass.
- 2026-10-02 — 1.3: added focused layout and Partial authorization checks; 28 Fuel Order integration tests pass on the disposable site.
- 2026-10-02 — 2.1: replaced the repeated alert and raw fields in the entry path with one server-backed panel; save, approval, and preview share the server result builder.
- 2026-10-02 — 2.2: added waiting-state, parity, explanations, source-input snapshot, server-authority, and approval-time recalculation checks; 16 signal integration and 34 signal unit tests pass on the disposable site. The focused DocType reload succeeded after full migration stopped during unrelated orphan cleanup (`Module None not found`).
- 2026-10-05 — Review clarified that the new baseline comes from the linked Fuel Order's Full authorization, not the transaction's Full Tank Confirmed field or the prior gauge. The requester confirmed the current order's gauge is used to estimate fuel used. Updated the query and regression assertions; Python compilation and spec-check pass, but the focused disposable-site tests have not yet rerun, so task 3.1 remains unchecked. The invalid tank/gauge and zero-consumption behaviors still need decisions.
- 2026-10-05 — The requester clarified that the Full-authorized source is preferred and the existing Previous Entry is the fallback when no Full baseline exists; identify which source was used. The server snapshot, panel label, and fallback regression assertion are added. Static checks pass; disposable-site database verification remains pending.
- 2026-10-05 — The requester confirmed that unusable tank capacity or current gauge data with a selected baseline, and a 100% gauge with zero estimated consumption, each produce a red cannot-calculate reason. A gauge not yet entered remains in the existing waiting state. Implemented the independent server-side baseline comparison and its captured result; focused tests are added, with disposable-site verification pending.
- 2026-10-05 — The preferred Full-authorized fueling baseline, Previous Entry fallback, current-gauge estimate, red cannot-calculate cases, unchanged old check, preview/save parity, and approved freeze passed 86 focused tests on the disposable MariaDB site. Role-based Desk walkthrough remains pending because the local test login inventory is absent.
- 2026-10-05 — 4.2: added append-only events for workflow decisions, separate Partial authorization, reasoned cancellations, every slip print, validity extensions, and submitted/cancelled actual fueling with captured source facts and evidence links. Cancellation permissions remain unchanged. The focused disposable-site suite passed; saved issue snapshots and resolution remain gated on the open timing decision.
- 2026-10-05 — Re-ran the six focused test modules on fleet_management-test.localhost (MariaDB): 144 passed and one existing concurrency proof was skipped by its environment guard. The shared Desk server still serves the separate feature/008-overseer-reports checkout; passwordless test login exists, but a fresh rebuild needs the missing local 001 CREDENTIALS.md.
- 2026-10-05 — 1.5: regrouped the request fields, paired meter and evidence columns, kept approval notes to two columns, added the read-only responsive asset summary, and placed the signal/history sections before System Details. The focused `test_fuel_order` module passed 28/28 on the disposable MariaDB site after a test-site-only `reload-doc`. JSON, JavaScript syntax, Python compilation, spec-check, and diff checks pass; visual walkthrough remains pending because the shared Desk server serves 008.
- 2026-10-05 — 4.1 and 4.3: signal history now records the first saved Red result, snapshots changed issue explanations and relevant readings or limits, deduplicates unchanged saves, records a linked resolution on a later Green save, and starts a new issue episode if Red returns. Decision events link to the issue snapshot they explain. The six focused MariaDB modules passed 144 tests with one existing concurrency test skipped by its environment guard. Desk walkthrough remains pending because the shared server serves feature/008 and the local test-site rebuild needs the missing 001 `CREDENTIALS.md`.
- 2026-10-05 — Added explicit coverage for a changed gauge limit while the reading stays fixed; the Fuel Order history module passed again, 12/12, on the disposable MariaDB site.
- 2026-10-05 — 1.6: removed the premature Request Date and Time default so the server sets it on first save and preserves it; asset changes now clear dependent readings/evidence/suggestions and ignore stale asynchronous fact responses. Metadata and server-facts tests passed in `test_fuel_order` (28/28), including required/editable participants, read-only snapshots, station suggestion only for one eligible station, and request-time persistence. Browser verification remains pending.
- 2026-10-05 — 2.4: separated vehicle target, observed recent average, and applicable economy source in the summary; added directional trend wording with km/L and equivalent units, and clarified baseline/date/estimate details for both distance checks. Unit and integration coverage passed, including 10 versus 5 km/L at 15%, target fallback, no false observed wording, and unchanged legacy mileage boundaries.
- 2026-10-05 — Final focused rerun on the disposable MariaDB test site: 145 passed and one existing concurrency test skipped by its environment guard across the six phase modules. Static checks pass. Wide/medium/phone Desk walkthroughs for Fleet User and Fleet Approver remain pending because the isolated browser could not start Chrome; no form screenshots or visual behavior are claimed.
- 2026-10-05 — Visual walkthrough on the isolated 009 checkout completed Phases 1–3 at 1440, 900, and 390 px: checked the three/two/one-column layout, editable participant fields, asset-driven driver/location refresh, no-previous-entry display, target fallback, Partial visibility/reason, vehicle/generator controls, native meter/gauge photo preview, server waiting/Red/Green panels, and the full-tank comparison. Fleet Approver reviewed a saved pending Red order read-only. The preview exposed that Desk sends numeric fields as strings; server normalization and a 19th signal integration regression test fix it. An existing order predating event capture showed an empty history panel, so task 4.4 remains pending. Latest six focused modules: 146 passed, one existing concurrency test skipped by its environment guard.
- 2026-10-05 — Follow-up display fix: System Details now hides the default zero Previous Odometer/Hour Meter and blank Previous Entry Date when the server explicitly reports no Previous Entry; focused DocType metadata assertions added.
