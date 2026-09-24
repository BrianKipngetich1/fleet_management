<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
The km/L interval was built under the wider 2026-09-18 Phase 0; its evidence is carried here.
-->

# Phase 4 — Partial fills and vehicle efficiency

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ uncommitted working tree on `develop` (D-2, D-12, D-16) |
| Status | Not started — partly built by Phase 0 |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-24, AC-25, AC-26 |
| Credential inventory | — |

## What this phase makes true

A partial vehicle fill happens only when the order authorizes an exact number of litres and
says why. Each full fill after the first rates the vehicle in kilometres per litre over every
litre since the last full fill, and colors the result green, orange, or red against its target.

## Build state by criterion

| Criterion | State | Carried evidence / gap |
|---|---|---|
| AC-24 — exact partial target and reason | Partly built by Phase 0 | The order accepts Partial with a positive litre quantity and prints it. **Gap:** no partial reason |
| AC-25 — km/L over all qualifying litres | Built by Phase 0 | `test_calculates_distance_litres_and_kilometres_per_litre`, `test_first_full_fill_is_baseline_and_second_creates_server_kpi`, KPI ordering test; Playwright `acceptance.spec.ts`; `phase-00-16-user-closing-full-kpi.png` |
| AC-26 — two-sided bands; no color after a target change | Not built | Band defaults exist in settings; no variance or rating is computed |

Also for this phase (spec Fueling Transaction data and request-time plausibility): the
transaction records no pre-fueling gauge.

## The rule, as observed

Not yet observed in this phase. Efficiency adds no state edges.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Interval calculation | Server-side controller on submit | Shared interval function reused by reports |
| Bands | Single DocType settings | Rating function |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Create a Partial order with no litres, then with litres but no reason | Both refused | AC-24 |
| 2 | Full fill at 10,000 km (60 L), partial of 10 L, full fill at 10,500 km with 40 L | Second full fill: 500 km, 50 qualifying litres, 10 km/L; client-sent KPI values ignored | AC-25 |
| 3 | Target 10 km/L; intervals giving 5%, 15%, and 25% under and over target | Green, orange, red, both directions | AC-26 |
| 4 | Change the vehicle's target inside an interval | Actual km/L shown with no color | AC-26 |

**How to run it.** Row 2 is asserted by the existing transaction tests; rows 1, 3, 4 need tests.
Desk walkthrough: partial order and slip, colored results.

**Result:** Not yet run in this phase. Row 2 passed under Phase 0.

## What we learned that the plan did not predict

- Nothing yet.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Build the partial reason, pre-fueling gauge, and bands.
