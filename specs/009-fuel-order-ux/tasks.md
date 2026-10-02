# Fuel Order experience: tasks

## Phase 1: Entry form

**Tracer:** a Fleet User enters an order in four clear sections, sees the selected vehicle's read-only facts, and records a partial quantity and its reason only when choosing Partial authorization.

- [x] 1.1 Arrange the four sections, wide-screen columns, narrow-screen stacking, asset summary, meter labels, vehicle-only gauge fields, native image preview, and collapsible system details.
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 1.8_
- [x] 1.2 Add the conditional partial-authorization reason and server validation before an order leaves Draft, while keeping the current quantity and approval rules.
  - _Requirements: 1.4, 3.3_
- [x] 1.3 Cover the entry form and partial-authorization cases with focused tests.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 3.3_
- [ ] 1.4 Walk through the entry form as a Fleet User at wide and narrow sizes, with a vehicle, a generator, a request photo, and both quantity choices.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

## Phase 2: Signal panel

**Tracer:** a person entering an order sees one current server-backed explanation beside the readings, including what is missing and what action is available.

- [x] 2.1 Use one server calculation for save, approval, and unsaved preview; return detailed reasons with their readings, comparison, limit, economy source, and next action; remove the repeated form alert.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2_
- [x] 2.2 Add focused checks for incomplete previews, matching preview/save results, reason explanations, and server authority over client-supplied signal values.
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3_
- [ ] 2.3 Walk through green and red orders as the Fleet User and the sent-up order as a permitted Fleet Approver; record the observed panel behavior.
  - _Requirements: 2.1, 2.2, 2.3, 2.6, 3.3_

## Phase 3: Full-tank mileage check

**Tracer:** a vehicle order shows a separate comparison from the latest confirmed full tank, while the existing Previous Entry check remains unchanged.

- [ ] 3.1 Add the latest full-tank baseline lookup, estimated-consumption calculation, distinct reason, visible source and result, and immutable approved snapshot; skip the check for generators and when there is no baseline.
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
- [ ] 3.2 Test no partial fueling, later partial fuelings, a newer full tank, no full-tank history, cancelled transactions, exact and beyond-margin values, differing old/new results, generators, unavailable economy, invalid inputs, and approved snapshot freezing.
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
- [ ] 3.3 Walk through a red full-tank comparison and a generator order on the disposable test site; confirm the source and result shown to the person match the saved server result.
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 4.5, 4.6_

## Phase 4: Issue and action history

**Tracer:** a permitted reviewer can follow each saved issue, explanation, decision, cancellation, extension, slip print, and actual fueling without losing the original facts.

- [ ] 4.1 Add append-only issue and action history records, including signal facts, explanations, decisions, partial-authorization reasons, actors, times, and evidence references, with reads limited by the linked order's existing permissions.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.5_
- [ ] 4.2 Require a written reason through the existing cancel action for permitted cancellations, and record each extension, slip print or reprint, and submitted or cancelled actual fueling with its source facts and evidence links.
  - _Requirements: 3.3, 3.4, 5.2, 5.3, 5.4, 5.5_
- [ ] 4.3 Test issue snapshot timing and deduplication, resolution, immutable earlier events, all action links, current cancellation permissions, and location-scoped history access.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5_
- [ ] 4.4 Walk through one resolved signal issue, one cancellation, one extension and reprint, and one completed fueling; confirm each appears once with its original facts.
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5_

## Progress log

- 2026-10-02 — 1.1: reordered the DocType into four primary sections with responsive columns, a read-only asset summary, dynamic meter wording, vehicle-only gauge fields, and collapsible system details. Test-site DocType metadata checks pass; Desk walkthrough awaits the test account inventory.
- 2026-10-02 — 1.2: added the conditional Partial reason and server enforcement before leaving Draft; existing partial slip test now supplies its reason. The focused order integration tests pass.
- 2026-10-02 — 1.3: added focused layout and Partial authorization checks; 28 Fuel Order integration tests pass on the disposable site.
- 2026-10-02 — 2.1: replaced the repeated alert and raw fields in the entry path with one server-backed panel; save, approval, and preview share the server result builder.
- 2026-10-02 — 2.2: added waiting-state, parity, explanations, source-input snapshot, server-authority, and approval-time recalculation checks; 14 signal integration and 34 signal unit tests pass on the disposable site. The DocType sync completed, but the migration exited during unrelated orphan cleanup (`Module None not found`).
