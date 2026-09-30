# Feature Specification: Management Email Readability

**Status**: In progress
**Input**: Make the daily management email easier to scan without removing report details.

## User Scenario

Management opens the daily email on a phone or desktop and can distinguish cash
collected today from order value, see outstanding balances on partial payments,
and review every report section without opening the web app.

## Requirements

- The summary shows report-date collections, recorded spending, new-order count
  and value, ready count, and the count of Paid Today invoices with a balance due.
- The email includes individual New Today orders as well as Paid Today, Daily
  Spending, In Progress, Ready for Pickup, and Completed Today.
- Paid Today cards use the report's `is_partial` and `current_balance` fields;
  payment type and method remain visible.
- Order values use a neutral color; collected amounts and spending are visually
  distinct without relying on color alone.
- HTML remains readable in common email clients, and the plain-text alternative
  contains the same summary and section details.
- The configured report title prefix is used in the email title and subject.
- Report classification, payment amounts, SMTP credentials, recipients, and
  scheduler behavior remain unchanged.

## Data and Verification

Use `get_report_data` section rows, `spending_service.get_spending_by_date`, and
`settings_service.load_settings`. Independently render a sample with a partial
payment, new order, spending item, and all operational sections; inspect both
MIME alternatives and the subject without sending an email.
