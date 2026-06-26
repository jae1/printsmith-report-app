# Feature Specification: Reporting Guardrails Baseline

**Feature Branch**: `001-reporting-guardrails`  
**Created**: 2026-06-26  
**Status**: Active baseline  
**Input**: Current production behavior and recent fixes documented in `GEMINI.md`
and git history.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Daily Paid Reporting (Priority: P1)

As the business owner, I need the Paid Today section to show only actual money
collected today so that the daily cash picture is not inflated by previously
paid deposits or posting activity.

**Why this priority**: This directly affects accounting confidence and daily
operational decisions.

**Independent Test**: Run regression tests that cover batch payments,
deposit-applied records, same-day post/deposit overlap, and previous-day fully
prepaid invoices.

**Acceptance Scenarios**:

1. **Given** an invoice was fully prepaid by deposit before today, **When** it is
   posted today with no new payment, **Then** it does not appear in Paid Today.
2. **Given** an invoice receives actual payment today, **When** the daily report
   is generated, **Then** the payment is counted once with the correct method
   display.
3. **Given** a payment method includes "Deposit", **When** methods are displayed,
   **Then** "Deposit" is filtered from the visible payment method list.

### User Story 2 - Current Ready and In Progress Work (Priority: P1)

As production staff, I need Ready for Pickup and In Progress lists to reflect
the correct production location state and recent orders so that the dashboard
matches the shop floor.

**Why this priority**: Incorrect status lists cause missed work and customer
service confusion.

**Independent Test**: Query representative invoices by location and ordered date,
then verify the report places them in the expected section.

**Acceptance Scenarios**:

1. **Given** an invoice is in a Ready location and ordered within the last 10
   days, **When** the report is generated, **Then** it appears in Ready for Pickup.
2. **Given** an invoice is older than 10 days, **When** the report is generated,
   **Then** it is excluded from Ready for Pickup.
3. **Given** `readytopickup` disagrees with production location, **When** the
   report is generated, **Then** location-based logic wins.

### User Story 3 - Subsidiary Account Exclusion (Priority: P2)

As the business owner, I need payments from subsidiary print accounts excluded
from paid reporting regardless of local settings drift so that internal account
movement does not appear as ordinary revenue.

**Why this priority**: These rows distort daily totals and can reappear when
local JSON settings become stale.

**Independent Test**: Load settings with and without the excluded accounts saved
locally, then verify the hardcoded subsidiary accounts are present in the merged
exclusion list.

**Acceptance Scenarios**:

1. **Given** `app_settings.json` omits subsidiary exclusions, **When** settings
   are loaded, **Then** Belltown Minuteman Press, Federal Way Minuteman Press,
   and Green River Printing are included in excluded paid accounts.
2. **Given** local settings include additional excluded accounts, **When**
   settings are loaded, **Then** those accounts are preserved alongside the
   mandatory subsidiaries.

## Edge Cases

- Batch payments may have multiple records that must not be double-counted.
- PrintSmith date fields may include reserved column names; use `localdate` where
  the current rules require it.
- Local JSON files may be missing, stale, or partially populated.
- Estimates must not leak into invoice reports.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include only records present in both `invoicebase` and
  `invoice` for invoice reports.
- **FR-002**: System MUST use authoritative PrintSmith payment records for paid
  totals and balance calculations.
- **FR-003**: System MUST exclude "Deposit" from displayed payment method labels.
- **FR-004**: System MUST exclude fully prepaid previous-day deposits from Paid
  Today when no new money was collected today.
- **FR-005**: System MUST use `localdate` for affected payment/sale date queries.
- **FR-006**: System MUST use production location logic for Ready/In Progress
  classification where that is the current business rule.
- **FR-007**: System MUST enforce mandatory subsidiary account exclusions even
  when local settings omit them.

### Key Entities

- **InvoiceBase**: PrintSmith invoice base record containing invoice number,
  customer, order date, pending/ready flags, and document location.
- **Invoice**: Companion invoice record used to exclude estimates.
- **Payment Records**: `tapeinvoicepayrecord` and
  `tapedepositappliedrecord`, used for paid totals and payment method display.
- **Settings**: Local JSON-backed configuration merged with mandatory defaults.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Existing batch-payment regression test passes.
- **SC-002**: Paid Today excludes previous-day fully prepaid invoices with no new
  money collected today.
- **SC-003**: Ready/In Progress report sections match production location rules
  for sampled live invoices.
- **SC-004**: Mandatory subsidiary exclusions are present after every settings
  load path.

## Assumptions

- The PrintSmith PostgreSQL schema remains the source of truth.
- Local JSON files are deployment state, not canonical business policy.
- This baseline documents existing behavior and recent fixes; future feature
  work should create separate numbered specs.
