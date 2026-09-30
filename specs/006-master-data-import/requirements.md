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

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->

# Import the fleet's master lists: requirements

Approved by: Brian Kipngetich (@BrianKipngetich1) · 30/09/2026 · revision 9e45cae (explained by agent)

| | |
|---|---|
| Tier | `Small` |
| Branch | `feature/006-master-data-import` |

## Introduction

The owner wants to collect the company's real master lists (locations, fuel types, vehicle
models, people, fuel stations, and the vehicles and generators with who holds them) in Excel
templates taken from the system, fill them in, and load them back. Today the system refuses
to start an import for any of these lists, so no template can be downloaded either.

## Requirements

### Requirement 1: Import the master lists

**User Story:** As a system administrator, I want to download a blank Excel
template for each master list and import the filled-in file, so that the real master data can
be loaded without typing each record by hand.

#### Acceptance Criteria

1. WHEN a system administrator starts an import for locations, fuel types,
   vehicle models, people, fuel stations, or vehicles and generators THE system SHALL accept
   it and offer a blank Excel template for that list.
2. WHEN a filled-in template is imported THE system SHALL create each record under the same
   rules as creating it by hand, and SHALL report every row it refuses and why.
3. WHEN the vehicles and generators template is filled in THE system SHALL accept each
   vehicle's holder history (holder, home location, from and until dates) in the same file.

### Requirement 2: Unchanged behaviour

**User Story:** As a Fleet User or Fleet Approver, I want everything else to work as before, so
that the import does not change who may do what.

#### Acceptance Criteria

1. WHEN a Fleet Admin, Fleet User, or Fleet Approver looks for the import tool THE system
   SHALL CONTINUE TO refuse it, as today; only a system administrator imports.
2. WHEN anyone looks for an import of fuel orders or fuellings THE system SHALL CONTINUE TO
   refuse it, so every order and fuelling still goes through approval.
3. WHEN the server and browser tests run THE system SHALL CONTINUE TO pass as before.

## Out of scope

- Past fuelling history: it is loaded into the test site by the sample-data script, not by
  import, because each order must pass approval, photos, and sign-off.
- The company rules page: it has a single set of values with nothing to import.
- The planned order-form automation (no driver field, requester and custodian from the
  vehicle, default company representative, fixed location and station, partial litres shown
  only for a partial fill), and the new generator tank size and per-order maximum: a later
  specification.
- Letting a Fleet Admin import without system administrator rights.
- An Export item in each list's menu (asked 30/09/2026, not urgent).

## Open questions

None.
