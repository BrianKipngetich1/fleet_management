<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Most of this phase was built and exercised under the wider 2026-09-18 Phase 0; that evidence
is carried here as the starting position and must be rerun on MariaDB before closure.
-->

# Phase 1 — Location access

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ uncommitted working tree on `develop` (D-16) |
| Status | Not started — built by Phase 0; rerun outstanding |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-02 |
| Credential inventory | `verification/CREDENTIALS.md` — Phase 0 QA users reused |

## What this phase makes true

People see and act only on records for the locations they are permitted. A Fleet User can
request fuel only for assets at their permitted locations. Someone from another location
cannot list, open, report on, print, or act on those records by any route.

## Build state by criterion

| Criterion | State | Carried evidence |
|---|---|---|
| AC-02 — list, direct, report, print, action scope | Built by Phase 0 | `test_permissions.py` (10 tests), transaction location tests, Playwright `tenancy.spec.ts` and `acceptance.spec.ts`; SQLite-era screenshots `ac02-*`, `phase-00-22/23/24-*` |
| AC-02 — requests only for permitted assets and stations | Built by Phase 0 | Asset access follows the assigned location; the server refuses a planned station outside the operational location; the Desk station picker filter is unverified |

## The rule, as observed

Not yet observed in this phase. Access scope adds no state edges; it filters who may take the
Phase 0 and Phase 3 edges.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Location scope on lists and links | User Permission on Fleet Location; `permission_query_conditions` | Query conditions follow the asset's effective assignment, which User Permission alone cannot |
| Direct document access | `has_permission` hook | Same location rule for read, write, print, submit, cancel |
| Reports | Report permissions | Report view stays denied without report permission; list access does not require it |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Two locations; a Fleet User and an Approver permitted only for location A. List Fuel Orders, Fueling Transactions, Fleet Locations, and Fleet Assets | Only location A records appear | AC-02 |
| 2 | As the location A users, open a location B order and transaction by direct URL; try read, write, print, submit, cancel | Every action is denied | AC-02 |
| 3 | As the location A Fleet User, open the list without report permission, then a restricted report; as the Approver, open reports and print | List loads; restricted report denied; Approver reports and prints only location A orders | AC-02 |
| 4 | As a Fleet User with no permitted location, open the lists | Nothing is listed | AC-02 |
| 5 | As the location A Fleet User, pick the asset on a new order | Only assets assigned to location A are offered and accepted | AC-02 |
| 6 | Pick a planned station outside the order's operational location, in the picker and via direct save | Not offered; refused on save | AC-02 |
| 7 | As Fleet Admin, repeat rows 1–2 | All locations visible and actionable | AC-02 |

**How to run it.** Rows 1–4 and 7 are asserted by `test_permissions.py`, the transaction location
tests, and Playwright `tenancy.spec.ts`; rows 5–6 need tests. A MariaDB `agent-browser` walkthrough as the location A and B users is required.

**Result:** Not yet run in this phase. Rows 1–4 and 7 passed under Phase 0 (SQLite gate
2026-09-23; MariaDB suites 2026-09-24).

## What we learned that the plan did not predict

- A custom request guard once treated ordinary Desk list calls as reports and demanded report
  permission (Phase 0 escalation, repaired). Keep list and report permission separate.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** Add tests for rows 5–6 and rerun rows 1–7 on MariaDB.
