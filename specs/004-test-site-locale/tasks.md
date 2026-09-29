<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->


# Test-site rebuild, regional settings, and pull-request checks: tasks

Tasks marked T1–T3 are built in a separate worktree on `chore/kit-update-6d6918d` (PR #7); this
record stays on `fix/004-test-site-locale` (D-6). Nothing is pushed until the owner says "push".

## Phase 1: The app's own files pass the checks and the test site builds with the Kenya Locale

**Tracer:** the pre-PR test-site rebuild produces the usual sample-data site, a migrate compares
the main site with a recorded Kenya Locale, and the app's own code passes the formatting and lint
hooks.

- [x] 1.1 Show the bug on `develop` and PR #7: blank `LOCALE_*`; PR #7's `require_locale` stops on
  `LOCALE_COUNTRY`; develop's `scripts/migrate.sh` says "Locale matches"; the stray root
  `fixtures/` is untracked; `pre-commit run --all-files` rewrites 23 files and reports the 5 lint
  errors; the Server and UI jobs stop at `bench get-app [app_name]`. Record the "before" snapshot
  (both sites' Locale, the test site's config flags, `list-apps`) and the server-suite baseline
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
- [x] 1.2 T1: apply ruff 0.14.10 and prettier 2.7.1 to the app's own files, leaving
  `scripts/spec-check.py` byte-identical (D-8); hand-fix `fleet_asset.py` (`itertools.pairwise`),
  `test_fuel_order.py` (`# noqa: RUF001`) and `tests/test_sample_data.py` (`ClassVar[dict]`) (D-7).
  Check: every hook except the one on `spec-check.py` passes; `ruff format --check` and
  `ruff check` pass on everything else; the syntax tree of every reformatted file is unchanged
  and differs only at the 3 hand fixes; `python -m compileall` passes; Semgrep reports no finding
  new against `develop` (D-11); the snapshot equals "before"
  - _Requirements: 2.6, 3.6, 3.7_
- [x] 1.3 T2: fill `LOCALE_*` from the main site (D-1) and set
  `TEST_SITE_BUILD=bench fleet-test-site up --replace` (D-2); `scripts/migrate.sh` reports "Locale
  matches" for the main site; the snapshot equals "before"
  - _Requirements: 2.1, 2.3, 2.4_
- [x] 1.4 Prove it: merge the finished PR #7 branch into `fix/004-test-site-locale` (D-6); run
  `scripts/rebuild-test-site.sh`, which runs `bench fleet-test-site up --replace` and ends with
  "Rebuilt … with the Locale"; confirm MariaDB, Philip, Vikas, Amina, the vehicles and generators,
  and dd/mm/yyyy; re-run the server suite and compare it with the baseline; run
  `npm run test:ui`; the main site gets no test records; `bench fleet-test-site down` stays
  available but is run only when the owner asks
  - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4, 3.6_
- [x] 1.5 Re-confirm and delete the untracked root `fixtures/` (D-5); migrate still creates the
  Fleet roles. Not in this round: waits for the owner's go-ahead
  - _Requirements: 2.5, 3.5_

## Phase 2: Pull-request checks install and test the app (waits for the kit fix)

**Tracer:** PR #7, or the kit-update PR that follows it, shows the Server, UI, and Frappe Linter
checks green.

- [ ] 2.1 Kit 8f268ac (PR #8) replaces `scripts/spec-check.py`; the Frappe Linter check passes on
  PR #8, and so does the Server check
  - _Requirements: 2.6, 2.7, 3.7_
- [ ] 2.2 T3 (D-9): on PR #8's branch set `SAMPLE_DATA_SEED=fleet_management.sample_data.seed` and
  let `e2e/sid.ts` use `PC_SID_CMD` when set; locally `npm run test:ui` still passes on the test
  site; `[app_name]` appears nowhere
  - _Requirements: 1.6, 2.7_
- [ ] 2.3 Push on the owner's OK; CI shows Server, UI, and Frappe Linter passing on PR #8
  - _Requirements: 2.7, 3.6_

- [ ] 2.4 D-12: in `e2e/tests/session.spec.ts` skip the realtime check under `CI` and assert the
  login form, not its heading; locally `npm run test:ui` still passes 24
  - _Requirements: 2.7, 3.6_

## Progress log

- `28/09/2026`: Spec written. Next: approval, then 1.1.
- `29/09/2026`: PR #7's three failing checks added (bugfix 1.5, 1.6, 2.6, 2.7, 3.6, 3.7). Baseline
  taken in a worktree: both sites Kenya / Africa/Nairobi / KES / dd/mm/yyyy / `en`; server suite
  143 pass, 1 skipped, 0 fail; lint reproduced. The kit prompt for `spec-check.py` and the CI
  template was handed to the owner; the owner chose to wait for the kit (D-8, D-9). Next:
  approval, then 1.2 (T1).
- `29/09/2026`: Design approved (`804d5a2`). 1.1 done: blank `LOCALE_*` on develop and PR #7; PR #7's
  `require_locale` stops on `LOCALE_COUNTRY`; develop's migrate says "Locale matches"; root
  `fixtures/` untracked and identical; PR #7 CI Server and UI stop at `bench get-app [app_name]`,
  Linter fails ruff (4 locations), ruff format (22 files) and prettier. Before snapshot: both sites
  Kenya / Africa/Nairobi / KES / dd/mm/yyyy / `en` (English). The kit fix for Phase 2 is merged to
  the kit's develop, not yet released to its main. Next: 1.2 and 1.3.
- `29/09/2026`: 1.3 done on `chore/kit-update-6d6918d` (`f00e4f1`): Kenya Locale and
  `TEST_SITE_BUILD=bench fleet-test-site up --replace` recorded; migrate reports "Locale matches";
  a blank currency is named, a USD currency is reported as drift; main site unchanged. Next: 1.2, then 1.4.
- `29/09/2026`: 1.2 done on `chore/kit-update-6d6918d` (`2b9155f` layout, `9ec9b62` hand fixes): 22 files
  re-laid-out, 3 hand fixes; every hook passes except the kit's `scripts/spec-check.py` (unchanged,
  D-8); syntax trees equal apart from the hand fixes and one import reorder in `fuel_order.py`;
  Semgrep 27 findings before and after, none new. Next: 1.4.
- `29/09/2026`: 1.4 done on `fix/004-test-site-locale` after merging PR #7's branch (`09649e8`):
  `scripts/rebuild-test-site.sh` ran `bench fleet-test-site up --replace` with no root password and
  ended "Rebuilt … with the Locale"; MariaDB, Philip, Vikas, Amina, 11 vehicles, 2 generators, 55
  orders and 40 fuellings, dd/mm/yyyy; server suite 143 pass, 1 skipped, 0 fail (baseline equal);
  Playwright 24 passed; main-site record counts unchanged. `bench browse --user` opens the desktop
  browser on this host instead of printing `?sid=`; sessions were confirmed in `tabSessions`.
  Test site left up. Next: 1.5 on the owner's go-ahead; Phase 2 waits for the kit release.
- `29/09/2026`: 1.5 done on the owner's go-ahead: root `fixtures/` re-confirmed untracked and identical,
  deleted; main-site migrate still creates Fleet Admin, Fleet Approver, Fleet User. Phase 1 complete.
  Next: Phase 2, once the kit releases its develop (kit PR #12) to main and PR #7 is merged.
