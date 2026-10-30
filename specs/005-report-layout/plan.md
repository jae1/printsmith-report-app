# Implementation Plan: Report Layout

## Approach and Constitution Check

Preserve the existing vanilla HTML/CSS/JavaScript template and one report DOM.
Use a CSS class to present operational table rows as labeled cards, retaining
all existing handlers and avoiding a second renderer. Add a guarded localStorage
view preference. Keep the navy `#0B1B3D`, sky blue `#00A3E0`, and transparent
favicon treatment. Add responsive form/table containers and explicit print rules.

Read the Constitution, full protected register, baseline spec/plan/tasks, and
coordinator/UI profiles. No protected-rule changes are required. No data queries
or production state mutations are needed for verification.

## Change Reach

Approved manager overview: add a compact four-metric strip plus a CSS proportional
due-date bar before the report. Reuse the existing response and currency helper;
no chart package, new endpoint, or SQL. Use returned `date`, `paid`, `new_today`,
`in_progress`, `ready`, and `picked_up`. Collected uses only proven paid-row
`grandtotal`; order value stays separate. Deduplicate production candidates by
normalized invoice number, exclude ready/completed invoices and ready-like or
shipping/completed locations, and count missing dates explicitly. Compare ISO
local date portions with the returned report date, avoiding timezone shifts.
Invoke the summary from the shared report renderer (load, refresh, sort, hide),
hide it during manual loading, and retain text labels and values for print.
Slightly reduce desktop lane caps to 52vh/560px to accommodate the summary.
Extend synthetic browser coverage for exact money, overlaps, due-date buckets,
historical dates, missing dates, empty data, view parity, responsive and print.

Table density follow-up: reduce header vertical padding from 10px to 6px and
body cell vertical padding from 12px to 7px. Preserve type size, touch targets,
Board's more-specific card rules, and print's 5px cells. Reach is the two shared
table CSS declarations, affecting report, hidden, and spending tables. Verify
with the existing browser regression; no new logic or backend changes are needed.
Offer manager-summary ideas without implementing new metrics in this follow-up.
The owner's screenshot also exposed top-aligned cells and baseline-aligned Hide
buttons. Set cell and inline Hide button vertical alignment to middle, preserving
the table structure and card layout.

Approved job-sheet direction: consolidate controls into date/view/secondary-action
groups beneath a smaller identity header; remove introductory/helper paragraphs.
Use restrained neutral surfaces, 4px corners, thin status rules, and counts beside
headings. At desktop widths >=1200px, cap operational list regions at the smaller
of 56vh or 600px, with native scrolling and existing keyboard focusability. Keep
headings outside the scrolling region. Below 1200px retain page scrolling.
Print clears the list caps and restores complete tables. Changes reach only the
template, browser checks, and this feature's documentation; no backend, exports,
or production dependencies. Use the verified UI/UX Pro Max data-dense-dashboard
style guidance with the repository's protected navy/sky colors.

2026-10-30 follow-up: Remove operational Board sorting controls and repeated card
labels; reduce card padding/spacing without truncating company or job text.
Reorder existing operational rows by numeric invoice number ascending in Board,
using each row's rendered Table position to restore Table order. Apply this after
render and on view switches so refresh respects Board order. Preserve checked
rows by moving the existing elements, and leave Paid Today and backend ordering
unchanged. Verify order, restored Table sort, selection, density, and print.

2026-10-30: Simplify operational Board cards to invoice number, company, and job
description using screen-only CSS and presentation classes on the shared cells
and sorting headers. Keep selection/hide controls and section totals. Hide card
payment badges; restore all details in Table and print. Paid Today is unchanged.
Extend the browser fixture to verify exactly three visible card fields and badge
visibility after switching back to Table and printing.

- Template styles and markup: toolbar, report sections, spending, hidden list,
  settings sizing, keyboard focus, labels, and print layout.
- Report renderer: field labels and accessible collapse/sort controls; preserve
  row values, balance calculations, section totals, and action handlers.
- Existing callers: initial load, auto-refresh, sorting, hide/unhide, and spending
  rerenders continue to use their current functions and API contracts.
- Checks: synthetic browser regression covering both modes and print. Existing
  accounting/email/watchdog tests remain unchanged.

## Risks

CSS card layouts must restore normal tables during print. Long account/job names
must wrap without hiding fields. A view switch must not reset checked invoices.
Paid Today must not look like a production status or be added to operational
totals. Browser preference failures must not prevent loading a report.

## Verification Results (2026-10-29)

- Full Python suite: `PGCONNECT_TIMEOUT=5 /tmp/printsmith-ui-check/venv/bin/python
  -m pytest -q` — **13 passed, 9 subtests passed**, including the existing
  database-backed payment regressions, email content, and watchdog checks.
  The temporary environment used system packages plus pytest/aiosmtplib; no
  production dependency or configuration changes were required.
- Browser regression: `NODE_PATH=/tmp/printsmith-ui-check/node_modules node
  tests/report_ui.cjs` — passed in headless Google Chrome. Playwright was installed
  outside the repository with `npm install --prefix /tmp/printsmith-ui-check
  --no-audit --no-fund playwright`. This standalone check needs Node, Playwright,
  and Chrome; it intercepts every request and never changes production data.
- Verified the default and remembered view, identical rows/totals/badges and
  preserved selection across switches, no additional report request on switching,
  keyboard sorting/collapse, individual and batch date-scoped hide payloads,
  responsive document widths at 375/768/1440px, visible spending actions, settings
  sizing and keyboard focus, empty groups, and unavailable localStorage.
- Visually inspected desktop Table/Board, mobile Board, and print screenshots.
  Print checks cover both views, expanded collapsed report/hidden/spending
  sections, restored column headings, hidden controls, date, and no scrollbars.
  Screenshots and an A4 landscape PDF are generated in a temporary directory.
- `git diff --check` passed. No generated artifacts are included in the change.

Limitations: browser verification covered Chrome with synthetic report data;
other browsers and deployment were not exercised. Excel/email implementation is
untouched; existing email regression coverage passed. No owner-controlled rule
was changed.

## Compact Card Verification (2026-10-30)

`NODE_PATH=/tmp/printsmith-ui-check/node_modules node tests/report_ui.cjs`
passed. The browser check now asserts exactly three visible data fields per
operational card, three sorting fields, hidden payment badges on cards, and
restored details/badges in Table and print. Existing checks for Paid Today,
selection/hide, responsive widths, and print also passed. Visually inspected the
compact desktop Board screenshot. `git diff --check` passed. The Python suite
was not rerun for this presentation-only follow-up; no backend files changed.

## Density and Ordering Verification (2026-10-30)

The standalone Chrome browser regression passed after removing operational Board
sorting controls and card field labels, tightening padding, and sorting existing
card elements by numeric invoice number ascending. Checks cover numeric ordering
across digit lengths (9999 before 10000), preserved checked invoices, restored
Table order, refresh, a compact long-text fixture card under 180px, and full print
details. Refreshed the local Board preview at `http://127.0.0.1:8765/`.
No backend code changed; the Python suite was not rerun for this follow-up.

## Job-Sheet Styling Verification (2026-10-30)

- Applied the approved compact header/toolbar, neutral columns, small corners,
  thin status accents, and counts beside headings. Removed introductory/helper
  prose. Existing controls retain their API handlers.
- Desktop list regions are capped at 56vh/600px with native scrollbars and
  keyboard focus; headings stay outside the scrolling area. Rerendering restores
  scroll positions by the existing unique section-region label.
- `NODE_PATH=/tmp/printsmith-ui-check/node_modules node tests/report_ui.cjs`
  passed, including a 30-card column, keyboard scrolling without heading movement,
  restored scroll position after rerender, Paid Today within the desktop viewport,
  uncapped tablet/mobile and Table views, and all 30 rows expanded for print.
- Visually checked the live desktop Board plus synthetic mobile/print screenshots.
  Refreshed the live local preview; Board begins about 169px below the page top
  on the current desktop, and the two long production columns scroll independently.
- `PGCONNECT_TIMEOUT=5 /tmp/printsmith-ui-check/venv/bin/python -m pytest -q`
  passed: **13 tests and 9 subtests**. `git diff --check` passed.
- Browser coverage remains Chrome. No deployment, backend edits, or production
  dependencies were introduced.

## Table Density Verification (2026-10-30)

Reduced vertical header/body padding to 6px/7px without changing typography or
button targets. The standalone Chrome browser check passed for Table, Board,
mobile, actions, and print; `git diff --check` passed. Refreshed the local preview
in Table view. No summary metrics were added; manager-summary ideas are presented
for the owner's selection. Python tests were not rerun for these CSS changes.
After the screenshot follow-up, centered cell contents and inline Hide buttons.
The Chrome browser regression passed again; live geometry for the supplied row
showed the company text and Hide button centers within 1px. Local Table preview
was refreshed. Screen/print behavior passed and `git diff --check` stayed clean.

## Manager Overview Verification (2026-10-30)

- Added four compact metrics and one labeled CSS due-date bar above both views.
  Reused the existing response and formatter; no backend/export changes or new
  dependencies. Missing or invalid due dates are explicitly shown as No date.
- `NODE_PATH=/tmp/printsmith-ui-check/node_modules node tests/report_ui.cjs`
  passed. New assertions cover actual paid amount versus invoice total/balance,
  new-order value, attention count, numeric/string invoice deduplication, ready/
  completed/shipping exclusions, local date portions with timezone offsets,
  impossible calendar dates, missing due dates, historical report dates, bucket
  proportions, unchanged source arrays, view parity, manual loading, and zeros.
  Existing responsive, long-list, actions, and print checks also passed.
- Visually inspected desktop Board, mobile Board, printable summary, and the
  live local Table overview. Browser checks still confirm Paid Today remains
  within the desktop viewport after the summary and adjusted 52vh/560px caps.
- `PGCONNECT_TIMEOUT=5 /tmp/printsmith-ui-check/venv/bin/python -m pytest -q`
  passed: **13 tests, 9 subtests**. `git diff --check` passed.
- Refreshed `http://127.0.0.1:8765/`. Verification covered Chrome; deployment
  and other browsers were not exercised. Protected rules remain unchanged.

## Charts and Logo (2026-10-30)

`index.html`: a `.dashboard` grid places the overview, "Collected, last 7
workdays", and "Jobs" cards in one row at >=1200px (two columns at tablet, stacked
on phones) so the report still starts high on desktop. Prior workdays are fetched
once per session from `/api/report?target_date=` and cached by date; the report
date always uses the loaded payload. Each bar is a button that sets the date
picker and calls `loadReport()`. Jobs bar uses inline accent variables, not
section classes, so report selectors are unaffected. Removed the visible due-date
bar/legend. `views.py` serves the logotype at `/logo.png` via `FileResponse`.
Verified: `tests/report_ui.cjs` (workday dates/amounts/bar heights, no weekend
requests, click + keyboard navigation, jobs counts, logo loads, print shows
charts, empty state) and the Python suite; inspected live 1440px/375px pages.

## Job Age and Hidden Note (2026-10-30)

Replaced the due-bucket code with `jobAge` (calendar days, ordered date to report
date; unusable dates skipped) and `AGE_LIMITS` (In Progress 7, Ready 5). Overview
shows "In progress 7+ days" with the oldest job, Ready shows "N waiting 5+ days",
and Table Ordered cells gain an age badge (highlighted text at/over the limit).
`loadHiddenList` stores the count for an overview note linking to the hidden list.
Verified with `tests/report_ui.cjs` (ages incl. timestamps/missing/invalid dates,
limits, historical date, empty report, hidden note) and the Python suite; checked
the live 1440px page. No backend or data changes.
