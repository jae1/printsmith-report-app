# Implementation Plan: AR Batch Partial Paid Today Attribution

**Branch**: `002-ar-batch-partial-paid-today` | **Date**: 2026-06-26 |
**Spec**: `specs/002-ar-batch-partial-paid-today/spec.md`
**Input**: Bug report for same-account AR batch invoices with older partial
payments/deposits.

## Summary

Change Paid Today attribution so generic AR batch rows are split using
invoice-level payment fields from account history instead of lifetime paid totals
from payment detail tables. Keep detail tables for balance calculation only.

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: FastAPI, psycopg2  
**Storage**: PostgreSQL PrintSmith database  
**Testing**: unittest/pytest-compatible live regression tests  
**Target Platform**: Local/server-hosted reporting web app  
**Project Type**: Python web service  
**Performance Goals**: Avoid expensive per-row scans beyond the listed invoices
in each AR batch  
**Constraints**: Preserve invoice-only filtering and existing batch attribution  
**Scale/Scope**: Paid Today section only

## Constitution Check

- [x] Production accounting accuracy preserved
- [x] Invoice-only reporting preserved where applicable
- [x] Behavior traces to spec requirements
- [x] Local runtime state kept out of source-controlled behavior unless specified
- [x] SQL & Report Logic role reviewed

## Project Structure

```text
app/services/report_service.py
tests/test_batch_payment.py
specs/002-ar-batch-partial-paid-today/
```

**Structure Decision**: Keep change scoped to report service and existing live
regression test file.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Live DB regression | Existing app tests use live PrintSmith data | Mocking would miss the PrintSmith account-history shape that caused the bug |
