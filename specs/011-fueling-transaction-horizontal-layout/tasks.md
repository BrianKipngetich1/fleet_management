# Fueling Transaction side-by-side layout and summary: tasks

## Phase 1: One-page comparison

**Tracer:** Staff can see the LPO on the left, invoice entry on the right, and a baseline/efficiency
summary underneath.

- [x] 1.1 Arrange and verify the read-only LPO context, invoice entry, responsive layout, live litre summary, and applicable efficiency; preserve existing checks.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - _Properties: 1, 2, 3_
- [x] 1.2 Fit the LPO details, invoice fields, and baseline/efficiency summary into one desktop view without vertical scrolling; keep the narrow-screen layout and existing transaction checks.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - _Properties: 1, 2, 3_
- [x] 1.3 Add clear spacing and a divider between the LPO and invoice panels on desktop; remove the divider when the panels stack on narrow screens.
  - _Requirements: 1.1, 1.4_
  - _Properties: 1, 3_

## Progress log

One line per finished task, newest last.
2026-10-06 — Built and checked the side-by-side form on the disposable test site. The fueling test module passed (5 unit, 38 integration; one opt-in concurrency check skipped); desktop, narrow-screen stacking, live litre status, tax totals, and location permission behavior were verified. Main site untouched.
2026-10-06 — Compact horizontal refinement verified at 905×752: LPO facts on the left, all transaction fields on the right, and baseline/status/efficiency visible below without scrolling. Narrow view stacks the panels. Test-site migration and asset build completed; JSON, JavaScript syntax, diff whitespace, and spec checks passed. Main site untouched.
2026-10-06 — Increased desktop separation between the LPO and invoice panels with a subtle divider; removed the divider at the narrow-screen breakpoint. Verified on the disposable test site; main site untouched.
