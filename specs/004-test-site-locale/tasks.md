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

- [ ] 1.1 Show the bug on `develop` and PR #7: blank `LOCALE_*`; PR #7's `require_locale` stops on
  `LOCALE_COUNTRY`; develop's `scripts/migrate.sh` says "Locale matches"; the stray root
  `fixtures/` is untracked; `pre-commit run --all-files` rewrites 23 files and reports the 5 lint
  errors; the Server and UI jobs stop at `bench get-app [app_name]`. Record the "before" snapshot
  (both sites' Locale, the test site's config flags, `list-apps`) and the server-suite baseline
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
- [ ] 1.2 T1: apply ruff 0.14.10 and prettier 2.7.1 to the app's own files, leaving
  `scripts/spec-check.py` byte-identical (D-8); hand-fix `fleet_asset.py` (`itertools.pairwise`),
  `test_fuel_order.py` (`# noqa: RUF001`) and `tests/test_sample_data.py` (`ClassVar[dict]`) (D-7).
  Check: every hook except the one on `spec-check.py` passes; `ruff format --check` and
  `ruff check` pass on everything else; the syntax tree of every reformatted file is unchanged
  and differs only at the 3 hand fixes; `python -m compileall` passes; Semgrep reports no finding
  new against `develop` (D-11); the snapshot equals "before"
  - _Requirements: 2.6, 3.6, 3.7_
- [ ] 1.3 T2: fill `LOCALE_*` from the main site (D-1) and set
  `TEST_SITE_BUILD=bench fleet-test-site up --replace` (D-2); `scripts/migrate.sh` reports "Locale
  matches" for the main site; the snapshot equals "before"
  - _Requirements: 2.1, 2.3, 2.4_
- [ ] 1.4 Prove it: merge the finished PR #7 branch into `fix/004-test-site-locale` (D-6); run
  `scripts/rebuild-test-site.sh`, which runs `bench fleet-test-site up --replace` and ends with
  "Rebuilt … with the Locale"; confirm MariaDB, Philip, Vikas, Amina, the vehicles and generators,
  and dd/mm/yyyy; re-run the server suite and compare it with the baseline; run
  `npm run test:ui`; the main site gets no test records; `bench fleet-test-site down` stays
  available but is run only when the owner asks
  - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4, 3.6_
- [ ] 1.5 Re-confirm and delete the untracked root `fixtures/` (D-5); migrate still creates the
  Fleet roles. Not in this round: waits for the owner's go-ahead
  - _Requirements: 2.5, 3.5_

## Phase 2: Pull-request checks install and test the app (waits for the kit fix)

**Tracer:** PR #7, or the kit-update PR that follows it, shows the Server, UI, and Frappe Linter
checks green.

- [ ] 2.1 Blocked on the kit PR (D-8): the next kit update replaces `scripts/spec-check.py` with a
  version clean under the Frappe boilerplate ruff config; `pre-commit run --all-files` then passes
  - _Requirements: 2.6, 2.7, 3.7_
- [ ] 2.2 T3, blocked on the kit PR (D-9): once the kit's `ci.yml` template needs no hand-filled
  placeholders, write `plans/ci-fix.patch` for the owner with only what this app still needs (at
  least `BENCH_ROOT` and `PC_BENCH_PATH` for `e2e/sid.ts`); `[app_name]` appears nowhere and the
  YAML parses
  - _Requirements: 1.6, 2.7_
- [ ] 2.3 The owner applies the patch; CI shows Server, UI, and Frappe Linter passing on the PR
  - _Requirements: 2.7, 3.6_

## Progress log

- `28/09/2026`: Spec written. Next: approval, then 1.1.
- `29/09/2026`: PR #7's three failing checks added (bugfix 1.5, 1.6, 2.6, 2.7, 3.6, 3.7). Baseline
  taken in a worktree: both sites Kenya / Africa/Nairobi / KES / dd/mm/yyyy / `en`; server suite
  143 pass, 1 skipped, 0 fail; lint reproduced. The kit prompt for `spec-check.py` and the CI
  template was handed to the owner; the owner chose to wait for the kit (D-8, D-9). Next:
  approval, then 1.2 (T1).
