<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Nothing in this phase has been built.
-->

# Phase 9 — Reports and release acceptance

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ uncommitted working tree on `develop` (D-13, D-16) |
| Status | Not started — not built |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-15, AC-16, AC-17, AC-18 |
| Credential inventory | — |

## What this phase makes true

Operations, management, and audit answer their questions from the system instead of the Excel
register: open orders, spend, vehicle and generator performance, and exceptions. Every total
traces back to its source records; people see only their permitted locations; audit views keep
cancelled records while performance views leave them out; dates mean the actual fueling date.

## Build state by criterion

| Criterion | State | Gap |
|---|---|---|
| AC-15 — five reports reconcile and apply permissions | Not built | No reports exist |
| AC-16 — audit includes cancelled, KPI excludes | Not built | — |
| AC-17 — actual-date filters and out-of-range prior record | Not built | — |
| AC-18 — no parallel Excel register | Not built | Release acceptance with the owner |

## The rule, as observed

Not yet observed in this phase.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Reports | Query/Script Report, Query Builder | Explicit location filters; shared interval calculation |
| Dashboards | Number Cards and Dashboard Charts over the reports | None |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Seed fuelings across two locations, including a cancelled one; open each of the five reports | Totals match the source records; each drills down to them | AC-15 |
| 2 | Open the reports as a user permitted for one location | Only that location's rows and totals | AC-15 |
| 3 | Compare the Exceptions and Audit report with Vehicle Performance | Cancelled fueling appears in audit, not in performance | AC-16 |
| 4 | Filter to a range whose first full fill's previous full fill is before the range | The interval is still rated using the earlier fill | AC-17 |
| 5 | Run a month of operations with the owner using only the system | No Excel register needed | AC-18 |

**How to run it.** Rows 1–4 need integration tests; row 5 is an owner acceptance session.

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

**Next:** Release acceptance; then the specification closes.
