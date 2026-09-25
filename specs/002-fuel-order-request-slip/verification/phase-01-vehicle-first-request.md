<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 1 — Vehicle-first request with photo evidence

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `3c37dbb` |
| Status | Building on `feature/002-fuel-order-request-slip` |
| Started / Closed | 2026-09-25 / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-04, AC-05, AC-06, AC-07 |
| Credential inventory | `verification/CREDENTIALS.md` (gitignored, mode 0600) |

## What this phase makes true

A Fleet User starts a request by picking a vehicle by its registration number, and the system fills in everything it already knows about that vehicle and locks it. The user sees the last recorded reading, types today's meter reading and gauge, and cannot send the request for approval without a photo of each.

## The rule, as observed

Not yet observed in this phase.

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Vehicle choice with model | Link field search fields | — |
| Auto-filled facts | fetch_from, read_only | Assignment lookup from 001 |
| Previous Entry | — | Last completed transaction lookup |
| Photos | Attach Image | Private-file and type check from 001 |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Save a new order whose request date was sent as 01/01/2020; change the date through the API and save again | The saved request date is the moment of the first save, and the later change is ignored; the order number series and request date are read-only | AC-04 — `test_request_date_is_set_by_the_server_and_never_changes` |
| 2 | Save an order naming a custodian other than the vehicle's assigned one, then try to change it again | Both saves keep the assignment's custodian; tank size, target km/L, home location, and fuel type come from the vehicle | AC-05 — `test_custodian_comes_from_the_effective_assignment` |

**How to run it.** Backend rows: `bench --site fleet_management-test.localhost run-tests --app fleet_management`.
Desk rows: `agent-browser` walkthrough on the test site as the named role.

**Result:** not yet run.

## What we learned that the plan did not predict

## Known limitations — accepted, not fixed

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|

**Closure:** —

**Next:** —
