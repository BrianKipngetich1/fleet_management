<!--
Canonical agent-instruction file for this Frappe repository. Keep feature-specific requirements
in specs/. `AGENTS.md` is a one-line pointer to this file — Codex and other compatible agents
follow it here; edit only this.
-->

# Project

- Repository: `BrianKipngetich1/fleet_management` · App/module: `fleet_management` / `Fleet Management`
- Working directory: `/home/kayadmin/frappe-bench/apps/fleet_management`
- Bench root: `/home/kayadmin/frappe-bench`
- Main site: `fleet_management.localhost` (`http://fleet_management.localhost:8000`) · Test site:
  `fleet_management-test.localhost` (`http://fleet_management-test.localhost:8000`). The main site is
  the working, non-production site; there is no production deployment yet. Neither relates to the
  `main` git branch.
- Required database backend: MariaDB for both sites. SQLite evidence and backups created before the
  2026-09-24 cutover remain historical only; do not create or run new SQLite acceptance evidence.
- UI surface: Frappe Desk
- Base branch: `main` · Integration/default branch: `develop`
- Codeowner who presses merge: `@BrianKipngetich1` (provisional; see `.github/CODEOWNERS`)

# Start a context

Read `PROGRESS.md` — it is a one-line-per-specification index. Open the active specification
and the phase record it names. That is the whole ritual.

If project state, observed behaviour, or an open review finding contradicts the specification,
stop and reconcile the documents before writing code.

# How work is documented

Two documents per specification, and no others. Both are written by the agent; they differ in
audience, language, and what they are allowed to contain.

| | `specs/<NNN-name>/spec.md` | `specs/<NNN-name>/verification/phase-NN-<name>.md` |
|---|---|---|
| Is | The design — what we understood and intend to build | The proof — what was actually observed |
| Written | Before implementation | As each phase is verified |
| For | A human deciding if this is right; an agent resuming cold | A reviewer who did not write the code, human or agent |
| Cap | ~400 lines for its whole life | ~200 lines |

Templates: `specs/TEMPLATE-spec.md`, `specs/TEMPLATE-verification.md`. The HTML comment at the
top of each is binding. There is no `PROGRESS` entry per phase, no review ledger, no completion
certificate, and no verification folder beyond the phase records themselves.

**Language.** Everything above "Current state" (spec) or "The rule, as observed" (verification)
is business-functional: name an actor, an action, an outcome. No file paths, no function names,
no field names in those sections. Below that line, name concrete surfaces freely.

**Verification is a procedure, never a transcript.** Never "I ran X and got Y" — always "put
the system in state X, expect Y". The test for every line: *could a reviewer who did not write
this code run it and get a yes or no?* If not, cut it. A check a machine can assert belongs in
a test file. Evidence that a run happened lives in CI and git and is linked, never pasted — a
CI run proves it on an exact commit; pasted output goes stale silently.

**The two diagrams.** `spec.md` draws the design. Each phase record redraws it from its own
verification table — an edge appears only if a numbered row observed it, which makes the
diagram double as a coverage map. The record then tallies every spec edge against its own in
"Design vs. observed". A difference is a finding: **Unbuilt or untested** (designed, never
observed — blocking), **Undesigned behaviour** (observed, never designed — reconcile or
remove), **Drift** (built differently — somebody made an undocumented call; record it), or
**Not in scope** (another phase delivers it). Never harmonise the two diagrams silently. Use
one transition per line and stable node names so they diff cleanly.

# Review closure

A review is scoped to **one phase** and never widens. Two rounds maximum: round 1 raises
findings, round 2 checks only those findings and nothing new. **Zero blocking findings closes
the cycle**, however many non-blocking remain — that is the diminishing-returns line. A
non-blocking finding never reopens a review; it becomes a **Known limitation** in the phase
record or a new specification. If round 2 still returns blocking findings the phase was scoped
too wide: split it, do not re-review it. A third round is an escalation, not a review.

Request review in a fresh context, preferably on a different model or from a qualified person.
Record the verdict as one row in the phase record's review table.

# Working rules

1. One phase per context. Start fresh when the objective changes.
2. Planning and implementation are separate. Inspect read-only, record decisions in the spec, get
   approval before editing implementation files.
3. **Frappe-first.** Check in order: a built-in Frappe engine or standard field; an
   already-installed app; a comparable Frappe/ERPNext implementation. Write custom code only when
   those fall short, and record why in the spec's Frappe-first table.
4. Inspect the closest existing local DocType, endpoint, form, page, component, or test before
   introducing a new pattern.
5. Every phase is a thin vertical slice with an observable outcome. Never schema-only,
   backend-only, or UI-only.
6. Build a fresh test site (`bench fleet-test-site up --replace`) after any schema or fixture
   change, before verifying — it installs from the current code, so no migrate is needed — and
   confirm the site reports MariaDB before treating backend evidence as valid.
7. Write proportional tests. `IntegrationTestCase` for database, document, permission, or hook
   behaviour on the test site; `UnitTestCase` only for logic needing no site context.
8. Keep unrelated cleanup out of the active specification.
9. Get explicit authorization before merging, pushing to a protected branch, deploying, changing
   repository or infrastructure settings, or touching secrets.

# Credential handling

- Every login created for a phase on the main site is recorded locally in that phase's
  `specs/<NNN-name>/verification/CREDENTIALS.md`, including username, role, site, and password.
- `CREDENTIALS.md` is gitignored, must be mode `0600`, and must never be committed, attached to a
  pull request, pasted into a verification record, or copied into logs. The tracked phase record
  names only this approved secret location, never a credential value.
- The test site mirrors each phase login and role. Both the test username and test password must
  contain the literal word `test`; test passwords must never reuse a main-site password.
- The test site is rebuilt often, so its logins are recreated each time with the same credentials:
  `bench fleet-test-site up` reads every test-site password (and the test-site Administrator and
  database passwords) from `specs/001-fleet-fuel-management/verification/CREDENTIALS.md`. A test
  login is added by adding it to the sample data and recording its password there.
- Create or update the main-site and test-site entries together so the local inventory remains the
  source of truth for manual login testing. Passwordless `bench browse --user` remains preferred
  for automated test-site browser checks so credentials do not enter automation output.

# UI verification

Two tools, two jobs, not interchangeable.

**`agent-browser` — per phase.** After implementation and before pushing, walk the new
behaviour through Desk as the intended role and capture screenshots. This satisfies the phase's
browser-workflow requirement. Run `agent-browser skills get core` once per context. Each phase's
screenshots go in their own folder named after the phase record,
`specs/<NNN-name>/verification/screenshots/phase-NN-<slug>/phase-NN-SS-short-slug.png` — gitignored,
listed by exact path in the PR for the human to attach; see the naming convention documented in
`specs/000-example-spec/verification/screenshots/`. On this Ubuntu host the bundled Chrome
needs `AGENT_BROWSER_ARGS=--no-sandbox` (AppArmor blocks its user-namespace sandbox; Playwright
disables the sandbox by default for the same reason).

**Playwright — repository root, generic.** `e2e/` guards root functionality: login and session,
tenancy scoping, list and form rendering, create/submit/cancel, permission allow and deny. It
is never per phase and must never encode one phase's acceptance criterion — its only job is
proving a finished phase broke nothing. `e2e/fixtures.ts` is the only file that carries project
facts, and every fact in it names a sample-data record: Philip, Vikas, and Amina as the suite's
users, and the pool vehicle KDH 201A for its generic orders. The suite never creates users,
permissions, or master data; its setup step only checks the sample data is present and stops with
the rebuild command when it is not. `npm run test:ui` before every push.

Sequence: implement → `bench fleet-test-site up --replace` → `agent-browser` walkthrough → local
Playwright plus `bench --site fleet_management-test.localhost run-tests --app fleet_management` →
`bench fleet-test-site down` → push → PR, where the same checks are rerun before merge.
`npm run test:all` (`scripts/test-cycle.sh`) runs the automated part — build, backend tests,
Playwright, teardown — in one step; `--keep` leaves the site up for a walkthrough.
Backend tests build their own records inside `IntegrationTestCase` and never rely on the sample
data, so they also pass on the empty site CI builds.

**Functional testing runs only on the test site.** Never write test records to the main
site: a Desk walkthrough cannot be rolled back the way a document-API run can, so it leaves
residue. `fleet_management-test.localhost` is the one home for every kind of test data — seeded
and throwaway records, QA user creation and deletion, unauthorised-access probes.

**The test site is disposable.** It exists only while testing is under way: build it with `bench
fleet-test-site up` whenever a walkthrough, Playwright run, or backend test run is needed, and throw
it away with `bench fleet-test-site down` when that testing is done. Each build installs the
current code into an empty database, copies the main site's regional settings, completes the
setup wizard, and loads the fixed sample data in `fleet_management/sample_data.py` — Philip
(Fleet User) and Vikas (Fleet Approver) in Nairobi, Amina (Fleet Approver) in Mombasa, the
Krystalline Salt locations, real vehicle models and standby generators, and about two months of
fuelling history. Describe checks and walkthroughs in those terms ("as Philip, open KDA 412M").
Nothing on the site is a record: evidence lives in CI, git, and the phase records. The build needs
no MariaDB root access — the site's own database user rebuilds its one database. Following Frappe's own UI
test convention, both tools reach it through the bench's standard web server (the `frappe-web`
user service, equivalent to `bench start`) at
`http://fleet_management-test.localhost:8000`; the site is selected by host name, and Playwright
reuses that server rather than starting its own. Both tools authenticate without a password — `bench
--site fleet_management-test.localhost browse --user <test-user-email>` persists a session; read
its id back from `tabSessions` (as `e2e/sid.ts` does — the printed `?sid=` is not reliably the
persisted one) and set it as the `sid` cookie without echoing it. Never type credentials into
a login form. This is a user-impersonation primitive that only works because `developer_mode`
is on — acceptable on the dedicated, non-production test site, a privilege-escalation surface anywhere else.

## Provisioning a site for UI tests

A site that never completed the setup wizard fails misleadingly: Desk re-routes everything to
the wizard, so every DocType route resolves as a Page and returns `403 Not permitted` — for
every user and DocType — while roles and `can_read` in the boot payload look perfectly correct.
`bench fleet-test-site up` does both steps below for the test site; they matter for any other new
site. Run `bench --site <new-site> execute frappe.utils.install.complete_setup_wizard` on any new site
first. It also needs `bench --site <new-site> set-config developer_mode 1`, without which `bench
browse --user` refuses to mint a session for a non-Administrator — and it prints the refusal
while exiting `0`, so check the output for `?sid=`, never the exit code.

## Dates

**Every site, everywhere, uses Frappe's `dd/mm/yyyy` date format** (System Settings → Date
Format). The app sets it on install, after the setup wizard (which would otherwise apply the
country's format, `mm-dd-yyyy` for the US helper above), and after every migrate. After
provisioning or migrating any site, confirm System Settings shows `dd/mm/yyyy` before testing.
Every check assumes it: backend tests assert it, Playwright asserts it at boot
(`DATE_FORMAT` in `e2e/fixtures.ts`), and walkthroughs read and type dates as `dd/mm/yyyy`.
Never type a hard-coded ISO date into a Desk date field; convert through
`frappe.datetime.str_to_user` (`userDate()` in `e2e/desk.ts`).

## Desk quirks that cost time when forgotten

- A currency or data field needs a `Tab` blur before Frappe commits the typed value. Reading
  `cur_frm.doc` straight back after typing returns the stale value.
- A link field needs its autocomplete option **clicked**. Typing the exact value and blurring
  leaves the model field undefined even though the input shows the text.
- Frappe renders autocomplete entries as `div[role="option"]`, never `li`. Scanning for `li`
  finds nothing and reads as "no options returned".
- `Cancel` on a submitted document is a `.page-actions` button, not a menu dropdown item.
- A date/datetime field must be **typed** after its date picker opens. An instant `fill`, or
  keys sent before the picker appears, lose the value or replace the typed time with now.
- An approved Fuel Order can show two "Actions" buttons: Frappe's workflow actions and the
  app's own group. Target the app's with `.inner-group-button[data-label="Actions"]`.

# Frappe conventions

- DocType JSON is the schema source. Never hand-alter framework-managed columns or tables.
- Server-side code is authoritative for price, totals, ownership, and state transitions. Treat
  client-supplied values as untrusted.
- Role permissions must cover every required operation. Where row-level access applies, verify
  both list-query filtering and direct-document access.
- A Server Script stays inside `safe_exec`; logic needing unrestricted imports belongs in the
  app.
- Child DocTypes use `istable: 1` and inherit access through the parent. `owner`, `creation`,
  `modified`, and `docstatus` remain framework-owned.
- Never commit credentials, tokens, passwords, cookies, or private keys. The only local plaintext
  exception is the gitignored, mode-`0600` phase `verification/CREDENTIALS.md` defined above; all
  tracked documents name the approved secret source only.

# Commits and pull requests

Every commit title follows Conventional Commits: `type(scope): subject`, imperative, no
trailing period. `scope` optional; `!` before the colon marks a breaking change. Allowed types:
`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`.
Never use the word "phase" in a commit message.

Nothing is pushed to `main` directly; work is staged and physically verified on `develop`, then
reaches `main` through a pull request.
A pull request is opened at each point a human decision is required, not per file touched:

| Branch | Carries | Merges into | The approval it seeks |
|---|---|---|---|
| `spec/<NNN-name>` | `spec.md`, scaffolded phase records, the `PROGRESS.md` pointer | `develop` | Specification approved, implementation may begin |
| `feature\|fix\|chore/<NNN>-phase-<N>` | Implementation, that phase's verification record with its review table filled in, the `PROGRESS.md` update | `develop` | The phase is signed off |
| `release/<version>` or `develop` itself | Accumulated, reviewed, physically verified work | `main` | The release is cut |

Every pull request runs the full check set — no fast path for documentation-only changes,
because a check skipped by a path filter reports "not run", which reads as "not blocking".

The agent prepares the pull request; a human opens it, attaches screenshots, and merges it:
push the branch, compose the body from `.github/pull_request_template.md`, hand over the
compare URL (or `gh pr create` command) and the exact screenshot paths, then the human opens
the PR, drags in the screenshots — `gh` cannot upload images — and the codeowner in
`.github/CODEOWNERS` merges it. The agent does not open, approve, or merge a pull request.

# Adopting this kit in an existing repository

The only pre-kit history is the initial Frappe app scaffold in commit `a21a579`; it contains no
planning or verification record to migrate. The documentation cutover begins with
`specs/001-fleet-fuel-management/`, and none of its phases rely on evidence from an older
location. There are no superseded documentation paths to keep closed.

# References

- Framework/API patterns: Frappe workflow/document behavior in
  `../frappe/frappe/model/workflow.py` and `../frappe/frappe/model/document.py`; permission
  behavior in `../frappe/frappe/permissions.py`.
- Comparable local feature: the implemented `Fuel Order` → `Fueling Transaction` vertical slice
  under `fleet_management/fleet_management/doctype/`.
- Tests: `fleet_management/tests/` and the DocType `test_*.py` files under
  `fleet_management/fleet_management/doctype/`; use `IntegrationTestCase` on
  `fleet_management-test.localhost` for site-backed behavior.
- Roles: `Fleet Admin`, `Fleet Approver`, and `Fleet User`.
- Test commands: `bench fleet-test-site up --replace` / `down` (or `npm run test:site:up` /
  `test:site:down`), `bench --site fleet_management-test.localhost run-tests --app fleet_management`,
  `npm run test:ui`, and `npm run test:all` for the whole cycle.
- Sample data: `fleet_management/sample_data.py` (describe checks with its people, vehicles, and
  generators); disposable-site commands: `fleet_management/commands.py`.
- Required pre-merge checks: backend tests, Playwright Desk tests, the phase's `agent-browser`
  walkthrough, and a human review of its recorded evidence. The repository currently has no
  committed `.github/workflows/` automation, so these checks remain local/manual until CI is added.
