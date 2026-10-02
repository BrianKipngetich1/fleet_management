# Phase 4 — Issue and action history

| | |
|---|---|
| Specification | [`../requirements.md`](../requirements.md) @ working tree |
| Status | Not started |
| Started / Closed | 2026-10-02 / — |
| Author | Codex |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | Requirements 3.3, 3.4, and 5.1–5.5 |

## What this phase makes true

A Fleet User, Fleet Approver, or fleet administrator can follow the original signal readings and limits, explanations, decisions, partial-authorization reason, cancellation reason, validity changes, every slip print, and the linked actual fueling facts and evidence. Earlier entries remain unchanged, and each person sees history only when they can read the linked order.

## The rule, as observed

```mermaid
stateDiagram-v2
    [*] --> VersionHistoryOnOrderAndTransaction
    Approved --> ExtensionJSON: prior and new validity, reason, actor, time
    Approved --> LatestPrintFields: current revision and last print time only
    Approved --> SubmittedFuelingTransaction: actual source facts stay on source record
    Cancelled --> NoRequiredReason
```

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|
| `SavedIssue → ImmutableSnapshot` | The order retains its latest `signal_details_json` snapshot, but a later save replaces it; no append-only issue event exists | Unbuilt — the selected snapshot timing rule is pending the requester |
| `IssueCleared → ResolutionEvent` | No resolution event is recorded when a later signal no longer contains a reason | Unbuilt |
| `WorkflowAction → ActorAndReasonEvent` | Current workflow fields retain the latest decision; no separate action event links an explanation to its red reason | Unbuilt |
| `Cancellation → ReasonedEvent` | Frappe's existing cancellation permission remains authoritative, but neither Fuel Order nor Fueling Transaction requires a cancellation reason | Unbuilt |
| `PrintOrExtension → SeparateEvent` | Each extension is appended to `validity_extension_history` with old/new dates, reason, actor, and time. Print bookkeeping retains only the current revision and latest print time; printing an unchanged revision creates no event | Extension source exists; per-action history is unbuilt |
| `FuelingTransaction → SourceAndEvidenceLink` | Submitted transaction facts and attached evidence remain on an immutable source record, but no Fuel Order history event links those values and evidence | Source integrity exists; history link is unbuilt |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why it is unavoidable |
|---|---|---|
| Preserve the original order and fueling source records | Existing Frappe document change history and submitted-record immutability | It does not retain each signal's captured inputs, decision reason, cancellation reason, and print event as one durable event. |
| Read the event trail on the Fuel Order | Existing location-scoped Fuel Order read permission | A read-only event record and parent-based permission check are needed to retain the same scope. |
| Require a cancellation reason | Native before-cancel lifecycle | Prompt and server staging are needed because the action runs across separate client and server requests. |

**Scope deliberately not taken:** No new role, wider location access, invoice discrepancy, late-entry rule, meter-reset record, cost field, or reconciliation process.

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Save a red issue for the first time, save unchanged readings again, change a captured reading or limit, then clear the issue | Follow the requester's chosen snapshot rule; unchanged saves do not create unapproved duplicates if that rule is selected; resolution is a separate event | `5.1`, `5.2` |
| 2 | Send a red order for approval, then approve or reject it | History retains the explanation, actor, time, decision reason, and link to the issue without changing prior issue facts | `5.2` |
| 3 | Approve a Partial authorization | Its quantity and separate reason are retained apart from red-order and decision explanations | `1.4`, `5.2` |
| 4 | Cancel a Fuel Order or Fueling Transaction as a user who already has permission | A blank reason is refused; a written reason, actor, time, and source facts are retained; other roles keep their current cancel access | `3.3`, `5.3` |
| 5 | Extend an approved order and print the slip more than once, including after the extension | Each extension and each print/reprint appears with its reason where required and the applicable slip revision | `5.4` |
| 6 | Submit then cancel a Fueling Transaction | History links to the actual station facts, time, meter, litres, invoice identifiers, attendant, and signed evidence; cancellation records its reason without changing those source values | `3.4`, `5.3`, `5.5` |
| 7 | Read an event as a user with and without access to the linked order's location | Permitted users can read it; users outside the location cannot list or open it directly | `3.3`, `5.1` |
| 8 | Attempt to edit or delete an earlier event through the form and server API | The event remains unchanged and the attempt is refused | `5.1`, `5.2` |

**How to run it.** Event, cancellation, permission, and append-only checks run on the disposable MariaDB site. A Desk walkthrough uses Fleet User, Fleet Approver, and Fleet Admin only where the existing role permits the action.

**Result:** Not run yet. The issue snapshot timing rule is pending the requester's answer.

## What we learned that the plan did not predict

The existing extension JSON already preserves earlier validity changes. The print handler updates bookkeeping only when a new slip revision needs printing, so repeated prints of the same revision leave no durable record. Submitted fueling facts and evidence are already kept on the source transaction and its immutable validation; history should link to that source rather than rewrite it. Fuel Order History reads will need to use the existing linked-order location scope from the permission hooks. Frappe provides both a client `before_cancel` event and a server `before_cancel` lifecycle method, so a written reason can be collected before cancel while the server continues to enforce its existing cancel permission.

## Known limitations — accepted, not fixed

- Issue snapshot timing is pending the requester's decision.
- Historical cancellations do not have reasons and will not be rewritten.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|

**Closure:** Not reviewed.

**Next:** Resolve the issue snapshot timing decision, then implement the event record and append-only history.
