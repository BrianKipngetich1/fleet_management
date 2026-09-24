<!--
The proof document. Scaffolded 2026-09-24 when the specification was re-phased (D-16).
Most of this phase was built and exercised under the wider 2026-09-18 Phase 0; that evidence
is carried here as the starting position and must be rerun on MariaDB before closure.
-->

# Phase 1 — Location access

| | |
|---|---|
| Specification | [`../spec.md`](../spec.md) @ `07bf479` (D-16) |
| Status | In progress — built by Phase 0; rerun outstanding |
| Started / Closed | 2026-09-24 / — |
| Author | Fleet Management team |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | AC-02 |
| Credential inventory | `verification/CREDENTIALS.md` — Phase 0 QA users reused |

## What this phase makes true

People see and act only on records for the locations they are permitted. A Fleet User can
request fuel only for assets at their permitted locations. Someone from another location
cannot list, open, report on, print, or act on those records by any route.

## Build state by criterion

| Verification row | State | Exact existing test(s) / evidence |
|---|---|---|
| 1 — permitted-location lists | Built by Phase 0; no dedicated Fleet Asset list assertion | `fleet_management/tests/test_permissions.py::test_list_query_is_limited_to_permitted_location`; `fleet_management/tests/test_permissions.py::test_list_and_direct_access_are_location_scoped`; `fleet_management/tests/test_permissions.py::test_fleet_user_can_request_location_list_without_report_permission`; `fleet_management/fleet_management/doctype/fueling_transaction/test_fueling_transaction.py::test_location_permissions_filter_and_block_out_of_location_access`; Playwright `e2e/tests/tenancy.spec.ts::the scoped list shows only the user's permitted records` |
| 2 — direct access and actions | Built by Phase 0 | `fleet_management/tests/test_permissions.py::test_direct_access_denies_other_location_for_all_document_actions`; `fleet_management/tests/test_permissions.py::test_list_and_direct_access_are_location_scoped`; `fleet_management/fleet_management/doctype/fueling_transaction/test_fueling_transaction.py::test_location_permissions_filter_and_block_out_of_location_access`; Playwright `e2e/tests/acceptance.spec.ts::live Desk transaction acceptance covers evidence, KPI, integrity, and scope` |
| 3 — report, print, and report permission | Built by Phase 0 | `fleet_management/tests/test_permissions.py::test_approver_can_report_and_print_only_permitted_orders`; `fleet_management/tests/test_permissions.py::test_fleet_user_can_request_location_list_without_report_permission`; `fleet_management/tests/test_permissions.py::test_restricted_query_report_remains_denied`; Playwright `e2e/tests/acceptance.spec.ts::live Desk transaction acceptance covers evidence, KPI, integrity, and scope` |
| 4 — user without a permitted location | Built by Phase 0 | `fleet_management/tests/test_permissions.py::test_list_query_denies_user_without_a_location` |
| 5 — asset choice and order creation | Built by Step 2 | `fleet_management/tests/test_permissions.py::test_fleet_user_can_create_orders_only_for_permitted_assets`; `fleet_management/tests/test_permissions.py::test_fleet_admin_can_create_orders_for_any_location` |
| 6 — planned-station choice and validation | Built by Step 2 | `fleet_management/tests/test_permissions.py::test_planned_station_must_match_operational_location`; `fleet_management/public/js/fuel_order.js::setup` filters the planned-station picker by operational location, active, and approved |
| 7 — Fleet Admin unrestricted access | Built by Phase 0 | `fleet_management/tests/test_permissions.py::test_fleet_admin_is_unrestricted` |

## The rule, as observed

Not yet observed in this phase. Access scope adds no state edges; it filters who may take the
Phase 0 and Phase 3 edges.

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why |
|---|---|---|
| Location scope on lists and links | User Permission on Fleet Location; `permission_query_conditions` | Query conditions follow the asset's effective assignment, which User Permission alone cannot |
| Asset choice during order creation | Linked-document `has_permission` hook plus controller validation | The create path did not reject the selected out-of-location asset, so Fuel Order validation enforces the server-side rule |
| Direct document access | `has_permission` hook | Same location rule for read, write, print, submit, cancel |
| Reports | Report permissions | Report view stays denied without report permission; list access does not require it |
| Planned station picker | Link-field `set_query` in `fleet_management/public/js/fuel_order.js` | Frappe's native dependent query filters operational location, active, and approved; server validation remains authoritative |

## Verification

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | Two locations; a Fleet User and an Approver permitted only for location A. List Fuel Orders, Fueling Transactions, Fleet Locations, and Fleet Assets | Only location A records appear | AC-02 |
| 2 | As the location A users, open a location B order and transaction by direct URL; try read, write, print, submit, cancel | Every action is denied | AC-02 |
| 3 | As the location A Fleet User, open the list without report permission, then a restricted report; as the Approver, open reports and print | List loads; restricted report denied; Approver reports and prints only location A orders | AC-02 |
| 4 | As a Fleet User with no permitted location, open the lists | Nothing is listed | AC-02 |
| 5 | As the location A Fleet User, pick the asset on a new order | Only assets assigned to location A are offered and accepted | AC-02 |
| 6 | Pick a planned station outside the order's operational location, in the picker and via direct save | Not offered; refused on save | AC-02 |
| 7 | As Fleet Admin, repeat rows 1–2 | All locations visible and actionable | AC-02 |

**How to run it.** Run `bench --site fleet_management-test.localhost run-tests --module fleet_management.tests.test_permissions`
for the permission tests named in rows 1–7, and the Fueling Transaction module for
`test_location_permissions_filter_and_block_out_of_location_access`. Run `npm run test:ui` for
the named `tenancy.spec.ts` and `acceptance.spec.ts` tests. A MariaDB `agent-browser` walkthrough
as the location A and B users is required.

**Result:** Not yet run in this phase. Rows 1–4 and 7 passed under Phase 0 (SQLite gate
2026-09-23; MariaDB suites 2026-09-24).

## What we learned that the plan did not predict

- A custom request guard once treated ordinary Desk list calls as reports and demanded report
  permission (Phase 0 escalation, repaired). Keep list and report permission separate.

## Known limitations — accepted, not fixed

- None yet.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|
| 1 | — | — | — |

**Closure:** Open.

**Next:** STEP 3 — rerun rows 1–7 on MariaDB
