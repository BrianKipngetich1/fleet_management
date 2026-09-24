# Fleet and Fuel Management — Grill-Me Questions and Answers

This record captures the product and workflow questions asked during the requirements interview before the phased implementation plan was drafted.

- Interview date: 17 September 2026
- Numbered question entries: 104
- The underlying interview contained 107 user-answer exchanges; three immediate clarification exchanges are consolidated into the surrounding entry.
- Some prompts contained multiple subquestions or answer choices.
- Later clarifications are marked where they superseded an earlier assumption.
- Technical discovery questions about the existing repository and Frappe version are not included; this file contains the business/product interview.

## 1. Vehicle fueling policy, authorization, and people

### 1. Vehicle fueling policy

**Question:** For vehicles, what is the real fueling policy: full tanks normally, routine partial fills, or rules that vary? What does “full” mean operationally?

**Answer:** Every vehicle Fuel Order normally fills the tank completely. Partial fills are exceptional and require a reason. “Full” means confirmation by the fuel attendant.

### 2. Inconsistent full-tank confirmation

**Question:** If the attendant confirms “full” but litres, tank capacity, or gauge readings are inconsistent, should the system block submission or allow a flagged exception requiring Fleet Manager approval? Who may resolve or override it?

**Answer:** Allow submission as a flagged exception requiring Fleet Manager approval.

### 3. Effect of a flagged exception on completion

**Question:** While a flagged exception awaits Fleet Manager approval, should the Fueling Transaction remain submitted with the Fuel Order open and excluded from KPIs, or complete normally with an exception flag in reports?

**Answer:** Use the first option: keep the order open and exclude it from efficiency/cost KPIs while the exception is unresolved.

### 4. Recovery after exception rejection

**Question:** If the Fleet Manager rejects the exception, should the transaction be amended, cancelled and replaced, or should the Fuel Order be rejected and replaced?

**Answer:** The response clarified the business process rather than selecting an option: a request is entered, an approver approves or rejects it before fueling, an approved slip is printed and issued to the Fleet Manager, the driver fuels, and the post-fueling transaction is entered afterward. Later clarification established that the only approval gate is the pre-order approval; there is no post-fueling approval.

### 5. Person who enters the Fueling Transaction

**Question:** After fueling, who enters and submits the Fueling Transaction: the driver, Fleet Manager, or Company Representative/Data Entry User?

**Answer:** The Data Entry User.

### 6. Company representative and Data Entry User

**Question:** Must the person who signs the printed slip as the company representative be different from the Data Entry User, or may one person perform both roles?

**Answer:** The Company Representative and Data Entry User are the same person. The person who signs the printed slip is the designated approver, not the Company Representative.

### 7. Timing of approver signature

**Question:** When does the approver sign the printed slip: before fueling as authorization, after fueling as verification, or at both stages?

**Answer:** Before fueling, as authorization.

### 8. Physical confirmation after fueling

**Question:** After fueling, should both the driver and fuel attendant sign the slip confirming litres, amount, meter reading, and receipt details, or is the tax invoice alone sufficient?

**Answer:** The Company Representative who goes with the vehicle and the fuel attendant sign the invoice.

### 9. What the approver authorizes

**Question:** Should the approver authorize a maximum KES amount, a maximum litres quantity, a full-tank fill constrained by tank capacity, or different rules for vehicles and generators?

**Answer:** Vehicles use a full-tank fill constrained by tank capacity. Generators use a maximum-litre quantity. There is no fixed KES amount.

### 10. Capacity tolerance

**Question:** What percentage over the vehicle’s recorded tank capacity should trigger a flagged exception: 0%, 2%, 5%, or another value?

**Answer:** The tolerance must be configurable so it can be changed in the future.

### 11. Scope of tolerance configuration

**Question:** Should there be one organization-wide default, or an organization-wide default with an optional per-vehicle override? Should changes affect only future transactions?

**Answer:** Use an organization-wide default with an optional per-vehicle override. Changes apply only to future transactions and never recalculate historical results.

### 12. Initial tolerance

**Question:** What initial default should ship with the system: 0%, 2%, 5%, or another percentage?

**Answer:** 2%.

### 13. Generator capacity tolerance

**Question:** Should exceeding the approved maximum litres for a generator use the same 2% tolerance or a separate configurable tolerance?

**Answer:** The generator should use the same tolerance.

### 14. Clarification of generator tolerance

**Question:** Should “yes” mean that generators use the same 2% tolerance, or have a separate configurable tolerance?

**Answer:** Generators use the same configurable 2% tolerance.

### 15. Authority for actual readings

**Question:** Who is authoritative for recording actual odometer/hour-meter and pre-fuel gauge readings: the driver or the accompanying Company Representative/Data Entry User?

**Answer:** The Data Entry User.

### 16. First vehicle transaction baseline

**Question:** For a vehicle’s first transaction, should the system require a baseline and prior full-fill record, accept it with no efficiency until the next qualifying full fill, or require historical Excel data?

**Answer:** Accept the first transaction, but show no efficiency result until the next qualifying full fill.

### 17. First generator transaction baseline

**Question:** Should the first generator transaction follow the same rule: accepted, but with no litres-per-hour result until a later valid hour-meter interval exists?

**Answer:** Yes.

### 18. Initial fuel-price maintenance rule

**Question:** How should the applicable fuel price be maintained: organization-wide, per station/supplier and fuel type, or a default with station overrides?

**Answer:** The initial answer selected a price per station/supplier, fuel type, and effective date. This was later superseded: the system must not store a price master; the actual fuel-station price printed at fueling is authoritative.

## 2. Pricing, stations, and approval routing

### 19. Missing price record

**Question:** If a fueling transaction uses a station or fuel type with no applicable price record, should submission be blocked, flagged for Fleet Manager approval, or allow manual price entry?

**Answer:** The initial answer was to block submission. This was later superseded when it was decided that no Fuel Price master would exist; the invoice/station price at fueling is used instead.

### 20. Price variance

**Question:** If a price record exists but the invoice unit price exceeds the configured variance tolerance, should submission follow the flagged-exception path or be blocked?

**Answer:** The question led to clarification of what a “price record” meant; no price-master variance rule is retained because station pricing at the time of fueling is used.

### 21. Meaning of “price record”

**Question:** What is meant by a price record?

**Answer:** A price record was explained as a Fuel Price master entry containing station, fuel type, effective date, and price. The decision was then changed: price records are not stored.

### 22. Pre-fueling price estimate

**Question:** Since a top-up estimate is needed before fueling but actual station price is known only at fueling, should the Fuel Order use an expected price, the latest station price, a manually entered current price, or no cost estimate until the invoice exists?

**Answer:** Do not estimate cost until the invoice exists.

### 23. Pre-fueling litre estimate

**Question:** Before fueling, should the Fuel Order still show estimated litres needed from tank capacity and gauge percentage, or show no top-up estimate at all?

**Answer:** Show estimated litres from tank capacity and gauge percentage. Do not show a pre-fueling KES estimate.

### 24. Timing of station selection

**Question:** Is the station selected on the Fuel Order, only during fueling from the invoice, or planned on the order with the actual station recorded on the transaction if different?

**Answer:** Store a planned station on the Fuel Order and an actual station on the Fueling Transaction.

### 25. Station master

**Question:** Should fuel stations come from a controlled Fuel Station master list or be entered as free text from the invoice?

**Answer:** Use a controlled Fuel Station master list.

### 26. Invoice and CU number uniqueness

**Question:** Should invoice/receipt numbers be unique globally or only within the issuing fuel station? Should the CU number be globally unique?

**Answer:** Invoice/receipt numbers are unique within the issuing station. CU numbers are globally unique.

### 27. Actual station differs from planned station

**Question:** If the actual station differs from the planned station, should the system allow it with a reason, allow it only as a flagged exception, or block the transaction?

**Answer:** Block the transaction.

### 28. Who selects the planned station

**Question:** Who may select the planned station on the Fuel Order: requester, Fleet Manager, or approver? Should it be immutable after approval?

**Answer:** The requester selects the station from the controlled master list.

### 29. Changing a planned station after approval

**Question:** Once a Fuel Order is approved, should the planned station be locked, requiring cancellation and a new order to change it?

**Answer:** Yes. Changing it requires cancellation and a new Fuel Order.

### 30. Approval routing

**Question:** Is there one designated approver for every Fuel Order, or should the system support different approvers by vehicle, custodian, department, or amount?

**Answer:** Support different approvers by location.

### 31. Location used to determine approver

**Question:** Which location determines the approver: vehicle assigned location, requester location, planned station, or a separate operational location selected on the Fuel Order?

**Answer:** The Fuel Order carries both the vehicle’s assigned location and a separately selected operational location.

### 32. Different assigned and operational locations

**Question:** If those locations differ, which determines the approver, or must both locations’ approvers approve?

**Answer:** The vehicle’s assigned location determines the approver.

### 33. Generator approval location

**Question:** For generators, should the approver be determined by the generator’s assigned location using the same rule?

**Answer:** Yes, use the same rule.

### 34. Self-approval

**Question:** Must requester and approver always be different users, or may an authorized user approve their own Fuel Order in a small team?

**Answer:** They must be different. Self-approval is prohibited.

### 35. Requester and Data Entry User

**Question:** May the Data Entry User also be the requester, or must requester, approver, and Data Entry User always be three different people?

**Answer:** The requester and Data Entry User may be the same person. The approver must be different. At this point, approximately 18 core questions remained.

## 3. Order lifecycle, exceptions, and attachments

### 36. Resolution of a flagged transaction

**Question:** When the Fleet Manager reviews a flagged transaction, may they approve the exception and complete the Fuel Order, or must the transaction be corrected first?

**Answer:** The transaction must be corrected first.

### 37. Correction method

**Question:** Should correction use a Frappe amendment, cancellation plus a new linked transaction, or a dedicated “Needs Correction” state?

**Answer:** Use cancellation of the original transaction plus creation of a replacement transaction; keep the cancelled record auditable. This was later superseded for order-versus-invoice quantity/amount differences, which are retained and flagged without changing values.

### 38. Cancellation of an approved Fuel Order

**Question:** Who may cancel an approved Fuel Order, and until what point—for example, only the approver/Fleet Manager and only before a Fueling Transaction is submitted?

**Answer:** Only the approver may approve or cancel a Fuel Order, and cancellation is allowed only before a Fueling Transaction is submitted.

### 39. Rejected Fuel Order

**Question:** After rejection, may the requester edit and resubmit the same Fuel Order, or must they create a new Fuel Order?

**Answer:** Rejection is final. The requester must create a new Fuel Order.

### 40. Approved-order validity

**Question:** How long does an approved Fuel Order remain valid: same day, a configurable number of days, or indefinitely?

**Answer:** Three days.

### 41. Expiry or extension

**Question:** After three days, should the order automatically expire and require a new order, or may an approver extend its validity?

**Answer:** The approver may extend its validity or expire it.

### 42. Authority and audit for extension/expiry

**Question:** Should only the assigned approver be allowed to extend or expire the order, with a mandatory reason and full audit trail?

**Answer:** Yes.

### 43. Start of validity

**Question:** Does the three-day validity window start from the Fuel Order approval timestamp or the order date/time?

**Answer:** The approval timestamp.

### 44. Timing of transaction entry and attachments

**Question:** Must attachments be present before submission, or may fueling happen first and the Fueling Transaction be entered later?

**Answer:** Fueling is done first. The Fueling Transaction is recorded later, with an attachment mandatory at submission.

### 45. Required attachments

**Question:** Must submission include the signed tax invoice only, the signed Fuel Order slip only, both, or either authoritative signed document?

**Answer:** Both the signed tax invoice and the signed Fuel Order slip.

### 46. Fueling date versus approval validity

**Question:** Must actual fueling date/time fall within the three-day approval validity window while allowing the transaction to be entered later?

**Answer:** Yes.

### 47. Capturing “full tank”

**Question:** Should “full tank” be captured with a structured checkbox and attendant identity supported by the signed invoice, by the invoice attachment alone, or another method?

**Answer:** Use a required checkbox plus attendant name/identifier, supported by the signed invoice.

### 48. Partial vehicle fills

**Question:** May a partial vehicle fill be recorded with a reason and Fleet Manager review, or must it be pre-authorized on the Fuel Order?

**Answer:** It must be pre-authorized on the Fuel Order before fueling.

### 49. Partial-fill quantity

**Question:** For an approved partial fill, is the litres value an exact target, a maximum quantity, or a target with the 2% overage tolerance?

**Answer:** It is an exact target quantity.

### 50. Partial-fill mismatch

**Question:** If the invoice litres differ from the exact partial-fill target, should the transaction be blocked or allowed only as a flagged exception requiring correction?

**Answer:** Allow only as a flagged exception requiring correction and an explanation. This is separate from the 2% tank-capacity tolerance.

### 51. Resolution after a corrected replacement

**Question:** After the original transaction is cancelled and a corrected replacement passes validation, should the Fleet Manager still approve it, or should the order complete automatically?

**Answer:** This was superseded by a later clarification: for order-versus-invoice quantity/amount differences, do not cancel or change values. Retain the values, record a discrepancy explanation, and keep a flag.

### 52. Completing an order with a discrepancy

**Question:** After Fleet Manager review of the discrepancy, may the exception be approved and the order completed with the flag retained in reports, or must the order remain open?

**Answer:** Complete the order with the flag retained in reports.

### 53. Remaining hard blocks

**Question:** Should approval-as-is apply only to quantity/amount differences, with rollback, wrong fuel type, duplicate invoice/CU number, station mismatch, and missing attachments remaining hard blocks?

**Answer:** The response clarified that the workflow has only one approval: pre-order approval. There is no post-fueling approval. Quantity/amount differences are flagged for Fleet Manager visibility and reporting.

### 54. Duplicate invoice/CU numbers

**Question:** Should duplicate invoice numbers or CU numbers be hard blocks at transaction submission?

**Answer:** Yes.

## 4. Meter, fuel type, target, and efficiency controls

### 55. Meter rollback

**Question:** If an odometer or hour-meter reading decreases because of replacement, rollover, or documented error, should the system always block it or allow a separately logged, authorized meter-reset event?

**Answer:** Allow a separately logged and authorized meter-reset event establishing a new baseline.

### 56. Authority for meter reset

**Question:** Who may authorize a meter reset: Fleet Manager, System Manager, or both?

**Answer:** System Manager only.

### 57. Required reset data

**Question:** Should every reset require a reason, reset date, old reading, new baseline reading, and supporting attachment where available?

**Answer:** Yes.

### 58. Calculations after reset

**Question:** After a reset, should efficiency/consumption calculations restart from the new baseline and exclude the pre-reset interval?

**Answer:** Yes.

### 59. Permitted fuel type

**Question:** Should each vehicle or generator have exactly one permitted fuel type at a time, with effective-dated changes and hard-blocked mismatches?

**Answer:** Yes.

### 60. Effective-dated vehicle targets

**Question:** Should vehicle efficiency targets be effective-dated so historical reports use the target active when each fueling occurred?

**Answer:** Yes.

### 61. Authority to change targets

**Question:** Who may change a vehicle’s target—Fleet Manager, System Manager, or both—and should a reason be mandatory?

**Answer:** System Manager only, with a mandatory reason.

### 62. Expected distance calculation

**Question:** Should expected distance per tank be calculated as target km/L multiplied by tank capacity, or maintained as a separate expected route/distance per vehicle?

**Answer:** The initial “yes” was clarified to option 1: calculate expected distance automatically as target km/L × tank capacity.

### 63. Odometer performance bands

**Question:** Should red/green/orange odometer bands be configurable with organization defaults and per-vehicle overrides, using green within ±10%, orange from ±10% to ±20%, and red beyond ±20%?

**Answer:** Yes. Use those starting bands and make them configurable.

### 64. km/L bands

**Question:** Should actual km/L versus target use the same color bands or a separate configurable tolerance?

**Answer:** Use the same color bands.

### 65. Over-performance band

**Question:** If actual km/L is more than 20% above target, should it also be red as potentially erroneous, or should only under-performance be red?

**Answer:** Both under- and over-performance beyond ±20% are red.

### 66. Generator efficiency target

**Question:** Should each generator have an effective-dated litres-per-operating-hour target with the same color bands, or should generators report actual consumption only?

**Answer:** Each generator should have an effective-dated litres/hour target using the same color bands.

### 67. Generator-target governance

**Question:** Should generator-target changes follow the same rule as vehicle targets: System Manager only, effective-dated, and mandatory reason?

**Answer:** Yes. Approximately 12 focused business questions remained at this point.

## 5. Generator fueling and physical measurements

### 68. Generator full/partial logic

**Question:** Should each generator fueling be marked full or partial and use a full-to-full interval, or should every valid generator transaction contribute directly to consumption?

**Answer:** Generators are rarely filled to full. Orders are made for the litres required.

### 69. Generator consumption method

**Question:** Given that generator orders are quantity-based, should consumption be calculated as litres added ÷ operating hours, from tank-inventory changes, or only when a full-fill/baseline event exists?

**Answer:** Track generator tank balance and calculate actual consumption from inventory changes.

### 70. Generator tank-balance measurement

**Question:** How will tank balance be measured: physical pre-/post-fueling level in litres or percentage, or only litres delivered?

**Answer:** Record physical pre- and post-fueling tank levels in litres or percentage.

### 71. Accepted tank-level units

**Question:** Should levels be required in litres, required in percentages, or accept either and convert using generator tank capacity?

**Answer:** Accept either litres or percentage and convert using tank capacity.

### 72. Generator reconciliation tolerance

**Question:** If pre-fueling level plus delivered litres does not reconcile with the post-fueling level, should the difference use the same 2% tolerance and be flagged, or block submission?

**Answer:** Use the same tolerance level.

### 73. Reconciliation over tolerance

**Question:** When reconciliation difference exceeds 2%, should submission be allowed with a discrepancy flag or blocked?

**Answer:** Allow it with a flag.

### 74. Fuel additions outside the workflow

**Question:** Can generator fuel ever be added outside the Fuel Order workflow, such as from an internal store, or must every addition come through an approved Fuel Order and Fueling Transaction?

**Answer:** All orders are through an approved Fuel Order transaction. No external fuel additions are allowed.

### 75. Vehicle gauge timing

**Question:** Should vehicle fuel-gauge percentage be captured only on the Fuel Order, only at fueling, or both at request and immediately before fueling?

**Answer:** Capture it both at request and immediately before fueling.

### 76. Gauge and litre snapshots

**Question:** Should the approved Fuel Order preserve request-time gauge and estimated litres as immutable snapshots, while the Fueling Transaction stores actual pre-fuel gauge and litres?

**Answer:** Yes.

### 77. Gauge value format

**Question:** Should gauge percentage be mandatory, constrained to 0–100%, and allow decimal values such as 37.5%?

**Answer:** The clarification was whole-number values only.

### 78. Whole-number gauge clarification

**Question:** Does “full values” mean whole-number percentages only, from 0% through 100%, with no decimals?

**Answer:** Yes.

### 79. Odometer authority

**Question:** Should the Fuel Order odometer be a request-time reference only, with the Fueling Transaction odometer authoritative for efficiency calculations?

**Answer:** Yes.

### 80. Authoritative fueling date/time

**Question:** Should actual fueling date/time come from the signed tax invoice as the authoritative source, with the Data Entry User recording it?

**Answer:** Yes.

## 6. Access, transaction evidence, notifications, reporting, and future scope

### 81. Asset access for requesters

**Question:** May a requester create an order for any active vehicle or generator, or only for assets assigned to them or their location?

**Answer:** Only for assets assigned to them or their location.

### 82. Station restriction by operational location

**Question:** Should the planned station list be restricted to stations in the Fuel Order’s operational location, or may the requester choose any active station in the master?

**Answer:** Restrict planned stations to the Fuel Order’s operational location. Approximately eight core questions remained at this point.

### 83. Immutability and replacement after submission

**Question:** After submission, should a Fueling Transaction be immutable, with genuine data-entry errors handled by cancelling it and creating a replacement linked to the same Fuel Order?

**Answer:** Cancel it, but do not create a replacement.

### 84. Fuel Order after transaction cancellation

**Question:** What happens to the linked Fuel Order after cancellation: automatically cancel it and require a new order, mark it unfulfilled and prevent more transactions, or leave it open for another transaction?

**Answer:** The recorded interpretation is that one active transaction is allowed per order; after cancellation, one new transaction may be entered, while the cancelled record remains auditable.

### 85. Attachment formats

**Question:** Which formats should be accepted for the mandatory signed invoice and signed Fuel Order slip: PDF only, or PDF plus JPG/PNG images?

**Answer:** Accept images and PDF: PDF, JPG, and PNG.

### 86. Attachment naming

**Question:** Should the system automatically rename attachments using the document number and type, such as a transaction-number invoice and signed-slip filename?

**Answer:** Yes.

### 87. Rejection notification

**Question:** When a Fuel Order is rejected, should the notification go only to the Fleet Manager or also to the requester?

**Answer:** Both the requester and Fleet Manager.

### 88. Approval notification

**Question:** On approval, should both requester and Fleet Manager be notified, with the Fleet Manager responsible for printing and issuing the slip?

**Answer:** Yes.

### 89. Expiry notifications

**Question:** Should the system notify requester, Fleet Manager, and assigned approver before a Fuel Order expires and again when it expires?

**Answer:** Yes.

### 90. Fueling Transaction entry deadline

**Question:** Should there be a deadline for entering the Fueling Transaction after fueling, such as 24 or 48 hours, or only an outstanding-order report?

**Answer:** 48 hours.

### 91. Late entry

**Question:** After 48 hours, should submission be blocked or allowed with a Late Entry flag and explanation?

**Answer:** Allow late entry with a flag and explanation. Sundays do not count toward the deadline.

### 92. Public holidays in the deadline

**Question:** Should public holidays also be excluded from the deadline, or only Sundays?

**Answer:** Exclude Sundays and public holidays. Saturdays count.

### 93. Report date basis

**Question:** Should reporting date filters use actual fueling date from the invoice rather than Fuel Order date or data-entry date?

**Answer:** Use actual fueling date.

### 94. Previous qualifying record outside a report range

**Question:** If the previous qualifying fueling falls before the selected report range, should an in-range fueling use that earlier record for efficiency, or should the result be omitted?

**Answer:** Use the earlier out-of-range fueling to calculate the in-range result.

### 95. Invoice pricing fields

**Question:** Should Data Entry enter only total amount and litres, with the system calculating unit price, or also enter the unit price printed on the invoice for arithmetic validation?

**Answer:** Enter total amount, litres, and the printed invoice unit price for arithmetic validation.

### 96. Invoice arithmetic mismatch

**Question:** If litres × unit price does not equal the invoice total because of rounding or an entry error, should submission be blocked or allowed with a discrepancy flag and explanation?

**Answer:** Allow it and require a flag with an explanation.

### 97. Historical Excel import

**Question:** Should historical Excel records be imported before go-live, or should the system start fresh while Excel remains an archived reference?

**Answer:** Do not import historical records for go-live. Start fresh and retain the old Excel register as an archive/reference.

### 98. OCR scope

**Question:** Should OCR be excluded from the first release, with manual validated entry and attachments only while OCR is evaluated separately later?

**Answer:** Evaluate OCR separately later. Release 1 uses validated manual entry and attachments only.

### 99. Capacity/approved-quantity overage

**Question:** If actual litres exceed vehicle capacity or generator approved quantity by more than 2%, should the system allow submission with a flag and explanation or hard-block it?

**Answer:** Allow it with a flag and explanation.

### 100. Naming series

**Question:** May the system use Fuel Order series FO-.YYYY.-.##### and Fueling Transaction series FT-.YYYY.-.#####, or is an organization-specific prefix required?

**Answer:** Those naming series are acceptable.

### 101. Who may cancel a submitted Fueling Transaction

**Question:** Who may cancel a submitted Fueling Transaction: Data Entry User, Fleet Manager, approver, or System Manager?

**Answer:** The approver and System Manager.

### 102. Cancellation audit

**Question:** Should cancellation require a mandatory reason and preserve cancelling user and timestamp in the audit trail?

**Answer:** Yes.

### 103. Identity records

**Question:** Should internal people—requester, approver, driver, and Data Entry User—be linked to Frappe User/Employee records, while the external fuel attendant is recorded by name?

**Answer:** Yes. Internal actors use Frappe User/Employee records; the external fuel attendant is captured by name.

### 104. Effective-dated custody and location

**Question:** Should vehicle/generator custodian and assigned-location changes be effective-dated so historical reports use the assignment active on the fueling date?

**Answer:** Yes.

## 7. Final decisions carried into the phased plan

The interview resulted in the following high-level conclusions:

1. There is one approval gate: location-based pre-order approval before printing and fueling.
2. Vehicles normally receive full-tank fills constrained by tank capacity; partial fills require pre-authorization with an exact target.
3. Generators use approved litre quantities and physical tank-balance measurements.
4. The requester and Data Entry User may be the same person; the approver must be different.
5. Station, fuel type, duplicate identifiers, missing attachments, and invalid meter sequences have hard controls where specified; allowed discrepancies remain flagged and explained.
6. Actual station price from the invoice is authoritative; there is no Fuel Price master.
7. Approved Fuel Orders are valid for three days from approval timestamp, with controlled extension/expiry.
8. Fueling Transactions may be entered later, with a 48-hour deadline excluding Sundays and public holidays; late entry is allowed with a flag and explanation.
9. Reports use actual fueling date and may use the prior qualifying record outside the selected date range.
10. Historical Excel import and OCR are outside Release 1.
