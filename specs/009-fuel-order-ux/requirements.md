<!--
What the requester needs, in their own business words (Kiro's requirements.md). Written in
step 1 of the Kaysalt workflow and approved before design starts. A bug uses
TEMPLATE-bugfix.md instead. Audience: the requester, who may be non-technical, and an agent
resuming cold.

Business language only: no DocType, field, file, or function names, and no snake_case.
Acceptance criteria are numbered within their requirement and cited as N.k (criterion 2 of
Requirement 1 is 1.2). Never renumber: retire a criterion by replacing its text with
"Removed: <reason>". Every criterion is cited by a task in tasks.md.
`scripts/spec-check.py` enforces all of this.

EARS forms (keywords in capitals):
- THE system SHALL <response>.
- WHEN <trigger> THE system SHALL <response>.
- WHILE <state> THE system SHALL <response>.
- IF <unwanted condition> THEN THE system SHALL <response>.
- WHERE <option is enabled> THE system SHALL <response>.
- WHEN <trigger> THE system SHALL CONTINUE TO <existing behaviour>.  (unchanged behaviour)

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->

# Fuel Order experience: requirements

Approved by: pending

| | |
|---|---|
| Tier | `Heavy` |
| Branch | `feature/009-fuel-order-ux-brian` |

## Introduction

Fleet staff use fuel orders to request and authorize fuel, review the vehicle and assignment
facts, and follow the order through approval and fueling. The current screen presents these
details in a long standard form, so related information and the current decision can be hard to
scan quickly. The experience should make the existing process easier to understand and use
while keeping the business rules and records intact.

## Requirements

### Requirement 1: Clear fuel-order entry

**User Story:** As a fleet staff member, I want the information for a fuel order grouped in a
clear sequence, so that I can enter or review a request without searching through an unrelated
stack of fields.

#### Acceptance Criteria

1. WHEN a staff member starts or reviews a fuel order THE system SHALL group the existing
   information into clear areas for the order, vehicle, people, fueling request, evidence, and
   decision or history details, showing only information that already exists in the process.
2. WHEN a vehicle is selected THE system SHALL CONTINUE TO show its existing make and model,
   type, fuel type, effective custodian and location, prior entry, and supported estimate, while
   making clear which values are supplied by the system and which choices the staff member may
   change.
3. WHEN the form is shown on a desktop THE system SHALL arrange related information in a compact
   two-column layout, and on a narrow screen SHALL show the same information in one column
   without horizontal scrolling or unusable controls.
4. WHEN a required value is missing or invalid THE system SHALL CONTINUE TO identify the value
   that needs attention and allow the staff member to correct it using the existing validation
   rules.

### Requirement 2: Clear review and decisions

**User Story:** As a fleet user or approver, I want to see an order's state and decision at a
glance, so that I can take the next action allowed to me and understand why the order needs
attention.

#### Acceptance Criteria

1. WHEN a staff member opens an existing fuel order THE system SHALL show its current state,
   decision signal, and available actions before the remaining order details, with the reasons
   and recorded history visible on the same page.
2. WHEN an order has a green or red signal THE system SHALL show the written signal and its
   reasons so that meaning does not depend on color alone.
3. WHEN a staff member uses the existing order list THE system SHALL CONTINUE TO let them find
   and open the records available to their role, with the existing location restrictions and
   standard create, review, print, and workflow actions.

### Requirement 3: Keep the existing fleet process

**User Story:** As the fleet owner, I want the improved screen to keep the current order process
and records intact, so that staff continue to rely on the same approvals and controls.

#### Acceptance Criteria

1. WHEN a staff member saves, submits, approves, rejects, withdraws, prints, extends, or cancels
   an order THE system SHALL CONTINUE TO apply the existing server checks, role permissions,
   approval transitions, audit history, notifications, and printed-slip rules.
2. WHEN an order uses a vehicle, person, location, station, fuel type, or linked fueling record
   THE system SHALL CONTINUE TO use the existing relationships, assignment snapshots, filters,
   and validation rules.
3. THE system SHALL CONTINUE TO store the same business information with the same field names
   and meanings, without requiring existing orders or fueling records to be migrated.

## Sample data

Use the app's existing disposable test-site sample data and role accounts. Do not add demo or
production records for this screen redesign.

## Out of scope

- Changing who selects or supplies the requester, driver, custodian, company representative,
  operational location, station, or authorized quantity.
- Adding fields for price, cost, payment, fuel cards, or purchase orders.
- Changing approval policy, assignment rules, notifications, reporting, APIs, or fueling
  transaction behavior.
- Building a separate dashboard, duplicate order-management page, or additional frontend
  framework.
- Changing the printed approval slip or existing attachment rules.

## Open questions

None. The request is scoped to presentation and interaction changes that preserve the existing
business process.
