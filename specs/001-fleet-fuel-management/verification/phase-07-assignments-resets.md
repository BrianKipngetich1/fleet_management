<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Assignment history was built under the wider 2026-09-18 Phase 0; its evidence is carried here.
-->

# Phase 7 — Assignments and meter resets

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `07bf479` (D-11, D-16) |
| Status | Not started — assignments built by Phase 0; resets not built |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-12, AC-13 |
| Credential inventory | — |

## What this phase makes true

A vehicle's custodian and location have a dated history without overlaps, and an approved order
keeps the assignment it was approved under. When a meter is replaced or wrongly read, Fleet
Admin records a reset with reason and evidence, and calculations restart from the new reading.

## Build state by criterion

| Criterion | State | Carried evidence / gap |
|---|---|---|
| AC-12 — assignments do not overlap; snapshots survive reassignment | Built by Phase 0 | Three assignment tests (accepted, overlap rejected, value at date) and the order's location-snapshot test; survival after reassignment is not asserted directly |
| AC-13 — Fleet Admin reset restarts the baseline | Not built | No Meter Reset; a lower reading is always refused (Phase 2) |

## The rule, as observed

Not yet observed in this phase. Assignments and resets add no order state edges.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Assignment history | Child table with from/until, `track_changes` | Non-overlap check and value-at-date lookup |
| Reset authority | Submittable Meter Reset with Fleet Admin permission | Baseline restart in the interval calculation |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Add two assignment periods that overlap, then two that do not | Overlap refused; non-overlapping accepted | AC-12 |
| 2 | Approve an order, then reassign the vehicle | The order keeps the old custodian and location | AC-12 |
| 3 | As Fleet Admin, record a reset with date, old reading, new baseline, reason, and evidence; submit a fill below the old reading | Accepted; the next interval starts at the reset | AC-13 |
| 4 | Try the reset as Fleet User or Fleet Approver, and without a reason | Refused | AC-13 |

**How to run it.** Row 1 is asserted by `test_fleet_asset.py`; rows 2–4 need tests.
Desk walkthrough: reassignment and Fleet Admin reset.

**Result:** Not yet run in this phase. Row 1 passed under Phase 0.

## What we learned that the plan did not predict

- Nothing yet.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Start after Phase 6 closes.
