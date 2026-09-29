# UI verification

Read before a Desk walkthrough or a Playwright run: both are part of the pre-PR gate
(`pre-pr-pipeline.md`), not of every task.

Two tools, two jobs, not interchangeable.

**`agent-browser` — per phase.** After implementation and before pushing, walk the new
behaviour through Desk as the intended role and capture screenshots. This satisfies the phase's
browser-workflow requirement. Run `agent-browser skills get core` once per context. Screenshots
go to `specs/[NNN-name]/verification/screenshots/phase-NN-SS-short-slug.png` — gitignored,
listed by exact path in the PR for the human to attach; see the naming convention documented in
`specs/000-example-spec/verification/screenshots/`.

**Playwright — repository root, generic.** `e2e/` guards root functionality: login and session,
tenancy scoping, list and form rendering, create/submit/cancel, permission allow and deny. It
is never per phase and must never encode one phase's acceptance criterion — its only job is
proving a finished phase broke nothing. `e2e/fixtures.ts` is the only file that carries project
facts. Its base address defaults to `TEST_SITE_URL` in `.kaysalt/project.conf`; `BASE_URL`
overrides it. The kit ships `package-lock.json`, which pins the Playwright version. Run `npm ci`
from the app root before `npm run test:ui` to install it; run the suite before every push.

**Pre-PR gate** (run only when the requester asks to publish, or on request; never after every
edit): rebuild the test site → `agent-browser` walkthrough → local Playwright plus `bench --site
[test site] run-tests --app [app_name]` → push → PR, where CI reruns both. `pre-pr-pipeline.md`
runs these in parallel.

**Functional testing runs only on the test site.** Never write test records to the main
site: a Desk walkthrough cannot be rolled back the way a document-API run can, so it leaves
residue. Both tools authenticate without a password — `bench browse [site] --user [email]`
mints a session id printed as `?sid=`. The shipped `e2e/sid.ts` reads `TEST_SITE` from
`.kaysalt/project.conf` unless `PC_SID_CMD` is set. For a walkthrough run
`scripts/ab-login.sh [email]`: it reuses `e2e/sid.ts`, sets the `sid` cookie in agent-browser,
and prints no secret. Never rebuild that lookup inline. Never type credentials into a login
form. This is a user-impersonation primitive that only works because `developer_mode`
is on — acceptable on a disposable test site, a privilege-escalation surface anywhere else.
