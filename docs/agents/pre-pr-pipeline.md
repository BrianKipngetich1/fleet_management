# Pre-PR pipeline

Read when the requester asks to publish ("push", "open a PR", "send it for review", "I'm
done"). This is step 4 of the Kaysalt workflow; nothing here runs after an ordinary task.

1. **At the same time:**
   - **A. Test site:** `scripts/rebuild-test-site.sh`. It runs the app's own build when
     `TEST_SITE_BUILD` is set; otherwise the kit build seeds `SAMPLE_DATA_SEED` (default
     `[app_name].tests.sample_data.seed`). Only when neither finds sample data, ask the requester
     for it first (who uses the app and one sample name per role), store it in that module and
     in `e2e/fixtures.ts`, then rebuild.
   - **B. Documentation:** overwrite the spec's `PROGRESS.md` row, run `graphify update .`, and
     for a feature finish the phase's verification record.
2. **After A, at the same time:**
   - **C. Full suites:** `bench --site [test site] run-tests --app [app_name]` and
     `npm run test:ui`. If `run-tests` prints "Testing is disabled for the site!", no test ran:
     report the suite as failed and rebuild the test site.
   - **D. Walkthrough:** on the test site only, sign in with `scripts/ab-login.sh [email]` as
     each role the change affects (see `ui-verification.md`). Save screenshots to
     `specs/[NNN-name]/verification/screenshots/[task]/` and the set for this PR to
     `specs/[NNN-name]/verification/pr-screenshots/`, replacing the previous set. Both folders
     are gitignored.
3. **The main agent** writes the PR body from `.github/pull_request_template.md` and runs
   the Kaysalt Frappe plugin's `scripts/open-or-update-pr.sh`, which pushes the branch and
   attaches every file in `pr-screenshots/` (gh 2.99.0 or later). Without the plugin, push and
   run `gh pr create --base develop --attach <file>...` yourself. Then it tells the
   requester: "The PR is open. A reviewer checks it, may suggest changes, and merges it.
   Nothing takes effect until it is merged."

Sub-agent models are set in the Kaysalt workflow. Report which checks passed, failed, or were
skipped; a failure stops the PR until it is fixed or the requester accepts it in writing.
