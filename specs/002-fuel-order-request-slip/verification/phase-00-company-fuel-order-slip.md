<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 0 — Company fuel order slip

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ — (awaiting approval) |
| Status | Not started |
| Started / Closed | — / — |
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
