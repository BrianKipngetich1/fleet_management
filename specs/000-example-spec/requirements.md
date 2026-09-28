# Equipment checkout: requirements

Approved by: Jordan Lee (@jordan-lee) · 12/08/2026 · revision a1c4e02

| | |
|---|---|
| Tier | `Heavy` |
| Branch | `feature/000-equipment-checkout` |

## Introduction

Shared equipment (cameras, laptops, site tools) is tracked in a spreadsheet a custodian
updates by hand. Nothing stops two people writing themselves down as holding the same item,
nobody can tell at a glance what is currently out, and a borrower has no record they can point
to when asked to bring something back.

## Requirements

### Requirement 1: Request an item

**User Story:** As a borrower, I want to request an item from the shared pool, so that I have
a record of what I asked for and can withdraw it if my plans change.

#### Acceptance Criteria

1. WHEN a borrower submits a request for an available item THE system SHALL record the
   request as waiting to be issued.
2. WHEN a borrower withdraws a request that has not been issued THE system SHALL record it as
   cancelled.
3. IF a borrower tries to cancel a request that has been issued THEN THE system SHALL refuse
   the cancellation.

### Requirement 2: Issue an item

**User Story:** As a custodian, I want to hand an item to a borrower through the system, so
that the pool always shows who holds what.

#### Acceptance Criteria

1. WHEN a custodian issues a waiting request THE system SHALL record the item as on loan to
   that borrower.
2. IF an item is already on loan THEN THE system SHALL refuse to issue it again, even when two
   custodians try at the same moment.
3. IF anyone other than a custodian tries to issue or return an item THEN THE system SHALL
   refuse the action.
4. IF anyone tries to delete an issued or returned loan THEN THE system SHALL refuse.

### Requirement 3: Return an item

**User Story:** As a custodian, I want to record an item coming back, so that it can be lent
again at once.

#### Acceptance Criteria

1. WHEN a custodian records a return THE system SHALL mark the item available and record the
   return time.

### Requirement 4: See overdue loans

**User Story:** As a custodian, I want loans past their due date to stand out, so that I know
whom to chase.

#### Acceptance Criteria

1. WHILE an issued item is past its due date and not returned THE system SHALL show the loan
   as overdue on the custodian's list.
2. WHEN an overdue loan is returned THE system SHALL stop showing it as overdue.

### Requirement 5: Unchanged behaviour

**User Story:** As a staff member, I want everything outside equipment loans to work as it
does today, so that this change disturbs nothing else.

#### Acceptance Criteria

1. WHEN a person uses any existing document or report THE system SHALL CONTINUE TO show and
   allow exactly what it did before.

## Sample data

- Jordan Lee (Custodian), Priya Nair (Borrower), Samuel Otieno (Borrower).
- Items: a Canon EOS R6 camera and a Dell Latitude 7440 laptop.

## Out of scope

- Condition or damage reporting on return.
- Reservations or a waitlist for an item that is already out.
- Overdue email or chat reminders; overdue loans are only shown, nobody is notified.
- Lending several items on one request.
