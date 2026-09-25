<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 2 — Green and red signal

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ — (awaiting approval) |
| Status | Not started |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-08, AC-09, AC-10, AC-11 |
| Credential inventory | `verification/CREDENTIALS.md` (gitignored, mode 0600) |

## What this phase makes true

When Philip enters an order, the system colours it green or red and, when red, lists every reason: mileage that does not add up, more litres than the tank has room for, a nearly full tank, another open order, fueling too soon, fueling away from home, an unusual driver, or a vehicle whose mileage is drifting. The limits come from settings a Fleet Admin can change, and nobody can choose the colour by hand.

## The rule, as observed

Not yet observed in this phase.

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Colour and reasons | Read-only fields | The eight checks |
| Average mileage | — | Last five completed intervals |
| Limits | Fleet Management Settings fields | — |


## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|

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
