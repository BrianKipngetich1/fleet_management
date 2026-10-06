<!--
Build each phase as a thin vertical slice. Every criterion is cited by at least one task. Add a
progress line only when a task is complete and committed.
-->

# Fuel Order authorization and fueling record: tasks

## Phase 1: Working-day validity and expiry enforcement

**Tracer:** A new approved order gets a saved deadline based on the configured working-day count,
displays its live expired state, and cannot be submitted as fueled outside that saved window.

- [ ] 1.1 Reuse the current validity setting, set the new-install default to two working days,
  apply the agreed company calendar, preserve the live site's saved three-day value, and keep
  approved deadlines and the separate transaction-entry rule unchanged.
  - _Requirements: 2.1, 2.2, 2.3, 2.6, 2.7_
- [ ] 1.2 Keep current audited extensions and enforce the saved validity boundary on transaction
  submission; show “EXPIRED — DO NOT FUEL” on the order after expiry.
  - _Requirements: 1.4, 2.4, 2.5, 6.1_
- [ ] 1.3 Test approval timestamps, working-day and holiday boundaries, expiry, extension,
  out-of-window submission, and preserved order deadlines.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

## Phase 2: Approved A5 authorization slip

**Tracer:** A permitted staff member prints an approved order as a one-page A5 authorization
that an attendant can verify without changing its vehicle or station.

- [ ] 2.1 Add the approved-only “Print Fuel Order” form action while preserving server-side
  approval, role, and slip-revision checks.
  - _Requirements: 1.1, 1.2, 1.3, 6.1_
- [ ] 2.2 Rebuild the print format with company identity, order and approval facts, vehicle,
  driver, representative, station name, operational location and full address, requested fuel,
  and prominent validity warning.
  - _Requirements: 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 6.2_
- [ ] 2.3 Add the actual fueling blanks, full-tank yes/no boxes, representative checks and
  signature, attendant confirmation, and revision footer; remove calculated fuel figures.
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_
- [ ] 2.4 Verify the print view and generated PDF on one A5 portrait page, including expired
  warning, address, generator meter wording, grayscale legibility, and unbroken signatures.
  - _Requirements: 1.4, 3.2, 4.5, 6.2_

## Phase 3: Transaction evidence and review values

**Tracer:** The signed slip and actual station values resolve to one Fueling Transaction linked
to the approved order; full-tank exceptions and qualified estimates are visible to reviewers.

- [ ] 3.1 Map the handwritten date/time, litres, correct meter, full-tank result, attendant, and
  representative confirmation to the existing order/transaction and signed-slip evidence.
  - _Requirements: 5.1, 5.2, 5.5, 6.1_
- [ ] 3.2 Show a not-full result for full-tank orders as a review exception, and derive the
  labelled before-fueling estimate only from valid confirmed-full transaction facts.
  - _Requirements: 5.3, 5.4_
- [ ] 3.3 Verify vehicle and generator records, full and partial authorizations, Yes and No
  outcomes, permission boundaries, order matching, and signed evidence on the disposable test
  site.
  - _Requirements: 1.1, 1.2, 2.4, 3.3, 3.5, 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2_

## Progress log

One line per finished task or phase, newest last.
