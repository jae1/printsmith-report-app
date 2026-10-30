# Tasks: Management Email Readability

- [x] Inspect report row fields and the current HTML email.
- [x] Show partial balance context in Paid Today cards.
- [x] Make order, payment, and spending amounts visually distinct.
- [x] Add a useful plain-text alternative and configured title prefix.
- [x] Verify the rendered MIME message without sending mail.
- [x] Rerun live report regressions; full suite passed on 2026-10-30.

## Simpler Email Revision

- [x] Restore the prior hierarchy and remove the expanded summary grid.
- [x] Restore compact two-column cards and align the amount column.
- [x] Keep partial balance context, safe text rendering, and plain-text email.
- [x] Rerun the MIME content check with the restored hierarchy.
- [ ] Check the revised layout in real Gmail/Outlook clients; browser preview
  and inline-CSS fallback checks do not verify those clients' rendering engines.

## Email Identity and Subject (2026-10-30)

- [x] Inspect the shared sender and its API/scheduler callers; preserve SMTP rules.
- [x] Set the sender display name and fixed report-date subject.
- [x] Apply the owner's correction to American MM/DD/YYYY subject dates.
- [x] Clarify that the prefix setting applies to the body title.
- [x] Verify headers, recipients, and unchanged body with mocked SMTP; run tests.

## Main Report Style in Email (2026-10-30)

- [x] Implement email-safe overview, due-date bar, and compact six-section tables.
- [x] Match HTML/plain-text data and test money, due scope, dates, empty states,
  escaping, payment context, and corrected American subject.
- [x] Inspect desktop/phone previews and show the actual generated HTML locally.
- [x] Reload the local server, run regression checks, and record limitations.
- [x] Remove email invoice `#` prefixes and New Today Ordered dates; verify both
  formats and refresh the preview. Propose money-focused summary ideas separately.

## Owner Three-Block Summary (2026-10-30)

- [x] Update spec/plan for the approved Collected / New orders / Recorded spending summary.
- [x] Replace the email four-metric overview and due-date bar; remove email due-count code.
- [x] Update HTML/plain-text tests for the three values and absence of due-date summary.
- [x] Regenerate the local preview with SMTP mocked, check 840px/375px/inline fallback, run suite.

## Owner Readability Pass (2026-10-30)

- [x] Remove due dates, stack summary on phones, +1px text, remove filler text.
- [x] Add the official logotype as an inline CID image; test the MIME part.
- [x] Regenerate preview, check 840px/375px/fallback, run suite.
- [x] Center the logo, title, and report date on phones; verify 375px/840px.
- [x] Center header on all screens; drop missing-account dash and Paid Today Ordered date; test both formats.

## At-a-Glance Graphics (2026-10-30)

- [x] Jobs bar with legend in HTML/plain text; test proportions and no total.
- [x] Seven-day Collected trend from existing report data; test values, fallback.
- [x] Regenerate preview, check 840px/375px/fallback, run suite.
- [x] Owner moved both graphics to the web report; remove them from the email.
