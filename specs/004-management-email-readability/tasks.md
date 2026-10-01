# Tasks: Management Email Readability

- [x] Inspect report row fields and the current HTML email.
- [x] Show partial balance context in Paid Today cards.
- [x] Make order, payment, and spending amounts visually distinct.
- [x] Add a useful plain-text alternative and configured title prefix.
- [x] Verify the rendered MIME message without sending mail.
- [ ] Rerun live report regressions when database access is available; this
  session's network policy blocked the database connection.

## Simpler Email Revision

- [x] Restore the prior hierarchy and remove the expanded summary grid.
- [x] Restore compact two-column cards and align the amount column.
- [x] Keep partial balance context, safe text rendering, and plain-text email.
- [x] Rerun the MIME content check with the restored hierarchy.
- [ ] Check the revised layout in a real email client; the browser policy blocks
  opening the local HTML preview from this session.
