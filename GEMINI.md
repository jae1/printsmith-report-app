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

## Agent Roles & Maintenance Plan

When modifying this codebase, the active AI agent must adopt one of the following roles based on the target files:

### 1. Coordinator Agent (Guardrails & Verification)
- **Files Owned**: `GEMINI.md`, `README.md`, testing configurations.
- **Protocol**: Ensures no logic updates violate the Core Reporting Rules above. Verifies code before merging.

### 2. SQL & Report Logic Agent (Core Database Query Expert)
- **Files Owned**: `app/services/report_service.py`, `app/db/`
- **Protocol**: Ensures correct SQL JOINs, fast indexes, and precise calculation of Invoice status, ready items, and paid transactions.

### 3. Receipt Parser & Sync Agent (Email & Expense Expert)
- **Files Owned**: `app/services/expense_parser_service.py`, `app/services/spending_service.py`, `daily_spending.json`
- **Protocol**: Optimizes receipt scanning regex patterns, parses invoice attachments using `pypdf`, and manages local spending stores.

### 4. Web UI & Experience Agent (Frontend & Interaction Expert)
- **Files Owned**: `app/templates/`, `app/static/`
- **Protocol**: Builds beautiful, responsive layouts. Implements print media CSS, modal views, and interactive state buttons in Javascript.

### 5. SysOps & Email Delivery Agent (Automation & Deployment Expert)
- **Files Owned**: `app/main.py`, `app/services/email_service.py`, `app/core/config.py`, `requirements.txt`
- **Protocol**: Manages background asynchronous loops (email scheduler, receipt sync task), monitors server startup, and handles SMTP settings.
