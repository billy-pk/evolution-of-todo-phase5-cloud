---
id: 0003
title: Remove Legacy Endpoints Tasks
stage: tasks
date: 2025-12-15
surface: claude-code-cli
model: claude-sonnet-4.5
feature: 003-remove-legacy-endpoints
branch: 003-remove-legacy-endpoints
user: bilali
command: /sp.tasks
labels: [refactoring, cleanup, phase3, task-generation]
links:
  spec: specs/003-remove-legacy-endpoints/spec.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  - path: specs/003-remove-legacy-endpoints/tasks.md
    created: true
    modified: false
    lines_added: 445
    lines_removed: 0
tests:
  - none
---

## Prompt

User invoked `/sp.tasks` command to generate actionable implementation tasks for removing legacy REST API endpoints and UI components.

**Command**: `/sp.tasks` (no additional arguments)

**Context**:
- Specification: specs/003-remove-legacy-endpoints/spec.md (3 user stories with priorities)
- Plan: specs/003-remove-legacy-endpoints/plan.md (complete implementation plan)
- Feature branch: 003-remove-legacy-endpoints
- Task: Break down removal work into executable tasks organized by user story

## Response snapshot

Successfully generated tasks.md with 57 tasks organized by 3 user stories:

### Task Organization

**By User Story** (spec.md priorities):
1. **User Story 1** (P1): Remove Backend Legacy Task Endpoints - 14 tasks
2. **User Story 2** (P2): Remove Frontend Legacy Task UI - 15 tasks
3. **User Story 3** (P3): Clean Up API Client Methods - 15 tasks

**By Phase**:
- Phase 1: Setup (4 tasks)
- Phase 2: Foundational (0 tasks - n/a for removal work)
- Phase 3: User Story 1 - Backend Removal (14 tasks)
- Phase 4: User Story 2 - Frontend UI Removal (15 tasks)
- Phase 5: User Story 3 - API Cleanup (15 tasks)
- Phase 6: Polish & Cross-Cutting (9 tasks)

### Task Breakdown Per User Story

**User Story 1 (Backend - P1)**:
- T005-T008: Delete files and restart (4 implementation tasks)
- T009-T018: Verification (10 verification tasks)
  - 5 endpoint 404 tests
  - 5 chat interface CRUD tests

**User Story 2 (Frontend - P2)**:
- T019-T024: Delete UI files and restart (6 implementation tasks)
  - 4 parallel deletions (TaskForm, TaskList, TaskItem, page.tsx)
  - Navbar cleanup
  - Server restart
- T025-T033: Verification (9 verification tasks)
  - Route 404 verification
  - Component deletion verification
  - Chat UI functional testing

**User Story 3 (API Cleanup - P3)**:
- T034-T041: Remove API methods (8 implementation tasks)
  - Remove 5 task methods (createTask, listTasks, updateTask, deleteTask, toggleComplete)
  - Verify helper functions remain
- T042-T048: Verification (7 verification tasks)
  - 5 parallel grep searches for method usage
  - Auth and chat API testing

### Dependencies Identified

**Sequential by Design**:
- US1 (Backend) → US2 (Frontend) → US3 (API Cleanup)
- Rationale: Backend must be clean before UI removal to prevent new dependencies
- Frontend must be removed before API cleanup to catch orphaned method calls

**Within-Story Dependencies**:
- Each story: Implementation → Restart → Verification
- Verification tasks can only run after implementation complete

### Parallel Opportunities (16 tasks, 28% of total)

**Setup Phase**:
- T003, T004 (backup, database count)

**User Story 2**:
- T019-T022 (delete 4 files simultaneously)

**User Story 3**:
- T042-T046 (5 grep searches in parallel)

**Polish Phase**:
- T049-T050, T053-T055 (builds and documentation)

### Format Validation

**All 57 tasks follow strict checklist format**:
- ✅ Checkbox prefix `- [ ]`
- ✅ Sequential Task IDs (T001-T057)
- ✅ [P] markers for parallelizable tasks (16 tasks)
- ✅ [US#] labels for user story tasks (44 tasks across US1, US2, US3)
- ✅ Exact file paths in descriptions
- ✅ Clear action verbs (Delete, Remove, Verify, Test)

**Example formats**:
- `- [ ] T005 [US1] Delete backend/routes/tasks.py file (271 lines)`
- `- [ ] T019 [P] [US2] Delete frontend/app/(dashboard)/tasks/page.tsx file (310 lines)`
- `- [ ] T042 [US3] Search for createTask usage with grep -r "api.createTask" frontend/ (expect no results)`

### Independent Test Criteria (Per User Story)

**US1**: Access removed endpoints, verify 404s, test chat CRUD operations
**US2**: Navigate to /tasks (verify 404), verify component deletion, test chat UI
**US3**: Search codebase for removed methods (verify none), test auth and chat APIs

### Suggested MVP Scope

**MVP = User Story 1 Only**
- Complete backend endpoint removal (14 tasks)
- Verify all endpoints return 404
- Verify chat interface provides full CRUD via MCP tools
- Stop and validate before proceeding to frontend

**Rationale**: Backend removal is independently valuable and low-risk. Can be deployed alone.

## Outcome

- ✅ Impact: Complete task list generated with 57 executable tasks
- 🧪 Tests: Manual verification tasks embedded in each user story (33 verification tasks total)
- 📁 Files: 1 file created (tasks.md)
- 🔁 Next prompts: `/sp.implement` to execute tasks, or manual execution task-by-task
- 🧠 Reflection: Tasks organized by user story enable incremental delivery. Each story is independently testable and deployable.

## Evaluation notes (flywheel)

- Failure modes observed: None - tasks generated successfully
- Graders run and results (PASS/FAIL): Format validation PASS (all 57 tasks follow checklist format)
- Prompt variant (if applicable): Standard /sp.tasks workflow with user story organization
- Next experiment (smallest change to try): Execute MVP (US1 only - 14 tasks) to validate approach before proceeding
