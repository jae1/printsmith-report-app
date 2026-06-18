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

### 6. Paid Today (No New Money Rule)
- **Rule:** If an invoice was fully pre-paid via deposit on a *previous* day, and is simply "Posted" today without any actual new payment collected today, it MUST NOT appear in the "Paid Today" section. 
- **Why:** To prevent artificially inflating today's cash flow when no actual new money was collected today.

### 7. PostgreSQL Reserved Keyword 'date'
- **Rule:** When querying dates in `tapeinvoicepayrecord` or `tapesalerecord`, ALWAYS use the `localdate` column instead of the `date` column.
- **Why:** `date` is a reserved keyword in PostgreSQL and causes persistent syntax and type-casting errors across different database driver versions. The `localdate` column contains the exact same date value without syntax ambiguity.

## Agent Roles & Maintenance Plan

When modifying this codebase, the active AI agent must adopt one of the specialized roles defined in the `.agents/` directory.

### Routing CLI Tool
We have implemented a helper CLI script `agent_selector.py` to easily list roles, load rules, and recommend which agent should handle specific files.
- **List Agents**: `python agent_selector.py --list`
- **Load Agent Instructions**: `python agent_selector.py --load [coordinator|sql_logic|expense_parser|web_ui|sysops]`
- **Recommend Agent for Files**: `python agent_selector.py --recommend app/services/report_service.py`

### 1. Coordinator Agent (Guardrails & Verification)
- **Profile**: [.agents/1_coordinator.md](file:///Users/onp/printsmith-report-app/.agents/1_coordinator.md)
- **Scope**: `GEMINI.md`, `README.md`, testing configurations.

### 2. SQL & Report Logic Agent (Core Database Query Expert)
- **Profile**: [.agents/2_sql_report_logic.md](file:///Users/onp/printsmith-report-app/.agents/2_sql_report_logic.md)
- **Scope**: `app/services/report_service.py`, `app/services/hide_service.py`, `app/db/`

### 3. Expense Parser & Sync Agent (Email & Expense Expert)
- **Profile**: [.agents/3_expense_parser_sync.md](file:///Users/onp/printsmith-report-app/.agents/3_expense_parser_sync.md)
- **Scope**: `app/services/expense_parser_service.py`, `app/services/spending_service.py`, `daily_spending.json`

### 4. Web UI & Experience Agent (Frontend & Interaction Expert)
- **Profile**: [.agents/4_web_ui.md](file:///Users/onp/printsmith-report-app/.agents/4_web_ui.md)
- **Scope**: `app/templates/`, `app/static/`, `app/services/export_service.py`

### 5. SysOps & Email Delivery Agent (Automation & Deployment Expert)
- **Profile**: [.agents/5_sysops_email.md](file:///Users/onp/printsmith-report-app/.agents/5_sysops_email.md)
- **Scope**: `app/main.py`, `app/services/email_service.py`, `app/services/settings_service.py`, `requirements.txt`

