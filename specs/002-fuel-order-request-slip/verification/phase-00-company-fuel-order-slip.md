<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 0 — Company fuel order slip

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `3c37dbb` |
| Status | Building on `feature/002-fuel-order-request-slip` |
| Started / Closed | 2026-09-25 / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-01, AC-02, AC-03 |
| Credential inventory | `verification/CREDENTIALS.md` (gitignored, mode 0600) |

## What this phase makes true

An Approver who prints an approved Fuel Order gets a page that reads like the company's paper fuel order slip: the company heading, the order number and date, the station's address, the litres and fuel to supply, the vehicle's registration and meter reading, and the name of the person who authorised it. Everything the earlier slip had to show — validity, the attendant instruction, and the signature lines — is still on the page.

## The rule, as observed

Not yet observed in this phase.

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Company heading from the site Letter Head | Letter Head | — |
| Station postal address and email | Address linked to Fuel Station | — |
| Slip layout | Jinja Print Format | — |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Build the test site. As Test Fleet Admin, open the Letter Head list | "Krystalline Salt Fuel Order Slip" is the default; its heading reads KRYSTALLINE SALT LIMITED, PIN NO. P000000000T, a P.O. Box, telephone, and email — all synthetic | AC-01 |
| 2 | As Test Fleet Admin, open Fuel Station "Mombasa Road Service Station" | An Address section lists its postal address (P.O Box 10001, 00100, Nairobi) and email mombasa-road.test@example.com; the other five stations each show their own | AC-01 |

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
