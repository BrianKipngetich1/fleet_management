See [CLAUDE.md](CLAUDE.md). This project keeps one set of agent instructions; this file is a pointer so either filename resolves to it.

<!-- kaysalt:workflow:begin (rendered by install.sh from the global KAYSALT_WORKFLOW.md) -->
# Kaysalt workflow

Every agent follows this procedure for every request. It is Kiro's Requirements-First spec
workflow (https://kiro.dev/docs/specs/) adapted to Frappe apps. Records live only in each
app's `specs/`, never in the global layer.

## Audience and voice

The requester may be non-technical. Use plain language and announce "Step N of 4"; while
building, also "part N of M" for phases and "task N of M". Head each question "Question N of
M", where M is the current estimate and may change as answers arrive. Never ask them to choose
between DocTypes, fields, or git terms; ask about their business and decide the technical side
yourself. When asking for approval, read each acceptance criterion back as a plain sentence.

## Before step 1 (not announced)

- A new session first reads `PROGRESS.md`, then the active spec's `tasks.md` progress log,
  and resumes from there.
- If `~/.kaysalt-agent/update-status` starts with `failed`, tell the requester the daily kit
  update failed and to contact IT, quoting the line. On an IT machine
  (`~/.kaysalt-agent/hooks/profile` reads `it`), quote the line and the end of `update.log`.
- A `chore(kit): update to …` commit on `develop` that the working branch lacks always counts
  as needed: merge `develop` in and read that commit's message for what the kit changed. If the
  active spec follows an older template (spec-check fails, or it is a single `spec.md`), explain
  in plain words what changed and offer to convert it on this branch. Converting edits the
  approved text, so its approval resets: read each criterion back and ask again. Then go
  through that message's kit changes and kept files: where one changes how the app is
  organised, built, or tested (not only wording), compare the app with the kit clone on this
  machine and offer the change as a kit suggestion. A kept `AGENTS.md` counts: offer the kit's
  new rules in it.
- When the app has `scripts/kit-check.py`, run it. Each kit suggestion says, in words for the
  requester, where this app differs from how the kit works now. After their own request is
  handled, offer the suggestions one at a time in those words, each as a Small task. A yes is
  built on a working branch; a no adds its id to `KIT_CHECK_SKIP` in `.kaysalt/project.conf`,
  so it is not asked again. Never adapt the app without a yes.
- The Locale defaults to Kenya: country `Kenya`, time zone `Africa/Nairobi`, currency `KES`,
  date format `dd/mm/yyyy`, language `English`. Read it back and change a value only when the
  requester says it differs.
- Sort the request: a feature or change gets `requirements.md`; a bug gets `bugfix.md`; a
  question is answered with no spec. A new app follows the bench root's `AGENTS.md` (Name →
  Set up → Show you → Offer the first feature) and needs no spec. When the request is vague, ask what they meant ("did you
  mean this or that?") first.
- Decide the tier and tell the requester:
  - **Small** (Kiro's Quick Spec): for example moving a field or changing its position. No new
    DocType, no role change, no data decision. The three files stay short and one "approve"
    covers requirements and design.
  - **Heavy**: needs thinking or touches many files. Say it is a large feature and recommend
    refining the plan with the `grilling` skill (Grill Me) before any building starts; on a yes,
    grill during step 1 and write `requirements.md` from the answers. Split it into phases that
    can run in separate sessions; suggest a PR once all are done.

## Steps

1. **Understand.** Ask one question at a time, in business words, then write
   `requirements.md` or `bugfix.md` from `specs/TEMPLATE-*.md`. Check it yourself (Kiro's
   Analyze Requirements): contradictions, vague words, unstated assumptions, missing edge
   cases; turn each finding into one plain question. Then run
   `python3 scripts/spec-check.py specs/NNN-name`. The requester approves.
2. **Design.** Write `design.md`. The requester approves; explain it in plain language when
   asked. A small task writes it together with step 1 and shares that approval.
3. **Build.** Work through `tasks.md`. After each task:
   - migrate the main site (`scripts/migrate.sh`) and run the quick checks (JSON validity,
     lint, spec-check);
   - tick the task's checkbox and add a progress-log line;
   - commit locally without waiting for approval and give a plain-language summary;
   - hand over a main-site link, say "tests run before the PR", and ask whether to start
     the next task.
4. **Deliver.** Only when the requester asks to publish ("push", "open a PR", "send it for
   review", "I'm done"): run the pre-PR pipeline below (`docs/agents/pre-pr-pipeline.md`
   in the app). Never start it unprompted.

## Approval and review lines

- `Approved by: <Full Name> (@<gh-login>) · DD/MM/YYYY · revision <short sha>` heads
  `requirements.md` (or `bugfix.md`) and `design.md`.
  - Write it only after an explicit "approve". Take the name and login from `gh api user` and
    confirm them with the requester; if they are not that account holder, ask their name and
    keep the session account's login.
  - The revision is the commit holding the approved text: commit the file, then add the line
    in a second commit. Add `(explained by agent)` when you presented the file instead of the
    requester reading it.
  - Any later edit resets the line to `Approved by: pending`; spec-check fails an approved
    file that changed.
- `Reviewed by: @<gh-login> · DD/MM/YYYY · model <model or "human">` goes in the PR review
  comment, and for features also as a row in the verification record.

## Stop and ask

Only before data loss or a data decision, and for anything the guard blocks.

## Pre-PR pipeline

1. At the same time: A rebuilds the test site; B updates the documentation.
2. After A, at the same time: C runs the full suites; D runs the walkthrough on the test
   site only.
3. The main agent writes the PR.

Sub-agent models:
- Claude: never a Fable model. Before spawning, pick from the models available in this
  session the two that best fit each sub-agent's work, each with a reasoning effort, and
  offer them as one line per sub-agent ("A, rebuild the test site: 1) <model> at <effort>,
  2) <model> at <effort>"). Use the requester's pick for the rest of the session.
- Codex: always `gpt-6-luna` at `max` reasoning; offer no choice.
- On an IT machine there is no model policy: use the models the session offers.
<!-- kaysalt:workflow:end -->
