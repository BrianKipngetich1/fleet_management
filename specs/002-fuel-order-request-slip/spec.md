<!--
The design document. Written before implementation, from the user's request.
Audience: a human deciding whether this is the right thing to build, and an agent
resuming cold who must not relitigate settled decisions.

Business-functional language above "Current state": name an actor, an action, and an
outcome. No file paths, no function names, no field names in the human-facing sections.
Keep the whole file under ~400 lines for its entire life.
-->

# Fuel Order request, signal, and slip

| | |
|---|---|
| Status | Draft |
| Owner | Fleet Management team |
| Started | 2026-09-25 |
| Approved by / date | — |
| Approved revision | — |
| Branch | spec/002-fuel-order-request-slip |

## Problem

A request to fuel a vehicle reaches the person who enters fuel orders. Today he picks a generic
asset and re-enters facts the system already knows, sees no earlier reading to compare against,
and types meter and gauge readings with no proof. Nothing tells him whether the request adds up.

Every order then needs a second person to approve it, even an ordinary one, while a suspicious
order looks the same as an ordinary one. There is no route that sends only the doubtful orders
to a higher authority. The printed slip does not look like the company fuel order slip that
stations and the statement reconciliation already recognise.

## Goal

Two sample people are used throughout this document and its tests:

- **Philip** enters fuel orders and decides them. A request reaches him to fuel a vehicle — a
  full tank or a number of litres. He picks the vehicle by registration number, sees what the
  system knows about it, types the current meter reading and gauge, attaches a photo of each,
  and enters the quantity. The system colours the order green or red and says why.
- **Vikas** is the higher authority. He never enters orders. He sees only the red orders
  Philip sends up with an explanation, and approves or rejects each with a reason.

Philip approves a green order himself. He can reject any order, whatever its colour. The printed
slip looks like the company's paper fuel order slip and names whoever approved it.

## Decisions (locked)

- D-1 — This specification extends 001. 001's slip content (validity, instruction, quantity
  basis, signatures), hard blocks, snapshots, and full-tank-or-exact-litres rule (with a reason
  for exact litres) all still apply. It **overrides** 001 on four points only: the person who
  entered a green order may approve it (001 D-5, AC-03); a green order has no waiting stage and
  sends no "waiting for approval" notice (001 AC-23); the slip names the person who approved
  (001 AC-04); the test site is disposable (001 D-15, see D-14). Chosen over adding phases to
  001, which is already past its length limit.
- D-2 — 001 is parked at its Phase 1 while 002 is built (owner, 2026-09-25).
- D-3 — The order number and request date are set by the system and cannot be edited; the request
  date is when the order was first saved. Chosen over an editable, back-datable date.
- D-4 — Philip chooses the vehicle by registration number; the choice list also shows its make
  and model and can be searched by either. What the system holds about the vehicle is filled in
  and cannot be changed: make and model, fuel type, tank size, target and average kilometres per
  litre, custodian, and home location. The usual driver, the location it is fuelling at, and —
  when that location has exactly one approved station — the station are suggested but may be
  changed. Philip types who made the request, the company representative, and the quantity:
  full tank, or an exact number of litres with a reason (001 D-2).
- D-5 — Previous Entry is the meter reading and date of the vehicle's last completed, not
  cancelled fueling. When the vehicle has never been fuelled it falls back to the last approved
  order's reading; when neither exists it reads "none" and the distance checks are skipped.
  Chosen over the last fuel order, which may never have been fuelled.
- D-6 — Current Meter Reading and Current Gauge (%) are typed by Philip, and each needs a photo
  attached before the order can be approved or sent up. Photos are private JPG or PNG files,
  checked the same way as the signed fueling evidence. Generator orders need the meter photo only.
- D-7 — A vehicle's average mileage is its own kilometres per litre over its last five completed
  fill-to-fill intervals (total distance ÷ total litres), after any meter reset. Until it has one
  interval, its target is used. Chosen over the target alone (owner: judge against the vehicle's
  own average).
- D-8 — The colour is worked out by the system, never chosen by a person. An order is **red** when
  any check below fails and **green** otherwise, and it lists every check that failed. Limits are
  settings a Fleet Admin can change; the starting values are the owner's.
  1. **Mileage does not add up** — the distance since Previous Entry differs from what the fuel
     used should have covered (average mileage × litres the gauge says were used) by more than
     the mileage margin, initially 15% (owner's range 10–15%). A meter that did not move or went
     backwards always fails.
  2. **More litres than the tank has room for** — a litres request exceeds the room the gauge
     shows by more than 10% of the tank size. A full-tank request skips this.
  3. **Tank nearly full** — the gauge is above 75%.
  4. **Open order exists** — the vehicle has another order waiting for Vikas, or approved and
     neither fuelled, expired, nor cancelled.
  5. **Too soon since the last fueling** — fewer than 24 hours since its last completed fueling.
  6. **Away from home** — it is fuelling at a location other than its home location.
  7. **Not the usual driver** — the driver named is not its usual driver (skipped when it has none).
  8. **Mileage off its own trend** — its last completed interval's kilometres per litre differs
     from its average mileage by more than the mileage margin (needs two intervals).
  Generators use checks 4, 5, and 6 only. New checks are added by amending this list.
- D-9 — Two people, two existing roles, no new role. Philip holds the order-entry role (Fleet
  User), Vikas the approver role (Fleet Approver); Fleet Admin keeps master data only. Chosen over
  a separate green-order approver and a new higher-authority role (owner, 2026-09-25).
- D-10 — Philip decides every order he enters. Green: he approves it and it is ready to print; if
  the colour has turned red by the time he approves (for example another order for the vehicle
  was just approved) the approval is refused. Red: he rejects it, or sends it to Vikas with a
  written explanation of why it is genuine. Any colour: he may reject it with a reason, including
  one already waiting for Vikas.
- D-11 — Vikas approves or rejects each order Philip sends up, with a written reason, for his
  permitted locations only. He cannot decide an order he entered or asked for himself. Vikas and
  fleet administration are told once each when an order is sent up; Philip is told the outcome.
- D-12 — The printed slip follows the layout of the company's paper fuel order slip. Its
  "authorised person" is whoever approved it — Philip for green, Vikas for red — printed by full
  name. It fits one A5 portrait page.
- D-13 — The company heading (name, PIN, postal address, telephone, email) and each station's
  postal address and email are site data maintained by a Fleet Admin, not written into the app.
  The test site uses synthetic values only.
- D-14 — Testing uses a disposable test site built for each test session from fixed sample data
  (Philip, Vikas, Amina, the Krystalline Salt locations, real vehicle models, standby generators,
  and two months of history) with the same logins and passwords every time, and thrown away
  afterwards. Every check and walkthrough in this specification is described with that data.
  Chosen over 001 D-15's kept test site (owner, 2026-09-25).

## Current state

As of `develop` @ `b2d5a06` (PR #3: vehicle-model tank capacity, the disposable test site, and
the first 001 Phase 1 location-access work).

- **Fuel Order** form: `naming_series` (one option, `FO-.YYYY.-`) and an editable
  `request_datetime` (default now); `asset` links Fleet Asset with no descriptive search fields;
  `fuel_type`, `custodian`, `driver`, `operational_location`, `planned_station` are editable
  links; the assignment snapshot (`assigned_*`, `asset_*_snapshot`) is read-only and server-set.
  `request_meter_reading` and `request_gauge_percent` are plain inputs with no photo;
  `quantity_authorization` (Full/Partial) and `authorized_quantity_litres` exist. There is no
  previous-reading field and no signal. `estimated_litres` is server-calculated.
- **Fleet Asset**: `asset_identifier` is the registration number and document name;
  `vehicle_model` (make, model, tank capacity) is required for a vehicle. Fleet Location has no
  default-station field. Fuel Station has name, location, active, approved — no address. Asset
  Assignment carries `primary_driver`.
- **Fueling Transaction** stores `vehicle_odometer`, `distance_km`, `qualifying_litres`,
  `km_per_litre` per full-to-full interval — the source for D-7.
- **Workflow** "Fuel Order Approval" (fixture): Draft → Pending Approval (Fleet User) → Approved
  or Rejected (Fleet Approver). Server rules block self-approval against the entering and
  submitting users and the requester's user.
- **Roles** (fixture): Fleet Admin, Fleet Approver, Fleet User. Kept as they are.
- **Slip**: Jinja print format "Fuel Order Approval Slip" (fixture), a label/value table plus
  approval, validity, instruction, and four signature lines; approver shown as a user id.
- **Settings**: Fleet Management Settings holds tolerance, orange/red bands, validity, print
  instruction. None of the D-8 limits.
- **Evidence checks**: Fueling Transaction validates private JPG/PNG/PDF attachments by
  extension and content type.
- **Test harness** (built 2026-09-25 at the owner's request, ahead of this approval):
  `fleet_management/sample_data.py` loads the D-14 data; `bench fleet-test-site up|down` builds and
  removes the test site with logins from the 001 `CREDENTIALS.md`.
- **Reference slip**: the owner's scan, kept locally and untracked, at
  `specs/001-fleet-fuel-management/To Build/F.O (Fuel Order).png`.

## Design

~~~mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Approved: Philip approves a green order
    Draft --> PendingApproval: Philip sends a red order to Vikas with explanation
    Draft --> Rejected: Philip rejects with reason
    PendingApproval --> Approved: Vikas approves with reason
    PendingApproval --> Rejected: Vikas rejects with reason
    PendingApproval --> Rejected: Philip withdraws with reason
    Rejected --> [*]
    Approved --> [*]
~~~

`Approved` is 001's Approved state; its fulfillment sub-states, extension, and cancellation are
unchanged and not redrawn here. `PendingApproval` keeps its existing name and now means "waiting
for Vikas", so orders already pending at cut-over land with the Fleet Approver as today.
Philip's two Draft transitions carry a workflow condition on the colour; the server recomputes
the colour on every save and at every transition, and freezes it with the approval snapshot.
001's self-approval check no longer applies to Philip approving green; it applies in full to
Vikas's decisions.

~~~text
room_litres        = tank_capacity * (100 - current_gauge_percent) / 100
distance           = current_meter_reading - previous_entry_reading
expected_distance  = average_km_per_litre * room_litres
mileage_variance   = abs(distance - expected_distance) / expected_distance * 100

1 red if mileage_variance > mileage_margin_percent or distance <= 0   (skip: no previous entry)
2 red if requested_litres > room_litres + excess_percent/100 * tank_capacity   (litres only)
3 red if current_gauge_percent > gauge_limit_percent        (limit < 100, so expected_distance > 0)
4 red if another open order exists for the asset
5 red if hours_since_last_fueling < min_hours_between_fuelings
6 red if operational_location != assigned_location
7 red if primary_driver and driver != primary_driver
8 red if abs(last_interval_km_per_litre - average_km_per_litre) / average_km_per_litre * 100
         > mileage_margin_percent                           (skip: fewer than two intervals)
~~~

Worked examples. Tank 20 L, average 10 km/L, previous 100 km, now 110 km, gauge empty: room 20 L,
expected 200 km, variance 95% → red on check 1. Tank 60 L, gauge 50%: room 30 L, so a request
above 36 L is red on check 2.

## Frappe-first

| What we need | Native Frappe mechanism | Custom code, and why it is unavoidable |
|---|---|---|
| Vehicle choice showing reg no and model | Link field + Fleet Asset `search_fields` | — |
| Auto-filled read-only vehicle facts | `fetch_from` + `read_only`; existing server snapshot | Home location, custodian, usual driver from the effective assignment (already custom in 001) |
| Automatic number and date | Naming series; `read_only` field set on insert | Server sets request date so a client value is ignored |
| Previous Entry and average mileage | — | Query completed transactions (D-5, D-7) |
| Mandatory photos | `Attach Image` fields | Reuse 001's private-file and type check |
| Colour and reasons | Read-only fields; workflow transition `condition` | The eight checks (D-8) |
| Philip/Vikas routing | Workflow states, actions, allowed roles, conditions | Reason required on send-up and decisions; narrowed self-approval check |
| Limits | Fields on Fleet Management Settings | — |
| Notices for sent-up orders | Notification Log | Reuse 001's location-scoped recipient helper |
| Company heading on the slip | Letter Head | — |
| Station address and email | Address (Dynamic Link to Fuel Station) | — |
| Slip layout | Jinja Print Format | — |

## Tracer bullet plan

Slip first because it is what the owner asked for first and needs no new data. Each phase
keeps 001's full test suite green.

### Phase 0 — Company fuel order slip

The approved slip is re-laid out as the company's paper slip: company heading from the Letter
Head; "COPY TO BE ATTACHED WITH STATEMENT" and "FUEL ORDER SLIP"; No. and Date; the station's
name, postal address, and email; "Please supply … Ltrs of … to the following motor vehicle";
Reg No and speedometer; the authorised person's full name; a stamp box. 001's validity,
instruction, quantity basis, and driver, representative, and attendant signature lines move
into a compact footer.

**Tracer:** an approved order prints and the page reads like the paper slip.

**Acceptance**
- AC-01 — The approved slip shows every element of the paper slip, drawn from the order, its
  station, and the site Letter Head, on one A5 page.
- AC-02 — The slip still carries every item 001 requires (its AC-04 and AC-21), including the
  exact valid-until and the attendant instruction.
- AC-03 — The authorised person is printed by full name, never as a login id.

### Phase 1 — Vehicle-first request with photo evidence

**Tracer:** Philip picks a vehicle by registration number and needs only to type the readings
and quantity, attach two photos, and name the requester and representative.

**Acceptance**
- AC-04 — The order number and request date are system-set and read-only; a client-supplied
  request date is ignored.
- AC-05 — Choosing a vehicle fills in and locks the D-4 facts and suggests the changeable ones.
- AC-06 — Previous Entry shows the reading and date defined in D-5, including both fallbacks.
- AC-07 — An order cannot be approved or sent up without a private, valid photo for each
  required reading; a public or wrong-type file is refused.

### Phase 2 — Green and red signal

**Tracer:** Philip sees a green or red colour on the order and, when red, every reason.

**Acceptance**
- AC-08 — Each D-8 check, failing on its own, turns the order red with its reason; an order
  passing every check is green; a first-ever order is judged on the checks that apply.
- AC-09 — Each limit is read from settings; a value exactly at a limit passes and one just past it
  fails.
- AC-10 — Average mileage uses the last five completed intervals after any reset, and the target
  until one exists.
- AC-11 — The colour is recalculated whenever the order changes and is frozen at approval.

### Phase 3 — Philip decides, Vikas signs off red

**Tracer:** Philip approves his own green order; he sends a red one to Vikas, who approves it
with a reason, and the slip names Vikas.

**Acceptance**
- AC-12 — Philip can approve a green order he entered, and can never approve a red one,
  server-side, including one that turned red while he was working on it.
- AC-13 — Philip can reject any order not yet approved, with a reason, including one waiting for
  Vikas; sending a red order up needs his explanation, and a green order cannot be sent up.
- AC-14 — Only a location-permitted Fleet Approver who did not enter or ask for the order can
  decide a sent-up order, with a reason; Vikas and Fleet Admin are notified once each.
- AC-15 — The slip names Philip for a green approval and Vikas for a red one.

## Out of scope

- Reading values from the photos (OCR) — 001 keeps OCR as a separate workstream.
- Requests stated as a money amount; there is no fuel price list (001 non-goal).
- Meter resets, generator tank levels, and the other open 001 phases; 001 resumes after 002.
- A new role, a fleet-wide higher authority with no location scope, or more than two levels.
- Different limits per vehicle; limits are site-wide settings.
- Moving tank capacity onto Vehicle Model — that is 001 Phase 1 work in progress.

## Risks and assumptions

| Type | Item and treatment |
|---|---|
| Assumption | The last fueling filled the tank. After a litres-only fill, checks 1 and 2 are approximate; the reason text says so. |
| Risk | Gauges are rough, so honest requests may turn red; limits are settings and Vikas's route exists. |
| Risk | A green order has no second person; the colour checks are the control (owner's choice, D-1). |
| Assumption | The site has one Letter Head for the company, set as default. |
| Risk | 001's slip and approval tests assert today's behaviour and will be rewritten in Phases 0 and 3. |

## Progress log

One entry per phase, appended when the phase closes. Link the verification record.
