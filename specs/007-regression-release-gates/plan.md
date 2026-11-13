# Implementation Plan: Accounting Regression and Release Gates

1. Add sanitized relational fixtures and execute the real report entry point
   against an in-memory SQL adapter. Add failing estimate-collision and future
   Ready regressions, then make the smallest rule-preserving query corrections.
2. Separate offline tests from explicitly enabled live regressions. Add an
   offline CI workflow and a standard-library release checker that runs both
   suites and compares normalized historical snapshots with an approved local
   baseline. A missing baseline or unexplained difference fails closed.
3. Expose launched revision at `/api/health`. Prepare isolated Windows releases
   in a background job, validate before switching, retain the last known-good
   descriptor, and recover automatically if the candidate cannot serve its own
   revision. Continue monitoring while preparation is slow.
4. Document baseline review, first migration, checks, deployment, and rollback.
   Keep `AGENTS.md` verification commands current. Run focused and broad checks.

## Constitution Check

Preserve invoice-only filtering, report-date money semantics, role ownership,
runtime-state isolation, and all protected rules. No rule 8 or 13 behavior change
is included without the pending explicit owner authorization. No secrets are
required for offline CI; live checks use configured read access only.

## Ownership

- SQL/report role: report query corrections and relational regression fixtures.
- Sysops role: isolated Windows preparation, health identity, recovery/rollback.
- Coordinator: release checker, CI, integration opt-in, documentation, and shared
  verification. No code or runtime deployment occurs as part of this work.

## Manual Database Probe Intent

Use read-only schema inspection to verify invoice/estimate joins and compare
known historical payment amounts before/after correction. Never use lifetime
detail totals as report-date payment evidence. Preserve all existing known-date
payment expectations. No probe scripts or output enter production paths.

## Implementation and Verification Notes

The snapshot compares candidate imports explicitly, even when tests retain the
original runtime working directory. Non-finite monetary values, missing tests,
skipped live checks, missing baselines, and snapshot changes fail closed.
Windows preparation uses a separate bounded native process and isolated build
directories; the controller retains responsibility for health and recovery.
See `tasks.md` for the completed checks and external activation limits, and
`RELEASING.md` for baseline review and controller migration safeguards.
