<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Nothing in this phase has been built beyond settings fields.
-->

# Phase 5 — Discrepancies and late entry

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `07bf479` (D-10, D-16) |
| Status | Not started — not built (settings fields only) |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-09, AC-27 |
| Credential inventory | — |

## What this phase makes true

When the invoice does not add up, litres exceed the tank or approved quantity by more than the
tolerance, or a reading looks implausible, the Fleet User can still record the fueling but must
explain each difference, and the original figures are never changed. A transaction entered
more than 48 working hours after fueling — Sundays and public holidays not counted — is marked
late and needs an explanation.

## Build state by criterion

| Criterion | State | Gap |
|---|---|---|
| AC-09 — allowed discrepancies keep source values and need explanations | Not built | Tolerance default and per-asset override exist. No invoice amount or printed unit price is recorded, and there are no discrepancy rows |
| AC-27 — late entry after 48 working hours flagged | Not built | Entry deadline and Holiday List fields exist in settings; nothing uses them |

## The rule, as observed

Not yet observed in this phase.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Working-hour deadline | Holiday List | Deadline counts hours excluding Sundays and listed holidays |
| Discrepancy records | Child table on the transaction | System-generated rows with a user explanation each |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Enter litres × printed unit price that does not equal the invoice total | Submits only with an explanation; all three values kept | AC-09 |
| 2 | Enter litres over capacity (vehicle) or approved maximum (generator) by more than 2%, then by 1% | Over tolerance: flagged, needs explanation; within: no flag | AC-09 |
| 3 | Change the vehicle's tolerance override and repeat row 2 | The override applies; earlier transactions are not recalculated | AC-09 |
| 4 | Enter a transaction 47 and 49 working hours after fueling, across a Sunday and a listed holiday, with a Saturday in between | 47: not late; 49: late and needs an explanation; Sunday and holiday not counted, Saturday counted | AC-27 |

**How to run it.** All rows need new integration tests; row 4 also a unit test for the working-hour count.
Desk walkthrough: explanation prompts on a flagged and a late transaction.

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

**Next:** Start after Phase 4 closes.
