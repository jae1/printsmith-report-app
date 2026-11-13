# Feature Specification: Accounting Regression and Release Gates

**Created**: 2026-11-12
**Status**: Implemented; production migration and repository-admin settings pending

## Intent

Prevent a later update from undoing a confirmed accounting fix. Every corrected
failure needs a deterministic test, and the Windows watchdog must validate a
candidate before switching away from a working release.

## User Scenarios and Acceptance

1. An estimate reuses a real invoice number. The invoice's payment is counted
   once; adding the estimate does not change the historical report.
2. A historical Ready report never includes invoices ordered after its date.
3. Prior deposits, partial/final AR payments, plain linked payments, multi-method
   batches, same-day deposit returns, no-new-money exclusions, mandatory account
   exclusions, and date-scoped hiding remain covered without a live database.
4. An accounting fix adds a failing regression first. Existing live regressions
   remain a mandatory release check, separate from offline CI checks.
5. Candidate historical accounting snapshots differ from the approved baseline.
   Deployment stops and produces a readable difference plus a candidate snapshot
   for operator review. No automatic baseline acceptance is allowed.
6. Candidate preparation or checks fail. The working app keeps its original
   source, dependencies, and runtime JSON; health monitoring continues.
7. A new server fails its health/version check after switching. The watchdog
   restores the last verified release. Operators can also request rollback.
8. The running app reports its launched revision, independent of checkout HEAD.

## Boundaries and Protected Rules

All existing protected rules remain in force. Invoice filtering implements rule
1; the report-date upper bound implements rule 2. Today's amounts and lifetime
balances stay separate. Mixed-contact attribution under rule 13 and adding held
deposit sources under rule 8 await explicit owner authorization; neither is
silently changed by this feature. Any authorization must update the register,
Constitution, relevant artifacts, and regression coverage together.

CI, tests, and snapshots must never send email, synchronize a mailbox, or write
to PrintSmith. Runtime baselines, candidate snapshots, release manifests, release
directories, logs, and probe outputs remain untracked. Fixed synthetic relational
fixtures are test data, not runtime state or replacement accounting policy.

## Release Requirements

- Offline tests run on pull requests and pushes, with pinned application
  dependencies and no production credentials/database required.
- Release checks explicitly enable the existing live database regression suite;
  unavailable database access is a failed release check, not a skipped success.
- Baselines cover representative historical dates and compare per-invoice
  report-date amounts/methods/types and new-order amounts. Mutable current queue
  status and lifetime balances are excluded from historical comparisons.
- Intentional changes require review of the generated difference and explicit
  baseline capture/acceptance before deployment; editing a baseline does not
  authorize a protected-rule change.
- Windows prepares isolated release source and dependencies before stopping the
  working app, preserves the original runtime working directory, checks version
  identity after launch, and retains a previous verified launch descriptor.

## Verification

Run deterministic fixtures against the actual report SQL/aggregation and prove
the collision and future-order tests fail before fixes. Run the full offline
suite, the eight existing live payment regressions, release-check failure-path
tests, and Windows orchestration tests where PowerShell is available. Report
Windows-only limits explicitly. Do not publish/deploy during implementation.
