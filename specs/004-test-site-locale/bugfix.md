<!--
What is wrong, what should happen, and what must not change (Kiro's bugfix.md). It replaces
requirements.md for a bug. Written in step 1 of the Kaysalt workflow and approved before the
fix is designed. Audience: the requester, who may be non-technical, and an agent resuming
cold.

Business language only: no DocType, field, file, or function names, and no snake_case.
Criteria are numbered within their section and cited as N.k: current behaviour is 1.k,
expected behaviour 2.k, unchanged behaviour 3.k. Never renumber: retire a criterion by
replacing its text with "Removed: <reason>". Every criterion is cited by a task in tasks.md,
including a task that shows the bug exists. `scripts/spec-check.py` enforces all of this.

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->


# Test-site rebuild, regional settings, and pull-request checks: bugfix

Approved by: Brian Kipngetich (@BrianKipngetich1) · 29/09/2026 · revision 4bc7b27

| | |
|---|---|
| Tier | `Small` |
| Branch | `fix/004-test-site-locale` (this record); the fix itself on `chore/kit-update-6d6918d` (PR #7) |

## How to reproduce

1. Ask the agent to publish a change, so that it starts the checks it runs before every pull
   request.
2. Its first check rebuilds the test site. Watch it stop at once and ask for the country,
   because the app's settings record no regional settings.
3. Migrate the main site. It reports that the regional settings match, although none are
   recorded to compare against.
4. Look at the top of the repository. A folder holds a copy of the list of Fleet roles that is
   not saved in the repository and that nothing reads.
5. Open the kit-update pull request and look at its checks. The formatting check, the server
   check, and the browser check all fail, and the main line of development fails them the same
   way.

## Current behaviour

1. WHEN a test-site rebuild is started before a pull request THEN the system stops at once
   because no country, time zone, currency, date format, or language is recorded.
2. WHEN that rebuild is given regional settings THEN the system looks for the sample data in a
   place this app does not use, asks for the database administrator's password, and builds a
   test site with no sample people, vehicles, generators, or logins.
3. WHEN the main site is migrated THEN the system reports that the regional settings match,
   although none are recorded, so a wrong setting would never be flagged.
4. WHEN the repository is opened THEN the system shows a stray, unsaved copy of the Fleet
   role list at the top level, which the app never reads.
5. WHEN a pull request is checked THEN the system rejects the layout of the app's own code files
   and of the kit's specification checker, and reports five lint errors.
6. WHEN a pull request is checked THEN the system stops the server and browser checks before
   the app is installed, because the check setup still holds the kit's unfilled app-name
   placeholder.

## Expected behaviour

1. WHEN the app's settings are read THEN THE system SHALL find the Kenya regional settings
   recorded: country Kenya, time zone Africa/Nairobi, currency KES, date format dd/mm/yyyy, and
   language English, matching the main site.
2. WHEN a test-site rebuild is started before a pull request THEN THE system SHALL build the
   test site the way this app always builds it, with the usual sample data: Philip, Vikas and
   Amina with their logins, and the Nairobi and Mombasa vehicles, generators, and fuelling
   history.
3. WHEN the main site is migrated THEN THE system SHALL compare its country, time zone,
   currency, and date format with the recorded ones and report every difference.
4. IF any regional setting is left blank THEN THE system SHALL stop and name the blank
   setting instead of reporting a match.
5. WHEN the repository is opened THEN THE system SHALL hold the Fleet role list only in the
   app's own list of records it installs.
6. WHEN a pull request is checked THEN THE system SHALL find every one of the app's own code
   files in the agreed layout and free of lint errors.
7. WHEN a kit update delivers the corrected specification checker and check setup THEN THE
   system SHALL pass the formatting check, install the app, and run the server and browser checks
   on a test site built with the Kenya regional settings and the usual sample data.

## Unchanged behaviour

1. WHEN a person builds the test site with the app's own build command THEN THE system SHALL
   CONTINUE TO build it as today, setting the test logins' passwords and needing no database
   administrator's password.
2. WHEN a person starts the one-step test run THEN THE system SHALL CONTINUE TO build the test
   site, run the backend and browser tests, and tear the site down as today.
3. WHEN any test or rebuild runs THEN THE system SHALL CONTINUE TO leave the main site free of
   test records.
4. WHEN the test site is built THEN THE system SHALL CONTINUE TO load the same sample people,
   vehicles, generators, fuelling history, and logins, showing dates as dd/mm/yyyy.
5. WHEN the app is installed or migrated THEN THE system SHALL CONTINUE TO create the Fleet
   Admin, Fleet Approver, and Fleet User roles.
6. WHEN the re-laid-out code runs THEN THE system SHALL CONTINUE TO behave as before: every
   server test that passed before the change still passes, and the same browser tests pass.
7. WHEN the app's own files are corrected THEN THE system SHALL CONTINUE TO hold the kit's own
   scripts exactly as the kit shipped them.

## Sample data

The existing sample data: Philip (Fleet User) and Vikas (Fleet Approver) in Nairobi, Amina
(Fleet Approver) in Mombasa, the Krystalline Salt vehicles and standby generators, and about
two months of fuelling history. Nothing is added.

## Open questions

None.
