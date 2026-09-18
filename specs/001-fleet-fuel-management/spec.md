<!--
The design document. Written before implementation, from the user's request.
Audience: a human deciding if this is the right thing to build, and an agent
resuming cold who must not relitigate settled decisions.

Business-functional language above "Current state": name an actor, an action, and an
outcome. No file paths, no function names, no field names in the human-facing sections.
Keep the whole file under ~400 lines for its entire life.
-->

# Fleet and Fuel Management

| | |
|---|---|
| Status | Draft |
| Owner | Fleet Management team |
| Started | 2026-09-17 |
| Approved by / date | — |
| Approved revision | — |
| Branch | version-16 |

## Problem

Fuel activity is spread across printed fuel-order sheets, receipts, and an Excel register.
The organisation cannot reliably connect an approved request to the fuel dispensed, measure
consumption, or explain discrepancies during review.

The process also lacks a dependable record of the actual requester, system user, approver,
driver, custodian, company representative, and physical evidence for each fueling event.

## Goal

A Fleet User can enter a request for a driver or custodian, an authorised location Approver
can approve it without self-approval, and an approved slip can be printed and signed before
fueling. A Fleet User then records the invoice-authoritative event and evidence.

The organisation can trace every event to the asset, assignment, people, readings, approved
station, invoice, and signed documents. Vehicle efficiency uses valid full-to-full intervals;
generator consumption uses measured tank balances and operating hours. Documentable
discrepancies remain visible without silently changing source values.

## Non-Goals

- ERPNext integration, accounting, stock ledgers, payments, or station integrations.
- A fuel-price master or pre-fueling KES estimate. Release 1 estimates litres only; the actual
  invoice price supports arithmetic and retrospective comparisons after fueling.
- Historical Excel migration or OCR in Release 1; each is a later approved workstream.
- Electronic signatures; the approval and fueling evidence remain physically signed.
- Fueling without an approved Fuel Order, or more than one active transaction per order.
- Routine exception paths for unapproved stations, wrong fuel, or out-of-window fueling.

## Decisions (locked)

- D-1 — The app is standalone on Frappe 16.22.0 with no ERPNext dependency.
- D-2 — Vehicles default to full-tank authorization. A partial fill requires an exact approved
  target and reason. Generators authorize a maximum quantity.
- D-3 — Asset fuel type and tank capacity are controlled master facts. Station, fuel type,
  asset, fill mode, and validity must match the approved order; mismatches are blocked.
- D-4 — The actual requester, driver, custodian, and company representative are people, not
  necessarily system users. Frappe records the users who enter, submit, approve, and cancel.
- D-5 — Operational access uses Fleet User, Fleet Approver, and Fleet Admin roles. Users may
  hold several roles, but no user may approve an order they entered or requested.
- D-6 — Approval and fulfillment are separate. Workflow authorizes the order; fulfillment is
  derived from validity and its active Fueling Transaction.
- D-7 — Default validity is configurable and initially 3 days (72 hours) from approval. An
  Approver may extend only the validity, with reason and audit history; the slip is reprinted.
- D-8 — The printed slip shows the exact valid-until timestamp and a configurable instruction
  telling the attendant not to dispense after it expires.
- D-9 — Both signed invoice and signed order slip are mandatory private PDF/JPG/PNG files.
  Submitted transactions are immutable; controlled cancellation allows one replacement.
- D-10 — Invoice/quantity discrepancies are retained and flagged with explanations. Invoice
  numbers are unique per station and CU numbers are globally unique.
- D-11 — Custodian and assigned location use non-overlapping effective-dated assignments.
  Stable asset facts and the current target remain on the asset; approved records snapshot all.
- D-12 — Vehicle km/L is distance divided by qualifying litres. First fills establish a
  baseline; partial litres accumulate until the next full fill.
- D-13 — Reports use actual fueling date, apply location permissions, and may use the previous
  qualifying record outside the selected range.

## Current state

The repository contains a scaffolded fleet_management app with no application DocTypes or
business controllers. Frappe source is tagged v16.22.0, the app is on branch version-16, and
there is no development or test site. The app declares Python >=3.14 and only bench-managed
Frappe as a dependency.

## Design

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingApproval: Fleet User submits
    PendingApproval --> Approved: location Approver approves
    PendingApproval --> Rejected: location Approver rejects
    Approved --> Cancelled: Approver cancels authorization
    state Approved {
        [*] --> AwaitingTransaction
        AwaitingTransaction --> Expired: valid-until passes
        Expired --> AwaitingTransaction: Approver extends and slip is reprinted
        AwaitingTransaction --> Completed: active transaction submitted
        Expired --> Completed: late entry proves fueling occurred in-window
        Completed --> AwaitingTransaction: active transaction cancelled in-window
        Completed --> Expired: active transaction cancelled after expiry
    }
    Rejected --> [*]
    Cancelled --> [*]
~~~

Fuel Order workflow records authorization. Approval submits and freezes the order; rejection is
terminal, and cancelling an approved order uses standard cancellation. Awaiting, Expired, and
Completed are fulfillment conditions, not approval workflow states. Expiry derives from
`valid_until`; the scheduler sends notifications but is not the source of truth.

A late entry may complete an expired order only when the invoice-authoritative fueling time was
inside the historical authorization window. Extending an unused order records old/new validity,
actor, timestamp, and reason, and cannot change asset, station, fuel, or quantity authorization.
The extension must precede fueling and cannot retroactively authorize an expired slip.

## Frappe-first

| Need | Native Frappe mechanism | Minimum custom rule |
|---|---|---|
| Forms, links, files, naming, print | DocTypes, Attach, naming series, Print Format | Private-file validation and optional deterministic names |
| Approval and immutability | Workflow and docstatus | Self-approval, validity extension, fulfillment derivation |
| Audit | owner/timestamps, workflow comments, Version, cancellation | Structured repeated extension/cancellation reasons |
| Access | Role Permission, User Permission, query conditions, has_permission | Location scope and direct-document guards |
| Notifications | Notification, Notification Log, scheduler | Validity and working-deadline recipients |
| Reports | Query/Script Report and Query Builder | Shared interval calculations and explicit location filters |
| Integrity | Validation, database constraints, transactions | Scoped uniqueness and active-order locking |

No custom API, cache, microservice, external OCR service, or price dependency is planned.

## Data Model

### Controlled masters

| DocType | Key data and rules |
|---|---|
| Fleet Person | Name, active flag, and optional User link; represents custodians, drivers, requesters, and representatives without requiring login. |
| Fleet Location | Name and active flag; User Permissions determine which Fleet Users and Approvers may act there. |
| Fuel Station | Name, active/approved flag, and operational location; a location may define a default station. |
| Fuel Type | Name and active flag. |
| Vehicle Model | Make, model, and descriptive engine capacity in CC. |
| Fleet Asset | Vehicle/Generator type, unique identifier, active flag, stable fuel type and tank capacity, current target, optional model, and tolerance override. |
| Asset Assignment | Child history with custodian, assigned location, effective-from/until, optional primary driver, and reason; periods cannot overlap. |
| Fleet Management Settings | Defaults for 2% tolerance, 10%/20% bands, 3-day validity, print instruction, 48-hour entry SLA, Holiday List, and reminders. |
| Meter Reset | Asset, reset date, old reading, new baseline, reason, evidence, and Fleet Admin authorization. |

Stable asset changes require Fleet Admin and a reason. `track_changes` records them; Fuel Order
and transaction snapshots preserve history. A separate target-history engine is deferred unless
future-dated targets become a real requirement.

### Fuel Order

The submittable document uses FO-.YYYY.-.##### and contains:

- Request datetime and actual requester Fleet Person; owner identifies the entering User and a
  server snapshot identifies who submitted it for approval.
- One Fleet Asset, request-time odometer/hour-meter, and whole-number vehicle gauge from 0–100.
- Operational location, approved planned station, and assignment snapshot: custodian, assigned
  location, fuel type, tank capacity, target, and tolerance.
- Vehicle Full/Partial mode. Partial requires exact litres and reason; Full estimates missing
  litres from capacity and gauge. Generator orders contain maximum litres.
- Approval actor/time, valid-until, rejection/cancellation/extension reasons, workflow state,
  and derived fulfillment status.

Approval freezes the authorization snapshot. The print shows exact validity, approved station,
asset, fuel, quantity basis, signatures, and configurable attendant instruction.

### Fueling Transaction

The submittable document uses FT-.YYYY.-.##### and links to one Fuel Order:

- Invoice-authoritative fueling datetime, driver and company representative Fleet Persons,
  external attendant name, invoice number, CU number, and read-only approved station.
- Read-only order/asset/fuel/assignment snapshots; owner and a server snapshot identify the
  creating and submitting Users.
- Vehicle odometer, pre-fueling gauge, full confirmation, and attendant identity; or generator
  hour-meter and pre/post tank levels with one selected unit and normalized litres.
- Invoice litres, total KES, printed unit price, and calculated unit-price snapshot.
- Mandatory private signed-invoice and signed-order attachments.
- Late-entry explanation and system-generated discrepancy rows with user explanations.

### Snapshot and derived-data policy

| Data | Treatment |
|---|---|
| Asset, assignment, target, capacity, fuel type, station, tolerance | Immutable order and transaction snapshots |
| Approval, validity, extension, rejection, cancellation | Audit facts; repeated actions never overwrite prior history |
| Request gauge and estimated litres | Approved-order snapshot |
| Invoice amount, litres, printed/calculated price | Immutable source/calculated snapshots |
| Efficiency, variance, generator litres/hour, cost per km/hour | Shared server calculation used by reports |
| Discrepancies | Auditable system rows; source values are never rewritten |

## Workflow and Permissions

Authorization requires both role and permitted Fleet Location. List queries, direct document
access, linked-document actions, reports, print, export, and cancellation enforce the same scope.
Query Builder report code applies location filters explicitly rather than assuming row permissions.

| Role | Capability |
|---|---|
| Fleet User | Create requests for permitted assets/locations, record actual requester and participants, submit transactions, and read permitted operational history. |
| Fleet Approver | Approve/reject/cancel orders, extend validity, print slips, and view reports for permitted locations. May also hold Fleet User, but cannot self-approve. |
| Fleet Admin | Maintain masters/settings/assignments/targets, authorize resets, cancel transactions, and access all operational and audit records. |
| Fleet Auditor (optional) | Read, print, report, and export without mutation; create only if direct auditor login is required. |

Self-approval checks both the entering/submitting User and the linked actual requester's User.
System Manager remains a platform role and is not required for routine fleet administration.
Submitted records cannot be deleted or directly edited; draft deletion, sharing, importing,
exporting, printing, cancelling, and reporting are granted only where required.

Approval/rejection notifications go to the entering user and Fleet Admin. Pending, pre-expiry,
expiry, and extension notifications go to the relevant location Approvers and Fleet Admin.

## Calculations and Validation

### Vehicle

For each submitted, non-cancelled full fill, find the prior qualifying full fill after the latest
meter reset. Distance is the odometer difference. Qualifying litres are every fill after the
previous full fill through the current full fill, including authorized partials.

~~~text
distance_km = current_odometer - previous_full_odometer
km_per_litre = distance_km / qualifying_litres
expected_interval_distance = target_km_per_litre * qualifying_litres
variance = km_per_litre - target_km_per_litre
variance_percent = variance / target_km_per_litre * 100
~~~

The first full fill is a baseline with no KPI. Green is within ±10%, orange is beyond ±10%
through ±20%, and red is beyond ±20% in either direction. The closing fill's target is used for
comparison; if the target changed within the interval, show the actual km/L but no color rating.

Request-time plausibility is approximate because the gauge is approximate:

~~~text
estimated_litres = tank_capacity * (100 - gauge_percent) / 100
estimated_distance_since_full = target_km_per_litre * estimated_litres
~~~

### Generator

~~~text
consumed_litres = previous_post_fuel_level - current_pre_fuel_level
operating_hours = current_hour_meter - previous_hour_meter
litres_per_hour = consumed_litres / operating_hours
expected_post_level = pre_fuel_level + delivered_litres
reconciliation_difference = expected_post_level - post_fuel_level
~~~

The first transaction establishes a baseline. Non-positive hours or unresolved rollback has no
KPI. Reconciliation over the shared tolerance is flagged with explanation.

### Price and retrospective comparison

~~~text
calculated_unit_price = invoice_amount / actual_litres
retrospective_estimated_amount = order_estimated_litres * calculated_unit_price
~~~

Printed and calculated unit prices are compared using defined currency precision. Without a
price master, the system validates arithmetic but does not claim that a station price is high.
The retrospective amount is labelled as a gauge estimate, never an authorization.

### Hard blocks and integrity

- Missing/unapproved order; fueling outside historical validity; asset, fuel, or station mismatch.
- Unapproved partial fill, missing partial reason, or invalid exact target.
- Duplicate active normalized station/invoice key or CU number, backed by database constraints.
- Missing/non-private/invalid evidence; unsupported content type or configured size excess.
- Zero/negative litres, amount, unit price, capacity, target, or invalid gauge/tank level.
- Meter decrease without an authorized reset; missing assignment/configuration snapshot.
- A concurrent second active transaction, prevented by locking the Fuel Order during submission.
- Deletion of submitted records or referenced masters.

Allowed quantity, amount, arithmetic, capacity, target, generator-balance, late-entry, and
plausibility discrepancies require explanations and complete the order without silent correction.
Cancellation preserves original identifiers but releases their active uniqueness keys only for a
replacement linked to that cancelled transaction and the same Fuel Order.
Transactions are ordered deterministically by actual fueling datetime and name; cancellation or
backdated entry recalculates affected report intervals from immutable source transactions.

## Reports

KPI reports exclude cancelled transactions; audit/reconciliation views retain them with status.
All reports use actual fueling date, drill down to source documents, and enforce location scope.

1. **Open Fuel Orders** — pending approval, approved without a submitted transaction, expired,
   late-entry, extended, and reopened orders.
2. **Fuel Register and Spend** — litres, KES, unit price, asset, assignment, station, fuel type,
   order, invoice, evidence, cancellation status, filters, groupings, trends, and export.
3. **Vehicle Performance** — full-to-full intervals, accumulated litres, distance, km/L,
   target variance, cost/km, color status, and estimated-versus-actual litres/amount.
4. **Generator Performance** — operating hours, tank movements, consumed litres, litres/hour,
   target variance, cost/hour, and reconciliation status.
5. **Exceptions and Audit** — discrepancies, late entry, resets, extensions, cancellations,
   draft missing evidence, explanations, actors, and timestamps.

Efficiency belongs to an asset interval and is not attributed naively to one station or custodian
when the interval spans several transactions or assignments. Dashboard cards and monthly/station/
custodian views reuse these reports; they do not implement separate calculations.

## OCR Evaluation and Historical Data

OCR is a separate post-core workstream. Any approved solution runs asynchronously, suggests
values only, requires Fleet User verification, preserves the original private attachment, and
retains manual entry. Accuracy, privacy, residency, cost, and maintenance require approval.

No Excel records are imported at go-live. If later approved, migration uses a validated template,
duplicate/sequence pre-check, dry-run errors, reconciliation summary, and no destructive overwrite.

## Tracer Bullet

| Phase | User-visible outcome | Main components | Verification focus |
|---|---|---|---|
| 0 — Secure vehicle journey | A Fleet User requests on behalf of a driver, a different location Approver approves and prints, and two full-fill cycles produce a correct km/L result. | People, locations, stations, fuel, model, asset/assignment, settings, three roles, order, transaction, workflow, print, Vehicle Performance | Identity separation, list/direct/report permissions, self-approval denial, validity print, private evidence, one active transaction, baseline then distance/litres KPI. |
| 1 — Integrity and exceptions | Partial authorization, discrepancies, assignment changes, resets, extension/reprint, notifications, cancellation/replacement, and audit work securely. | Assignment history, Meter Reset, discrepancy rows, constraints/locking, permission hooks, scheduler | Non-overlap, hard-block matrix, concurrency, scoped uniqueness, file validation, flags, audit, cancel/reopen. |
| 2 — Generators | Approved quantity and measured tank balances produce reliable litres/hour. | Generator fields on Fleet Asset/order/transaction and Generator Performance | Unit normalization, inventory reconciliation, hour interval, baseline, reset, target bands. |
| 3 — Operational reporting | Operations, management, and audit reconcile the fleet without Excel. | Five reports, dashboards, exports, indexes, permission filters | Totals, boundaries, cancelled inclusion rules, cross-range prior record, export scope, bounded queries, mobile use. |

### Acceptance criteria

- AC-01 — Fleet User records the actual requester and participants without requiring them to log in.
- AC-02 — Role plus location permission controls list, direct, report, print, and action access.
- AC-03 — A different location Approver can approve/reject; self-approval is denied server-side.
- AC-04 — The print shows exact validity, approved station/fuel/quantity, signatures, and instruction.
- AC-05 — Transaction submission requires valid private signed invoice and order attachments.
- AC-06 — First full fill creates no KPI; the second calculates distance/litres km/L correctly.
- AC-07 — Station, fuel, asset, validity, rollback, duplicate, and active-transaction violations block.
- AC-08 — A pre-fueling extension changes only validity, preserves history, and requires a reprinted slip; retroactive extension is denied.
- AC-09 — Allowed discrepancies retain source values and require explanations.
- AC-10 — Database constraints and order locking protect active uniqueness; a linked replacement can reuse its cancelled source identifiers.
- AC-11 — Cancelling a transaction preserves it and permits only one controlled replacement.
- AC-12 — Assignment periods do not overlap and approved snapshots survive later reassignment.
- AC-13 — A Fleet Admin reset restarts the calculation baseline with reason and evidence.
- AC-14 — Generator litres/hour uses measured inventory and excludes cancelled KPI records.
- AC-15 — The five reports reconcile to source records and apply the documented permissions.
- AC-16 — Audit views include cancelled records; KPI views exclude them.
- AC-17 — Actual-date filters and a prior qualifying record outside the range behave correctly.
- AC-18 — The workflow operates without a parallel Excel register.

## Verification

Pure calculations use UnitTestCase; documents, workflow, permissions, files, constraints, and
reports use IntegrationTestCase on the test site. Coverage includes both sides of every permission
boundary, formulas, full/partial intervals, effective assignments, reset baselines, currency
precision, duplicate normalization, concurrency, hard blocks, flags, extension, cancellation,
report reconciliation, date boundaries, and notifications.

~~~sh
bench --site <test-site> migrate
bench --site <test-site> run-tests --app fleet_management
npm run test:ui
~~~

Manual acceptance covers the three roles, request-on-behalf, two full fills, printed validity and
instruction, extension/reprint, physical signatures, private attachments, partial authorization,
generator measurements, mobile-width entry, report reconciliation, and cancellation audit.

Implementation must not begin until this specification is approved and disposable development
and test sites are available.

## Risks and Assumptions

| Type | Item and treatment |
|---|---|
| Dependency | No site exists; provision development/test sites and install the app before implementation verification. |
| Assumption | Fueling always uses an approved order, station, asset fuel type, and authorization window; unsupported events require a later explicit policy. |
| Assumption | Frappe User identifies system actors; Fleet Person identifies operational people and optionally links to User. |
| Assumption | Three days means 72 hours from approval; the exact timestamp is printed. |
| Assumption | The site supplies a Holiday List; Saturdays count and Sundays/public holidays do not count toward the entry SLA. |
| Open at review | Notification transport and reminder lead time; default is native in-app/email one day before expiry. |
| Open at review | If an invoice lacks time, Fleet User enters the known station time and explains that it was not printed. |
| Risk | Gauges and generator tank levels are approximate; retain source readings and flag discrepancies. |
| Risk | No price benchmark means no pre-fueling KES estimate or market-price variance claim. |
| Risk | Old slips remain physically available after extension; they show an expired timestamp and the extended order must be reprinted. |

## Progress log

- 2026-09-18 — Revised after architecture review: simplified roles/reports, separated people
  from users and approval from fulfillment, narrowed assignment history, and corrected formulas.
  Awaiting human review and approval. [Phase 0 verification](verification/phase-00-tracer-bullet.md)
