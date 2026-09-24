<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Most of this phase was built and exercised under the wider 2026-09-18 Phase 0; that evidence
is carried here as the starting position and must be rerun on MariaDB before closure.
-->

# Phase 2 — Integrity and hard blocks

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ uncommitted working tree on `develop` (D-16) |
| Status | Not started — built by Phase 0; concurrency proof open |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-07, AC-10, AC-20 |
| Credential inventory | `verification/CREDENTIALS.md` — Phase 0 QA users reused |

## What this phase makes true

A fueling record that does not match its approved order — wrong station, fuel, or asset,
fuelled outside the approved window, a meter that went backwards, or a reused invoice or CU
number — is refused. Two people submitting for the same order at the same moment cannot both
succeed. The fueling time is the one printed on the invoice, or a known station time with an
explanation, never the time of data entry, and the approved window is judged against it.

## Build state by criterion

| Criterion | State | Carried evidence |
|---|---|---|
| AC-07 — mismatch, window, rollback, duplicate, second-active blocks | Built by Phase 0 | Transaction tests for station, fuel, asset, window, odometer and hour-meter rollback, invoice-per-station and CU duplicates, second active; Playwright `acceptance.spec.ts` |
| AC-10 — constraints and locking, including concurrency | Partly built by Phase 0 | Three unique indexes and an order row lock exist; the concurrent overlap has never been observed |
| AC-20 — fueling-time source and explanation | Built by Phase 0 | Four time-source tests and KPI ordering by fueling time; SQLite-era screenshots `phase-00-25/26-*` |

## The rule, as observed

Not yet observed in this phase.

| Specification edge | Observed | Verdict |
|---|---|---|
| `Expired → Completed` (late entry proves in-window fueling) | The derived condition reads Completed for an order past validity once its transaction is active (tested with the Phase 0 gaps); the late-entry path itself is not yet observed | Unbuilt or untested |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Duplicate identifiers | Database unique indexes | Normalized keys scoped per station, and one active transaction per order |
| Concurrent submission | Row lock via `frappe.get_doc("Fuel Order", …, for_update=True)` | Lock the order before the active-transaction check |
| Order/transaction agreement | `validate` / `before_submit` | Compare against the approved order's snapshots |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Submit a transaction with a changed station, fuel type, or asset; fueling time outside the approved window; a lower odometer or hour-meter; an invoice number already used at that station; a CU number already used anywhere | Each is refused server-side; the order's snapshots are unchanged | AC-07 |
| 2 | Submit a second transaction for an order that already has an active one | Refused | AC-07 |
| 3 | Prepare two valid drafts for one approved order; submit them from two independent connections, holding the first after it locks the order | Exactly one submits; the other gets a controlled validation error, not a raw lock error; one active key remains | AC-10 |
| 4 | Submit one transaction whose invoice prints the time, one whose invoice does not (station time plus explanation), and try one with no time and one with no explanation | Printed time kept exactly; station time needs the explanation; missing time refused; validity uses the recorded time | AC-20 |
| 5 | After an order's validity lapses, enter a transaction whose invoice time is inside the window | Accepted as a late entry and the order shows Completed | AC-20 |

**How to run it.** Rows 1, 2 and 4 are asserted by `test_fueling_transaction.py` in the full
backend suite. Row 3 is `test_concurrent_submissions_wait_for_order_lock`, opt-in through
`FLEET_RUN_CONCURRENCY_PROOF=1`; it is skipped in the normal suite. Row 5 depends on the
fulfillment condition, built with Phase 0 row 8.

**Result:** Not yet run in this phase. Rows 1, 2 and 4 passed under Phase 0 (SQLite gate
2026-09-23; MariaDB suites 2026-09-24). Row 3 has never been observed.

## What we learned that the plan did not predict

- Frappe omits `FOR UPDATE` on SQLite, so the concurrency proof was impossible until the
  MariaDB cutover.

## Known limitations — accepted, not fixed

- The concurrency harness targets a separate `fleet_management-concurrency-test.localhost`
  site, which contradicts D-15 (one kept test site). Before row 3 runs, either point it at the
  test site or record a D-15 exception in the spec. Its docstring still cites AC-07; under the
  re-phasing the concurrency claim is AC-10.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Reconcile the concurrency site with D-15, run row 3 on MariaDB, rerun rows 1–2 and 4.
