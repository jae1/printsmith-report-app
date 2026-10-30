# Implementation Plan: Show PrintSmith Job Holds

- `app/services/report_service.py`: add `hs.name AS hold_name` and
  `LEFT JOIN holdstate hs ON ib.holdstate_id = hs.id AND hs.isdeleted = false`
  to the four operational queries only. `holdstate.id` is a key, so the join
  cannot duplicate rows; WHERE clauses are untouched. `process_rows` passes the
  field through.
- `app/templates/index.html`: `holdTag(item)` in the job cell (visible in both
  views); `jobAge`-based stuck count and age highlight skip held jobs; tile
  detail appends "N on hold".
- `app/services/email_service.py`: `_invoice_notes` puts `hold_name` first.
- Constitution check: invoice-only filtering, classification, payment logic,
  date-scoped hiding, and scheduler are unchanged; no new dependency.

## Verification (2026-10-30)

`get_report_data` for 10/30, 10/27, 10/20 matched pre-change `/api/report`
snapshots exactly (invoice numbers, order, amounts, all five sections incl. Paid
Today); the four WAND invoices carry Credit Hold. Email test (hold first in the
detail line, both formats), browser test (tag visible in Board, held job excluded
from the 7+ count and highlight, "1 on hold"), full suite (15 + 9 subtests) and
`tests/test_batch_payment.py` passed. Restarted the local preview (`--lifespan
off`) and inspected the overview, Table, Board, and regenerated email preview.
