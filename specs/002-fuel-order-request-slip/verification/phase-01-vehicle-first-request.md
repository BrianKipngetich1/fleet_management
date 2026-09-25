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
| 3 | Save an order for a vehicle that has never been fuelled and has no approved order | Previous Entry reads "none", with no reading or date | AC-06 — `test_previous_entry_is_none_for_a_vehicle_never_ordered` |
| 4 | A vehicle has an approved order but no completed fueling; save a new order for it | Previous Entry names that approved order with its meter reading and approval date; the approved order's own Previous Entry stays as it was when approved | AC-06 — `test_previous_entry_falls_back_to_the_last_approved_order` |
| 5 | Ask for the facts of a vehicle whose home location has exactly one approved station; then add a second station there | Custodian, usual driver, home location, tank size, target, and the one station are returned; with two stations no station is suggested | AC-05 — `test_request_facts_suggest_driver_home_location_and_a_single_station` |
| 6 | As Philip, start a new Fuel Order and type "Hilux" in the vehicle field; choose KDA 412M | KDA 412M is offered with its make and model. On choosing it, make and model, fuel type, tank size 80 L, target km/L, custodian, and home location Nairobi fill in and cannot be edited; the usual driver and location Nairobi are suggested and can be changed; no station is suggested (Nairobi has two approved stations); Previous Entry shows its last completed fueling at 52,024 km | AC-05, AC-06 |
| 7 | As Philip, start a new Fuel Order for KDH 201A | Previous Entry reads "none" | AC-06 |

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
