# Fueling Transaction entry layout: tasks

## Phase 1: Clearer transaction page

**Tracer:** Staff can read the Fuel Order down the left, enter and review transaction details
across rows on the right, and compare the signed documents in one row.

- [x] 1.1 Reflow the order facts and transaction rows, highlight the vehicle registration
  number, place the signed order to the left of the signed invoice, hide the time-source field
  on submitted records while retaining it for draft entry, and preserve the summary, responsive
  layout, and transaction checks.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1_

## Progress log

One line per finished task, newest last.

2026-10-06 — Reflowed the Fuel Order into a compact left column, highlighted the vehicle
registration number, arranged invoice details in wider rows, and placed signed order/invoice
side by side. Hid time-source on submitted records while retaining the choice on draft entry.
At 905×751 the summary fits on screen; at 700px the order stacks above the transaction. Test
site build and migration passed; main site untouched.
