# Documentation rules

Read when writing or reviewing a specification or a verification record.

**Language.** `requirements.md` and `bugfix.md`, and everything above "The rule, as observed"
(verification), are business-functional: name an actor, an action, an outcome. No file
paths, no function names, no field names in those sections. Below that line, name concrete
surfaces freely.

**Verification is a procedure, never a transcript.** Never "I ran X and got Y" — always "put
the system in state X, expect Y". The test for every line: *could a reviewer who did not write
this code run it and get a yes or no?* If not, cut it. A check a machine can assert belongs in
a test file. Evidence that a run happened lives in CI and git and is linked, never pasted — a
CI run proves it on an exact commit; pasted output goes stale silently.

**The two diagrams.** `design.md` draws the design. Each phase record redraws it from its own
verification table — an edge appears only if a numbered row observed it, which makes the
diagram double as a coverage map. The record then tallies every spec edge against its own in
"Design vs. observed". A difference is a finding: **Unbuilt or untested** (designed, never
observed — blocking), **Undesigned behaviour** (observed, never designed — reconcile or
remove), **Drift** (built differently — somebody made an undocumented call; record it), or
**Not in scope** (another phase delivers it). Never harmonise the two diagrams silently. Use
one transition per line and stable node names so they diff cleanly.
