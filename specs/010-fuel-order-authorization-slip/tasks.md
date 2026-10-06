# Fueling Transaction layout and fuel analysis: tasks

## Phase 1: Transaction entry and read-only order context

**Tracer:** Staff can enter and review one Fueling Transaction with its approved LPO context,
without modifying the LPO or looking up a physical document.

- [ ] 1.1 Show the approved LPO details needed for transaction entry as a read-only context panel
  on the existing Fueling Transaction.
  - _Requirements: 1.1, 1.2, 1.3_
- [ ] 1.2 Reorganize the existing transaction fields into a clear entry sequence, fill station
  and fuel from the selected LPO, show only the correct meter for the linked asset, and retain
  the existing time, evidence, and transaction validations.
  - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.8_
- [ ] 1.3 Show a live litre variance status against the LPO's existing estimated litres and
  include the same status in transaction review.
  - _Requirements: 1.7_
- [ ] 1.4 Verify the transaction reads LPO context without writing to or changing any LPO data,
  and preserves existing role, location, order-link, validity, station, and evidence checks.
  - _Requirements: 1.2, 1.8_

## Phase 2: Fuel cost and analysis

**Tracer:** Reviewers can analyze fuel usage, litre variances, efficiency, and pre-tax fuel
spend from permission-filtered transaction records.

- [ ] 2.1 Record the fuel-only pre-tax amount in KES, require both litres and pre-tax amount
  before saving a new transaction, calculate tax at 8% and the invoice total, and leave
  historical amounts unfilled.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.8, 2.9_
- [ ] 2.2 Provide filtered analysis of actual and LPO-estimated litres, variance status, pre-tax
  spend, cost per litre, vehicle efficiency, generator litres per operating hour, and full-tank
  exceptions, with export under existing permissions.
  - _Requirements: 1.7, 2.4, 2.5, 2.6, 2.7, 2.8, 2.10_
- [ ] 2.3 Verify save is blocked when either litres or pre-tax amount is missing; check tax and
  total calculations, cost analysis, vehicle and generator
  efficiency, litre variance thresholds, missing LPO estimates, report filters, historical
  records without costs, export permissions, and existing transaction controls.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

## Progress log

One line per finished task or phase, newest last.
