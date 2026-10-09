<!--
The build order (Kiro's tasks.md). Written after design approval and updated as work
happens; the progress log is where a resumed session picks up.

Each phase is a tracer bullet: a thin vertical slice with an observable outcome, never
schema-only, backend-only, or UI-only. Every task carries a `_Requirements: N.k_` line naming
the acceptance criteria it serves (a property test also names its property), and every
criterion is cited by at least one task. Tick a task's checkbox when it is committed.
-->


# Fleet home page, one login file, and a test site that copies the main site: tasks

## Phase 1: One login file, and a sign-in helper that works on this computer

**Tracer:** the test site rebuilds from the one login file, and an agent signs in as Philip on the
test site without the owner's browser opening.

- [x] 1.1 Show the bug: the login file is in the 001 records with five table shapes; the kit's
  rebuild prints "No CREDENTIALS.md"; `scripts/ab-login.sh` stops with `ERR_MODULE_NOT_FOUND`
  - _Requirements: 1.5, 1.6_
- [x] 1.2 Write the root `CREDENTIALS.md` in the D-6 shape at mode 0600; a script compares every
  moved value with the old file, printing names only
  - _Requirements: 2.7, 3.4, 3.7_
- [x] 1.3 `commands.py` reads the root file (D-7); Test Property 4
  - _Requirements: 2.7, 2.8_
- [x] 1.4 Point every reference at the root file and rewrite `CLAUDE.md`'s credential rule (D-8)
  - _Requirements: 2.9_
- [x] 1.5 Add `bench fleet-test-site session` and use it in `e2e/sid.ts`, with the `.ts` import
  (D-9); Test Property 5; write the kit-owner prompt for `ab-login.sh` (D-10)
  - _Requirements: 2.10, 3.6_
- [x] 1.6 Prove it: rebuild the test site (app build and kit step both find the file); with the
  owner's permission, sign in as Philip for a walkthrough and see no desktop browser open; server
  suite and `npm run test:ui` pass; then delete the old file and confirm no file names it
  - _Requirements: 2.8, 2.9, 2.10, 3.1, 3.3, 3.6, 3.7_

## Phase 2: Every Fleet role gets a Fleet home page

**Tracer:** Philip opens the home screen and finds a Fleet icon leading to his fuel orders.

- [x] 2.1 Show the bug: on the test site Philip's home screen has no icon (screenshot); neither site
  has a Fleet `Desktop Icon`; the main site's Fleet User has only standard icons
  - _Requirements: 1.1, 1.2_
- [x] 2.2 Add the "Fleet" and "Fleet Setup" desktop icons, sidebars, and workspace (D-1, D-2);
  migrate the main site
  - _Requirements: 2.1, 2.2, 2.3, 3.5_
- [x] 2.3 Test Property 1: Fleet icon visible to all three Fleet roles, Fleet Setup to Fleet Admin
  only (IntegrationTestCase)
  - _Requirements: 2.1, 2.2, 2.3_
- [x] 2.4 Walk it through on the test site as Philip, Vikas, Amina, and the Test Fleet Admin, and
  as Administrator; Philip's lists still show only Nairobi
  - _Requirements: 2.1, 2.2, 2.3, 3.2, 3.5_

## Phase 3: The test site copies the main site's setup and checks every login

**Tracer:** a rebuild takes the main site's Fleet rules and refuses to finish with a login missing.

- [x] 3.1 Show the bug: the test site's Fleet rules differ from the main site's set values; a sample
  person left out of a copy of the login file only loses their login
  - _Requirements: 1.3, 1.4_
- [x] 3.2 Copy the main site's date format and non-blank Fleet rules after seeding (D-3); Test
  Property 2
  - _Requirements: 2.4, 3.1_
- [x] 3.3 Stop on a missing login before changing anything, and check every login signs in (D-4);
  Test Property 3
  - _Requirements: 2.5, 2.6, 3.4_
- [x] 3.4 Prove it: rebuild the test site; Philip, Vikas, Amina, and the Test Fleet Admin sign in;
  settings match the main site; server suite and `npm run test:ui` pass; main site unchanged
  - _Requirements: 2.4, 2.6, 3.1, 3.3, 3.6_

## Progress log

- `29/09/2026`: Spec written from the owner's answers to questions 1 and 2. Next: approval, then 1.1.
- `29/09/2026`: Owner added the move to the kit's one login file, kept simple, and the walkthrough
  sign-in fix deferred from spec 004; both became Phase 1. Next: approval, then 1.1.
- `29/09/2026`: Owner approved the design (revision `6d8acf1`) and permitted walkthrough sign-ins
  as Philip, Vikas, Amina, the Test Fleet Admin, and Administrator on the test site only. Next: 1.1.
- `29/09/2026`: 1.1 done: the logins sit in the 001 records (mode 600) under four headed tables
  of different shapes (main site; test site; framework fixtures; MariaDB), and there is no root
  `CREDENTIALS.md`, so the kit's rebuild takes its "No CREDENTIALS.md" branch; `kit-check.py`
  raises `credentials-location`; importing `e2e/sid.ts` under Node stops with
  `ERR_MODULE_NOT_FOUND` for `e2e/target`. The desktop-browser half of 1.6 is shown by Frappe
  16.22's `browse` calling `click.launch`, not reproduced, to keep the owner's browser untouched.
  Next: 1.2 (orchestrator) with 1.3 and 1.4 alongside.
- `29/09/2026`: 1.2 done: root `CREDENTIALS.md` written at mode 600 (gitignored) in the D-6 shape —
  4 main-site and 6 test-site logins, 2 database rows; a script compared all 12 values with the
  old file (no mismatch, nothing extra) and every test login keeps "test" in username and
  password. Framework fixture accounts not carried over (D-6). Next: 1.3.
- `29/09/2026`: 1.3 done: `bench fleet-test-site up` reads the root `CREDENTIALS.md`, telling its
  two tables apart by header; Property 4 tests pass (12 unit, 2 integration in
  `test_sample_data`), and the real file yields the 5 test logins, the Administrator and the
  database password. Next: 1.4.
- `29/09/2026`: 1.4 done: `CLAUDE.md`'s credential rule follows the kit's one-file rule; PROGRESS,
  the 002 spec, every 001 and 002 phase record's credential row, and the sample-data note name the
  root file; `specs/TEMPLATE-verification.md` is the kit's copy; the old `.gitignore` line is gone
  (the root `CREDENTIALS.md` line still covers every copy). Only 004's closed records and this
  spec still name the old place, as history. Next: 1.5.
- `29/09/2026`: 1.5 done: `bench --site <test site> fleet-test-site session <email>` saves a session
  with `login_as`, commits, and prints the saved `?sid=`; it refuses other sites and sites without
  developer_mode before any login (Property 5, 2 tests pass). `e2e/sid.ts` uses it and loads under
  plain Node; the `PC_SID_CMD` path CI uses is unchanged. Kit-owner prompt for `ab-login.sh`
  handed to the owner (D-10). Next: 1.6.
- `29/09/2026`: 1.6 done: the kit's `scripts/rebuild-test-site.sh` ran the app's build and restored
  the test passwords from the root file (no "No CREDENTIALS.md"); site on MariaDB. As Philip, signed
  in through `e2e/sid.ts` with no password and no desktop browser (owner-desktop Chrome count 3
  before and after); screenshot `verification/screenshots/phase-01-login-file/phase-01-01-philip-signed-in.png`.
  Server suite 56 + 95 pass (1 skipped); `npm run test:ui` 24 pass. The old 001 login file is
  deleted; only the root file remains in the app. Still naming the old place, as history: 004's
  closed design and this design's Current state (left unedited to keep their approvals). Phase 1
  complete. Next: 2.1.
- `29/09/2026`: 2.1 done: the test site, built from the code before this fix, has no Desktop Icon
  from the app (0 on both sites; the same 11 Frappe icons on each). As Philip, `/desk` shows only
  the search bar, bell, and avatar
  (`verification/screenshots/phase-02-fleet-home/phase-02-01-philip-empty-home.png`). On the
  main site, Frappe 16's `get_desktop_icons` hides all 11 icons from the Fleet User: each
  sidebar icon has no item the user may open, and Framework fails the app check. Only Printing
  (System Manager) and Data (Accounts User) carry roles.
- `29/09/2026`: 3.1 done: the main site sets six Fleet rules (tolerance 2, validity 3, orange 10,
  red 20, entry SLA 48, print instruction), not seven as the design's Current state says
  (holiday list is blank on both). It leaves gauge limit, litres excess, mileage margin, and
  minimum hours blank; the test site holds the sample 75, 10, 15, 24 there. Date format is
  dd/mm/yyyy on both. A made-up login file in the owner's two-heading layout, with Amina left
  out, was read without complaint, and `up` (at `2e15565`) never compared it with the sample
  people, so Amina would only have lost her login. A copy of the real file was not made (the
  safety check refused it); the made-up file shows the same path. Next: 3.2, 3.3.
- `29/09/2026`: 3.2 and 3.3 done (`2cd9a20`): the build copies the main site's date format and
  every set Fleet rule over the sample values (read raw, so a blank stays blank and "0" counts
  as set); it stops before changing anything, naming every sample person with no test login,
  and after seeding checks every login signs in. Property 2 and 3 tests, a login-check test,
  and a Property 4 case for the owner's two-heading login file pass (20 unit, 3 integration).
  Next: 2.2 and 2.3.
- `29/09/2026`: 2.2 and 2.3 done (`5b1cabb`): the Fleet and Fleet Setup desktop icons, sidebars,
  and workspaces ship as standard records; the main site migrated and holds them, Locale
  unchanged. **Drift from D-1:** Frappe 16.22's `get_desktop_icons` ignores `Desktop Icon.roles`
  and shows an icon when its sidebar keeps an item the user may open; all three Fleet roles read
  the setup DocTypes, so the setup links moved onto a "Fleet Setup" workspace (roles: Fleet Admin),
  and the Fleet Setup sidebar holds only that workspace and Fleet Management Settings. The icon
  roles stay as intent. Property 1 tests pass (5, through `get_bootinfo().desktop_icons`).
- `29/09/2026`: 2.4 done: on the rebuilt test site, as Philip, Vikas, and Amina the home screen
  shows Fleet and no Fleet Setup; Philip's Fleet page lists the five Fleet lists, his Fuel Orders
  are 52, all Nairobi, and `/desk/fleet-setup` says "Not permitted"; Amina's 3 are all Mombasa;
  the Test Fleet Admin sees both icons and the setup page's four links; Administrator keeps
  Framework (the standard icons) beside the two Fleet icons. Screenshots
  `verification/screenshots/phase-02-fleet-home/phase-02-02` to `-13`. Known limitation: both
  icons show the letter "F", not their truck and settings symbols. Phase 2 complete.
- `29/09/2026`: 3.4 done: `bench fleet-test-site up --replace` rebuilt the site on MariaDB and
  passed its own login check; its Fleet rules equal the main site's six set values, with the
  sample 75, 10, 15, 24 where the main site is blank; date format dd/mm/yyyy. Given a made-up
  login file without Amina, `up` stopped with "The login file has no test login for:
  amina.test@example.com." and left the test site untouched. Philip, Vikas, Amina, the Test Fleet
  Admin, and Administrator all signed in. Server suite 64 unit + 101 integration pass (1
  skipped); `npm run test:ui` 24 pass; the main site's rules and 6 users unchanged. Phase 3
  complete. Next: the owner's review, then the pull request when asked.
