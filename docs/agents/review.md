# Review closure

Read when requesting, performing, or closing a review.

A review is scoped to **one phase** and never widens. Two rounds maximum: round 1 raises
findings, round 2 checks only those findings and nothing new. **Zero blocking findings closes
the cycle**, however many non-blocking remain — that is the diminishing-returns line. A
non-blocking finding never reopens a review; it becomes a **Known limitation** in the phase
record or a new specification. If round 2 still returns blocking findings the phase was scoped
too wide: split it, do not re-review it. A third round is an escalation, not a review.

Request review in a fresh context, preferably on a different model or from a qualified person.
Record the verdict as one row in the phase record's review table.
