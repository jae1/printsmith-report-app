# Tasks: Accounting Regression and Release Gates

- [x] T001 Read Constitution, protected rules, role guardrails, and fix history.
- [x] T002 Specify allowed corrections and release behavior before code changes.
- [x] T003 Prove deterministic collision/future-order failures; fix shared queries.
- [x] T004 Cover existing accounting shapes with offline relational fixtures.
- [x] T005 Add offline CI and explicit live-test release verification.
- [x] T006 Add historical snapshot comparison and fail-closed baseline handling.
- [x] T007 Add launched revision health endpoint and its regression test.
- [x] T008 Prepare isolated Windows releases while monitoring the working app.
- [x] T009 Gate switches, verify new revision, and retain/restore previous release.
- [x] T010 Document first baseline review, deployment, and rollback.
- [x] T011 Run focused/offline/live checks and record platform limitations.

## Verification Results

- Collision/future-order fixtures failed against the original implementation,
  then passed after the shared query corrections. Twelve relational scenarios
  cover existing accounting behavior; a separate invariance test proves adding
  estimate rows cannot change invoice reports.
- Final suite after integrating the concurrent layout/job-hold update: 34
  unittest methods passed with live checks enabled and the
  imported application dependencies pinned from `requirements.txt` (Python 3.13).
  This includes all eight live PrintSmith payment regressions and the functional
  PowerShell harness. Offline CI deliberately skips the live class; release
  checks run it separately and reject any skipped live checks.
- The concurrent layout/job-hold update is preserved. Its standalone Playwright
  browser regression also passed after integration; the offline relational
  adapter includes the hold-state schema used by the production queries.
- Full release checker passed a matching temporary baseline. Comparing against
  the original inflated historical report snapshot exited with failure and
  generated a review diff, preserving the approved reference.
- Read-only comparison across 12 representative dates changed paid totals only
  for 2024-05-24 ($6,039.89 to $4,250.23) and 2024-06-03 ($5,257.25 to
  $4,572.15), matching the four removed estimate/invoice duplicates. Other
  sampled accounting snapshots stayed unchanged.
- PowerShell 7.7 parsing and fully mocked control flow passed, including gate
  failure, timeout, crash recovery during preparation, unknown port owner,
  unhealthy startup, pending-switch recovery, interrupted manual rollback, and
  legacy adoption/reboot recovery. No real server or Scheduled Task was changed.
- Git diff whitespace checks passed. Temporary captures and logs are outside
  production paths; no local production baseline was approved or committed.

## External Activation Still Required

The release includes the CI workflow and review ownership. A repository
administrator must require the CI check and code-owner review (current
credentials have push, not admin). Approve the server baseline and perform the
documented Windows controller migration/reboot verification. Production
deployment has not been independently verified.

## Pending Owner Decision

Rule 8 (held-deposit balance sources) and rule 13 (same-account mixed-contact
payments) require explicit authorization before changing their protected scope.
Preserve current behavior until the owner answers the named-rule question.
