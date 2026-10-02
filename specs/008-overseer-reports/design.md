<!--
How the requirements will be met (Kiro's design.md). Written in step 2 of the Kaysalt
workflow and approved before building starts; a small task writes it with requirements.md
and shares that approval. Audience: the requester and an agent resuming cold.

This is the first file allowed to name DocTypes, fields, routes, and roles. Every
correctness property validates at least one acceptance criterion. Never invent records or
labels for existing data; ask the requester and record the answer in "Data and migration plan".

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->

# Fleet Oversight Reports: design

Approved by: pending

## Current state

- No Fleet Management reports exist yet.
- `Fuel Order` stores the request date, workflow state, fulfillment status, warning signal and reasons, and approval or rejection audit details. Rejections and withdrawals both end in `Rejected`; `decision_action` distinguishes them, and `rejected_on` records the event time for either action.
- `Fueling Transaction` stores the actual fueling date, delivered litres, vehicle odometer or generator hour meter, and vehicle full-fill interval values. Submitted transactions are immutable and cancellations retain their source values.
- Fueling transactions have no invoice total or printed unit price fields. The transaction form already requires a private invoice attachment.
- `fleet_management.permissions` already provides location-scoped document checks and `get_report_query_conditions()` for `Fuel Order` and `Fueling Transaction`. A report must apply those conditions itself; report filters alone do not protect rows or exports.
- The approved 001 role plan says Fleet Approvers can view reports for permitted locations and Fleet Admins can access all operational and audit records. It describes a Fleet Auditor as optional, only if a separate auditor login is needed.

## Words in this request

| Requester's word | Means in this app |
|---|---|
| overseer | Fleet Approver for permitted locations, or Fleet Admin for all locations, as set out in the approved 001 role plan |
| fueling date | `Fueling Transaction.actual_fueling_datetime` |
| request date | `Fuel Order.request_datetime` |
| decision date | The stored approval or rejection/withdrawal event time on `Fuel Order` |
| completed fueling | A submitted `Fueling Transaction` that has not been cancelled |
| generator fuel | Litres delivered in a transaction; reports do not call this consumption |
| discrepancy | A separate recorded observation linked to a `Fueling Transaction`; source transaction values stay unchanged |
| unavailable amount | An older fueling record with no invoice amount; the report shows no amount and does not estimate one |

## Decisions (locked)

- `D-1`: Provide three reports: Fueling Summary, Asset Performance, and Requests & Audit. The first combines the requested fueling and spend summaries; the second combines vehicle and generator views with the asset's request history; the third combines decisions, warnings, discrepancies, and cancellations. Chosen over separate reports for each topic to meet the three-report limit.
- `D-2`: Use native Frappe Script Reports, report filters, built-in export, and a Fleet Oversight Workspace linking the three reports. The standard report result is the single source for on-screen rows and export. Chosen over a custom dashboard page because it would duplicate filtering, export, and permission behavior.
- `D-3`: Give report access to Fleet Approver and Fleet Admin, with no new role. Fleet Approvers remain limited to their permitted locations; Fleet Admin retains its existing all-location access. Do not create the optional Fleet Auditor role because this request does not ask for a separate auditor login.
- `D-4`: Add an invoice total and an optional printed unit price to `Fueling Transaction`. Require a positive invoice total when a new transaction is submitted; capture a printed unit price when the invoice shows one. Calculate price per litre as invoice total divided by delivered litres in the report. Chosen over storing a second calculated value, because the source fields are immutable after submission and the result can be derived consistently.
- `D-5`: Leave existing invoice totals and printed prices empty. Reports show an unavailable amount for records without one; do not backfill or estimate historical amounts.
- `D-6`: Store each discrepancy as a separate `Fueling Discrepancy` record linked to its transaction, with type, details, reason, server-recorded user, and server-recorded date. Keep it separate from the submitted transaction so recording an observation never edits the source record. Allow multiple discrepancy records per transaction.
- `D-7`: Use a free-text discrepancy type because the request supplies no fixed category list. Chosen over inventing a list that could exclude a real discrepancy.
- `D-8`: Apply the existing location scope in every report query, including the new discrepancy record through its linked transaction. Populate location filter choices only from the current user's permitted locations. Run built-in exports from the same filtered result.
- `D-9`: Use the existing full-to-full interval values and ordering rules for vehicle efficiency. Use an earlier full fill outside the visible date range when required by the interval, but do not display its activity as an in-range row. Do not rate an interval when its target changed.
- `D-10`: Exclude cancelled transactions from fueling, efficiency, and spending totals. Show them in Requests & Audit with their cancellation status. Filter fueling records by actual fueling date; filter requests and their decisions by their request or decision event date.
- `D-11`: Do not change existing request, approval, or transaction submission rules. Fleet Users may record a discrepancy only for a transaction they can access; Fleet Approver and Fleet Admin may also record one within their existing scope.

## Design

```mermaid
stateDiagram-v2
    [*] --> Filters
    Filters --> DateRangeError: start date is after end date
    Filters --> Results: valid date range
    Results --> Exported: export the same filtered rows
    Results --> Filters: change filters
    DateRangeError --> Filters: correct date range
```

**This diagram is the design, not the build.** The report returns an error without totals for an invalid range. A valid range returns results filtered by the event date appropriate to each record type. Export uses those same results and filters.

### Report layout

| Report | Contents |
|---|---|
| Fueling Summary | Monthly delivered litres, transaction counts, recorded invoice totals in KES, weighted calculated price per litre for records with an amount, printed unit price as its own detail value, monthly trend, and source transaction rows. Rows without an amount are visibly unavailable and counted separately. |
| Asset Performance | The selected asset's Fuel Orders and fueling transactions in the requested period, links to each source, request and fulfillment status, and vehicle interval efficiency or generator delivered litres and hour-meter readings. |
| Requests & Audit | Request decisions and reasons, warning signals and reasons, recorded discrepancies, and cancelled fueling transactions with their status and source links. |

All reports use inclusive start and end dates and accept any span covered by retained records. The relevant filters are date range, location, asset, fuel type, and station. A location, asset, fuel, or station filter applies to every summary, trend, detail row, and export in that report. The Workspace is a navigation page only; it adds no fourth report or separate calculations.

For a month with records that lack invoice amounts, the total is the sum of recorded invoice amounts only. The report shows how many records have no amount, rather than implying the total covers those records. The calculated price per litre uses only transactions with a recorded amount and is the recorded amount total divided by their delivered litres. Each detail row shows the calculated value beside, not in place of, a printed unit price.

## Frappe-first

| What we need | Native Frappe/ERPNext mechanism | Custom code, and why it is unavoidable |
|---|---|---|
| Three filterable reports and spreadsheet export | Script Reports, standard report filters, charts, and built-in report export | Report queries and calculations must combine `Fuel Order` and `Fueling Transaction` data and explicitly apply the location scope. |
| One place to open the reports | A standard Desk Workspace with links to the three reports | None beyond its report links and role visibility. |
| Invoice amount and printed unit price | `Currency` fields on `Fueling Transaction` | Controller validation must require an amount on new submissions and preserve submitted-record immutability. |
| Discrepancy observations | A standard `Fueling Discrepancy` DocType linked to `Fueling Transaction` | Controller and permission hooks must set audit fields on the server and enforce the linked transaction's location scope. |
| Full-fill efficiency | Existing `Fueling Transaction` interval fields and shared interval calculation | The report must select a prior full fill outside the visible period when needed and suppress ratings when the target changed. |

## Data and migration plan

Add `invoice_amount` and `printed_unit_price` as optional `Currency` fields in the schema so existing submitted transactions migrate without invented values. New transactions require a positive invoice amount at submission. A printed unit price is optional and is saved separately when present. The report derives calculated unit price; it does not store a duplicate calculation.

Add the `Fueling Discrepancy` DocType with a link to `Fueling Transaction`, discrepancy type, details, reason, recorded-by user, and recorded-on timestamp. The server sets the audit fields. A discrepancy is its own record; neither adding it nor viewing it changes or amends the transaction. No existing records are changed or backfilled. Existing transactions without a discrepancy entry display “No discrepancy was recorded,” which does not claim that no issue occurred.

## Correctness properties

### Property 1: Date range and filter consistency

For every valid date range, the report includes both boundary dates, uses the correct event date, and applies the selected location, asset, fuel type, and station filters to every displayed total, trend, detail row, and export. A reversed range returns an error and no totals.

**Validates: Requirements 1.1, 1.2, 1.5, 4.2**

### Property 2: Spend uses recorded source amounts

For every fueling summary, only non-cancelled transactions contribute to litres, counts, and spend. Spend totals only recorded invoice amounts in KES; a missing amount remains unavailable, and calculated and printed unit prices remain separate.

**Validates: Requirements 1.3, 1.4, 3.4**

### Property 3: Asset history preserves source status

For every selected asset and period, the report links its in-range Fuel Orders and fueling transactions and shows the correct request, decision, fulfillment, and cancellation status. Generator litres are presented as delivered, not consumed.

**Validates: Requirements 2.1, 2.4, 3.1, 3.2, 3.4**

### Property 4: Vehicle efficiency follows full-to-full intervals

For every vehicle interval, efficiency is distance divided by the qualifying litres between full fills, including partial fills. The prior full fill may be outside the display range. Missing intervals show unavailable; a changed target removes the rating; rating boundaries are inclusive at 10 percent and 20 percent as written in the requirement.

**Validates: Requirements 2.2, 2.3**

### Property 5: Discrepancies are traceable observations

For every discrepancy, the source transaction remains unchanged and the report shows the type, details, reason, server-recorded user, and date. A transaction without a discrepancy entry is described as having no recorded discrepancy, not as having no issue.

**Validates: Requirements 3.3**

### Property 6: Report rows stay within location permissions

For every report and export, Fleet Approvers receive only rows from permitted locations and Fleet Admins retain their existing access. A user cannot widen access by changing report filters or opening a linked record.

**Validates: Requirements 4.1, 4.2**

### Property 7: Existing fueling operations continue

For every request and fueling submission, the existing approval, evidence, and location checks remain in force.

**Validates: Requirements 5.1**

## Errors and permissions

- A start date after the end date produces a clear report message and an empty result with no totals.
- Fleet Approver and Fleet Admin can open the Workspace and reports. Fleet Users do not receive report access through this feature, but may create a discrepancy for a transaction they can access.
- Every report query and discrepancy lookup checks the same existing location scope as its linked source record. The server rejects an out-of-scope filter or linked transaction; the client cannot grant access.
- Fleet Admin has the app's existing all-location access. No role gains access to a new location.
- Report exports use the rows returned to the current user under the current filters.
