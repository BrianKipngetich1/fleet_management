<!-- Small presentation change for the existing Fueling Transaction. -->

# Fueling Transaction entry layout: requirements

Approved by: Margaret Maina (@BrianKipngetich1) · 06/10/2026 · revision a19f675 (explained by agent)

| | |
|---|---|
| Tier | Small |
| Branch | feature/010-fuel-order-authorization-slip |

## Introduction

The Fueling Transaction page feels cramped when staff compare the approved Fuel Order with
the invoice. The vehicle registration number is mixed into other asset details, and the
signed order and invoice are not positioned together for review.

## Requirements

### Requirement 1: Make the order and transaction easier to read

**User Story:** As fleet staff, I want the Fuel Order and invoice details arranged clearly,
so that I can check the approved order while recording and reviewing the transaction.

#### Acceptance Criteria

1. WHEN staff open a Fueling Transaction on a wide screen THE system SHALL show the approved
   Fuel Order details as a vertical list on the left and the transaction details in horizontal
   rows in the wider area on the right.
2. WHEN the linked asset is a vehicle THE system SHALL show its registration number on its
   own line above the other vehicle details in the Fuel Order list.
3. WHEN staff review transaction evidence THE system SHALL show the signed Fuel Order on the
   left and the signed invoice on the right in the same row.
4. WHEN staff review the transaction THE system SHALL CONTINUE TO show the existing baseline,
   litre status, and efficiency summary below the order and transaction details.
5. WHEN staff open a Fueling Transaction on a narrow screen THE system SHALL CONTINUE TO stack
   the Fuel Order above the transaction details and keep the summary below them.

### Requirement 2: Preserve transaction behaviour

**User Story:** As fleet staff, I want the layout change to preserve the current transaction
checks, so that approved order and invoice records remain reliable.

#### Acceptance Criteria

1. WHEN staff submit a Fueling Transaction THE system SHALL CONTINUE TO enforce the existing
   order approval, fueling time, litres, amount, evidence, role, and location checks and preserve
   the linked Fuel Order without changes.

## Out of scope

- Changing Fuel Order approval, values, or printed slip.
- Changing the time-source validation, invoice calculations, litre thresholds, or efficiency
  calculations.
- Changing transaction permissions or storing additional transaction data.

## Open questions

None.
