# PrintSmith Report App Agent Guide

This repository uses a Spec Kit style workflow for new work. Specifications are
the source of truth for feature intent, and implementation should trace back to
the active spec, plan, and tasks.

## Required Workflow

For any non-trivial behavior change:

1. Read `.specify/memory/constitution.md`.
2. Read the relevant feature directory under `specs/`.
3. If no feature spec exists, create one before changing code.
4. Keep the implementation plan and tasks current as the work changes.
5. Preserve the domain rules in `GEMINI.md` and the role guardrails in `.agents/`.

Small diagnostics, log inspection, and one-off verification scripts may skip a
new spec, but they must not change production behavior without updating the
appropriate Spec Kit artifacts.

## Existing Role System

The legacy agent profiles remain active and are now treated as domain-specific
review lenses:

- `.agents/1_coordinator.md`: rule protection, tests, shared verification
- `.agents/2_sql_report_logic.md`: report SQL, invoice filtering, accounting
- `.agents/3_expense_parser_sync.md`: receipt parsing and spending sync
- `.agents/4_web_ui.md`: templates, UI, and export presentation
- `.agents/5_sysops_email.md`: app startup, settings, email, scheduling

Use `python agent_selector.py --recommend <path>` when ownership is unclear.

## Spec Kit Locations

- Constitution: `.specify/memory/constitution.md`
- Templates and overrides: `.specify/templates/`
- Feature specs: `specs/[###-feature-name]/spec.md`
- Implementation plans: `specs/[###-feature-name]/plan.md`
- Task lists: `specs/[###-feature-name]/tasks.md`

## Verification Expectations

Before committing behavior changes, run the smallest relevant verification:

- Report logic: `python -m pytest tests/test_batch_payment.py`
- Broader changes: `python -m pytest`
- Manual database probes: keep scripts out of production paths and document the
  exact query intent in the relevant spec or plan.

Do not commit generated runtime files such as `__pycache__/`, logs, local JSON
state, or ad hoc probe outputs.
