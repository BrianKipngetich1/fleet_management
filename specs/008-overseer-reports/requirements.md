<!--
What the requester needs, in their own business words (Kiro's requirements.md). Written in
step 1 of the Kaysalt workflow and approved before design starts. Audience: the requester and
an agent resuming cold.

Business language only: no DocType, field, file, or function names. Acceptance criteria are
numbered within their requirement and cited as N.k. Never renumber; retire by replacing text
with "Removed: <reason>".

The approval line is written only after an explicit "approve" and reset to pending whenever
this file changes.
-->

# Fleet Oversight Reports: requirements

Approved by: pending

| | |
|---|---|
| Tier | Heavy |
| Branch | feature/008-overseer-reports |

## Introduction

Overseers need one place to review fueling volumes, monthly spending, vehicle efficiency,
requests, warnings, and recorded discrepancies. Today they have to piece this picture together
from individual fuel requests and fueling records. The system will present those needs in no
more than three reports, with figures that can be traced to the records they summarize.

## Requirements

### Requirement 1: Fueling summary and trends

**User Story:** As an overseer, I want to summarize fueling activity and spending over a period I choose, so that I can review changes over time.

#### Acceptance Criteria

1. WHEN an overseer selects a date range in any report THE system SHALL include activity on both selected dates, use the actual fueling date for fueling activity and the event date for requests or decisions, and allow any span across retained records without a 12-month maximum.
2. IF an overseer selects a start date later than the end date THEN THE system SHALL show a clear date-range error and no report totals.
3. WHEN the selected period includes calendar months THE system SHALL group the summary by year and month, include only activity within the selected dates, and show delivered litres and transaction counts.
4. WHEN staff record a completed fueling THE system SHALL record the invoice amount and any unit price printed on the invoice; WHEN the summary reports spending THE system SHALL total recorded invoice amounts in KES, show the calculated price per litre and any printed price separately, and show older records without an amount as unavailable without estimating them.
5. WHEN an overseer filters by location, asset, fuel type, or station THE system SHALL apply the same filters to summary figures, trends, detail rows, and exports.
6. WHEN the reports are presented THE system SHALL provide no more than three separate reports for the requested oversight needs.

### Requirement 2: Asset performance and fueling history

**User Story:** As an overseer, I want to review a vehicle's fueling requests and performance, and a generator's delivered fuel and operating hours, so that I can compare activity by asset.

#### Acceptance Criteria

1. WHEN an overseer selects an asset and period THE system SHALL show its related fuel requests and completed fueling records, including dates, requester or driver, fuel, station, requested and delivered quantities, links to their source records, and whether requests are pending, approved, rejected, withdrawn, awaiting fueling, completed, expired, or cancelled.
2. WHEN the system reports vehicle efficiency THE system SHALL calculate it from distance and qualifying litres between full fills, include partial fills, and rate the difference from target as green within 10 percent, orange above 10 through 20 percent, or red beyond 20 percent above or below target.
3. WHEN a vehicle interval needs an earlier full fill outside the selected period THE system SHALL use that fill in the calculation while keeping displayed activity within the selected period; WHEN no valid interval exists THE system SHALL show efficiency as unavailable; WHEN the target changed within the interval THE system SHALL show the efficiency without a rating.
4. WHEN an overseer reviews a generator THE system SHALL show delivered litres and operating hours and SHALL NOT label delivered litres as fuel consumed.

### Requirement 3: Requests, flags, discrepancies, and audit

**User Story:** As an overseer, I want to review request decisions, system warnings, and staff-recorded discrepancies, so that exceptions are clear and traceable.

#### Acceptance Criteria

1. WHEN a fuel request is rejected or withdrawn THE system SHALL show the action, written reason, decision-maker, and decision date while distinguishing rejection from withdrawal.
2. WHEN a fuel request has a system warning THE system SHALL show its warning status, recorded reasons, and request date.
3. WHEN staff identify one or more fueling discrepancies THE system SHALL let them record each type, details, reason, recorder, and date against the related fueling record and show those details in the report; WHEN an older fueling record has no discrepancy entry THE system SHALL show that no discrepancy was recorded without implying that none occurred.
4. WHEN a fueling record is cancelled THE system SHALL exclude it from fueling, performance, and spending totals and retain it in the audit report with its cancellation status.

### Requirement 4: Location access and traceability

**User Story:** As an overseer, I want reports limited to locations I am allowed to see and figures linked to their records, so that I can review them without losing access controls or context.

#### Acceptance Criteria

1. WHEN a user views any report THE system SHALL show only records and totals for locations that user is permitted to access.
2. WHEN a user exports report details THE system SHALL preserve the user's location access and selected report filters.

### Requirement 5: Unchanged behaviour

**User Story:** As a staff member, I want the current request and fueling process to keep working, so that reporting does not disrupt operations.

#### Acceptance Criteria

1. WHEN staff create, approve, reject, or complete fuel requests THE system SHALL CONTINUE TO apply the existing approval, evidence, and location-access rules.

## Out of scope

- Actual generator fuel consumption; this feature reports delivered litres and operating hours only.
- More than three report entries or new cross-location access for existing users.

## Open questions

None. The requester confirmed generator reporting, spending, and discrepancy recording on 02/10/2026.
