<!--
The proof document. Written as the phase is verified, from what was actually observed.
This scaffold remains Not started until implementation and test-site verification.
-->

# Phase 0 — One complete vehicle journey

| | |
|---|---|
| Specification | [../spec.md](../spec.md) @ draft |
| Status | Not started |
| Started / Closed | — / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-01–AC-06 |

## What this phase makes true

An authorised requester can create a vehicle Fuel Order and submit it for approval. A
different location approver can approve or reject it, and an approved order can be printed
for the physical fueling process. After fueling, the Data Entry User can attach the signed
invoice and signed slip, submit one linked transaction, and see either a valid first baseline
or an explicit absence of an efficiency result.

## The rule, as observed

Not yet observed. This phase has not been implemented.

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingApproval: requester submits
    PendingApproval --> Approved: approver approves
    PendingApproval --> Rejected: approver rejects
    Approved --> Completed: transaction submitted
~~~

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|
| Draft → PendingApproval | no | Unbuilt or untested |
| PendingApproval → Approved | no | Unbuilt or untested |
| PendingApproval → Rejected | no | Unbuilt or untested |
| Approved → Completed | no | Unbuilt or untested |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Forms, naming, attachments, print | Not yet observed | Not yet implemented |
| Approval state and role gate | Not yet observed | Not yet implemented |
| One active transaction per order | Not yet observed | Not yet implemented |

**Scope deliberately not taken:** generator calculations, full exception matrix, historical
import, and OCR belong to later workstreams.

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | As an authorised requester, create an order for the configured vehicle and submit it. | The order enters Pending Approval and the derived approver is the vehicle-location approver. | AC-01 |
| 2 | As the assigned approver, approve the order. | The order enters Approved and the requester and Fleet Manager receive notification. | AC-02 |
| 3 | Print the approved order and inspect it. | The asset, readings, approved quantity basis, order number, and approver signature area are readable. | AC-03 |
| 4 | As Data Entry, submit a transaction without one required attachment. | Submission is rejected with the missing attachment identified. | AC-04 |
| 5 | Attach the signed invoice and signed slip, then submit one transaction. | The transaction submits, the order completes, and the source documents are linked and renamed. | AC-05 |
| 6 | Open the first vehicle transaction report. | No efficiency result is shown because no prior qualifying full fill exists. | AC-06 |

**How to run it.** Automated rows cover document, workflow, attachment, and calculation
assertions on the test site. Rows 2–6 also require a Desk walkthrough because printing,
physical-signature workflow, attachment presentation, and role experience are not fully
asserted by unit tests.

**Result:** 0 of 6 observed. Phase not started.

## What we learned that the plan did not predict

None yet.

## Known limitations — accepted, not fixed

- No development/test site exists yet; provisioning is a prerequisite, not a phase defect.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Not applicable before implementation.

**Next:** Review and approve the specification, then provision the development and test sites.
