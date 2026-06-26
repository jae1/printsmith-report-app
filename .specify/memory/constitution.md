# PrintSmith Report App Constitution

## Core Principles

### I. Production Accounting Accuracy

Daily report totals, paid-today rows, and account exclusions must reflect actual
new money and PrintSmith transaction semantics. Use the authoritative payment
tables named in `GEMINI.md`, and do not replace them with easier aggregate
queries unless a spec proves equivalent behavior with tests.

### II. Invoice-Only Reporting

Report features must exclude estimates and quotes by requiring matching records
in both `invoicebase` and `invoice`. Any feature that widens document scope must
be specified as a separate workflow with explicit acceptance criteria.

### III. Business Rule Traceability

Every non-trivial behavior change must trace to a feature spec under `specs/`.
The spec must name the relevant user scenario, business rule, data entities, and
independent verification path. `GEMINI.md` remains the operational rule summary;
Spec Kit artifacts explain the change history and implementation plan.

### IV. Safe Operational State

Local runtime state such as settings JSON, hidden invoice lists, processed
receipt files, pycache, logs, and ad hoc probe scripts must not become the
source of production behavior unless the behavior is specified and reviewed.
Secrets and environment-specific configuration stay out of git.

### V. Role-Aware Ownership

Changes must use the relevant `.agents/` profile as a review lens. SQL/report
logic, expense parsing, UI/export, and sysops/email work each have separate
guardrails; cross-cutting changes require the coordinator role to reconcile
them.

## Development Workflow

Feature work follows this sequence:

1. Specify the user-visible behavior in `specs/[###-feature]/spec.md`.
2. Plan the technical approach in `plan.md`, including Constitution checks.
3. Break implementation into verifiable tasks in `tasks.md`.
4. Implement tasks in order, keeping each user story independently testable.
5. Update `GEMINI.md` only when an operational rule changes or is clarified.

Hotfixes are allowed for urgent production corrections, but the corresponding
spec and plan must be backfilled before the work is considered complete.

## Quality Gates

- Report totals must have regression coverage for payment edge cases.
- SQL changes must identify the PrintSmith tables and date columns used.
- Date filtering must prefer `localdate` where existing rules require it.
- UI/export changes must verify print behavior and hide interactive controls in
  printed output.
- Scheduler/email changes must document async and configuration impacts.

## Governance

This constitution supersedes informal implementation preferences when behavior
is ambiguous. Amendments require updating this file, `GEMINI.md` when relevant,
and any active specs whose acceptance criteria are affected.

**Version**: 1.0.0 | **Ratified**: 2026-06-26 | **Last Amended**: 2026-06-26
