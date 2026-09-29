<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->


# Fleet home page and a test site that copies the main site: tasks

## Phase 1: Every Fleet role gets a Fleet home page

**Tracer:** Philip opens the home screen and finds a Fleet icon leading to his fuel orders.

- [ ] 1.1 Show the bug: on the test site Philip's home screen has no icon (screenshot); neither site
  has a Fleet `Desktop Icon`; the main site's Fleet User has only standard icons
  - _Requirements: 1.1, 1.2_
- [ ] 1.2 Add the "Fleet" and "Fleet Setup" desktop icons, sidebars, and workspace (D-1, D-2);
  migrate the main site
  - _Requirements: 2.1, 2.2, 2.3, 3.5_
- [ ] 1.3 Test Property 1: Fleet icon visible to all three Fleet roles, Fleet Setup to Fleet Admin
  only (IntegrationTestCase)
  - _Requirements: 2.1, 2.2, 2.3_
- [ ] 1.4 Walk it through on the test site as Philip, Vikas, Amina, and the Test Fleet Admin, and
  as Administrator; Philip's lists still show only Nairobi
  - _Requirements: 2.1, 2.2, 2.3, 3.2, 3.5_

## Phase 2: The test site copies the main site's setup and checks every login

**Tracer:** a rebuild takes the main site's Fleet rules and refuses to finish with a login missing.

- [ ] 2.1 Show the bug: the test site's Fleet rules differ from the main site's set values; a sample
  person left out of a copy of the login file only loses their login
  - _Requirements: 1.3, 1.4_
- [ ] 2.2 Copy the main site's date format and non-blank Fleet rules after seeding (D-3); Test
  Property 2
  - _Requirements: 2.4, 3.1_
- [ ] 2.3 Stop on a missing login before changing anything, and check every login signs in (D-4);
  Test Property 3
  - _Requirements: 2.5, 2.6, 3.4_
- [ ] 2.4 Prove it: rebuild the test site; Philip, Vikas, Amina, and the Test Fleet Admin sign in;
  settings match the main site; server suite and `npm run test:ui` pass; main site unchanged
  - _Requirements: 2.4, 2.6, 3.1, 3.3, 3.6_

## Progress log

- `29/09/2026`: Spec written from the owner's answers to questions 1 and 2. Next: approval, then 1.1.
