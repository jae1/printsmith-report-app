# Feature Specification: Report Readability and Optional Board View

**Created**: 2026-10-29  
**Status**: Implemented and verified

## Intent

Improve usability, readability, and responsive layout without changing report
membership, amounts, payment data, API operations, or exports. Preserve all
rules in `PROTECTED_RULES.md`, especially date-scoped hiding and rule 19 branding
and print presentation. This extends the UI presentation of spec 001.

## User Scenarios and Acceptance

1. Staff can read the default table report with clear headings, aligned amounts,
   readable text, labeled fields, visible actions, and a wrapping toolbar.
2. A Table / Board button group changes presentation without fetching, mutating,
   duplicating, or reclassifying invoices. Table remains the default; the browser
   remembers an explicit choice. Switching preserves selections and restores
   Table's existing sort order when returning from Board.
3. Board view shows the four existing operational sections as responsive card
   columns. Cards show only invoice number, organization/company name, and job
   description; contact, dates, status, amounts, and payment badges are hidden on
   cards. Cards use tight padding and no repeated field labels, with complete
   company and job text wrapping naturally. Operational columns always show
   ascending invoice numbers (oldest first), including after refresh. Board
   sorting controls are removed. Selection and hide
   controls remain available. Paid Today remains a separate full-width financial
   table. Table view and print retain all existing fields and payment badges;
   section totals, collapse, individual and batch hide remain available.
   No drag-and-drop or new workflow states are introduced; groups may overlap
   exactly as they do in the existing report.
4. Keyboard users can toggle views, collapse sections, and sort columns. Spending
   edit/delete controls remain visible without hover. Settings fit small screens.
5. Print always uses expanded tables in either mode, retains report date and
   invoice details, and hides interactive controls, editing forms, and scrollbars.
   Excel and email generation remain unchanged.
6. The interface uses a compact print-shop job-sheet layout: a short identity
   header, a single wrapping toolbar grouping date/load/refresh, Table/Board,
   and secondary export/email/settings actions. Remove introductory/helper prose.
   Preserve the brand colors, system typography, neutral surfaces, subtle borders,
   small corners, readable company/job text, and aligned financial amounts.
7. Desktop Board columns scroll independently inside keyboard-focusable regions
   with visible scrollbars when needed; section headings stay outside the scrolling
   region. Bound long lists so Paid Today and Spending remain near the board.
   Preserve each column's scroll position when the report rerenders on refresh.
   Tablet/phone use normal page scrolling. Print removes all height/overflow caps
   and retains every row. Existing collapse, selection, and hide remain usable.
8. Table cells use slightly less vertical padding while keeping the current font
   sizes, full wrapping text, and button/touch targets. Center table cell contents
   vertically and align the inline Hide button with the invoice text. Board card padding and print
   cell spacing stay as specified.
9. Above both views, show a compact overview for the returned report date:
   Collected (sum only Paid Today grandtotal), New orders (count and order value),
   Needs attention (overdue plus due today), and Ready for pickup (existing count).
   Totals follow current report filters and date-scoped hiding; do not imply
   whole-store balances, profit, or combined totals across overlapping groups.
10. (Owner removed the visible due-date bar 2026-10-30; the buckets below still
    feed Needs attention.) Show one slim, labeled proportional due-date bar for unique invoice numbers
    from New Today and In Progress, excluding invoices also in Ready or Completed
    and ready-like/Shipping/Complete production locations. Group valid due dates
    relative to the returned report date as Overdue, Due today, Later, or No date.
    Missing/unusable dates are never overdue. Paid rows do not determine whether
    a job is in production. Derive the overview without mutating report arrays.
11. Refresh/sort/hide rerenders update the overview. Manual loading hides stale
    overview values. Both views show identical metrics; empty reports show zeros
    and an empty bar with a clear message. Provide visible category/count labels
    and accessible text, responsive layout, and a complete printable summary.

12. (Owner request 2026-10-30) Beside/below the overview, two chart cards.
    "Collected, last 7 workdays": seven vertical bars for the report date and
    the six prior Monday–Friday dates (the shop is closed weekends),
    each the sum of that date's Paid Today grandtotal from the existing
    `/api/report?target_date=` response (so exclusions, date-scoped hiding, and
    proven amounts apply), with compact amount, weekday, and date labels; the
    report date is highlighted. Prior days load once per page session in the
    background and never block the report; a failed day shows a dash. View
    switches and sorting make no requests. "Jobs": one proportional bar of New
    Today / In Progress / Ready for Pickup / Completed Today counts in the
    section accent colors with a labeled count legend; lists may overlap, so no
    combined total. Both are readable as text, responsive, and printable.
    Choosing a date in the date picker loads that report immediately; the Load
    Report button is removed (Refresh remains). A Today button loads the
    browser's local-date report; "today" is local time, not UTC. Cleared or partially typed
    dates do not load.
    Each workday bar is a keyboard-accessible button that loads that date's
    report (same as choosing it in the date picker).
13. The page header shows the official Overnight Printing Seattle horizontal
    logotype (`app/static/email-logo.png`, served at `/logo.png`) instead of
    the text eyebrow, with alt text; it remains in print.

14. (Owner request 2026-10-30; supersedes the Needs attention metric and the
    due-date buckets in items 9-10, because most jobs have no due date.) Job age
    is calendar days from the ordered date to the returned report date.
    - The third overview metric is "In progress 7+ days": the count of In
      Progress rows aged 7+ days, with the oldest age and its ordered date.
    - Ready for pickup's detail line counts rows waiting 5+ days.
    - In Table view, In Progress and Ready rows show the age next to the
      Ordered date; ages at/over the limit are highlighted (text, not color
      only). Board cards stay as specified in item 3.
    - When invoices are hidden for the selected date, the overview says how
      many are excluded from these totals, linking to the hidden list.
    No new requests beyond the existing hidden-list call; no data changes.
15. The overview uses 2×2 metric tiles that fill its card beside the charts
    (a single row of four on tablets), without filler captions; the hidden
    note sits in the overview heading. The report still starts within 400px
    of the top at 1440px.

## Verification

Use synthetic browser fixtures (no production database or email) to compare
rows, amounts, badges, selections, sort, collapse, and hide request payloads across
views; verify remembered preference, empty groups, narrow/desktop layout, and
print styles. Run repository tests where dependencies and database allow.

## Scope

Only the served `app/templates/index.html`, a `/logo.png` file route in
`app/api/views.py`, focused UI checks, and these Spec Kit artifacts. No SQL, classification, backend, scheduler, settings schema, or export
service changes. No new production dependencies.
