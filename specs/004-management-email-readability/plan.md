# Implementation Plan: Management Email Readability

Keep email rendering in `app/services/email_service.py`. Build the HTML and
plain-text bodies from the same report and spending snapshot. Use inline styles
and table structure for email-client compatibility, escape display text, and
preserve the existing card details and SMTP call. Apply the existing `report_title_prefix`
setting to the title and subject.

Constitution check: report data and protected accounting rules stay untouched;
email delivery remains async and credentials stay in configuration. Verify a
sample MIME message without sending it and keep print/export behavior unchanged.
