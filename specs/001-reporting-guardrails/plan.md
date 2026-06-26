# Implementation Plan: Reporting Guardrails Baseline

**Branch**: `001-reporting-guardrails` | **Date**: 2026-06-26 |
**Spec**: `specs/001-reporting-guardrails/spec.md`
**Input**: Baseline specification for current reporting rules.

## Summary

Capture the current PrintSmith Report App business rules in Spec Kit form so
future changes are planned, testable, and traceable. This is a documentation and
governance adoption step; it does not change runtime behavior.

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: FastAPI, psycopg2, Jinja2, pypdf  
**Storage**: PostgreSQL PrintSmith database and local JSON state files  
**Testing**: pytest  
**Target Platform**: Local/server-hosted reporting web app  
**Project Type**: Python web service with server-rendered UI  
**Performance Goals**: Preserve current report responsiveness  
**Constraints**: Do not weaken accounting, invoice filtering, or local-state
guardrails  
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

No new runtime research is required for the baseline. Source material:

- `GEMINI.md`
- `.agents/`
- Recent commits affecting `app/services/report_service.py`
- Recent commit affecting `app/services/settings_service.py`
- Existing `tests/test_batch_payment.py`

## Phase 1: Design

The baseline design maps current business rules to user stories, requirements,
and success criteria. Future changes should add focused specs rather than
expanding this baseline indefinitely.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
