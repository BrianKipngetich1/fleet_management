<!--
What the requester needs, in their own business words (Kiro's requirements.md). Written in
step 1 of the Kaysalt workflow and approved before design starts. A bug uses
TEMPLATE-bugfix.md instead. Audience: the requester, who may be non-technical, and an agent
resuming cold.

Business language only: no DocType, field, file, or function names, and no snake_case.
Acceptance criteria are numbered within their requirement and cited as N.k (criterion 2 of
Requirement 1 is 1.2). Never renumber: retire a criterion by replacing its text with
"Removed: <reason>". Every criterion is cited by a task in tasks.md.
`scripts/spec-check.py` enforces all of this.

The approval line is written only after an explicit "approve" and reset to `pending`
whenever this file changes.
-->

# Import the fleet's master lists and load the company's real fleet: requirements

Approved by: pending

| | |
|---|---|
| Tier | `Heavy` |
| Branch | `feature/006-master-data-import` |

## Introduction

The owner wants to collect the company's real master lists (locations, fuel types, vehicle
models, people, fuel stations, and the vehicles and generators with who holds them) in Excel
templates taken from the system, fill them in, and load them back. Today the system refuses
to start an import for any of these lists, so no template can be downloaded either.

The templates are now filled in (07/10/2026). The company wants that real fleet, not the
invented one, to be the starting data on the main site and the fixed data every rebuilt test
site starts from. The vehicles belong to two companies, Kabete and Kanha, and all of them fill
up at one station, Ecoflame Limited; today a station can serve only one location, so no
Kabete or Kanha vehicle could be sent to Ecoflame for both. The people who enter and approve
orders also change: Phyllis enters orders and Vishal signs off the ones that turn red.

## Requirements

### Requirement 1: Import the master lists

**User Story:** As a system administrator, I want to download a blank Excel
template for each master list and import the filled-in file, so that the real master data can
be loaded without typing each record by hand.

#### Acceptance Criteria

1. WHEN a system administrator starts an import for locations, fuel types,
   vehicle models, people, fuel stations, or vehicles and generators THE system SHALL accept
   it and offer a blank Excel template for that list.
2. WHEN a filled-in template is imported THE system SHALL create each record under the same
   rules as creating it by hand, and SHALL report every row it refuses and why.
3. WHEN the vehicles and generators template is filled in THE system SHALL accept each
   vehicle's holder history (holder, home location, from and until dates) in the same file.

### Requirement 2: Unchanged behaviour

**User Story:** As a Fleet User or Fleet Approver, I want everything else to work as before, so
that the import does not change who may do what.

#### Acceptance Criteria

1. WHEN a Fleet Admin, Fleet User, or Fleet Approver looks for the import tool THE system
   SHALL CONTINUE TO refuse it, as today; only a system administrator imports.
2. WHEN anyone looks for an import of fuel orders or fuellings THE system SHALL CONTINUE TO
   refuse it, so every order and fuelling still goes through approval.
3. WHEN the server and browser tests run THE system SHALL CONTINUE TO pass as before.
4. WHEN an order names a station that does not serve the vehicle's company THE system SHALL
   CONTINUE TO refuse it.
5. WHEN Phyllis's order turns red THE system SHALL CONTINUE TO need her written reason and
   Vishal's sign-off; a green order she approves herself.

### Requirement 3: The company's real fleet is the starting data

**User Story:** As the fleet owner, I want the main site and every rebuilt test site to start
from the company's real fleet, so that people try and test the system with the vehicles,
people, and station they know.

#### Acceptance Criteria

1. WHEN the starting data is loaded THE system SHALL hold the two companies Kabete and
   Kanha, the fuel types Diesel and Petrol, the 14 vehicle models, the people, the fuel
   station Ecoflame Limited, and the 15 vehicles and generator listed under "Sample data",
   each vehicle held by its listed person at its listed company from 01/09/2026.
2. WHEN the test site is rebuilt THE system SHALL load exactly the same master lists, every
   time.
3. WHEN the starting data is loaded on the main site THE system SHALL add only what is
   missing and SHALL leave every record already there unchanged, so later corrections made
   by hand are kept.
4. WHEN the starting data is loaded THE system SHALL apply the owner's corrections listed
   under "Sample data" (one Dennis Kamau, corrected spellings, the Isuzu ELF model name, the
   generator and crane holders, sizes, and targets, 10% tolerance), so no record carries the
   templates' mistakes.
5. WHEN a fleet administrator later changes a vehicle's tolerance, target, or tank size THE
   system SHALL keep the change on the main site.

### Requirement 4: One station serves both companies

**User Story:** As Phyllis, I want to send a Kabete or a Kanha vehicle to Ecoflame, so that the
order matches where every company vehicle actually fills up.

#### Acceptance Criteria

1. WHEN an order for a Kabete or a Kanha vehicle names Ecoflame Limited THE system SHALL
   accept the station.
2. WHEN a fleet administrator sets up a station THE system SHALL let them choose every
   company it serves.
3. WHEN an approved order's slip is printed THE system SHALL show Ecoflame's postal address
   (P.O. Box 818 – 00606 Nairobi) and email (ecoflamelimited@gmail.com).

### Requirement 5: Phyllis, Vishal, and who sees what

**User Story:** As the fleet owner, I want Phyllis and Vishal to work on both companies'
vehicles, so that the people in the system are the people doing the work.

#### Acceptance Criteria

1. WHEN Phyllis signs in THE system SHALL let her enter orders for every Kabete and Kanha
   vehicle, and SHALL name her as each company's representative on the order.
2. WHEN Phyllis sends up a red order THE system SHALL put it in Vishal's queue for either
   company.
3. WHEN the test-only Kanha approver signs in on the test site THE system SHALL show only
   Kanha's vehicles and orders, never Kabete's.
4. WHEN Phyllis picks a vehicle on an order THE system SHALL accept its holder as the driver.

## Sample data

People and logins:

- Phyllis (Fleet User): enters orders and is the company representative for Kabete and Kanha;
  holds the KLW generator and the mobile crane. Main site `fleet.user@example.com`, test site
  `phyllis.test@example.com`.
- Vishal (Fleet Approver): signs off Phyllis's red orders for both companies. Main site
  `fleet.approver@example.com`, test site `vishal.test@example.com`.
- Kanha approver (Fleet Approver, test site only): sees Kanha only, so the checks can prove
  one company's orders stay hidden from the other.
- Holders: Mrs. Danbhai Kanji, Dennis Kamau (one person, four vehicles), Amrat Deepak Patel,
  Deepak Kanji Patel, Joseph Wakhungu, Harish Kumar, Vinu Pindoria, Mukesh Singh, Sanjeev
  Modi, Mr. Kanji K. Patel. Each holder drives the vehicle they hold.

Companies: Kabete and Kanha. Station: Ecoflame Limited, serving both.

| Vehicle | Model | Fuel | km/L | Holder | Company |
|---|---|---|---|---|---|
| KAY222A | Toyota Avensis | Petrol | 8 | Mrs. Danbhai Kanji | Kabete |
| KBD159W | Toyota Fortuner | Petrol | 6 | Dennis Kamau | Kanha |
| KBR136G | Isuzu ELF PB-NPR81AN | Diesel | 6 | Dennis Kamau | Kanha |
| KBX093J | Toyota ZSA42R | Petrol | 7 | Amrat Deepak Patel | Kabete |
| KCL225R | Toyota Rav4 | Petrol | 7 | Deepak Kanji Patel | Kabete |
| KCL966X | Toyota Axio | Petrol | 10 | Joseph Wakhungu | Kanha |
| KCV927J | Toyota Axio | Petrol | 10 | Dennis Kamau | Kanha |
| KDD516Z | Toyota Hilux | Diesel | 7 | Harish Kumar | Kanha |
| KDE169V | Toyota Starlet | Petrol | 10 | Vinu Pindoria | Kanha |
| KDE189V | Toyota Starlet | Petrol | 10 | Mukesh Singh | Kanha |
| KDG173X | Toyota Urban Cruiser | Petrol | 10 | Sanjeev Modi | Kanha |
| KDK039L | Isuzu NMR | Diesel | 6 | Dennis Kamau | Kanha |
| KDQ111J | Lexus LX600-3BA-VJA310W | Petrol | 7 | Mr. Kanji K. Patel | Kabete |
| KLW-Generator | GEN 45KVA/36KW, generator, 100 L tank, 100 L most per order | Diesel | n/a | Phyllis | Kabete |
| MobileCrane | Locatel KZL284, vehicle, 100 L tank | Diesel | 2 | Phyllis | Kanha |

Every vehicle: 10% tolerance, held from 01/09/2026. Tank and engine sizes come from the
vehicle models template; the Land Cruiser model is listed but no vehicle uses it. The crane's
2 km/L is an estimate (no official record found), to be corrected from its fuelling history.

## Out of scope

- Past fuelling history: it is loaded into the test site by the sample-data script, not by
  import, because each order must pass approval, photos, and sign-off. Until Phyllis's real
  September 2026 fill-ups exist, the test site has no fuelling history, so it shows no
  ready-made red examples or waiting, rejected, or expired orders.
- Copying Phyllis's 01/09/2026–30/09/2026 fill-ups from the main site into the test data: a
  later phase, once she has entered them.
- Anything only in the company's old Master workbook (the Land Cruiser KAZ992R, the second
  block of vehicles, colour, year of make, tracking status).
- KSL-Westlands: it holds no vehicles.
- Ecoflame's PIN: the system has no place for a station's PIN; noted for the slip work in
  010.
- Defaulting the driver and requester to the holder on the order form: built on the order-form
  branch (009), not here.
- The company rules page: it has a single set of values with nothing to import.
- The planned order-form automation (no driver field, requester and custodian from the
  vehicle, default company representative, fixed location and station, partial litres shown
  only for a partial fill), and a place in the system for the generator tank size and
  per-order maximum: a later specification.
- Letting a Fleet Admin import without system administrator rights.
- An Export item in each list's menu (asked 30/09/2026, not urgent).

## Open questions

None.
