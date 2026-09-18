<!--
The proof document. Written as the phase is verified, from what was actually observed.
This scaffold remains Not started until implementation and test-site verification.
-->

# Phase 0 — Secure vehicle journey

| | |
|---|---|
| Specification | [../spec.md](../spec.md) @ draft |
| Status | Not started |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-01–AC-07 |

## What this phase makes true

A Fleet User can enter a request on behalf of a driver or custodian without giving that person
system access. A different Approver for the asset's location can approve and print an order
whose exact validity and station instruction are clear. Two approved full-fill cycles with
private signed evidence produce first a baseline and then a correct kilometres-per-litre result.

Users outside the permitted location cannot list, open, report on, print, or act on its records.
Asset, fuel, station, validity, evidence, and one-active-transaction controls are server-enforced.

## The rule, as observed

Not yet observed. This phase has not been implemented.

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingApproval: Fleet User submits
    PendingApproval --> Approved: location Approver approves
    PendingApproval --> Rejected: location Approver rejects
    state Approved {
        [*] --> AwaitingTransaction
        AwaitingTransaction --> Completed: active transaction submitted
    }
~~~

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|
| Draft → PendingApproval | no | Unbuilt or untested |
| PendingApproval → Approved | no | Unbuilt or untested |
| PendingApproval → Rejected | no | Unbuilt or untested |
| AwaitingTransaction → Completed | no | Unbuilt or untested |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Masters, assignments, forms, names, private files, print | Not yet observed | Not yet implemented |
| Approval submission and role gate | Not yet observed | Self-approval and location guard not yet implemented |
| List and direct access | Not yet observed | Matching query condition and document guard not yet implemented |
| One active transaction and full-to-full calculation | Not yet observed | Lock and shared interval calculation not yet implemented |

**Scope deliberately not taken:** partial fills, extension/reprint, full discrepancy matrix,
assignment changes, resets, cancellation/replacement, generators, consolidated reporting,
historical import, and OCR belong to later workstreams.

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Configure two locations and users, one approved station, fuel type, vehicle model, vehicle asset, active assignment, validity instruction, and the three operational roles. | The vehicle has one active custodian/location assignment; stable fuel/capacity/target values and role/location grants are visible to Fleet Admin. | AC-01, AC-02 |
| 2 | As a Fleet User permitted for the vehicle location, create an order naming a non-login Fleet Person as requester/driver and submit it. | The order enters Pending Approval; the operational person and entering User remain distinct audit facts. | AC-01, AC-02 |
| 3 | Give the entering user both Fleet User and Fleet Approver, then try to approve their order; approve it as another permitted location Approver. | Self-approval is denied server-side; the different Approver submits and freezes the order. | AC-03 |
| 4 | Print the approved order. | It shows order number, asset, station, fuel, quantity basis, exact valid-until timestamp, configurable no-dispense-after-expiry instruction, and signature areas. | AC-04 |
| 5 | As a permitted Fleet User, try to submit the transaction with a missing, public, or invalid signed document. | Submission identifies and rejects the invalid evidence. | AC-05 |
| 6 | Attach both valid private signed documents and submit a full-fill transaction at odometer 10,000. | The transaction submits, its order becomes Completed, and Vehicle Performance shows a baseline with no km/L. | AC-05, AC-06 |
| 7 | Complete a second independently approved full-fill order at odometer 10,500 with 50 actual litres. | Vehicle Performance shows 500 km, 50 litres, and 10 km/L; it links both interval endpoints and source records. | AC-06 |
| 8 | As a user permitted only for the other location, try list, direct URL, report, print, and workflow access to the vehicle records. | Every path denies or filters the records consistently. | AC-02 |
| 9 | Try transaction submission with a changed station, fuel type, asset, or actual fueling time outside the approved window. | Each mismatch is rejected server-side without changing the order snapshots. | AC-07 |
| 10 | Submit or concurrently attempt another active transaction for either completed order. | The order lock and active-transaction rule allow only one active transaction. | AC-07 |

**How to run it.** Automated checks cover document, workflow, permission, file, locking, and
calculation assertions on the test site. Rows 2–10 also require a Desk walkthrough because role
experience, printing, physical-signature flow, private-file presentation, and report drill-down
are not fully asserted by unit tests.

**Result:** 0 of 10 observed. Phase not started.

## What we learned that the plan did not predict

None yet.

## Known limitations — accepted, not fixed

- No development/test site exists; provisioning is a prerequisite, not a phase defect.
- The phase proves only full vehicle fills; controlled partial accumulation is Phase 1.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Not applicable before implementation.

**Next:** Review and approve the revised specification, then provision development and test sites.
