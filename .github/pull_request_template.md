#### What does this PR do?

#### Which specification and phase does it belong to?

<!-- e.g. specs/001-name, phase 5. For a closure PR, name the specification being closed. -->

#### Description of Task to be completed?

#### How should this be manually tested?

<!--
Build a fresh test site first: `bench fleet-test-site up --replace`. Describe each step with the
sample data, e.g. "as Philip, create an order for KDA 412M at 52,650 km and 21%; as Vikas,
approve it and print the slip". Throw the site away afterwards: `bench fleet-test-site down`.
-->

#### Any background context you want to provide?

#### Verification

<!--
- `bench fleet-test-site up --replace` — test site built from the sample data
- `bench --site fleet_management-test.localhost run-tests --app fleet_management` — N passed
- `npm run test:ui` — N passed (or `npm run test:all` for build, both suites, and teardown)
- `agent-browser` walkthrough as [sample user, e.g. Philip / Vikas]
- `bench fleet-test-site down` — test site removed
- Phase verification record: `specs/[NNN-name]/verification/phase-NN-slug.md`
-->

#### Screenshots (if appropriate)

<!--
Phase work: the agent lists the exact local paths of the `agent-browser` walkthrough
screenshots here, e.g.

  specs/001-example/verification/screenshots/phase-05-01-draft-form.png
  specs/001-example/verification/screenshots/phase-05-02-submitted-state.png

That directory is gitignored, so the files are not in the diff. The agent passes each file to
`gh pr create --attach`, `gh pr edit --attach`, or `gh pr comment --attach`; GitHub replaces
the local references with uploaded attachment URLs.
-->

#### Questions:
