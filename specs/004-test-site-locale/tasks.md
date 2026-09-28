<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->


# Test-site rebuild and regional settings: tasks

## Phase 1: Test site builds with the Kenya Locale

**Tracer:** the pre-PR test-site rebuild produces the usual sample-data site, and a migrate
compares the main site with a recorded Kenya Locale.

- [ ] 1.1 Show the bug: blank `LOCALE_*`, `scripts/rebuild-test-site.sh` stops on
  `LOCALE_COUNTRY`, `scripts/migrate.sh` says "Locale matches", and the stray root `fixtures/`
  is untracked
  - _Requirements: 1.1, 1.2, 1.3, 1.4_
- [ ] 1.2 Fill `LOCALE_*` in `.kaysalt/project.conf` from the main site's System Settings
  (D-1); `scripts/migrate.sh` reports the Kenya Locale matches
  - _Requirements: 2.1, 2.3_
- [ ] 1.3 Re-confirm and delete the untracked root `fixtures/` (D-5); migrate still creates the
  Fleet roles
  - _Requirements: 2.5, 3.5_
- [ ] 1.4 Point the kit's build-command setting at `bench fleet-test-site up --replace` (D-2)
  and confirm a blank Locale stops the scripts (D-3)
  - _Requirements: 2.2, 2.4_
- [ ] 1.5 Build the test site the way the pipeline will, confirm MariaDB, Philip, Vikas, Amina,
  the vehicles and generators, and dd/mm/yyyy, run the one-step test run, then tear it down;
  the main site gets no test records
  - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4_

## Progress log

- `28/09/2026`: Spec written. Next: approval, then 1.1.
