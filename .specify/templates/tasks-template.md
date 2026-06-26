# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`  
**Prerequisites**: plan.md and spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files
- **[Story]**: Which user story the task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup

- [ ] T001 Read `.specify/memory/constitution.md`
- [ ] T002 Read relevant `.agents/` profile
- [ ] T003 Confirm current behavior and failing/desired scenario

## Phase 2: Tests First

- [ ] T004 Add or update focused regression test
- [ ] T005 Confirm the test fails for the intended reason before implementation

## Phase 3: Implementation

- [ ] T006 Implement the smallest behavior change that satisfies the story
- [ ] T007 Update related operational docs if a rule changed

## Phase 4: Verification

- [ ] T008 Run focused tests
- [ ] T009 Run broader tests if shared behavior changed
- [ ] T010 Record verification results in final handoff
