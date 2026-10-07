# Phase 4 — Issue and action history

| | |
|---|---|
| Specification | [`../requirements.md`](../requirements.md) @ working tree |
| Status | Issue and action history built and database-verified; issue and resolution rendering observed for both roles at wide, medium, and phone widths; other action-event walkthroughs remain pending |
| Started / Closed | 2026-10-05 / — |
| Author | Codex |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | Requirements 3.3, 3.4, and 5.1–5.5 |

## What this phase makes true

Append-only records retain the first saved Red result, changed issue snapshots, deduplicated unchanged saves, later resolution, workflow decisions and explanations, a separate Partial authorization reason, reasoned cancellations, each slip print, validity extensions, and submitted or cancelled actual fueling with its original source facts and evidence links. Decisions link to the latest issue snapshot they explain. Reads inherit the linked Fuel Order's permissions and location scope.

## The rule, as observed

```mermaid
stateDiagram-v2
    [*] --> FuelOrder
    FuelOrder --> WorkflowActionEvent: send, approve, reject, withdraw
    FuelOrder --> PartialAuthorizationEvent: separate reason and quantity
    FuelOrder --> CancellationEvent: existing permission plus written reason
    Approved --> ExtensionEvent: each validity change
    Approved --> SlipPrintEvent: every print/reprint
    Approved --> ActualFuelingEvent: source facts and evidence reference
    SavedSignalIssue --> SameFingerprint: unchanged saved issue
    SameFingerprint --> SameFingerprint: deduplicate save
    SavedSignalIssue --> ChangedSnapshot: explanation or relevant facts changed
    ChangedSnapshot --> ChangedSnapshot: same issue key
    ChangedSnapshot --> SignalResolved: later saved result is Green
    SignalResolved --> NewIssueEpisode: later saved result is Red
    NewIssueEpisode --> SavedSignalIssue: new issue key
    SavedSignalIssue --> WorkflowActionEvent: decision links to issue snapshot
```

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|
| `SavedIssue → ImmutableSnapshot` | The first saved Red result creates an immutable `Signal Issue` event. A changed issue explanation or relevant displayed reading/limit appends a linked snapshot under the same issue key; an unchanged save adds nothing. | Verified by database tests for first appearance, evidence capture, deduplication, changed odometer/gauge facts, and a changed gauge limit with the reading held fixed. |
| `IssueCleared → ResolutionEvent` | A later saved Green result creates one `Signal Resolved` event linked to the latest issue snapshot. Repeated Green saves add nothing; a later Red result starts a new issue key. | Verified by database tests. |
| `WorkflowAction → ActorAndReasonEvent` | Send-up, approve, reject, and withdraw transitions write actor, time, explanation/decision reason, captured order facts, and a link to the issue snapshot. Partial authorization gets a separate event linked to its approval. | Verified by database tests. |
| `Cancellation → ReasonedEvent` | The existing cancel permission remains authoritative. A written reason is staged for the native cancel action; the server rejects cancellation without one and saves actor, time, reason, and source facts. | Verified for Fuel Orders and Fueling Transactions. |
| `PrintOrExtension → SeparateEvent` | Each slip render, including repeat prints of the same revision, writes an event. Each extension records its reason, actor, time, old/new validity, and revision. | Verified by database tests. |
| `FuelingTransaction → SourceAndEvidenceLink` | Submission and cancellation write separate parent-order events with transaction source facts and private evidence references. Submitted source records remain unchanged. | Verified by database tests. |
| `HistoryRead → LinkedOrderPermission` | Event read permission checks the linked Fuel Order; list-query conditions filter through the order's assigned location. The history endpoint checks ordinary parent read access. | Verified by database tests. |
| `EarlierEvent → Immutable` | The event controller refuses update, delete, and rename actions; role permissions grant read only. | Update and delete refusal verified by database tests. |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why it is unavoidable |
|---|---|---|
| Preserve original order and fueling records | Existing document history and submitted-record immutability | A read-only event DocType retains action-specific facts, reasons, and evidence references across later changes. |
| Show the trail on a Fuel Order | Existing linked-order read permission and location scope | A small form reader renders the escaped, captured events and checks parent access on the server. |
| Require cancellation reasons | Native `before_cancel` lifecycle and existing cancel action | A short-lived, user/document-scoped staged reason carries the written answer into the native server cancellation request. |

**Scope deliberately not taken:** No new role, wider location access, invoice discrepancy, late-entry rule, meter-reset record, cost field, or reconciliation process. Historical cancellations are not rewritten.

## Verification

The latest six focused modules passed on `fleet_management-test.localhost`, confirmed as MariaDB: **146 passed and one existing concurrency test skipped by its environment guard**. This includes 12 decision-history integration tests; 2 transaction unit and 31 integration tests (30 passed, one expected skip); 6 permission unit and 8 integration tests; 28 Fuel Order integration tests; 19 signal integration tests; and 41 signal unit tests. Coverage includes first issue appearance, evidence capture, identical-save deduplication, changed readings and limits, resolution and a new issue episode, decision links, immutable events, cancellations, extensions, every print/reprint, actual fueling source and evidence, linked-order permission checks, preview/save parity, approval recalculation, and frozen approved results.

Python compilation, JavaScript syntax, DocType JSON, `e2e/sid.ts` import, `git diff --check`, and spec-check passed. The spec checker reports filename-based coverage warnings because relevant cases live in existing test modules; Ruff was unavailable. No full suite was run.

On the disposable MariaDB site, Fleet User Philip created new draft order FO-2026-00056 so the history reader had events produced by the current implementation. Saving an initial Red result recorded a `Signal Issue` event: 976 km travelled versus 478.1 km expected. After changing Driver to John Mwangi and the odometer to 52,500 km, the preview became Green (476 km versus 478.1 km expected); saving recorded one linked `Signal Resolved` event. The order remains Draft and Green. Fleet Approver Vikas opened the same order read-only and saw both entries. No pre-existing sample order was changed, and no approval, cancellation, extension, reprint, or actual fueling action was performed.

The issue and resolution history was observed at 1600, 900, and 390 px as Fleet User and Fleet Approver. At all widths the history entries remained readable, the narrow layouts reflowed without horizontal overflow, and the Approver had no editable Driver or Actual Requester inputs. Screenshots: `verification/screenshots/phase-04-01-wide-user-event-history.png`, `phase-04-02-medium-user-event-history.png`, `phase-04-03-phone-user-event-history.png`, `phase-04-04-wide-approver-event-history.png`, `phase-04-05-medium-approver-event-history.png`, and `phase-04-06-phone-approver-event-history.png`.

The old sample order FO-2026-00043 predates history capture, which explains its empty panel; it is no longer being used as the history-rendering fixture. The issue-to-resolution display is now visually verified, while the remaining Phase 4.4 cancellation, extension/reprint, and completed-fueling displays have not been walked through. The shared server serving `feature/008-overseer-reports` was not used. The earlier orphan-cleanup failure and main-site recovery-bin changes remain documented; no functional/database tests or migrations ran against the main site during this verification.

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Save a red issue, save unchanged readings, change a captured reading or limit, clear it, save green again, then make it red | Keep one initial snapshot for unchanged saves, append changed snapshots and one resolution, then start a new issue episode | `5.1`, `5.2` |
| 2 | Send a red order for approval, then approve, reject, or withdraw it | Retain explanation, actor, time, decision reason, and any issue link without changing earlier facts | `5.2` |
| 3 | Approve a Partial authorization | Retain quantity and its separate reason apart from red-order and decision explanations | `1.4`, `5.2` |
| 4 | Cancel an order or fueling transaction as a user who already has permission | Refuse a blank reason; retain a written reason, actor, time, and source facts; preserve existing role access | `3.3`, `5.3` |
| 5 | Extend an approved order and print the slip more than once, including after extension | Retain each extension and each print with applicable reason and slip revision | `5.4` |
| 6 | Submit then cancel a Fueling Transaction | Link station, time, meter, litres, invoice identifiers, attendant, and signed evidence; retain cancellation facts without changing the submitted source | `3.4`, `5.3`, `5.5` |
| 7 | Read an event as users with and without access to its linked order | Permit the same linked-order readers and deny out-of-location listing and direct reads | `3.3`, `5.1` |
| 8 | Attempt to edit, delete, or rename an earlier event | Refuse the action and leave the event unchanged | `5.1`, `5.2` |

## What we learned that the plan did not predict

The existing extension history already captures each earlier validity change, but it did not capture every print of an unchanged revision. The existing transaction is the source of actual fueling facts and signed evidence, so events link and snapshot those values instead of replacing them. The server can enforce a written cancellation reason in the native lifecycle while keeping role and location permissions unchanged. The test CLI can mint browser sessions without a password, but the shared server still serves the separate checkout.

## Known limitations — accepted, not fixed

- Cancellation, extension/reprint, and completed-fueling event displays remain unwalked; the issue and resolution events are visually verified on a newly created disposable draft order.
- Historical cancellations do not have reasons and are not rewritten.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|

**Closure:** Not reviewed.

**Next:** If Phase 4.4 is resumed, use disposable records to walk through a reasoned cancellation, an extension and reprint, and a completed fueling; do not rewrite historical cancellations.
