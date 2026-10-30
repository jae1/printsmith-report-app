# Tasks: Report Layout

- [x] Read protected rules, Constitution, baseline spec, and UI/coordinator roles.
- [x] Audit template and callers; document scope and acceptance before code.
- [x] Improve typography, toolbar, table alignment, forms, and responsive layout.
- [x] Add optional persistent Board presentation using the existing report DOM.
- [x] Preserve actions; add keyboard collapse/sort and clear selection labels.
- [x] Verify desktop, narrow screen, empty data, preferences, and print.
- [x] Run relevant regression checks and document results/limitations.
- [x] Simplify Board cards to invoice/company/job description; verify Table and
  print still display full details and badges (2026-10-30).
- [x] Tighten card spacing, remove Board sorting controls, and default operational
  cards to oldest invoice first; verify Table order and selected rows survive.
- [x] Apply the approved job-sheet styling and consolidated toolbar.
- [x] Bound desktop Board lists with keyboard-accessible native scrolling; retain
  natural mobile scrolling and expand every row for print.
- [x] Verify long lists, fixed column headings, control layout, mobile/print,
  and refresh the live local preview.
- [x] Reduce Table vertical cell spacing and verify Board, mobile, and print.
- [x] Add four manager metrics and a labeled due-date bar using existing data.
- [x] Cover payment amount, unique job scope, historical/missing dates, empty
  states, both views, loading, responsive layout, and print.
- [x] Run verification, inspect the summary, and refresh the local preview.

## Charts and Logo (2026-10-30)

- [x] Seven-day Collected chart from existing report responses; no requests on view switch.
- [x] Jobs proportional bar and count legend in section colors; no combined total.
- [x] Logo in header via `/logo.png`; kept in print.
- [x] Extend `tests/report_ui.cjs`; run desktop/phone/print checks and the Python suite.
- [x] Skip weekends (last 7 workdays); clickable bars open that date's report.
- [x] Remove the visible due-date bar; keep Needs attention.
- [x] Load on date change; remove Load Report; ignore cleared/partial dates.
- [x] Today button; compute today in local time (UTC rolled over at 5pm PT).
- [x] Job age metric/badges (In Progress 7+, Ready 5+) replacing Needs attention.
- [x] Hidden-invoice note in overview.
- [x] Update UI test; run checks.
- [x] Overview as 2×2 tiles beside charts (one row of four on tablets); drop filler text; hidden note in the overview heading.
- [x] Table/Board as a labeled segmented switch, divided from the date/action buttons.
