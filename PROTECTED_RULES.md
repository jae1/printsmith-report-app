# PrintSmith Report App Protected Rules

This file is the tool-neutral, canonical operational rule register for this
repository. Every agent must read it before changing production behavior.

## Owner-Controlled Change Policy

- Every rule in this file is **PROTECTED**.
- A feature request, bug report, refactor, cleanup, optimization, migration, or
  test update is **not** permission to weaken, remove, bypass, reinterpret, or
  replace a protected rule.
- A protected rule may change only when the repository owner explicitly asks to
  change that specific rule. Permission to change one rule does not authorize
  changes to any other rule.
- If requested work conflicts with a protected rule and the owner has not
  explicitly authorized that rule change, stop the conflicting work, preserve
  current behavior, and report the conflict.
- An authorized rule change must update this file, the Constitution, the
  relevant feature spec/plan/tasks, and regression coverage in the same change.
- When a fix can satisfy the request without changing a protected rule, use the
  narrowest implementation and prove the surrounding rules still pass.

## Protected Reporting and Accounting Rules (NEVER RESET)

### 1. Document Filtering (Invoices vs Estimates)
- **Rule:** Only records that exist in both `invoicebase` and the `invoice` table may appear in invoice reports.
- **Why:** Estimates and quotes must never leak into invoice reporting.

### 2. Ready for Pickup
- **Rule:** Show active pending invoices where `ordereddate` is within the last 10 days when either `readytopickup` is enabled or production location is `Ready for Pickup`, `Ready for Delivery`, or `Complete`.
- **Why:** The explicit ready toggle and ready-like locations are shop-floor signals; the recency limit prevents stale clutter.

### 3. New Today
- **Rule:** New Today includes active, non-voided invoices whose `ordereddate` is the report date.
- **Why:** It represents invoices created on the selected day.

### 4. In Progress
- **Rule:** In Progress includes active pending invoices ordered before the report date only when `readytopickup` is false and production location is not `Ready for Pickup`, `Ready for Delivery`, `Shipping`, or `Complete`.
- **Why:** Ready, shipped, and completed work must not remain in the active production queue or overlap Ready for Pickup.

### 5. Completed Today
- **Rule:** Completed Today includes an active invoice on the report date when its pickup date is that date, it left the pending list on that date, or its location changed to `Shipping` or `Complete` on that date.
- **Why:** Completion is operational movement on the selected day and is independent from whether money moved that day.

### 6. Payment Method Display
- **Rule:** Filter out `Deposit` from the visible payment method list.
- **Why:** Deposit is an internal movement label, not a customer-facing payment method for the daily report.

### 7. Payment Sources and Dates
- **Rule:** Use report-date `accounthistorydata` records of type `1`, `2`, and `7` to decide whether posting, payment, or deposit activity occurred that day. Exclude `Charge` as new money.
- **Why:** Paid Today must follow report-date PrintSmith transaction semantics.

### 8. Lifetime Balance Sources
- **Rule:** Use `tapeinvoicepayrecord`, `tapedepositappliedrecord`, and non-`Charge` `tapesalerecord` amounts for lifetime paid and balance context. Never treat lifetime totals as today's payment amount.
- **Why:** Detail tables are authoritative for balance context but do not alone establish when today's money moved.

### 9. Post/Deposit Overlap
- **Rule:** If a job was fully paid by deposit and posted on the same day, consolidate it into one PAID row with the full amount.

### 10. Paid Today (No New Money)
- **Rule:** If an invoice was fully prepaid on a previous day and is only posted today without an actual payment or deposit today, it MUST NOT appear in Paid Today.
- **Why:** Posting must not inflate today's cash flow when no new money was collected.

### 11. PostgreSQL Reserved Keyword `date`
- **Rule:** When date-filtering `tapeinvoicepayrecord` or `tapesalerecord`, use the schema's unambiguous local-date field rather than an unqualified reserved `date` identifier; verify the live table schema before adding such a query.
- **Why:** Reserved date identifiers and schema differences have repeatedly caused runtime failures.

### 12. Generic AR Batch Payment Attribution
- **Rule:** For charge-account batches shown as `Payment(...)`, Paid Today must show each invoice's actual report-date amount, not invoice total or lifetime paid amount. Match the batch total to invoice-level `finalpaytotal` or `partialpaytotal` values.
- **Why:** Older deposits and partial payments must not be counted again.

### 13. Plain `Payment` Multi-Invoice Attribution
- **Rule:** When PrintSmith stores one plain `Payment` row against only one invoice in a multi-invoice payment, split it only across preceding posted invoices that share the same normalized account/contact identity and payment method, occur after that customer's prior payment row on the report date, include the linked invoice, and exactly reconcile through `finalpaytotal`, `partialpaytotal`, or posted total to the combined payment.
- **Fallback:** If every condition does not match, retain existing single-invoice behavior. Never guess a split.
- **Why:** PrintSmith can duplicate customer IDs and attach a combined payment only to the last invoice; loose matching could misattribute revenue.

### 14. Today's Amount Must Not Be Invented
- **Rule:** Paid Today must show each invoice's proven report-date amount. Do not substitute invoice grand total, lifetime paid total, or an arbitrary proportional split when attribution cannot be proven.
- **Why:** A plausible fallback can silently corrupt the daily cash report.

### 15. Mandatory Paid-Account Exclusions
- **Rule:** Always exclude `Belltown Minuteman Press`, `Federal Way Minuteman Press`, and `Green River Printing` from Paid Today while preserving additional owner-configured exclusions.
- **Why:** Subsidiary/internal account movement is not ordinary revenue, and local settings drift must not restore it.

### 16. Date-Scoped Hidden Invoices
- **Rule:** Hiding an invoice applies only to the selected report date. Hidden state must not silently become global across all dates.
- **Why:** Hiding is report-date presentation state, not deletion or permanent accounting exclusion.

## Protected Operational Rules

### 17. Safe Local State
- **Rule:** Settings JSON, hidden invoice data, spending data, processed-receipt state, logs, pycache, and probe outputs are runtime state. Do not commit generated runtime files or make them canonical policy without explicit owner authorization.

### 18. Receipt Parsing and Duplicate Prevention
- **Rule:** Receipt synchronization must preserve `pypdf` extraction with strict parsing for tax, totals, vendor, and dates, and must check processed-receipt state before inserting spending records.

### 19. UI, Branding, and Export
- **Rule:** Preserve the Overnight Printing Seattle deep navy `#0B1B3D`, sky blue `#00A3E0`, and transparent-background favicon treatment. Printed/exported output must hide interactive buttons, scrollbars, and sidebar controls.

### 20. Email, Scheduler, and Secrets
- **Rule:** Preserve thread/async safety for scheduled email and receipt tasks. SMTP passwords and environment-specific configuration must remain outside source control and load through configuration.

### 21. Windows Server Availability
- **Rule:** The Windows deployment must run through its registered watchdog task, start after reboot, restart the report server after unexpected exit, and retry the watchdog after failure. Update preparation must not stop a working server until repository synchronization and dependency installation succeed.
- **Why:** A transient GitHub, dependency, console-session, or process failure must not leave the report server offline indefinitely.

## Required Verification Before Handoff

- Report/payment changes: run focused regression coverage for generic AR,
  partial/final, linked plain-payment, and no-new-money cases.
- Classification changes: independently verify New Today, In Progress, Ready
  for Pickup, and Completed Today placement without overlap.
- Settings changes: verify mandatory subsidiary exclusions survive missing,
  stale, and partially populated local settings.
- UI/export changes: verify screen and print/export presentation.
- If the expected test runner is unavailable, use the closest available runner
  and disclose the limitation; never claim unrun verification.
