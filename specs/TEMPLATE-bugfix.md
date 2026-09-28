<!--
What is wrong, what should happen, and what must not change (Kiro's bugfix.md). It replaces
requirements.md for a bug. Written in step 1 of the Kaysalt workflow and approved before the
fix is designed. Audience: the requester, who may be non-technical, and an agent resuming
cold.

Business language only: no DocType, field, file, or function names, and no snake_case.
Criteria are numbered within their section and cited as N.k: current behaviour is 1.k,
expected behaviour 2.k, unchanged behaviour 3.k. Never renumber: retire a criterion by
replacing its text with "Removed: <reason>". Every criterion is cited by a task in tasks.md,
including a task that shows the bug exists. `scripts/spec-check.py` enforces all of this.

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->

# <Bug name>: bugfix

Approved by: pending

| | |
|---|---|
| Tier | `Small` \| `Heavy` |
| Branch | `fix/<NNN>-<summary>` |

## How to reproduce

The steps a person takes, as which role, and what they see.

## Current behaviour

1. WHEN <condition> THEN the system <wrong behaviour>.

## Expected behaviour

1. WHEN <condition> THEN THE system SHALL <correct behaviour>.

## Unchanged behaviour

1. WHEN <condition> THEN THE system SHALL CONTINUE TO <existing behaviour>.

## Sample data

Optional. The people (one per role, named with the role) and the records needed to reproduce
the bug.

## Open questions

Each one is answered by the requester before approval, then removed.
