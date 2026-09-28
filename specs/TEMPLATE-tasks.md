<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->

# <Feature name>: tasks

## Phase 1: <name>

**Tracer:** <the one thing a person can do afterwards that they could not do before.>

- [ ] 1.1 <task>
  - _Requirements: 1.1_
- [ ] 1.2 Test Property 1: <name>
  - _Requirements: 1.1_
- [ ] 1.3 Confirm existing behaviour still holds
  - _Requirements: 2.1_

## Progress log

One line per finished task or phase, newest last. Link the verification record when a phase
closes.

- `DD/MM/YYYY`: <what was done>. Next: <task>.
