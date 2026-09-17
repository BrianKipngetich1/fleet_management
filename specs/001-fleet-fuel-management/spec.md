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

Fuel activity is currently spread across printed fuel-order sheets, receipts, and an Excel
register. The organisation cannot reliably connect an approved request to the fuel actually
dispensed, detect abnormal mileage or consumption, or explain discrepancies during review.

The process also lacks a dependable record of who requested, approved, carried out, entered,
and physically signed each fueling event.

## Goal

Requesters can submit a fuel request for an authorised vehicle or generator, the correct
location approver can approve or reject it, and the Fleet Manager can issue an approved
printed slip to the driver. After fueling, the Data Entry User records the signed invoice and
signed slip, and the organisation can trace the event to the asset, people, readings, station,
and source documents without maintaining a parallel operational register.

Vehicle efficiency is calculated only from valid full-to-full intervals. Generator consumption
uses measured tank balances and operating hours. Suspicious but documentable discrepancies
remain visible in reports without altering source values.

## Non-Goals

- ERPNext integration, accounting, stock ledgers, payments, or fuel-station integrations.
- A station-price master or pre-fueling KES estimate. Release 1 estimates vehicle litres only;
  the invoice price is used for retrospective cost comparison after fueling.
- Historical Excel migration at go-live. The existing register remains an archive.
- OCR implementation in Release 1. OCR is a separate evaluation and approval workstream.
- Electronic signatures. The approver signs the printed slip before fueling; the Company
  Representative/Data Entry User and fuel attendant sign the invoice physically.
- More than one active fueling transaction or more than one fueling cycle per Fuel Order.

## Decisions (locked)

- D-1 — The app is standalone on Frappe 16.22.0; no ERPNext dependency.
- D-2 — Vehicles default to full-tank authorization; partial fills require an exact pre-authorised target and reason. Generators authorize maximum litres and need no full-fill flag.
- D-3 — Full means attendant confirmation plus attendant name, backed by the signed invoice, which is authoritative for actual datetime, litres, amount, price, numbers, and station.
- D-4 — Requesters choose an operational location and planned station from masters; stations are location-scoped and actual station must match. Approval follows asset assigned location; requester and approver differ.
- D-5 — There is one pre-fueling approval gate. Rejection requires a new order. Approved orders last three days from approval; the assigned approver may extend or expire with reason.
- D-6 — Fueling must occur within the approval window. Entry is due within 48 hours excluding Sundays/public holidays; late entry is allowed with explanation and flag.
- D-7 — Both signed invoice and signed order slip are mandatory; PDF/JPG/PNG are accepted and renamed with transaction number and document type.
- D-8 — Submitted transactions are immutable. The approver or System Manager may cancel with reason; cancellation reopens the order for one new active transaction.
- D-9 — Quantity, amount, arithmetic, capacity, and generator-balance discrepancies are flagged with explanations, retained unchanged, and need no post-fueling approval. Invoice numbers are unique per station; CU numbers are globally unique and hard-blocked.
- D-10 — Fuel type, target, custodian, and assigned location are effective-dated and snapshotted. System Manager alone changes targets and authorises documented meter resets.
- D-11 — First transactions have no metric. Expected distance is target km/L × capacity; green is within ±10%, orange ±10–20%, and red beyond ±20% in either direction.
- D-12 — Generator consumption uses physical pre-/post-levels in litres or percentage and inventory changes; no fuel is added outside this workflow.
- D-13 — Reports use actual fueling date and may use the previous qualifying record outside the selected range. Internal actors link to Frappe Users; attendants are named.

## Current state

The repository contains a scaffolded fleet_management app with no application DocTypes or business controllers; hooks and tests/specs are generated scaffolding. Frappe source is tagged v16.22.0, the app is on branch version-16, and sites/ has no development or test site. The app declares Python >=3.14 and no dependency beyond bench-managed Frappe.

## Design

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingApproval: requester submits
    PendingApproval --> Approved: assigned approver approves
    PendingApproval --> Rejected: assigned approver rejects
    Approved --> Cancelled: approver cancels before transaction
    Approved --> Expired: window ends or approver expires
    Expired --> Approved: approver extends validity
    Approved --> Completed: valid transaction submitted
    Expired --> Completed: late entry for fueling inside window
    Completed --> Approved: active transaction cancelled
    Rejected --> [*]
    Cancelled --> [*]
    Completed --> [*]
~~~

The Fuel Order is the authorisation record; the separate submitted Fueling Transaction links to it. A valid transaction completes the order, flags do not create another approval state, and cancelling the active transaction reopens one slot while preserving the cancelled record.

Expired orders cannot authorize new fueling, but may accept a late transaction when its invoice proves fueling occurred by the original valid-until timestamp. This separates authorization expiry from data-entry lateness.

## Frappe-first

| What we need | Native Frappe mechanism | Custom code, and why it is unavoidable |
|---|---|---|
| Forms, lists, links, attachments, naming series, print | DocTypes, Link/Attach fields, Print Format, naming series | None |
| Approval and terminal states | Workflow, docstatus, workflow transition roles | State-specific guards for expiry and reopening |
| Audit history | track_changes, Version/timeline, docstatus cancellation | Structured approval, expiry, and cancellation reasons |
| Role permissions and asset/location scoping | Role permissions, User Permission, permission query conditions, has_permission | Asset-effective-date and self-approval guards |
| Notifications | Notification, Notification Log, scheduler | Due-window and late-entry event calculation |
| Background work | scheduler events and frappe.enqueue | Expiry/reminder checks; OCR later if approved |
| Aggregated reports | Query Report/Script Report and Query Builder | Full-to-full and inventory interval algorithms |
| Server authority | Document controllers and lifecycle hooks | Cross-document validation, snapshots, scoped uniqueness |
| Files | Private File records and Attach fields | Deterministic post-submit file naming |

No custom API, cache, microservice, external OCR service, or price dependency is planned for Release 1.

## Data Model

### Controlled masters

| DocType | Key data and rules |
|---|---|
| Fleet Location | Name, active flag, and one designated approver User. |
| Fuel Station | Name, operational location Link, active flag. No price history. |
| Fuel Type | Name and active flag. |
| Vehicle Model | Make, model, and engine capacity in CC. CC is descriptive only. |
| Vehicle | Unique registration, model Link, active flag, and Asset Configuration history. |
| Generator | Unique identifier, active flag, and Asset Configuration history. |
| Asset Configuration | Child history with effective dates, tank capacity, permitted fuel type, target, custodian User, and assigned Fleet Location. Overlapping periods are rejected. |
| Fleet Management Settings | Single record containing default tolerance 2%, green/orange bands 10%/20%, three-day validity, 48-hour late-entry SLA, selected public-holiday calendar, and reminder settings. |
| Meter Reset | Asset, reset date, old reading, new baseline, reason, evidence attachment, and System Manager authorisation. |

The current effective Asset Configuration is copied into transaction snapshots; master changes do not rewrite historical reports.

### Fuel Order

The submittable document uses FO-.YYYY.-.##### and contains one asset only:

- Request datetime, requester, asset type, vehicle or generator, request-time odometer or
  hour-meter reading, and vehicle gauge percentage as an integer from 0 to 100.
- Operational location, planned station, derived approver, and read-only asset snapshots for
  assigned location, custodian, fuel type, tank capacity, and target.
- Vehicle fill mode: Full or Partial. Partial requires an exact litres target and reason.
  Full computes estimated litres from capacity and gauge. Generator orders contain maximum
  litres and no fixed KES amount.
- Approval, rejection, expiry, extension, and cancellation timestamps/reasons; valid-until
  timestamp; workflow state.

The approved record freezes authorisation and estimate snapshots and contains no pre-fueling price or KES top-up estimate.

### Fueling Transaction

The submittable document uses FT-.YYYY.-.##### and links to exactly one Fuel Order:

- Invoice-authoritative fueling datetime, Data Entry User/Company Representative, driver,
  actual station, invoice/receipt number, CU number, and external attendant name.
- Read-only asset, custodian, fuel type, planned station, and order references.
- Vehicle odometer or generator hour-meter. Vehicles also capture actual pre-fueling gauge,
  full-tank confirmation, and attendant identity. Generators capture pre- and post-fueling
  tank level plus unit (litres or percentage) and normalized litre values.
- Invoice litres, total KES amount, printed unit price, and calculated unit price snapshot.
- Two mandatory Attach fields: signed tax invoice and signed Fuel Order slip.
- Late-entry flag/explanation and a child table of system/manual discrepancy flags.

The server renames attachments to the transaction number plus invoice or signed-slip type,
preserving the extension and keeping files private.

### Snapshot and derived-data policy

| Data | Treatment |
|---|---|
| Asset configuration, target, capacity, fuel type, custodian, assigned location | Store immutable request/transaction snapshots |
| Approval timestamp and valid-until | Store as audit facts |
| Request estimated litres | Store on approved Fuel Order |
| Invoice amount, litres, printed unit price, calculated unit price | Store source values and calculated unit-price snapshot |
| Vehicle efficiency, variance, generator litres/hour, cost per km/hour | Calculate in reports from submitted non-cancelled transactions |
| Exception flags | Store as auditable child rows; never rewrite source values |

## Workflow and Permissions

The requester selects only an active asset assigned to them or to an authorised location. The station selector is limited to active stations in the operational location. The approver is derived from the asset’s assigned location and cannot self-approve.

| Role | Allowed behaviour |
|---|---|
| Fuel Requester | Create and submit own Fuel Orders for authorised assets; view own order history; no approval or post-submit edits. |
| Fuel Approver | Approve/reject/cancel orders for assigned locations; extend or expire them with reasons; print approved slips; cannot approve own request. |
| Driver/Fuel Collector | Read approved slip information where granted; no transaction submission. |
| Company Representative/Data Entry User | Enter and submit transactions after fueling for permitted orders; attach both signed documents; record the driver and attendant; cannot approve orders. |
| Fleet Manager | Read all operational orders, transactions, flags, and reports; receive notifications; issue printed slips; no post-fueling approval. |
| Auditor | Read, print, export, and reconcile records and audit history; no mutation. |
| System Manager | Configure masters, roles, settings, effective-dated targets/assignments, meter resets, and cancel submitted transactions. |

Submitted orders and transactions are not directly edited. Approval, rejection, extension,
expiry, and cancellation use workflow or controlled server actions. The approver and
System Manager checks are enforced server-side as well as in Desk permissions.

Notifications:

- Approval: requester and Fleet Manager.
- Rejection with reason: requester and Fleet Manager.
- Pre-expiry reminder and expiry: requester, Fleet Manager, and assigned approver.
- The reminder lead time is a configurable setting; the initial implementation assumes one
  calendar day before valid-until.

## Calculations and Validation

### Vehicle

For each submitted, non-cancelled full fill, find the previous qualifying full fill after the latest meter reset. Distance is current minus previous odometer; qualifying litres sum all transactions after the previous full fill through the current full fill, including partials. No result is shown without a previous qualifying full fill.

Vehicle efficiency is:

~~~text
km_per_litre = qualifying_litres / distance_km
variance = actual_km_per_litre - target_km_per_litre
variance_percent = variance / target_km_per_litre * 100
~~~

Expected distance for plausibility is target km/L multiplied by tank capacity. The same
colour bands apply to distance and efficiency: green within ±10%, orange from ±10% through
±20%, red beyond ±20% in either direction.

### Generator

Convert percentage tank readings to litres using the effective tank capacity. With no fuel
added outside this workflow:

~~~text
consumed_litres = previous_post_fuel_level - current_pre_fuel_level
operating_hours = current_hour_meter - previous_hour_meter
litres_per_hour = consumed_litres / operating_hours
~~~

The first generator transaction establishes history but has no result. Pre-/post-level
reconciliation is checked as:

~~~text
expected_post_level = pre_fuel_level + delivered_litres
reconciliation_difference = expected_post_level - post_fuel_level
~~~

More than the shared 2% tolerance is allowed with a discrepancy flag and explanation. A
non-positive operating-hour interval or an unresolvable meter rollback has no KPI result.

### Price and top-up

The calculated unit price is amount divided by litres. The invoice’s printed unit price is
also retained. Arithmetic or rounding disagreement is allowed with an explanation flag.

Vehicle top-up litres are estimated on the Fuel Order:

~~~text
estimated_litres = tank_capacity * (100 - gauge_percent) / 100
~~~

The KES cost estimate is intentionally blank before the invoice. After submission, reports
may show a retrospective comparison using the invoice’s calculated unit price; it is labelled
as an estimate, not an authorization.

### Hard blocks

- Missing or unapproved Fuel Order; actual fueling outside its approval window.
- Asset, fuel type, or planned/actual station mismatch.
- Vehicle partial fill not pre-authorised, missing partial reason, or invalid exact target.
- Duplicate invoice/receipt within the station or duplicate CU number globally.
- Missing signed invoice or signed Fuel Order slip.
- Zero/negative litres, amount, unit price, capacity, target, or invalid 0–100 gauge.
- Odometer/hour-meter decrease unless a System Manager reset event establishes a new baseline.
- More than one active Fueling Transaction for the same Fuel Order.
- Missing effective asset configuration required for the requested asset type.

### Allowed flags

The transaction remains submitted and the order completes when the Data Entry User supplies
an explanation for an order/invoice quantity or amount difference, partial target difference,
capacity/max-quantity overage above 2%, invoice arithmetic mismatch, generator reconciliation
difference above 2%, late entry, or red/orange plausibility result. The system retains both
source values and the flag; no post-fueling approval or silent correction occurs.

## Reports

All reports exclude cancelled transactions, use actual fueling dates, and reconcile to source orders/transactions. The previous qualifying record may precede the selected range.

- Vehicle consumption and km/L by vehicle, custodian, station, and period.
- Actual km/L versus effective target, expected-distance status, and red/orange/green flags.
- Generator litres/hour, operating hours, tank-balance movements, targets, and flags.
- Litres and KES cost by vehicle, generator, custodian, station, fuel type, and period.
- Cost per kilometre and cost per generator operating hour.
- Monthly litres and KES trends.
- Vehicle estimated litres versus actual litres and retrospective estimated cost.
- Invoice arithmetic and capacity/quantity discrepancy register.
- Approved orders awaiting fueling/entry, expired orders, late entries, and cancelled
  transactions that reopened an order.
- Transactions missing required evidence, station spending, and exportable audit/reconciliation.

Report queries use indexed Link/date/status fields and Query Builder aggregation. They fetch
only the prior qualifying record needed for an interval rather than loading unbounded history.

## OCR Evaluation

OCR is a separate post-core workstream and is not a Release 1 dependency. After representative
invoice samples are collected, the team will compare local and cloud options for field-level
accuracy, privacy/data residency, cost, operational dependency, and maintainability.

Any approved OCR implementation must run asynchronously, populate suggestions only, require
Data Entry verification before submission, preserve the original attachment, and retain manual
entry as the authoritative fallback. The recommendation and dependency require approval before
implementation.

## Historical Data

No Excel records are imported at go-live. The existing register remains an archive, and the
first in-system transaction for each asset starts a new measurement baseline.

If migration is later approved, it will be a separate staged workstream: a validated import
template, duplicate/sequence pre-check, dry-run error report, reconciliation summary, and no
destructive overwrite.

## Tracer Bullet

Each increment is vertical: it includes the minimum data, server rules, Desk surface, print or
report output, tests, and manual walkthrough needed to prove a usable outcome.

| Phase | User-visible outcome | DocTypes/components | Dependencies or approvals | Automated verification | Manual verification |
|---|---|---|---|---|---|
| 0 — Vehicle journey | Request, approve, print, fuel, attach, submit, and see first-baseline result. | Location, Station, Fuel Type, Vehicle Model, Vehicle, Settings, Fuel Order, Fueling Transaction, workflow, print, first report. | Specification approved; one configured vehicle, station, location, and test users; dev/test sites. | Naming, derived approver, links, attachments, one active transaction, baseline behaviour, reconciliation. | Full Desk journey, printed slip, physical-signature simulation, attachments, report. |
| 1 — Controls | Blocks, flags, notifications, audit history, effective dates, reset, and cancellation/reopen work. | Configuration history, Meter Reset, exception child, controllers, permissions, scheduler. | Phase 0 accepted; System Manager confirms roles and holiday calendar. | Hard-block matrix, scoped uniqueness, 2% flags, calendar SLA, permissions, reset, cancel/reopen. | Role access, notifications, attachment names, audit timeline. |
| 2 — Generators | Quantity-based generator entry produces inventory-derived litres/hour. | Generator, configuration history, transaction fields, calculation service, generator report. | Generator capacity, target, location, custodian, and sample readings supplied. | Unit conversion, inventory reconciliation, hour intervals, baseline, reset, target bands. | Generator order, litres/percentage entry, report and flagged mismatch. |
| 3 — Reporting hardening | Fleet Manager and Auditor reconcile cost, consumption, exceptions, and outstanding work without Excel. | Complete Query/Script Reports, dashboards, exports, indexes, permission filters. | Phases 0–2 accepted; Fleet Manager reviews KPI labels and sample data. | Totals, date boundaries, cancelled exclusion, export, permissions, query bounds. | Mobile entry, print readability, evidence traceability, report reconciliation. |

**Acceptance**

- AC-01 — An authorised requester can submit a Fuel Order with the correct derived approver.
- AC-02 — A different approver can approve or reject; rejection requires a new order.
- AC-03 — An approved order prints with required asset, readings, quantity, and signature area.
- AC-04 — Data Entry cannot submit without both signed attachments.
- AC-05 — A submitted transaction links to one active order and completes it.
- AC-06 — The first vehicle transaction is accepted and reports no efficiency result.
- AC-07 — Station/fuel mismatch, duplicate invoice/CU, rollback, and missing attachments block.
- AC-08 — Quantity, amount, arithmetic, capacity, reconciliation, and late-entry differences
  flag with explanation without changing source values.
- AC-09 — A cancelled transaction reopens the order for one new active transaction only.
- AC-10 — A System Manager reset restarts the relevant calculation baseline with evidence.
- AC-11 — Approval, rejection, expiry, and cancellation history identifies user, time, and reason.
- AC-12 — A generator order authorises maximum litres without a KES ceiling.
- AC-13 — Data Entry can enter generator tank levels in litres or percentage.
- AC-14 — Generator litres/hour uses measured inventory and excludes cancelled records.
- AC-15 — Every report total reconciles to submitted, non-cancelled source transactions.
- AC-16 — Actual fueling date filters and cross-range prior records behave as specified.
- AC-17 — Fleet Manager and Auditor can inspect flags/evidence without editing source data.
- AC-18 — The complete requisition-to-fueling journey works without an operational Excel register.

## Verification

Automated tests belong beside the relevant controllers and calculation modules. Pure formulas
use UnitTestCase; document, workflow, permission, attachment, and report tests use
IntegrationTestCase on the separate test site.

Required automated coverage includes naming, effective-date lookup, full-to-full intervals,
partial accumulation, generator inventory, target and color bands, top-up litres, working
deadline calculation, duplicate scopes, hard blocks, flags, cancellation/reopen, reset
baseline, report totals/date boundaries, permissions, and notification event creation.

After a test site exists, verification uses:

~~~sh
bench --site <test-site> migrate
bench --site <test-site> run-tests --app fleet_management
npm run test:ui
~~~

Manual acceptance covers:

- Requester, approver, Fleet Manager, Data Entry, and Auditor Desk journeys.
- Printed slip layout and pre-fueling approver signature.
- Signed invoice and signed slip attachment, private access, and deterministic names.
- Vehicle full fill, pre-authorised partial fill, and first-baseline behaviour.
- Generator litre and percentage tank-level entry.
- Mobile-width Data Entry use and report reconciliation.
- Cancelled transaction reopening and audit history.

Implementation must not begin until this specification is approved and a disposable
development/test site is available.

## Risks and Assumptions

| Type | Item and treatment |
|---|---|
| Dependency | No site is configured. Site provisioning, app installation, developer mode, and a separate test site precede implementation verification. |
| Assumption | One active approver is configured per Fleet Location. A future multi-approver rule would change workflow design. |
| Assumption | Frappe User is the internal identity source; no ERPNext Employee dependency is introduced. |
| Assumption | The site supplies a Frappe Holiday List for Sundays/public holidays. The selected list is a System Manager setting. |
| Open at review | Notification transport and the exact pre-expiry reminder lead time; initial plan uses native in-app/email notifications and one calendar day. |
| Open at review | If an invoice has no printed time, Data Entry must provide the known station time and explain that it was not printed; the tracer bullet must confirm this is acceptable. |
| Risk | Manual tank-level measurements can be inaccurate. The system retains both source readings and reconciliation flags; it does not silently correct them. |
| Risk | No price master means pre-fueling KES estimates are intentionally unavailable. The UI and reports must label post-invoice cost comparisons clearly. |
| Risk | Configuration changes can distort history. Effective-dated rows plus transaction snapshots and reset events are mandatory. |
| Risk | Late entry after automatic expiry could hide a valid fueling. The server validates actual fueling datetime against the historical valid-until timestamp, not only current workflow state. |

## Progress log

- 2026-09-17 — Drafted after business grilling and read-only repository discovery. Awaiting
  human review and approval. [Phase 0 verification](verification/phase-00-tracer-bullet.md)
