# Tasks: AR Batch Partial Paid Today Attribution

**Input**: `specs/002-ar-batch-partial-paid-today/spec.md`

## Phase 1: Diagnosis

- [x] T001 Inspect Paid Today aggregation in `app/services/report_service.py`
- [x] T002 Inspect PrintSmith schema for AR payment source tables
- [x] T003 Identify live regression invoice `56276`

## Phase 2: Tests

- [x] T004 Add regression coverage for partial and final AR batch attribution
  in `tests/test_batch_payment.py`

## Phase 3: Implementation

- [x] T005 Split AR `Payment(...)` batch amounts using invoice-level account
  history payment fields
- [x] T006 Stop using lifetime payment detail sums as today's display amount

## Phase 4: Verification

- [x] T007 Run focused regression test
