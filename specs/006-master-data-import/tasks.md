<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->

# Import the fleet's master lists: tasks

## Phase 1: Import the master lists

**Tracer:** An administrator saves a Data Import for Fleet Location, downloads its blank Excel
template, and imports a filled one.

- [ ] 1.1 Show the refusal today: saving a Data Import for Fleet Location fails
  - _Requirements: 1.1_
- [ ] 1.2 Set `allow_import` on the six master DocTypes; migrate the main site
  - _Requirements: 1.1_
- [ ] 1.3 Test Property 1: import open for the six, refused for orders and fuellings
  - _Requirements: 1.1, 2.2_
- [ ] 1.4 Test Property 2: an asset with an assignment row imports; a bad row is reported
  - _Requirements: 1.2, 1.3_
- [ ] 1.5 Confirm Fleet Admin, Fleet User, and Fleet Approver still cannot open the import tool, and the suites still pass
  - _Requirements: 2.1, 2.3_

## Progress log

- `30/09/2026`: Requirements and design written. Next: approval, then 1.1.
