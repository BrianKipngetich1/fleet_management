<!--
Canonical agent-instruction file for a Frappe repository. Replace every bracketed value, delete
rules that do not apply, and keep feature-specific requirements in specs/. `AGENTS.md` is a
one-line pointer to this file — Codex and other compatible agents follow it here; edit only
this.
-->

# Project

- Repository: `[repository_name]` · App/module: `[app_name]` / `[module_name]`
- Working directory: `[directory where the agent is started]`
- Bench root: `[path containing apps/, sites/, and Procfile]`
- Development site: `[app-name].localhost` · Test site: `[app-name]-test.localhost`
- UI surface(s): `[Desk | portal | Vue 3 + frappe-ui]`
- Base branch: `[branch, e.g. main]` · Integration branch: `[branch, e.g. develop]`
- Codeowner who presses merge: `[handle, matching .github/CODEOWNERS]`

# Start a context

Read `PROGRESS.md` — it is a one-line-per-specification index. Open the active specification
and the phase record it names. That is the whole ritual.

If project state, observed behaviour, or an open review finding contradicts the specification,
stop and reconcile the documents before writing code.

# How work is documented

Two documents per specification, and no others. Both are written by the agent; they differ in
audience, language, and what they are allowed to contain.

| | `specs/[NNN-name]/spec.md` | `specs/[NNN-name]/verification/phase-NN-[name].md` |
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
6. Run `bench --site [site] migrate` after any schema or fixture change, before verifying.
7. Write proportional tests. `IntegrationTestCase` for database, document, permission, or hook
   behaviour on the test site; `UnitTestCase` only for logic needing no site context.
8. Keep unrelated cleanup out of the active specification.
9. Get explicit authorization before merging, pushing to a protected branch, deploying, changing
   repository or infrastructure settings, or touching secrets.

# UI verification

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
facts. `npm run test:ui` before every push.

Sequence: implement → `agent-browser` walkthrough → local Playwright plus `bench --site [test
site] run-tests --app [app_name]` → push → PR, where CI reruns both.

**Functional testing runs only on the test site.** Never write test records to the development
site: a Desk walkthrough cannot be rolled back the way a document-API run can, so it leaves
residue. Both tools authenticate without a password — `bench browse [site] --user [email]`
mints a session id printed as `?sid=`; set it as the `sid` cookie. Never type credentials into
a login form. This is a user-impersonation primitive that only works because `developer_mode`
is on — acceptable on a disposable test site, a privilege-escalation surface anywhere else.

## Provisioning a site for UI tests

A site that never completed the setup wizard fails misleadingly: Desk re-routes everything to
the wizard, so every DocType route resolves as a Page and returns `403 Not permitted` — for
every user and DocType — while roles and `can_read` in the boot payload look perfectly correct.
Run `bench --site [site] execute frappe.utils.install.complete_setup_wizard` on any new site
first. It also needs `bench --site [site] set-config developer_mode 1`, without which `bench
browse --user` refuses to mint a session for a non-Administrator — and it prints the refusal
while exiting `0`, so check the output for `?sid=`, never the exit code.

That helper sets a US locale, so the site's date format becomes `mm-dd-yyyy`. Never type a
hard-coded ISO date into a Desk date field; convert through `frappe.datetime.str_to_user`.

## Desk quirks that cost time when forgotten

- A currency or data field needs a `Tab` blur before Frappe commits the typed value. Reading
  `cur_frm.doc` straight back after typing returns the stale value.
- A link field needs its autocomplete option **clicked**. Typing the exact value and blurring
  leaves the model field undefined even though the input shows the text.
- Frappe renders autocomplete entries as `div[role="option"]`, never `li`. Scanning for `li`
  finds nothing and reads as "no options returned".
- `Cancel` on a submitted document is a `.page-actions` button, not a menu dropdown item.

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
- Never commit credentials, tokens, passwords, cookies, or private keys. Name the approved secret
  source only.

# Commits and pull requests

Every commit title follows Conventional Commits: `type(scope): subject`, imperative, no
trailing period. `scope` optional; `!` before the colon marks a breaking change. Allowed types:
`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`.
Never use the word "phase" in a commit message.

Nothing is pushed to `[base branch]` directly; work reaches it through `[integration branch]`.
A pull request is opened at each point a human decision is required, not per file touched:

| Branch | Carries | Merges into | The approval it seeks |
|---|---|---|---|
| `spec/[NNN-name]` | `spec.md`, scaffolded phase records, the `PROGRESS.md` pointer | `[integration branch]` | Specification approved, implementation may begin |
| `feature\|fix\|chore/[NNN]-phase-[N]` | Implementation, that phase's verification record with its review table filled in, the `PROGRESS.md` update | `[integration branch]` | The phase is signed off |
| `release/[version]` or `[integration branch]` itself | Accumulated, reviewed work | `[base branch]` | The release is cut |

Every pull request runs the full check set — no fast path for documentation-only changes,
because a check skipped by a path filter reports "not run", which reads as "not blocking".

The agent prepares the pull request; a human opens it, attaches screenshots, and merges it:
push the branch, compose the body from `.github/pull_request_template.md`, hand over the
compare URL (or `gh pr create` command) and the exact screenshot paths, then the human opens
the PR, drags in the screenshots — `gh` cannot upload images — and the codeowner in
`.github/CODEOWNERS` merges it. The agent does not open, approve, or merge a pull request.

# Adopting this kit in an existing repository

Delete this section when the repository has no history that predates the kit. A repository that
already carries planning or verification documents does not have to migrate them. Record here,
once: where the pre-kit record lives, cited as reference rather than re-verified (`[path]`);
where the cutover happened — the first specification tracked under `specs/`, and which of its
phases are evidenced only in the old location (`[NNN-name]`, `[phase IDs]`); and what must not
be created again — the old paths, now closed to new work (`[paths]`). Re-verifying completed
work to satisfy a new format costs more than it proves. Cite it and move on.

# References

- Framework/API pattern: `[path or repository and exact pattern]`
- Comparable feature: `[path or repository and exact feature]`
- Tests: `[path]`, `IntegrationTestCase` on `[test site]`.
- Roles: `[role names]`.
- Test commands: `bench --site [test site] run-tests --app [app_name]` and `npm run test:ui`.
- Required CI: `CI` workflow (`.github/workflows/ci.yml`, jobs `tests` and `ui`) and `Linters`
  (`.github/workflows/linter.yml`).
