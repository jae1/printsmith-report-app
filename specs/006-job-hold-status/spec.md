# Feature Specification: Show PrintSmith Job Holds

**Created**: 2026-10-30
**Status**: Implemented
**Input**: Owner: "there are jobs that are on hold ... mark the jobs that are on hold."

## User Scenario

The owner sees which open jobs are on hold (for example Credit Hold) on the
report page and in the daily email, so held jobs are not mistaken for jobs stuck
in production.

## Data

PrintSmith stores holds as `invoicebase.holdstate_id` → `holdstate` (`id`,
`name`, `isdeleted`). Live values (read-only probe, 2026-10-30): Credit Hold,
Customer Hold, Hold, ONP Hold. Four pending invoices were on Credit Hold.

PrintSmith stores only the current hold, so a past report date shows each
job's hold as of now, not as of that date.

## Requirements

- New Today, In Progress, Ready for Pickup, and Completed Today rows include
  `hold_name` (null when no active hold) through a `LEFT JOIN` to `holdstate`
  on its id, excluding deleted hold states. Membership, ordering, amounts,
  hidden-invoice handling, and Paid Today are unchanged (protected rules 1–16).
- Report page: an amber hold tag with the hold name on held rows in Table and
  Board views. Held In Progress jobs are excluded from "In progress 7+ days" and
  their age is not highlighted; the overview tile shows how many are on hold.
- Email (HTML and plain text): a held row's detail line starts with the hold name.

## Verification

Compare `/api/report` section counts and invoice numbers before/after for
several dates; confirm the four held invoices carry `Credit Hold`. Extend the
browser fixture and the email MIME test; run the Python suite.
