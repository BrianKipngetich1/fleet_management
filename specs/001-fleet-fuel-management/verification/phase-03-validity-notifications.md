<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Most of this phase was built under the wider 2026-09-18 Phase 0; that evidence is carried here
as the starting position and must be rerun on MariaDB before closure.
-->

# Phase 3 — Validity, extension, and notifications

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ uncommitted working tree on `develop` (D-7, D-8, D-16) |
| Status | Not started — built by Phase 0 except Approver cancellation; one spec contradiction to reconcile |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-08, AC-21, AC-22, AC-23 |
| Credential inventory | `verification/CREDENTIALS.md` — Phase 0 QA users reused |

## What this phase makes true

An approved order is valid for three days, and the slip says exactly until when. Before fueling,
an Approver can extend it with a reason kept in its history, and the slip must then be
reprinted. A location Approver can cancel an approved order that has not been fuelled. The
location's Approvers, the person who entered the request, and fleet administration are told
when an order is pending, approved, rejected, about to expire, expired, or extended — nobody else.

## Build state by criterion

| Criterion | State | Carried evidence / gap |
|---|---|---|
| AC-08 — pre-fueling extension; retroactive extension denied | Built by Phase 0 | Six extension tests (validity only, reason, role and location, lapsed order refused, fueling started refused, stale slip); `phase-00-12/13/14-*`; Phase 0.5 rows 6–7 |
| AC-21 — slip shows valid-until and instruction | Built by Phase 0 | `test_approved_print_contains_ac04_fields_and_instruction`; `phase-00-14-approver-extended-print.png` |
| AC-22 — location Approver cancels an unfuelled approved order, with reason | Not built | **Drift:** role permissions grant order cancel to Fleet Admin only, although the spec's role table gives it to Fleet Approver; no cancellation reason is recorded |
| AC-23 — notices reach exactly the documented recipients | Built by Phase 0 | Five notification tests (scope, de-duplication, idempotent scheduler, extension notice, email queue); `phase-00-27/28-*` |

## The rule, as observed

Not yet observed in this phase.

| Specification edge | Carried observation | Verdict |
|---|---|---|
| `AwaitingTransaction → AwaitingTransaction` (extend before fueling) | Observed under Phase 0 and Phase 0.5 | Rerun here |
| `AwaitingTransaction → Expired` (valid-until passes) | Scheduler notice observed; the derived condition reads Expired past valid-until (built and tested with the Phase 0 gaps) | Rerun here |
| `Expired → AwaitingTransaction` (Approver extends and slip is reprinted) | Refused by the build, as AC-08 and the design text require | **Spec contradiction:** the diagram allows it, AC-08 and the text deny it. Reconcile the spec before this phase closes |
| `Approved → Cancelled` | Observed by Playwright `lifecycle.spec.ts` as Administrator only | Drift — must be possible for the location Approver (AC-22) |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Validity | Datetime set on approval | Extension action with reason history and reprint marker |
| Notices | Notification Log, scheduler, email queue | Location-scoped recipient sets and idempotent reminders |
| Order cancellation | Standard docstatus cancel | Role permission for Fleet Approver, location check, reason |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Approve an order and print it | Valid-until is approval time plus the configured days; the slip shows it and the instruction | AC-21 |
| 2 | As a location Approver, extend an unused order before it lapses, with a reason; print again | Only validity, history, slip revision, and reprint marker change; the new slip shows the new time | AC-08 |
| 3 | Try extending with a blank reason, after the order lapsed, after fueling started, as a Fleet User, and as another location's Approver | Each is refused | AC-08 |
| 4 | As the location Approver, cancel an unfuelled approved order with a reason; try without a reason, after fueling, and as another location's Approver | First succeeds with the reason kept; the others are refused | AC-22 |
| 5 | Generate pending, approved, rejected, pre-expiry, expiry, and extension events across two locations; run the scheduler twice; read every user's Notification Log | Each notice reaches exactly its recipients in the spec, once; the other location's Approver gets none | AC-23 |

**How to run it.** Rows 1, 2, 3 and 5 are asserted by the extension, print, and notification
tests. Row 4 needs tests once built. Desk walkthrough: Approver extension dialog, print, and
cancellation.

**Result:** Not yet run in this phase. Rows 1, 2, 3 and 5 passed under Phase 0.

## What we learned that the plan did not predict

- A Datetime field in a dialog must be typed after its picker opens; an instant fill loses the
  value (Phase 0.5).
- An approved order can show two "Actions" buttons; target the app's own group.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Reconcile the lapsed-order edge in the spec, build Approver cancellation, rerun rows 1–5.
