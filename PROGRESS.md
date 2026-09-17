# Progress

One row per specification. Detail lives in the specification and its phase records —
this file is a pointer, never a journal. Overwrite the rows; do not append to them.
Status history is git's job.

| Specification | Status | Phases | Next action |
|---|---|---|---|
| [001 — Fleet and Fuel Management](specs/001-fleet-fuel-management/spec.md) | Draft | not started | Review and approve the implementation specification before implementation |

Record execution order here when it is not phase-id order.

A specification may be **parked** so another takes priority. Parked is not abandoned and
not cleared: its phase records and open findings stay exactly as they are, and it resumes
at the phase named in its status.

## Environment

| | |
|---|---|
| Bench root | /home/kayadmin/frappe-bench |
| Development site | not configured |
| Test site | not configured (all functional testing) |
| Base branch | version-16 (current app branch) |

## Phase records

Every phase has exactly one record under `specs/[NNN-name]/verification/phase-NN-[slug].md`,
written to `specs/TEMPLATE-verification.md`. A record states the current position; it is
not a chronicle.
