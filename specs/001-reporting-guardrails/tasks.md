# Tasks: Reporting Guardrails Baseline

**Input**: `specs/001-reporting-guardrails/spec.md` and
`specs/001-reporting-guardrails/plan.md`

## Phase 1: Spec Kit Adoption

- [x] T001 Create `.specify/memory/constitution.md`
- [x] T002 Create reusable Spec Kit templates under `.specify/templates/`
- [x] T003 Add `AGENTS.md` to route agents through the Spec Kit workflow

## Phase 2: Baseline Documentation

- [x] T004 Document current reporting guardrails in
  `specs/001-reporting-guardrails/spec.md`
- [x] T005 Document implementation context in
  `specs/001-reporting-guardrails/plan.md`
- [x] T006 Record this task list in `specs/001-reporting-guardrails/tasks.md`

## Phase 3: Follow-Up Cleanup

- [ ] T007 Decide whether ad hoc root-level probe scripts should be moved,
  deleted, or converted into tests
- [ ] T008 Decide whether generated logs and pycache changes should be removed
  from the working tree
- [ ] T009 Add targeted tests for mandatory subsidiary exclusions
- [ ] T010 Add or document focused Ready/In Progress verification

## Phase 4: Ready Toggle Classification

- [x] T011 Update Ready for Pickup query to include pending recent invoices where
  `readytopickup` is true
- [x] T012 Update In Progress query to exclude invoices where `readytopickup` is
  true so sections do not overlap
- [x] T013 Update the protected-rule register, spec, and plan with the ready-toggle rule

## Verification

- [ ] Run `python -m pytest tests/test_batch_payment.py`
- [ ] Verify a live or fixture invoice with `readytopickup = true` and non-ready
  location appears in Ready for Pickup

## Phase 5: Protected Rule Register

- [x] T014 Consolidate current reporting, accounting, state, receipt, UI/export,
  and scheduler/security rules in `PROTECTED_RULES.md`
- [x] T015 Require explicit owner authorization for a specifically named rule
  change in `AGENTS.md` and the Constitution
- [x] T016 Add the protected-rule workflow to the baseline spec and plan
- [x] T017 Route every specialist agent profile through the protected register
