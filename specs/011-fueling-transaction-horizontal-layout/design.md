<!-- Small, read-only presentation change for the existing Fueling Transaction. -->

# Fueling Transaction side-by-side layout and summary: design

Approved by: Margaret Maina (@BrianKipngetich1) · 06/10/2026 · revision f341970 (explained by agent)

## Current state

The Fueling Transaction form shows the read-only approved order context first, followed by
invoice, meter, amount, evidence, and efficiency sections. The litre status updates as litres are
entered. Vehicle efficiency is already stored on qualifying submitted transactions; generator
litres per operating hour is calculated in the analysis report.

## Words in this request

| Requester's word | Means in this app |
|---|---|
| LPO details | The linked, read-only Fuel Order context on Fueling Transaction. |
| Invoice details | Actual fueling time, station and fuel, invoice numbers, litres, meter, amount, attendant, and evidence. |
| Summary | LPO baseline, actual invoice litres, the existing litre status, and the applicable efficiency result. |

## Decisions (locked)

- `D-1`: Put the LPO context on the left and the invoice entry on the right on wide screens; on
  narrow screens, stack the order first. Keep both in the same page.
- `D-2`: Update baseline status while invoice litres are entered, using the current green/orange/red
  thresholds.
- `D-3`: Show vehicle km/L or generator L/hour only when a valid result exists for the transaction;
  otherwise show “Efficiency is not yet available.”
- `D-4`: Keep order facts read-only and preserve current transaction permissions and validation.

## Design

Use Frappe's native form columns to place the existing approved-order context and invoice fields
beside each other. Place a full-width summary section underneath. Keep the existing live litre
comparison in that summary and display the efficiency that applies to the linked asset. For
submitted generator transactions, use the same permission-filtered full-tank interval calculation
as the analysis report; do not grant report access or store duplicate results. Let the form stack
the columns on narrow screens.

## Frappe-first

| What we need | Native Frappe mechanism | Custom code, and why it is unavoidable |
|---|---|---|
| Side-by-side form | Section Break and Column Break fields | Reorder existing fields into the requested columns. |
| Live baseline summary | Existing HTML field and form events | Move the current litre-status display into the full-width summary below both columns. |
| Generator efficiency | Existing Script Report interval calculation | A read-permission-checked lookup is needed on the transaction form because report access is not granted to Fleet Users. |

## Data and migration plan

No transaction data or Fuel Order data changes. Reuse the existing litre-status HTML field for the
summary; no new transaction field or stored efficiency value is needed. Migrate the disposable test
site only; do not migrate the main site.

## Correctness properties

### Property 1: LPO facts and variance stay authoritative

For every transaction, the left panel reflects the linked order without writing to it, and the
summary uses the existing LPO baseline and variance thresholds.

**Validates: Requirements 1.1, 1.2, 1.5**

### Property 2: Efficiency is shown only when valid

For every transaction, the summary shows vehicle km/L or generator L/hour only when the existing
qualifying readings support that result; otherwise it explains that a result is not yet available.

**Validates: Requirements 1.3, 1.5**

### Property 3: The layout adapts to screen width

For every screen width, the order, invoice, and summary remain readable in the requested order.

**Validates: Requirements 1.1, 1.2, 1.4**

## Errors and permissions

The order context keeps its existing permission check. The efficiency lookup checks permission to
read the current transaction and uses only transactions the current user can read. A missing
efficiency result is displayed as not yet available; it does not block saving or submission.
