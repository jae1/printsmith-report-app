# Implementation Plan: Management Email Readability

Keep email rendering in `app/services/email_service.py`. Restore the pre-change
HTML structure, adjust card column widths and mobile font sizes, and retain the
partial balance correction. Build HTML and plain text from one spending snapshot.
Escape display text and preserve the SMTP call and configured body title prefix.

Current owner-approved direction supersedes the earlier card-only email layout:
match the main job-sheet UI with an email-safe four-metric overview, proportional
due-date table, and compact tables for all five report groups plus spending.
Share due-count calculation between HTML/plain text in this module; match the
JavaScript scope/date rules from spec 005 without changing report SQL or payloads.
Continue using one spending snapshot, configured body prefix, fixed American-date
subject, branded sender, existing recipients, and async SMTP call. Extend the MIME
and due-count tests, render previews at 375px/desktop, and show the actual HTML
locally. Do not send email for preview. No dependencies or public preview endpoint.

Owner-email cleanup: remove the `#` prefix only in the email HTML/plain-text
invoice labels and suppress Ordered date only for New Today in the shared notes
helper. Keep due dates and all other sections' date context. Extend the existing
MIME test to verify both formats. Financial-summary simplification is a proposal
until the owner selects the metrics; do not change the current overview yet.

2026-10-30 email identity update: use standard-library `email.utils.formataddr`
for the sender display name and configured SMTP address. Format the returned ISO
report date as `%m/%d/%Y` (American month/day/year, per owner correction) and use the fixed `Overnight - ... Daily Report` subject
in the shared `send_report_email` path. Both the API and scheduler call this path;
no caller, recipient, SMTP authentication, TLS, scheduling, or body changes are
needed. Relabel the existing prefix field as a body-title setting and explain
the fixed subject. Update the existing mocked MIME test with dummy SMTP config
and multiple recipients; never send verification mail.

2026-10-30 owner-approved summary: replace only the email overview with three
small native-table blocks (Collected today, New orders count/value, Recorded
spending) computed from the existing paid rows, New Today rows, and the single
spending snapshot. Delete the email due-count helper, due-date bar, Needs
attention metric, and their tests; `app/templates/index.html` keeps its own
due-date logic untouched. Keep section order, row notes (In Progress status,
payment type/method, partial/balance due), right-aligned amounts, no `#`, New
Today without Ordered date, sender/subject, and plain-text parity. No SQL change.

Constitution check: report data and protected accounting rules stay untouched;
email delivery remains async and credentials stay in configuration. Verify a
sample MIME message without sending it and keep print/export behavior unchanged.

## Email Identity Verification (2026-10-30)

The existing MIME test now verifies sender display name/address, two recipients,
the exact `Overnight - 09/30/2026 Daily Report` subject for a historical report,
and unchanged body-prefix behavior using dummy configuration and mocked SMTP.
Full Python suite passed: **13 tests, 9 subtests**. The standalone Chrome UI check
passed after clarifying the prefix field; `git diff --check` passed. No email was
sent for verification. Restarted the local preview to load the Python change;
its email/receipt schedulers remain disabled. No deployment or protected-rule
change was made.

## Main Report Email Verification (2026-10-30)

- Replaced large cards with compact native HTML tables, protected navy/sky
  styling, four metrics, a labeled due-date bar, and six sections in main-report
  order. HTML and plain text use shared due counts and invoice context. Kept
  configured body title, sender/recipients/SMTP call, and American-date subject.
- Due-count regression covers numeric/string invoice deduplication, ready,
  completed/shipping exclusions, partial payments remaining in production,
  historical report dates, timezone-offset strings, raw database datetime values,
  malformed dates, no mutation, and empty reports. MIME assertions cover escaping,
  all invoice groups including New Today, payment/balance details, and headers.
- Full suite: **15 tests, 9 subtests passed**. `git diff --check` passed.
- Generated actual HTML/plain text/EML using current `/api/report`, `/api/spending`,
  and `/api/settings` reads and the real sender function with SMTP mocked. No new
  database query or communication occurred. Temporary artifacts stay outside git.
- Preview opened at `http://127.0.0.1:8766/report.html`, served by a separate local
  temporary-file server. Inspected 840px and 375px screenshots plus a long-name
  partial-payment sample; checked no document overflow, six sections, no controls/
  scripts, and inline-CSS fallback with the style block removed.
- Restarted the local app to load the Python changes; local background jobs stay
  disabled. No deployment or email sending. Gmail/Outlook client rendering has
  not been tested; the preview verifies the generated HTML in Chrome.

## Owner-Email Cleanup Verification (2026-10-30)

Removed invoice-number `#` prefixes from both email formats and suppressed Ordered
date only in New Today. Extended the MIME test to confirm those changes while
preserving due dates and other sections' Ordered dates. All three focused email
tests passed, as did the 840px/375px HTML and inline fallback checks. Regenerated
and refreshed the local email preview, and restarted the local app to load the
Python change. No message was sent. Financial overview changes remain ideas only.

## Three-Block Summary Verification (2026-10-30)

Email overview is now Collected today / New orders / Recorded spending; the email
due-count helper, due-date bar, and Needs attention metric are removed, and the
web report is untouched. Focused email tests passed (3), and so did the full suite
(15 tests, 9 subtests), the main web UI browser check, and the 840px/375px/inline
fallback email checks. `git diff --check` passed. The preview was regenerated from
live local API reads with SMTP mocked; no email was sent. Gmail/Outlook untested.

## Owner Readability Pass (2026-10-30)

Drop the `Due:` note in `_invoice_notes`; add a `metric` class with a
`max-width:480px` media rule that stacks summary cells (desktop/clients without
media queries keep three columns); bump every email font size by 1px; remove
filler captions/headers/footer. Commit the 761x240 `Logotype - Horizontal.png`
(15 KB) as `app/static/email-logo.png` and attach it as a `multipart/related`
inline image (`cid:overnight-logo`) via `EmailMessage.add_related`, with alt text
so blocked images still show the name. Preview swaps the CID for a local data URI.
Verified: focused email tests (3) incl. inline logo MIME part and no `Due:`; full
suite 15 tests + 9 subtests; web UI browser check; 840px three-column / 375px
stacked summary, logo loaded, inline fallback. No email sent; Gmail/Outlook untested.

## At-a-Glance Graphics (2026-10-30)

Jobs bar: proportional `<td>` segments from the four section lengths, legend
with counts; HTML and plain text. Trend: `send_report_email` loads the six prior
days with `asyncio.to_thread(report_service.get_report_data, day)` sequentially
(each call opens its own connection; ~0.27s each locally) so the scheduler loop
is not blocked, sums each day's paid-row grandtotal, and passes `trend` to both
renderers. Bars are nested tables with pixel heights (max 60px) for Outlook.
A history failure is logged and the trend omitted rather than blocking delivery.
Preview patches history to read the local `/api/report` like the main data.
Verified: 4 focused email tests (trend days/values from paid rows only, jobs bar
widths and no total, history-failure fallback still sends); full suite; web UI
check; 840px/375px/inline fallback. Legend swatches use background spans because
the black-square glyph was missing in Chrome's fallback font. No email sent.
Superseded the same day: owner moved both graphics to the web report (spec 005).
Removed the email chart helpers, history lookups, trend tests, and preview patch.
