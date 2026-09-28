# Equipment checkout: tasks

## Phase 0: Request and issue, with the duplicate-issue guard

**Tracer:** A borrower submits a request for an available item; a custodian issues it; a second
attempt to issue that same item, including a concurrent one, is rejected.

- [x] 0.1 Add `Equipment Item` and `Equipment Checkout` with the Draft → Requested path
  - _Requirements: 1.1_
- [x] 0.2 Add the workflow with withdraw-before-issue only
  - _Requirements: 1.2, 1.3_
- [x] 0.3 Add the Issue transition, gated to Equipment Custodian; test Property 2
  - _Requirements: 2.1, 2.3_
- [x] 0.4 Add the duplicate-issue guard; test Property 1, including a concurrent attempt
  - _Requirements: 2.2_

## Phase 1: Return

**Tracer:** A custodian returns an Issued checkout; the item's on-loan flag clears and it can
immediately be issued to someone else.

- [ ] 1.1 Add the Return transition and clear the on-loan flag
  - _Requirements: 3.1_

## Phase 2: Overdue visibility

**Tracer:** An Issued checkout past its due date shows as Overdue on the custodian's list without
any manual flag-setting; returning it clears the flag.

- [ ] 2.1 Add a due date and the Overdue state
  - _Requirements: 4.1_
- [ ] 2.2 Clear Overdue on return
  - _Requirements: 4.2_

## Phase 3: Permission audit and closure

**Tracer:** A borrower is denied Issue and Return on every checkout, including their own, while a
custodian is allowed on every checkout regardless of who filed it.

- [ ] 3.1 Audit the role matrix under direct-document access and list filtering
  - _Requirements: 2.3_
- [ ] 3.2 Confirm no role can delete an issued or returned checkout
  - _Requirements: 2.4_
- [ ] 3.3 Confirm existing documents and reports behave as before
  - _Requirements: 5.1_

## Progress log

- `14/08/2026`: Phase 0 ✅ request-and-issue path shipped, duplicate-issue guard closed under a
  concurrent attempt. [Verification](verification/phase-00-example.md). Next: 1.1.
