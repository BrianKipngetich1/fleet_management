<!--
The proof document. Scaffolded 2026-09-25 with the specification; filled in as the phase is
verified, from what was actually observed. Procedure, not transcript. Never record credentials.
-->

# Phase 0 — Company fuel order slip

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `3c37dbb` |
| Status | Built — awaiting Stage C |
| Started / Closed | 2026-09-25 / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-01, AC-02, AC-03 |
| Credential inventory | `verification/CREDENTIALS.md` (gitignored, mode 0600) |

## What this phase makes true

An Approver who prints an approved Fuel Order gets a page that reads like the company's paper fuel order slip: the company heading, the order number and date, the station's address, the litres and fuel to supply, the vehicle's registration and meter reading, and the name of the person who authorised it. Everything the earlier slip had to show — validity, the attendant instruction, and the signature lines — is still on the page.

## The rule, as observed

Not yet observed in this phase.

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Company heading from the site Letter Head | Letter Head | — |
| Station postal address and email | Address linked to Fuel Station | — |
| Slip layout | Jinja Print Format | — |
| Station address on its form | HTML field rendered by Frappe's address list (`load_address_and_contact`) | — |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Build the test site. As Test Fleet Admin, open the Letter Head list | "Krystalline Salt Fuel Order Slip" is the default; its heading reads KRYSTALLINE SALT LIMITED, PIN NO. P000000000T, a P.O. Box, telephone, and email — all synthetic | AC-01 |
| 2 | As Test Fleet Admin, open Fuel Station "Mombasa Road Service Station" | An Address section lists its postal address (P.O Box 10001, 00100, Nairobi) and email mombasa-road.test@example.com; the other five stations each show their own | AC-01 |
| 3 | A default Letter Head exists; a vehicle order at a station with a primary postal address is approved full-tank; print the slip with and without the letter head | With it: COPY TO BE ATTACHED WITH STATEMENT, FUEL ORDER SLIP, the heading, No. and Date (dd/mm/yyyy), the station name, "P.O Box … – postcode TOWN" and email, "Please supply FULL TANK Ltrs of <fuel>", "to the following motor vehicle", Reg No and speedometer, NAMES OF AUTHORISED PERSON, a company stamp box; the slip CSS sets A5 portrait. Without it: no heading | AC-01 — `test_approved_slip_reads_like_the_company_paper_slip` |
| 4 | Approve a partial order for 42.5 L at a 40% gauge and print it | The footer still shows the quantity basis, gauge, estimated litres, location, station, fuel, meter reading, approver, approval timestamp, the exact valid-until, the attendant instruction, the do-not-dispense warning, and all four signature lines | AC-02 — `test_approved_print_contains_ac04_fields_and_instruction` |
| 5 | An approver whose full name is "Vikas Test Approver" approves an order; print it | His full name is on the authorised-person line and the signature line; his login id appears nowhere on the page | AC-03 — `test_slip_names_the_authorised_person_by_full_name` |
| 6 | As Vikas, open the approved KDA 412M order (52,650 km, 21%) and print it with the default letter head; save it as PDF | One A5 portrait page that reads like the owner's paper slip: Krystalline heading, Mombasa Road Service Station with its P.O. Box and email, FULL TANK of Diesel, Reg No KDA 412M, speedometer 52650, "Vikas" as authorised person, stamp box, footer with validity, instruction, and signature lines | AC-01, AC-02, AC-03 |
| 7 | As Vikas, print the approved GEN-NRB-01 order | "Please supply UP TO 200 Ltrs", "to the following generator", "hour meter" 1283.5; no gauge or estimated litres in the footer | AC-01, AC-02 |

**How to run it.** Backend rows: `bench --site fleet_management-test.localhost run-tests --app fleet_management`.
Desk rows: `agent-browser` walkthrough on the test site as the named role.

**Result:** not yet run.

## What we learned that the plan did not predict

## Known limitations — accepted, not fixed

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|

**Closure:** —

**Next:** —
