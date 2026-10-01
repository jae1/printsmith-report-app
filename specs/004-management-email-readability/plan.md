# Implementation Plan: Management Email Readability

Keep email rendering in `app/services/email_service.py`. Restore the pre-change
HTML structure, adjust card column widths and mobile font sizes, and retain the
partial balance correction. Build HTML and plain text from one spending snapshot.
Escape display text and preserve the SMTP call and configured title prefix.

Constitution check: report data and protected accounting rules stay untouched;
email delivery remains async and credentials stay in configuration. Verify a
sample MIME message without sending it and keep print/export behavior unchanged.
