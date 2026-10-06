<!--
What the requester needs, in their own business words. Acceptance criteria use EARS form and
are cited by tasks after the design is approved. Keep technical names and implementation details
in design.md.
-->

# Fuel Order authorization and fueling record: requirements

Approved by: pending

| | |
|---|---|
| Tier | `Heavy` |
| Branch | `feature/010-fuel-order-authorization-slip` |

## Introduction

Fleet staff need a controlled paper authorization that a station attendant can check before
dispensing fuel and that the company can later match to the electronic fueling record. The
current approved order slip does not bring the authorization, validity warning, actual fueling
record, and both parties' confirmations together on one page.

The new slip will use the approved order and its linked vehicle, driver, representative, and
station. Staff will enter the actual fueling in the system's current transaction record, attach
the signed slip, and retain the order-to-transaction audit trail.

## Requirements

### Requirement 1: Print only an approved authorization

**User Story:** As a permitted fleet staff member, I want to print an approved order as an
authorization, so that the station receives a document backed by the current approval.

#### Acceptance Criteria

1. WHEN an order reaches Approved through the current approval process THE system SHALL make
   the official print action available to users who already have permission to print it.
2. IF an order is a draft, waiting for a decision, rejected, or cancelled THEN THE system SHALL
   refuse to generate an official authorization slip for it.
3. WHEN an approved order is printed THE system SHALL show its order number and approved status
   and use the order's approved vehicle, fuel, representative, and station as the authorization
   source.
4. WHEN an approved order has expired THE system SHALL mark the opened order and any printed
   copy “EXPIRED — DO NOT FUEL”; printing that copy SHALL NOT extend its validity.

### Requirement 2: Configurable working-day validity

**User Story:** As a fleet administrator, I want the fueling deadline to follow the company's
working days, so that the order cannot be honored after its approval period.

#### Acceptance Criteria

1. WHEN a fleet administrator opens the validity setting THE system SHALL show a configurable
   working-day grace period. New installations SHALL start at two days; the current site's saved
   value of three SHALL be preserved until a fleet administrator changes it.
2. WHEN an order is approved THE system SHALL calculate and save its last valid date and time
   from the approval date and time, the configured grace period, and the company's working-day
   calendar; Sundays and public holidays SHALL be excluded and Saturdays SHALL count as working
   days.
3. WHEN the validity setting changes THE system SHALL leave the saved deadline on every already
   approved order unchanged.
4. WHEN an approved order's actual fueling date and time is before approval or after its saved
   deadline THE system SHALL refuse submission of the fueling record.
5. WHEN an approved order's validity is extended under the current extension rules THE system
   SHALL retain the extension reason and require the current slip revision to be printed before
   a fueling record is submitted.
6. WHEN the approval-validity setting changes THE system SHALL leave the separate post-fueling
   transaction-entry deadline and late-entry controls unchanged.
7. WHEN no usable Holiday List is installed THE system SHALL let permitted fleet administrators
   maintain public holiday dates in Fleet Management Settings, and SHALL exclude those dates
   from the approval-validity calculation.

### Requirement 3: Show the authorization clearly

**User Story:** As a station attendant, I want to identify the company, order, vehicle, station,
and deadline at a glance, so that I can check the authorization before dispensing fuel.

#### Acceptance Criteria

1. WHEN an approved order is printed THE system SHALL show the company name and logo when
   available, the Fleet and Fuel Management heading, the title “FUEL ORDER AUTHORIZATION &
   FUELING RECORD”, order number, and approval status.
2. WHEN an approved order is printed THE system SHALL prominently show “APPROVED ON” and
   “FUELING VALID UNTIL” with the saved date and time, and SHALL show “FUEL MUST NOT BE
   DISPENSED AFTER” with that deadline.
3. WHEN an approved order is printed THE system SHALL identify the authorized vehicle or
   generator, its registration or asset name, its make and model when available, fuel type,
   driver, and company representative from the order and linked records.
4. WHEN an approved order is printed THE system SHALL show the station selected on the approved
   order and its full saved address, and SHALL state “Fuel may only be dispensed at the
   authorized station indicated on this order.”
5. WHEN an approved order requests a full tank THE system SHALL show “FULL TANK” prominently;
   WHEN it authorizes a partial quantity THE system SHALL show that approved quantity and SHALL
   NOT describe it as a full tank.
6. WHEN a printed order includes instructions for the attendant THE system SHALL retain the
   current instruction that agrees with the system's station restriction.

### Requirement 4: Record the actual fueling on paper

**User Story:** As a company representative, I want clear spaces to record and confirm what the
station actually supplied, so that the signed slip can support the later electronic record.

#### Acceptance Criteria

1. WHEN an approved order is printed THE system SHALL provide blank spaces for the actual
   fueling date, fueling time, litres purchased, and the correct vehicle odometer or generator
   hour-meter reading.
2. WHEN fuel is recorded on the slip THE system SHALL provide separate “YES” and “NO” choices
   for whether the full tank was achieved; the answer SHALL be a human confirmation and SHALL
   NOT be inferred from litres purchased.
3. WHEN the company representative completes the slip THE system SHALL show the representative's
   known name and provide checks for vehicle identity, order match, full-tank result, litres, and
   meter reading, plus space for signature and date.
4. WHEN the attendant completes the slip THE system SHALL show the confirmation “I confirm that
   the above vehicle was fueled against the stated Fuel Order.” and provide space for attendant
   name, signature, date, and station stamp.
5. WHEN the slip is printed THE system SHALL fit the authorization and completion areas on one
   A5 portrait page, keep each signature block together, and render its essential values without
   client-side JavaScript; each signature area SHALL be large enough for a handwritten signature.
6. WHEN the slip is printed THE system SHALL NOT ask staff to write calculated fuel remaining,
   tank capacity minus litres, or another system-calculated value.

### Requirement 5: Keep the transaction and audit trail connected

**User Story:** As a fleet reviewer, I want the completed paper slip and actual fueling record
to point to the same approved order, so that I can trace what was authorized and what happened.

#### Acceptance Criteria

1. WHEN staff submit a fueling record THE system SHALL link it to the approved order and retain
   the actual station, fuel type, fueling date and time, litres purchased, applicable meter
   reading, full-tank confirmation, attendant name, and signed-slip evidence.
2. WHEN staff record actual fueling THE system SHALL use the current fueling record and
   SHALL NOT create a competing fueling record.
3. WHEN a full-tank authorization is recorded as not achieved THE system SHALL preserve the
   actual litres and meter reading and make that result visible for review.
4. WHEN a full tank is confirmed and the system has a valid tank capacity and positive actual
   litres no greater than that capacity THE system SHALL calculate tank capacity minus actual
   litres as an estimate of fuel present before fueling, label it as an estimate, and keep it
   off the paper slip.
5. WHEN users inspect or submit the order, slip, or fueling record THE system SHALL continue to
   enforce the current approval, evidence, location, and role permissions.

### Requirement 6: Preserve the current fuel-order process

**User Story:** As a fleet staff member, I want current order, extension, and fueling rules to
keep working, so that the new paper record does not weaken existing controls.

#### Acceptance Criteria

1. WHEN staff create, approve, reject, extend, or fulfill an order THE system SHALL CONTINUE TO
   use the current workflow, approval roles, location checks, extension history, and slip
   revision controls.
2. WHEN a user searches for an order's vehicle or station THE system SHALL use the records
   already selected on that order and their existing identifying details; printing SHALL NOT
   invite a user to substitute another vehicle or station.

## Out of scope

- Replacing partial-quantity authorizations with full-tank-only orders.
- A new fueling transaction DocType or duplicate copies of values already linked to the order.
- A public verification page, public QR token, or QR code that exposes order details without
  the existing access checks. The printed order number remains the lookup key.
- Changing who may create, approve, extend, or submit fuel records.
