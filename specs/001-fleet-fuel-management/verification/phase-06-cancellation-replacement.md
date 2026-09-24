<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Only standard cancellation permission exists; nothing specific to this phase has been built.
-->

# Phase 6 — Cancellation and replacement

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `07bf479` (D-9, D-16) |
| Status | Not started — not built beyond Fleet Admin's standard cancel permission |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-11, AC-28 |
| Credential inventory | — |

## What this phase makes true

A mistaken fueling record can be cancelled only by Fleet Admin, with a reason. The cancelled
record stays visible for audit, the order becomes available again, and one replacement may be
entered for the same order, reusing the cancelled invoice and CU numbers.

## Build state by criterion

| Criterion | State | Gap |
|---|---|---|
| AC-11 — cancelled record kept; one replacement reusing its identifiers | Not built | Standard cancel exists; no replacement link or identifier release has been verified |
| AC-28 — only Fleet Admin cancels, with a recorded reason | Partly built | Role permissions grant cancel to Fleet Admin only. **Gap:** no cancellation reason |

## The rule, as observed

Not yet observed in this phase.

| Specification edge | Observed | Verdict |
|---|---|---|
| `Completed → AwaitingTransaction` (cancelled in-window) | The derived condition leaves Completed when the transaction is cancelled (tested with the Phase 0 gaps); cancellation reason and replacement not built | Unbuilt or untested |
| `Completed → Expired` (cancelled after expiry) | Same test: reads Expired after cancellation past validity | Unbuilt or untested |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Cancellation | Standard docstatus 2 and role permission | Mandatory structured reason |
| Replacement | Link to the cancelled transaction | Release of the cancelled record's uniqueness keys to that replacement only |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | As Fleet Admin, cancel a submitted transaction with a reason | Cancelled, still listed in audit views; the order returns to Awaiting (or Expired if lapsed) | AC-11, AC-28 |
| 2 | Try to cancel as Fleet User, as Fleet Approver, and as Fleet Admin without a reason | Each refused | AC-28 |
| 3 | Enter a replacement for the cancelled transaction reusing its invoice and CU numbers; then try a second replacement | First accepted; second refused | AC-11 |

**How to run it.** All rows need new tests. Desk walkthrough: cancel dialog, audit view, replacement.

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

**Next:** Start after Phase 5 closes.
