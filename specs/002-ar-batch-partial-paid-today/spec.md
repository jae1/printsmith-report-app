# Feature Specification: AR Batch Partial Paid Today Attribution

**Feature Branch**: `002-ar-batch-partial-paid-today`  
**Created**: 2026-06-26  
**Status**: Complete
**Input**: AR charge-account invoices can be posted as a same-account batch after
older deposits or partial payments. Paid Today must show only the amount paid
today, not each invoice full amount.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Same-Account AR Batch Shows Today's Money Only (Priority: P1)

As the business owner, I need a same-account AR batch payment to show each
invoice's actual payment amount for the report date so that Paid Today is not
inflated by prior deposits, prior partial payments, or invoice totals.

**Why this priority**: The daily cash report is materially wrong when a batch of
older charge-account invoices is shown as fully paid today.

**Independent Test**: Run live regression checks for known AR batch dates where
invoice totals differ from the amount paid on the report date.

**Acceptance Scenarios**:

1. **Given** a charge-account invoice had an earlier partial payment, **When**
   the remaining balance is paid in a later AR batch, **Then** Paid Today shows
   only the remaining balance for that later date.
2. **Given** a single charge-account invoice receives only a partial payment
   today, **When** the Paid Today report is generated, **Then** it shows only
   today's partial amount, not the invoice total.
3. **Given** multiple invoices from the same charge account are posted together,
   **When** the batch is parsed from `Payment(...)`, **Then** each invoice amount
   is attributed independently.
4. **Given** multiple same-account invoices are posted and paid together, **When**
   PrintSmith stores a plain `Payment` row against only one invoice, **Then** Paid
   Today shows every invoice whose posted payment amounts exactly reconcile to
   the combined payment.
5. **Given** one same-account posting batch is settled with multiple payment
   methods, **When** PrintSmith stores multiple plain `Payment` rows against only
   some of the invoices, **Then** Paid Today includes every posted invoice when
   the shared timestamp and combined amounts exactly reconcile.

## Edge Cases

- Batch payment rows can have no `invoicenumber` and list invoices in the
  `Payment(...)` record name.
- Batch payment rows can also be named plain `Payment` and carry only the last
  invoice number even though the amount covers several immediately preceding
  same-account posted invoices.
- A single posting batch can contain multiple plain `Payment` rows with different
  methods, and an invoice paid within the batch may have no payment row linked
  directly to it.
- Payment detail tables do not carry dates, so they cannot by themselves answer
  "paid today".
- A single invoice can appear in separate AR payment batches on different dates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Paid Today MUST use report-date transaction rows to decide whether
  money moved today.
- **FR-002**: For generic AR `Payment(...)` rows, the system MUST distribute the
  batch amount to listed invoices without using invoice full totals as a default.
- **FR-003**: If the batch total matches the sum of listed invoices'
  `finalpaytotal`, each invoice MUST use its `finalpaytotal`.
- **FR-004**: If the batch total matches the sum of listed invoices'
  `partialpaytotal`, each invoice MUST use its `partialpaytotal`.
- **FR-005**: For a single listed invoice where no per-invoice split can be
  inferred, the system MUST use the batch row amount itself.
- **FR-006**: Prior deposits or partial payments MUST remain available for
  balance calculation but MUST NOT be used as today's Paid Today amount.
- **FR-007**: For a plain `Payment` row linked to one invoice, the system MUST
  attribute it to multiple posted invoices only when they share the same
  normalized account/contact identity, occur after that customer's preceding
  payment row on the report date, include the linked invoice, and their
  invoice-level payment fields exactly reconcile to the batch total. This
  identity rule MUST tolerate duplicate PrintSmith account/contact row IDs.
- **FR-008**: If plain-payment batch reconciliation fails, the system MUST retain
  the existing single-invoice behavior and MUST NOT infer a split.
- **FR-009**: Multiple plain `Payment` rows MUST be treated as one posting batch
  only when they share the exact account/contact identity and history timestamp,
  every linked invoice is among the posted invoices, and the combined payment
  total exactly equals the sum of the positive posted invoice amounts.
- **FR-010**: A payment row consumed by an exactly reconciled multi-payment batch
  MUST NOT also be processed independently.

### Key Entities

- **AR Batch Payment**: `accounthistorydata` recordtype `2` row with a
  `Payment(...)` record name and no direct invoice number.
- **Invoice Posted Row**: `accounthistorydata` recordtype `1` row containing
  invoice-level `finalpaytotal`, `partialpaytotal`, and total values.
- **Payment Detail Records**: `tapeinvoicepayrecord`,
  `tapedepositappliedrecord`, and `tapesalerecord`, used for lifetime balance
  context only.
- **Multi-Method Posting Batch**: Same-customer recordtype `1` and plain
  recordtype `2` rows sharing one exact `posteddate`, where the posted and paid
  totals reconcile.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Invoice `56276` on 2026-06-16 shows `20.62`, not `1689.14`.
- **SC-002**: Invoice `56276` on 2026-06-22 shows `1668.52`, not `1689.14`.
- **SC-003**: Existing 2026-06-16 batch attribution regression remains passing.
- **SC-004**: Invoices `56762` and `56896` on 2026-07-15 show `355.95` and
  `199.99` respectively, and their displayed sum equals the `555.94` payment.
- **SC-005**: Existing no-new-money regression invoice `56673` remains excluded
  from Paid Today on 2026-06-18.
- **SC-006**: Invoices `56858`, `56954`, and `56974` on 2026-07-24 show
  `6658.69`, `665.44`, and `4568.93`, and their displayed sum equals the
  combined `11893.06` card/check payment.
