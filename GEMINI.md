# PrintSmith Report App Logic Rules

## Core Reporting Rules (NEVER RESET)

### 1. Document Filtering (Invoices vs Estimates)
- **Rule:** Only records that exist in both `invoicebase` and the `invoice` table should be included.
- **Why:** To strictly exclude Estimates/Quotes (which live in the `estimate` table).

### 2. Ready for Pickup
- **Rule:** Only show invoices where `ordereddate` is within the **last 10 days**.
- **Why:** To keep the list focused on recent orders and prevent clutter from old unclaimed jobs.

### 3. Payment Method Display
- **Rule:** Filter out "Deposit" from the payment methods list.
- **Why:** User preference to hide internal deposit movement labels in the daily report.

### 4. Consolidated AR Payments
- **Rule:** Use `tapeinvoicepayrecord` and `tapedepositappliedrecord` for balance and amount calculations.
- **Why:** `accounthistorydata` sums are unreliable for batch payments.

### 5. Post/Deposit Overlap
- **Rule:** If a job was fully paid via deposit and posted on the same day, consolidate into one PAID row with the full amount.
