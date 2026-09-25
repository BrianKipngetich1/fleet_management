<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Only the generator asset type and hour-meter reading exist; built under the wider Phase 0.
-->

# Phase 8 — Generators

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `07bf479` (D-2, D-16) |
| Status | Not started — partly built (asset type, hour meter) |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-14 |
| Credential inventory | — |

## What this phase makes true

A generator is ordered by the litres it needs, never as a full tank. At fueling the Fleet User
records the hour meter and the tank level before and after, in litres or percent. The system
works out litres per operating hour from the tank's movement between fuelings, flags a
before-plus-delivered-versus-after mismatch over the tolerance, and ignores cancelled fuelings.

## Build state by criterion

| Criterion | State | Carried evidence / gap |
|---|---|---|
| AC-14 — generator litres/hour from measured inventory, cancelled excluded | Partly built by Phase 0 | Generator asset type and hour meter exist; hour-meter rollback is refused (Phase 2). **Gap:** no maximum-litre order check, tank levels, unit conversion, reconciliation, or litres/hour |

## The rule, as observed

Not yet observed in this phase.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Tank levels | Fields with a unit select | Conversion to litres from capacity |
| Consumption | Shared interval calculation | Inventory-based formula in the spec |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Order 100 L for a generator; fuel 101 L, then 103 L | 101 L within tolerance; 103 L flagged | AC-14 |
| 2 | Record pre/post levels once in litres and once in percent | Both normalized to litres from capacity | AC-14 |
| 3 | First fueling, then a second after 10 operating hours with 40 L consumed | First is a baseline; second gives 4 L/h against the target band | AC-14 |
| 4 | Pre-level plus delivered differs from post-level by more than the tolerance | Flagged with explanation | AC-14 |
| 5 | Cancel the second fueling | It drops out of litres/hour | AC-14 |

**How to run it.** Row 1's rollback half is covered by Phase 2 tests; all rows need new tests.
Desk walkthrough: generator order, level entry in both units, result.

**Result:** Not yet run in this phase.

## What we learned that the plan did not predict

- Nothing yet.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Start after Phase 7 closes.
