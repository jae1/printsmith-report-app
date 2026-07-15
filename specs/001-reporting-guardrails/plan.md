# Implementation Plan: Reporting Guardrails Baseline

**Branch**: `001-reporting-guardrails` | **Date**: 2026-06-26 |
**Spec**: `specs/001-reporting-guardrails/spec.md`
**Input**: Baseline specification for current reporting rules.

## Summary

Capture and maintain the PrintSmith Report App business rules in Spec Kit form
so reporting changes are planned, testable, and traceable. This update changes
Ready/In Progress classification so the PrintSmith `readytopickup` toggle is
treated as a ready signal alongside ready-like production locations. The
baseline also establishes `PROTECTED_RULES.md` as the canonical protected-rule register
and requires explicit owner authorization for any named rule change.

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: FastAPI, psycopg2, Jinja2, pypdf  
**Storage**: PostgreSQL PrintSmith database and local JSON state files  
**Testing**: pytest  
**Target Platform**: Local/server-hosted reporting web app  
**Project Type**: Python web service with server-rendered UI  
**Performance Goals**: Preserve current report responsiveness  
**Constraints**: Do not weaken accounting, invoice filtering, local-state
guardrails, the 10-day Ready for Pickup recency limit, or any protected rule
without explicit owner authorization for that rule
**Scale/Scope**: Single internal reporting app

## Constitution Check

- [x] Production accounting accuracy preserved
- [x] Invoice-only reporting preserved where applicable
- [x] Behavior traces to spec requirements
- [x] Local runtime state kept out of source-controlled behavior unless specified
- [x] Relevant `.agents/` role reviewed

## Project Structure

```text
app/
├── api/
├── core/
├── db/
├── services/
└── templates/
tests/
specs/
```

**Structure Decision**: Keep the existing single Python app structure.

## Phase 0: Research

Source material:

- `PROTECTED_RULES.md`
- `.agents/`
- Recent commits affecting `app/services/report_service.py`
- Recent commit affecting `app/services/settings_service.py`
- Existing `tests/test_batch_payment.py`
- User clarification that enabling PrintSmith `readytopickup` must move pending
  recent invoices into Ready for Pickup even when production location differs

## Phase 1: Design

Ready for Pickup classification now uses one ready predicate:
`COALESCE(ib.readytopickup, false) = true OR pl.name IN ('Ready for Pickup',
'Ready for Delivery', 'Complete')`. In Progress applies the inverse ready-toggle
guard and keeps the existing non-ready production location filter so the same
pending invoice does not appear in both sections.

Protected-rule governance is enforced at every repository entry point:
`AGENTS.md` requires reading `PROTECTED_RULES.md`; the Constitution limits rule-change
authority to explicit owner instructions for a named rule; feature specs must
trace any authorized change; and all specialist profiles inherit the same gate.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
