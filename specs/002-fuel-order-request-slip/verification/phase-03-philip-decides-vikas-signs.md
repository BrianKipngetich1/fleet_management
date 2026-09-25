<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 3 — Philip decides, Vikas signs off red

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ — (awaiting approval) |
| Status | Not started |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-12, AC-13, AC-14, AC-15 |
| Credential inventory | `verification/CREDENTIALS.md` (gitignored, mode 0600) |

## What this phase makes true

Philip approves green orders himself, including ones he entered, and can reject any order at any stage before approval. A red order can only go ahead if Philip sends it to Vikas with an explanation and Vikas approves it with a reason; the slip then names Vikas. Vikas and fleet administration hear about each sent-up order once.

## The rule, as observed

Not yet observed in this phase.

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Green/red routing | Workflow states, actions, allowed roles, conditions | Reason on send-up and decisions; narrowed self-approval check |
| Notices | Notification Log | Recipient helper from 001 |


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
