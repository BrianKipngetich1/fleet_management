# Phase screenshots

`agent-browser` writes each phase's Desk walkthrough evidence here, one directory per
specification. This example directory is the only one committed — every real spec's
screenshots directory is gitignored, kept local, and attached to the pull request by
hand.

## Naming

```
phase-NN-SS-short-slug.png
```

| Part | Meaning |
|---|---|
| `NN` | Phase number, zero-padded. `phase-05`, not `phase-5`. |
| `SS` | Two-digit sequence within the phase, in the order a reader should view them. |
| `short-slug` | What the frame shows, two or three hyphenated words, lower case. |

`SS` is what makes the set readable. A phase with six screenshots and no sequence leaves
the person attaching them to the pull request guessing at the order, and leaves the
reviewer assembling the story out of filenames.

## Worked example

```
specs/001-invoicing/verification/screenshots/
  phase-05-01-draft-form.png          the form as the intended role first sees it
  phase-05-02-validation-error.png    the guard refusing an invalid value
  phase-05-03-submitted-state.png     docstatus 1, the state the criterion claims
  phase-05-04-denied-as-other-role.png the deny half of the permission pair
```

`phase-05-01-draft-form.png` in this directory is that first frame, at the size and
crop these screenshots should be: the whole Desk viewport, nothing redacted away that a
reviewer needs, nothing zoomed so far in that the route and the logged-in user are lost.

## What to capture

One frame per claim the phase makes. A screenshot proves a state a human can see —
the record in its new state, the guard refusing the invalid case, the other role being
denied. It does not replace the phase record's verification table; it is the part of
the evidence a reader can check at a glance, for the rows no machine can assert.
