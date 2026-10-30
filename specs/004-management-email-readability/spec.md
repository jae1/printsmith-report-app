# Feature Specification: Management Email Readability

**Status**: In progress
**Input**: Match the main report's compact job-sheet UI/UX in the actual email,
including its manager overview and due-date graphic.

## User Scenario

Management opens the daily email on a phone or desktop and sees the same compact
branding, four manager metrics, due-date graphic, and section order as the main
report. Amounts line up on the right and the report remains readable without JS.

## Requirements

- Use protected navy/sky branding, neutral surfaces, thin section accents, small
  corners, compact type/spacing, and no decorative emoji or oversized hero card.
- Owner-approved overview (2026-10-30, supersedes the four-metric/due-date
  overview in email only): a small three-block summary of Collected today (sum
  of proven Paid Today row grandtotal, never invoice total or lifetime paid),
  New orders (New Today count plus total order value), and Recorded spending
  (Daily Spending recorded for the report date; not profit). The three values
  are never added together. The email has no due-date bar or due-date-driven
  Needs attention metric; the main web report overview/Board/Table is unchanged.
- Include New Today, In Progress, Ready for Pickup, Completed Today, Paid Today,
  and Daily Spending in main-report order, retaining all invoice rows and totals.
  Use compact tables with invoice/account/job on the left and amount on the right;
  keep payment type, payment method, partial/balance context, and optional job
  contact/dates/status readable. Empty sections and zero summaries are explicit.
- Owner readability pass (2026-10-30): the email shows no due dates anywhere;
  the three summary blocks stack vertically on phones; all email text is 1px
  larger; the header uses the official Overnight Printing Seattle horizontal
  logotype (inline CID image with text alt); remove filler text (the "From
  visible report invoices" line, summary count captions, table column headers,
  and the duplicate footer). New orders keeps its order value.
  The logo, title, and report-date line are centered on all screens. A missing
  account shows the invoice number alone (no placeholder dash), and Paid Today
  rows omit the Ordered date.
- The owner moved the jobs bar and seven-day Collected trend out of the email
  (2026-10-30); they live on the web report only (spec 005). The email has no
  charts and makes no extra report lookups.
- Email invoice numbers appear without a leading `#` in HTML and plain text.
  New Today omits Ordered date because the section already establishes that date;
  keep Ordered dates in other sections.
- Use inline CSS and native presentation tables for summary/layout/chart so the
  critical content works without CSS Grid, Flexbox, JavaScript, or remote assets.
  Wrap long text on phones while preserving legible aligned monetary amounts.
- Paid Today cards use the report's `is_partial` and `current_balance` fields;
  payment type and method remain visible.
- Order values use a neutral color; collected amounts and spending remain
  visually distinct without relying on color alone.
- The plain-text alternative contains the same three-block summary, six sections,
  invoice details, and totals. Escape HTML dynamic content.
- The configured report title prefix is used in the email body title.
- Every manual or scheduled report email, for all configured recipients, uses
  the sender display name `Overnight Printing Seattle` with the configured SMTP
  email address. Its subject is exactly `Overnight - MM/DD/YYYY Daily Report`,
  using the report's date, including zero-padded days/months. A custom body title
  prefix does not override that subject. The settings label/help must reflect
  this distinction without changing the stored setting key.
- Report classification, payment amounts, SMTP credentials, recipients, and
  scheduler behavior remain unchanged.

## Data and Verification

Use `get_report_data` section rows, `spending_service.get_spending_by_date`, and
`settings_service.load_settings`. Render a sample with a partial payment,
spending item, and all operational sections at phone and desktop widths; inspect
both MIME alternatives and the subject without sending an email.
Verify the From display name/address, fixed subject with a custom body prefix,
historical report date, and preserved recipients using a mocked SMTP transport.
Verify the three summary values (paid-row grandtotal, not invoice totals; new
order count/value; recorded spending), no due-date bar/metric, empty reports, escaping and partial payments, and render desktop/phone previews without
sending. Show the user a local preview of the actual generated HTML.
