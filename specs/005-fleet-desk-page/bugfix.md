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


# Fleet home page and a test site that copies the main site: bugfix

Approved by: pending

| | |
|---|---|
| Tier | `Small` |
| Branch | `fix/005-fleet-desk-page` |

## How to reproduce

1. Build the test site and sign in as Philip, a Fleet User in Nairobi.
2. Watch the home screen: it shows only the search bar, with no Fleet icon and nothing to click.
3. Sign in to the main site as its Fleet User: the home screen is just as empty.
4. Compare the Fleet rules (signal bands, validity, limits) on the two sites: the test site takes
   fixed sample values, not the main site's.
5. Leave one sample person out of the private login file and build the test site: the build
   finishes, and that person cannot sign in.

## Current behaviour

1. WHEN a person whose only roles are Fleet roles opens the home screen on the test site THEN the
   system shows an empty page with no Fleet icon.
2. WHEN the main site's Fleet User opens the home screen THEN the system shows the same empty page.
3. WHEN the test site is built THEN the system copies only the main site's country, time zone,
   language, and currency, and takes the Fleet rules from fixed sample values.
4. WHEN a sample person has no test login in the private login file THEN the system still
   finishes the build, and that person cannot sign in.

## Expected behaviour

1. WHEN a person with any Fleet role opens the home screen THEN THE system SHALL show a Fleet
   icon that opens a Fleet page listing fuel orders, fuellings, vehicles and generators, fuel
   stations, and locations.
2. WHEN a Fleet Admin opens the home screen THEN THE system SHALL also show a Fleet Setup icon
   that opens vehicle models, fuel types, fleet people, and the Fleet settings.
3. WHEN a Fleet User or a Fleet Approver opens the home screen THEN THE system SHALL NOT show the
   Fleet Setup icon.
4. WHEN the test site is built THEN THE system SHALL copy the main site's setup: country, time
   zone, language, currency, date format, and every Fleet rule the main site has set; a Fleet rule
   the main site leaves blank takes the sample value.
5. WHEN the test site is built and a sample person has no test login in the private login file
   THEN THE system SHALL stop before changing anything and name every such person.
6. WHEN the test site is ready THEN THE system SHALL have confirmed that every sample person
   signs in with the password recorded for them in the private login file.

## Unchanged behaviour

1. WHEN the test site is built THEN THE system SHALL CONTINUE TO load the same sample people,
   vehicles, generators, fuelling history, and logins, showing dates as dd/mm/yyyy.
2. WHEN a person opens a Fleet list or record THEN THE system SHALL CONTINUE TO show only the
   records of the locations they are allowed, as today.
3. WHEN the test site is built THEN THE system SHALL CONTINUE TO leave the main site unchanged and
   never copy the main site's people or logins to the test site.
4. WHEN a test login is recorded THEN THE system SHALL CONTINUE TO keep its password only in the
   private login file, never in a saved file, with the word "test" in the username and password.
5. WHEN a system administrator opens the home screen THEN THE system SHALL CONTINUE TO show the
   standard icons.
6. WHEN the server and browser tests run THEN THE system SHALL CONTINUE TO pass as before.

## Sample data

The existing sample data: Philip (Fleet User) and Vikas (Fleet Approver) in Nairobi, Amina
(Fleet Approver) in Mombasa, the Test Fleet Admin, the Krystalline Salt vehicles and standby
generators, and about two months of fuelling history. Nothing is added.

## Open questions

None. Answered 29/09/2026: the test site copies the main site's setup, not its people or
records (question 1); one Fleet page for every Fleet role, with the setup items for Fleet Admins
only (question 2).
