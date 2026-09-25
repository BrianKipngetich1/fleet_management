<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 1 — Vehicle-first request with photo evidence

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ — (awaiting approval) |
| Status | Not started |
| Started / Closed | — / — |
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
