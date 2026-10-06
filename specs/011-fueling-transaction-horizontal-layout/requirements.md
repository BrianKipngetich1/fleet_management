<!--
Small layout change for the existing Fueling Transaction. The linked Fuel Order stays read-only.
-->

# Fueling Transaction side-by-side layout and summary: requirements

Approved by: pending

| | |
|---|---|
| Tier | Small |
| Branch | feature/010-fuel-order-authorization-slip |

## Introduction

The Fueling Transaction page currently places the approved LPO details and invoice entry in a
long vertical flow. Staff want to compare the order and the actual invoice at a glance, with a
short summary underneath.

## Requirements

### Requirement 1: Compare the LPO and invoice on one page

**User Story:** As fleet staff, I want the LPO details beside the invoice entry, so that I can
record and review a transaction without scrolling back and forth.

#### Acceptance Criteria

1. WHEN staff open a Fueling Transaction on a wide screen THE system SHALL show read-only LPO
   details on the left and actual invoice transaction details on the right.
2. WHEN staff enter or change invoice litres THE system SHALL update a summary below those details
   with the LPO baseline, actual litres, and the existing green, orange, or red litre status.
3. WHEN a valid efficiency result exists for the transaction THE system SHALL show vehicle
   kilometres per litre or generator litres per operating hour, as applicable; IF no valid result
   exists yet THEN THE system SHALL say that efficiency is not yet available.
4. WHEN the page is viewed on a narrow screen THE system SHALL stack the LPO details above the
   invoice details and keep the summary below them.
5. WHEN staff save or submit a transaction THE system SHALL CONTINUE TO enforce the existing
   required values, order approval, timing, evidence, role, and location checks without changing
   the linked LPO.

## Out of scope

- Changing Fuel Order fields, approvals, calculations, or printed slip.
- Changing invoice amounts, tax calculation, role access, or the existing analysis report.
- Saving duplicate LPO details or a new efficiency value to a transaction.

## Open questions

None.
