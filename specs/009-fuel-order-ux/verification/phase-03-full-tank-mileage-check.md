# Phase 3 — Full-tank mileage check

| | |
|---|---|
| Specification | [`../requirements.md`](../requirements.md) @ working tree |
| Status | In progress; baseline lookup and approved source snapshot verified; comparison not built |
| Started / Closed | 2026-10-02 / — |
| Author | Codex |
| Reviewed by | — |
| Signed off | — |
| Landed in | — |
| Covers | Requirements 3.1, 3.2, and 4.1–4.6 |

## What this phase makes true

A vehicle's new mileage comparison starts from its latest submitted, non-cancelled fueling record that confirms a full tank. Later partial transactions neither add litres to the estimate nor replace the baseline. A newer full tank does replace it; no full-tank history skips only this check. The existing Previous Entry comparison remains independent.

## The rule, as observed

```mermaid
stateDiagram-v2
    [*] --> ExistingMileageCheck
    ExistingMileageCheck --> LatestFullTankLookup: vehicle only
    LatestFullTankLookup --> CapturedBaseline: latest submitted full tank
    LatestFullTankLookup --> NoBaseline: no qualifying record or generator
    CapturedBaseline --> SeparateComparison: pending capacity/gauge edge decisions
```

### Design vs. observed

| Specification edge | Observed | Verdict |
|---|---|---|
| `LatestFullTank → NewBaseline` | `test_latest_full_tank_baseline_ignores_partial_and_cancelled_fuelings` checks actual event-time ordering and returns the newer full transaction, actual odometer, and fueling time | Lookup verified; comparison not built |
| `PartialFueling → BaselineUnchanged` | The lookup test places a later partial between the full tanks and confirms the partial does not replace the source | Lookup verified; estimated consumption not built |
| `NoBaseline → NewCheckSkipped` | `get_latest_full_tank_baseline` returns no source without vehicle history | Source lookup verified; signal behavior not yet connected |
| `ApprovedOrder → BaselineAndResultFrozen` | `test_signal_is_frozen_once_approved` checks the saved baseline in raw MariaDB and confirms it stays unchanged after a newer source appears | Baseline snapshot verified; comparison result not built |
| `Generator → VehicleMileageChecksSkipped` | `test_full_tank_baseline_is_missing_without_vehicle_history_or_for_generator` confirms the vehicle-only lookup returns no generator baseline | Lookup verified; signal behavior not yet connected |

## Frappe-first / native-first

| What we needed | Native mechanism used | Custom code, and why it is unavoidable |
|---|---|---|
| Find the full-tank baseline | Submitted Fueling Transaction records and their actual event times | A distinct lookup must filter full-tank confirmations without changing Previous Entry. |
| Calculate expected distance | Existing up-to-five interval average and vehicle target | Add the requested estimated-consumption formula and independent reason. |
| Freeze the approved result | Existing Fuel Order snapshot validation | Add the new server-managed baseline and result fields to its immutable set. |

**Scope deliberately not taken:** Do not change the current mileage check, fueling transactions, generator checks, or vehicle economy intervals.

## Verification

On `fleet_management-test.localhost`, the new baseline tests pass: `test_latest_full_tank_baseline_ignores_partial_and_cancelled_fuelings` and `test_full_tank_baseline_is_missing_without_vehicle_history_or_for_generator`. The existing `test_signal_is_frozen_once_approved` now checks the captured source against raw MariaDB and verifies it remains unchanged when a newer full tank is added after approval.

| # | Put the system in this state | Expect | Covers |
|---|---|---|---|
| 1 | A vehicle has a full-tank transaction and no later fueling | Its actual odometer and fueling time are the new baseline | `4.1` |
| 2 | Add one or more submitted partial transactions after that baseline | The new baseline and estimated consumed litres stay unchanged; the old check still uses its latest Previous Entry | `3.2`, `4.2`, `4.3` |
| 3 | Add a newer submitted, non-cancelled full-tank transaction | The new transaction becomes the baseline | `4.1` |
| 4 | Add a later full-tank transaction, then cancel it | The cancelled transaction is ignored and the prior qualifying full tank remains the baseline | `4.1` |
| 5 | Give the vehicle no qualifying full-tank history | The new check adds no reason; the existing check follows its current Previous Entry behavior | `3.2`, `4.4` |
| 6 | Use 300 km expected distance with a 15% margin | 255 km and 345 km pass; 254.97 km and 345.03 km fail under the existing rounded comparator | `3.2`, `4.2` |
| 7 | Set a partial fueling between the two check baselines so the old and new results differ | Both reasons are calculated independently; the old one is unchanged and the new one uses the full-tank baseline | `3.2`, `4.3` |
| 8 | Use a generator reading | Neither vehicle mileage check runs; existing generator checks still run | `4.6` |
| 9 | Give the baseline vehicle no usable recent average and no usable target | The new check adds its own red cannot-calculate reason; the old check keeps its current behavior | `4.4` |
| 10 | Approve an order, then change settings or add a newer fueling source | The saved signal, full-tank baseline, and result remain frozen on that approved order | `3.1`, `4.5` |
| 11 | Use unusable capacity or gauge data, or a full gauge with zero estimated consumption | Apply the behavior selected by the requester before running this row | `4.2` |

**How to run it.** All calculation and database rows are focused tests on the disposable MariaDB site. The visible source and result need a Fleet User Desk walkthrough on that site.

**Result:** The baseline lookup and frozen source snapshot are verified. The independent comparison, reason text, formula, and boundary cases have not been built. Row 11 still awaits the requester's capacity/gauge and zero-consumption decisions; no Desk walkthrough has run.

## What we learned that the plan did not predict

The current previous-entry lookup already excludes cancelled transactions and includes partial transactions. The existing recent average comes from submitted positive full-to-full interval records and otherwise falls back to the vehicle target.

## Known limitations — accepted, not fixed

- The response to unusable capacity or gauge data and zero estimated consumption is pending the requester.

## Review

| Round | Date | Verdict | Closed by |
|---|---|---|---|

**Closure:** Not reviewed.

**Next:** Continue the separate comparison after the pending business questions are answered; then run the complete Phase 3 matrix.
