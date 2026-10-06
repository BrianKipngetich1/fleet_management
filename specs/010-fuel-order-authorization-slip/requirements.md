<!--
Requirements for the Fueling Transaction only. The approved LPO is a read-only source of context.
-->

# Fueling Transaction layout and fuel analysis: requirements

Approved by: Margaret Maina (@BrianKipngetich1) · 06/10/2026 · revision 4344b53 (explained by agent)

| | |
|---|---|
| Tier | Heavy |
| Branch | feature/010-fuel-order-authorization-slip |

## Introduction

Fleet staff need a clear Fueling Transaction screen that brings the approved LPO details and
actual fuel delivery together, so they can enter and review a transaction without switching
between the order, the transaction, and a physical document. Reviewers also need enough
transaction data to analyze fuel use, efficiency, litre overruns, and fuel-only spend.

This change applies only to the existing Fueling Transaction and its analysis. The existing
approved LPO can be selected and read for reference, but its fields, form, workflow, approval
process, calculations, and printed slip must not be changed.

## Requirements

### Requirement 1: Enter and review a transaction with its approved order context

**User Story:** As fleet staff, I want the approved order details and actual fueling facts together
on the transaction screen, so that I can record a fueling without looking up the order or paper.

#### Acceptance Criteria

1. WHEN staff start a transaction by entering or selecting an approved LPO number THE system
   SHALL show the asset identity, location, approved station and fuel, full-tank or partial
   quantity authorization, validity deadline, driver, and company representative from that LPO.
2. WHEN the LPO details appear on the transaction screen THE system SHALL treat them as
   read-only reference information and SHALL NOT change any LPO field, form, workflow, approval,
   calculation, or printed slip.
3. WHEN staff enter or review a transaction THE system SHALL show the approved order context
   beside the actual fueling facts, distinguish approved values from actual results, and keep
   the information together so staff do not need to switch screens to compare them.
4. WHEN the linked asset is a vehicle THE system SHALL show the vehicle odometer for entry and
   SHALL NOT show a generator hour meter; WHEN it is a generator THE system SHALL show its hour
   meter and SHALL NOT show a vehicle odometer.
5. WHEN staff save a new transaction THE system SHALL require both actual litres and the pre-tax
   fuel amount in KES, and SHALL refuse to save if either is missing. Staff SHALL be able to
   enter the fueling date and time, invoice and CU numbers, applicable meter reading, full-tank
   result, attendant, and signed invoice and order evidence; the station and fuel already
   available from the LPO SHALL NOT need to be re-entered.
6. WHEN a receipt has no printed fueling time THE system SHALL require staff to explain how the
   known station fueling time was established.
7. WHEN staff enter or change actual litres THE system SHALL compare them with the applicable
   LPO litre baseline: the saved estimated litres for a vehicle and the approved litres for a
   generator. It SHALL show green when actual litres are at or below the baseline, orange when
   they are more than zero and up to 15% over, and red “Overrun” when they are more than 15%
   over. The variance SHALL use litres only and SHALL NOT use the pre-tax amount. IF no usable
   baseline exists THEN THE system SHALL show that no comparison is available.
8. WHEN staff submit or review a transaction THE system SHALL continue to enforce the existing
   transaction, order-link, validity, station, evidence, role, and location checks.

### Requirement 2: Record fuel cost and analyze fuel transactions

**User Story:** As a fleet reviewer, I want fuel-only cost and usage measures available from
Fueling Transactions, so that I can analyze fuel use, efficiency, litre overruns, and spend
without looking up the physical document.

#### Acceptance Criteria

1. WHEN staff record a fuel-only receipt THE system SHALL let them enter the fuel amount before
   tax in KES.
2. WHEN staff save a new transaction THE system SHALL require both invoice litres and the
   pre-tax fuel amount in KES, and SHALL refuse to save if either value is missing. New
   submissions SHALL also require the existing required fueling facts and signed invoice
   evidence.
3. WHEN staff enter the pre-tax amount THE system SHALL calculate tax at 8% and show the final
   invoice amount as pre-tax amount plus calculated tax.
4. WHEN a transaction's pre-tax cost per litre is shown THE system SHALL calculate it from the
   pre-tax fuel amount divided by actual litres; IF either value is missing or invalid THEN the
   result SHALL be unavailable.
5. WHEN staff review fuel analysis THE system SHALL allow filtering by date range, asset,
   location, fuel type, and station, and SHALL show the order number, approved authorization,
   applicable LPO litre baseline, actual date and time, station, fuel, actual litres, litre
   variance status, applicable meter reading, full-tank result, total pre-tax fuel spend, pre-tax
   cost per litre, valid vehicle efficiency, and full-tank exceptions.
6. WHEN a vehicle has valid qualifying full-tank readings THE system SHALL show its existing
   valid distance-per-litre efficiency; WHEN a generator has two confirmed full-tank readings
   with increasing hour-meter values THE system SHALL show litres used per operating hour between
   those readings, including fuel purchased after the earlier full tank through the later full
   tank.
7. WHILE a generator lacks two confirmed full-tank readings or increasing hour-meter values THE
   system SHALL leave its litres-per-operating-hour result unavailable.
8. WHEN analysis combines multiple transactions THE system SHALL calculate combined pre-tax cost
   per litre from total pre-tax fuel spend divided by total litres.
9. WHEN an existing transaction has no recorded fuel amount THE system SHALL show “Not recorded”
   and SHALL NOT invent or estimate an amount.
10. WHEN a user reviews or exports fuel analysis THE system SHALL continue to enforce existing
    role, location, and export permissions, and SHALL allow permitted users to download the
    filtered results for further analysis.

## Out of scope

- Any changes to the LPO, including its fields, form, workflow, approvals, validity, calculations,
  or printed slip. The transaction may display existing LPO values as read-only context.
- A new Fueling Transaction DocType or a duplicate transaction record.
- Recording costs for non-fuel items or allocating mixed purchases to fuel.
- Changing current transaction roles, location access, or approval permissions.
- Backfilling or estimating historical fuel costs.
