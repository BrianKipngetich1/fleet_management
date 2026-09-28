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

# <Feature name>: requirements

Approved by: pending

| | |
|---|---|
| Tier | `Small` \| `Heavy` |
| Branch | `<type>/<NNN>-<summary>` |

## Introduction

One or two paragraphs. What can a person not do today, or what goes wrong when they try?
No solution here.

## Requirements

### Requirement 1: <title>

**User Story:** As a <role>, I want <action>, so that <outcome>.

#### Acceptance Criteria

1. WHEN <trigger> THE system SHALL <response>.

### Requirement 2: Unchanged behaviour

**User Story:** As a <role>, I want <existing behaviour> to keep working, so that <outcome>.

#### Acceptance Criteria

1. WHEN <trigger> THE system SHALL CONTINUE TO <existing behaviour>.

## Sample data

Optional. The people (one per role, named with the role, e.g. "<Name> (<Role>)") and the
real places or products the requester wants to see in test and demo data.

## Out of scope

What this deliberately does not do, so a reviewer does not raise it as a gap.

## Open questions

Each one is answered by the requester before approval, then removed.
