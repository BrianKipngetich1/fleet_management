<!--
Business requirements for the Fuel Order experience. Keep this readable to fleet staff.
Acceptance criteria use EARS wording and are cited by tasks after the design is approved.
The approval line is written only after explicit approval.
-->

# Fuel Order experience: requirements

Approved by: pending

| | |
|---|---|
| Tier | Heavy |
| Branch | feature/009-fuel-order-ux-brian |

## Introduction

Fleet staff already use a vehicle-first fuel request, a server-calculated green or red signal, approval, and a separate record for the actual fueling. The current form puts related facts far apart, repeats the signal, and does not refresh it while a person types. Some information the app says should be recorded, including a separate reason for a partial quantity, is not currently captured.

This change will arrange the existing request into four main sections, explain the signal while the person enters readings, add a second vehicle-mileage check based on the latest confirmed full tank, and keep a durable history from issue through decision and fueling. Existing validation, authority, location access, and approved records remain protected.

## Current behavior checked

- The vehicle is already selected first. The system fills in assignment facts, the previous entry, and vehicle estimates. The person entering the request can change the suggested driver and fueling location.
- The order number, request date, asset snapshots, and signal are supplied by the system. The order form shows several snapshots, calculations, and print details alongside the entry fields.
- The current mileage reason, “Mileage does not add up,” compares the distance since the Previous Entry with the distance expected from the gauge estimate and applicable economy average. It uses the most recent completed fueling reading, including a partial fueling, or falls back to the last approved order. A cancelled fueling is excluded. This check has no confirmed-full-tank baseline.
- The signal is calculated on the server when an order is saved or an approval action is taken, and it stays frozen after approval. The page shows it in an introduction and again in the form. Changing a reading does not refresh the signal until the next save.
- A Fleet User can approve a green order. A red order can be rejected or sent to a permitted Fleet Approver with an explanation; the approver decides with a reason. Existing validation and location restrictions remain server enforced.
- Vehicle gauge and gauge-photo fields are already limited to vehicles. The meter label is generic. Partial litres are visible even for a full authorization, and the app has no separate partial-authorization reason, although the earlier approved specification says an exact-litre request needs one.
- A separate actual-fueling record already captures the fueling time and its source, actual station, vehicle odometer or generator hour meter, litres, invoice and tax-device identifiers, attendant, and signed documents.
- Change history is enabled on orders and fueling records. Extensions have a reasoned history, but cancellations have no required reason and the order only retains the latest print revision and time. There is no purpose-built issue history that brings each red reason, its source readings and limits, explanation, decision, and resolution together.
- Invoice amount or unit-cost comparison, working-hour late-entry handling, and meter-reset behavior are not built. The current fueling-date rule requires the actual time to fall within the approved order’s validity window; a lower submitted meter reading is refused.

## Requirements

### Requirement 1: Four clear sections for entry and review

**User Story:** As a Fleet User, I want the order information grouped in a predictable sequence, so that I can enter a request and find system-supplied facts without scanning unrelated fields.

#### Acceptance Criteria

1. WHEN a Fleet User opens or reviews an order THE system SHALL present four main sections in this order: Vehicle and Order, People and Location, Readings and Evidence, and Quantity, Approval and Audit.
2. WHEN a person starts an order THE system SHALL put Asset first and place Asset, Driver, and Actual Requester together on one row when the screen is wide enough, and SHALL show a read-only summary of the vehicle, its assignment, its previous entry, and supported estimates after an asset is selected.
3. WHEN an order is shown on a desktop THE system SHALL use two or three columns where labels and controls remain readable, and on a narrow screen SHALL stack the same information in one column without horizontal scrolling.
4. WHEN a person selects Full authorization THE system SHALL hide partial litres and the partial-authorization reason, and WHEN the person selects Partial authorization THE system SHALL show both and require a specific reason before the order leaves Draft.
5. WHEN a person enters an order THE system SHALL group the company representative, operating location, and planned station under People and Location, the odometer or hour-meter reading and evidence under Readings and Evidence, and quantity authorization and decision history under Quantity, Approval and Audit.
6. WHEN a vehicle is selected THE system SHALL label its meter reading Odometer and show its gauge and gauge photo, and WHEN a generator is selected THE system SHALL label its meter reading Hour Meter and hide the gauge and gauge photo.
7. WHEN a person attaches a request photo THE system SHALL let the person inspect an image preview using the existing image attachment control before the order is approved or sent for sign-off.
8. WHEN a person reviews an order THE system SHALL keep system snapshots, signal calculations, and print bookkeeping available as read-only review details outside the main entry path.

### Requirement 2: One useful signal panel during entry

**User Story:** As a Fleet User or Fleet Approver, I want to see why an order is green or red and what I can do next, so that I can make or review the decision using the relevant readings.

#### Acceptance Criteria

1. WHEN the order form shows a signal THE system SHALL show one textual signal panel immediately after the last applicable reading field, and SHALL not repeat the same alert elsewhere on the form.
2. WHEN a person changes a reading that affects the signal THE system SHALL refresh an unsaved preview using the same server calculation used when an order is saved, and WHEN a required reading is missing THE system SHALL state which reading is needed instead of showing an older result.
3. WHEN a signal reason is shown THE system SHALL identify the relevant reading, comparison, threshold, and next action, and SHALL distinguish a red result that can be reviewed from a hard validation or permission failure.
4. WHEN a mileage comparison is shown THE system SHALL identify whether its expected economy comes from the vehicle target or its recent average, SHALL use Odometer for distance and Fuel economy for km/L, and SHALL show km/L with equivalent L/km and L/100 km values when the source data supports an observed efficiency.
5. WHEN the existing distance-only mileage check is shown THE system SHALL show distance since the previous entry, expected distance, the fuel estimate used, and the configured margin without describing the estimate as observed fuel economy.
6. WHEN a red order is shown to a Fleet User THE system SHALL state that the user may reject it or send it to a permitted Fleet Approver with an explanation, WHEN a green order is shown THE system SHALL state that the user may approve it, and WHEN a sent-up order is shown to a permitted Fleet Approver THE system SHALL state that the approver may approve or reject it with a reason.

### Requirement 3: Preserve the current request and approval rules

**User Story:** As the fleet owner, I want the new form and signal to respect the current controls, so that a clearer screen does not weaken authorization or change the meaning of existing records.

#### Acceptance Criteria

1. WHEN the order is saved or a workflow action is taken THE system SHALL CONTINUE TO calculate the signal on the server, reject client attempts to set or override it, recompute it before approval, and freeze its approved result and source snapshots.
2. WHEN the existing “Mileage does not add up” check runs THE system SHALL CONTINUE TO use its current Previous Entry behavior, configured margin, and treatment of missing history, missing average, and a meter that has not moved forward; the new check SHALL have its own distinct reason and SHALL NOT replace or weaken this check.
3. WHEN an order is green or red THE system SHALL CONTINUE TO enforce the current approval and rejection roles, independent-approver rule, location scope, notifications, evidence gate, server validations, and immutable approved snapshots.
4. WHEN an order is approved and later fuel is recorded THE system SHALL CONTINUE TO keep authorization separate from actual fueling and reconciliation, using the linked actual-fueling record as the source for what happened at the station.

### Requirement 4: A separate mileage check from the latest full tank

**User Story:** As a Fleet User or Fleet Approver, I want a second mileage check from the latest confirmed full tank, so that intervening partial transactions do not move the comparison point.

#### Acceptance Criteria

1. WHEN a vehicle has a submitted, non-cancelled fueling record confirming a full tank THE system SHALL use the most recent such record’s actual odometer reading and fueling date and time as the new check’s baseline; a later confirmed full tank SHALL replace the earlier baseline.
2. WHEN the new check has a baseline and a usable economy average THE system SHALL compare request distance from that baseline with expected distance using the existing configured mileage margin, where estimated remaining litres equal tank capacity multiplied by current gauge percent and divided by 100, estimated fuel consumed equals tank capacity minus estimated remaining litres, and expected distance equals the applicable economy average times estimated fuel consumed; the applicable average SHALL use the recent average from up to five completed full-to-full vehicle intervals when available and otherwise use the vehicle target.
3. WHEN partial fueling records occur after the baseline THE system SHALL keep their odometer readings from replacing that baseline and, per the requester’s decision, SHALL NOT add their litres to the new check’s estimated fuel consumed.
4. WHEN no submitted, non-cancelled full-tank baseline exists THE system SHALL skip the new check and leave all existing checks unchanged; WHEN a baseline exists but no usable recent average or vehicle target exists THE system SHALL show a distinct red “cannot calculate” reason, while the existing mileage check keeps its current behavior.
5. WHEN the new check is shown THE system SHALL let users and approvers inspect the selected baseline source, reading, date and time, current reading, fuel estimate, expected distance, economy source, and margin, and SHALL preserve the baseline and result used when the order is approved.
6. WHEN a generator order is checked THE system SHALL skip both vehicle odometer mileage checks and SHALL continue to apply the existing generator checks.

#### Worked examples for the new check

Use a vehicle with a 60-litre tank, a 10 km/L applicable average, and a 15% mileage margin. These examples describe the new check only; other signal reasons can still make an order red.

- **Example 1 — Full-tank baseline, no later partial fueling:** baseline 10,000 km; current reading 10,300 km; gauge 50%. Remaining fuel is estimated at 30 L, estimated consumption is 30 L, expected distance is 300 km, and the new check passes.
- **Example 2 — Partial fuelings do not reset or add to the estimate:** baseline 10,000 km; partial records at 10,200 km for 10 L and 10,400 km for 15 L; current reading 10,450 km; gauge 50%. The baseline remains 10,000 km, partial litres are excluded, estimated consumption is 30 L, expected distance is 300 km, and 450 km is 50% above expected, so the new check is red.
- **Example 3 — A newer full tank becomes the baseline:** an older full tank is at 10,000 km, a later partial record is at 10,400 km, and a newer full tank is at 10,800 km; current reading is 10,915 km; gauge 80%. The new baseline is 10,800 km; expected distance is 120 km and the 115 km distance is within the margin, so the new check passes.
- **Example 4 — No full-tank history:** the new check is not applied, even if a partial record or approved order supplies the existing Previous Entry; the old check follows its unchanged Previous Entry rules.
- **Example 5 — A cancelled later full tank:** a valid full-tank baseline is at 10,000 km and a later full-tank record at 10,500 km is cancelled; with a current reading of 10,300 km and gauge 50%, the baseline remains 10,000 km and the new check passes at 300 km expected.
- **Example 6 — At and beyond the margin:** with 300 km expected, distances of 255 km and 345 km are exactly 15% below or above expected and pass; 254.97 km and 345.03 km are just beyond the margin and fail.
- **Example 7 — The old and new checks differ:** baseline 10,000 km; a partial record at 10,250 km for 20 L; current reading 10,550 km; gauge 50%. The old check uses the previous reading of 10,250 km and sees 300 km against 300 km expected, so its mileage reason does not fail. The new check uses 10,000 km and sees 550 km against 300 km expected, so it adds its separate red reason.
- **Example 8 — Generator:** a generator has an hour-meter reading but no vehicle odometer or gauge. Neither vehicle mileage check applies.
- **Example 9 — No usable economy average:** if a full-tank baseline exists but neither recent average nor vehicle target gives a usable positive km/L value, the new check adds a red reason that says it cannot calculate the comparison; it does not invent an expected distance.

### Requirement 5: A durable issue and action history

**User Story:** As a Fleet User, Fleet Approver, or fleet administrator, I want each issue and decision to keep its original facts and outcome, so that I can understand what was known and decided later.

#### Acceptance Criteria

1. WHEN a saved signal first reports an issue or its relevant readings or limits change THE system SHALL add a new history entry containing the issue, source readings, comparison values, applicable limits, source record, actor, time, and any evidence attached at that point, without changing earlier entries; identical repeated saves SHALL NOT create duplicate entries.
2. WHEN an order is sent for sign-off, approved, rejected, or withdrawn THE system SHALL retain a separate action entry with the actor, time, and explanation or reason when required, and SHALL link any red issue to its explanation and decision; WHEN a later saved signal no longer reports an open issue THE system SHALL record its resolution without replacing the original issue entry; WHEN a Partial authorization is decided THE system SHALL retain its reason separately from red-order explanations and decision reasons.
3. WHEN an order or actual-fueling record is cancelled THE system SHALL require and retain a cancellation reason, actor, time, and the source facts needed to understand the cancellation, without changing who is allowed to cancel.
4. WHEN a validity extension or slip print occurs THE system SHALL retain a separate event for each action, including the actor, time, reason where required, and applicable slip revision.
5. WHEN a fueling record is submitted THE system SHALL keep the linked trail to its actual fueling time and source, odometer or hour meter, litres, station, invoice identifiers, attendant, and signed documents, and SHALL preserve those submitted source values.

## Sample data

Use the existing disposable test-site people, vehicles, generators, fueling history, and role accounts. Do not add demonstration or production records.

## Confirmed gaps kept for separate approval

- The app does not compare invoice totals or printed unit prices with litres, and it has no cost fields. Duplicate invoice and tax-device identifiers are checked today.
- The app does not mark a fueling as late under the planned working-hour rule. It currently refuses a fueling time outside the approved order’s validity window.
- Meter resets are not recorded. A lower submitted reading is refused, and historical mileage intervals are not restarted after a reset.
- Cancellation reasons are not required today. This specification proposes to add them as part of the durable history phase without changing cancel permissions.

Invoice discrepancy handling, late-entry rules, meter resets, and cost fields are not included in this implementation unless separately defined and approved.

## Working assumption for review

The history records an issue when a reason first appears in a saved result or when that issue’s captured readings or limits change. Re-saving an unchanged result does not add a duplicate. A later result that clears the issue records its resolution.

## Out of scope

- Changing who may enter or decide an order, the existing location restrictions, or the current approval and rejection policy.
- Changing the existing “Mileage does not add up” calculation or its behavior.
- Adding invoice discrepancy rules, late-entry behavior, meter resets, or invoice cost fields.
- Changing the printed approval-slip layout or the station’s fueling process.

## Proposed phases for review

1. **Entry form:** arrange the four sections, vehicle summary, conditional gauge and quantity fields, and partial-authorization reason.
2. **Signal panel:** add the single server-backed live preview and explain the existing signal reasons with their readings, comparisons, limits, and next actions.
3. **Full-tank check:** add the separate baseline calculation, visible source and result, approved snapshot, and the worked boundary cases.
4. **History:** add durable issue and action events, cancellation reasons, extension and print records, and the link to the actual fueling record; keep the listed invoice, late-entry, meter-reset, and cost gaps out of scope.

## Open questions

None. The requester's answers are recorded above; the history timing is stated as a working assumption for approval.
