# Tasks: Remove Legacy Task API and UI

**Feature Branch**: `003-remove-legacy-endpoints`
**Input**: Design documents from `/specs/003-remove-legacy-endpoints/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Manual verification only (no automated tests for removal work)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root
- **Frontend**: `frontend/` at repository root
- All paths are relative to `/home/bilali/vibe-coding-projects/evolution-of-todo/phase3-ai-chatbot/`

---

## Phase 1: Setup (No Dependencies)

**Purpose**: Verify prerequisites and prepare for removal

- [x] T001 Verify chat interface is accessible at frontend/app/(dashboard)/chat/page.tsx
- [x] T002 Verify MCP server tools exist at backend/tools/server.py with 5 task tools
- [x] T003 [P] Create backup of current git state with `git stash` or commit current work
- [x] T004 [P] Document current task count in database for integrity verification

**Checkpoint**: Prerequisites verified - safe to proceed with removal

---

## Phase 2: Foundational (No User Story Specific Work)

**Purpose**: No foundational work required - this is purely removal

**Note**: Since this feature only removes code, there are no blocking prerequisites. We can proceed directly to user story implementation.

---

## Phase 3: User Story 1 - Remove Backend Legacy Task Endpoints (Priority: P1) 🎯 MVP

**Goal**: Remove all REST API endpoints for task management from backend, leaving only chat interface for task operations

**Independent Test**: Access removed endpoints (GET/POST/PUT/PATCH/DELETE /api/{user_id}/tasks) and verify 404 responses, then use chat interface to verify all CRUD operations still work via MCP tools

### Implementation for User Story 1

- [x] T005 [US1] Delete backend/routes/tasks.py file (271 lines)
- [x] T006 [US1] Remove tasks import from backend/main.py (lines 95-96: "from routes import tasks")
- [x] T007 [US1] Remove tasks router inclusion from backend/main.py (lines 96-101: app.include_router block)
- [x] T008 [US1] Restart backend server with `cd backend && uvicorn main:app --reload`

### Verification for User Story 1

- [x] T009 [US1] Verify GET /api/test-user/tasks returns 404 Not Found
- [x] T010 [US1] Verify POST /api/test-user/tasks returns 404 Not Found
- [x] T011 [US1] Verify PUT /api/test-user/tasks/some-id returns 404 Not Found
- [x] T012 [US1] Verify PATCH /api/test-user/tasks/some-id/complete returns 404 Not Found
- [x] T013 [US1] Verify DELETE /api/test-user/tasks/some-id returns 404 Not Found
- [ ] T014 [US1] Test chat interface: Create task via "add a task to buy milk"
- [ ] T015 [US1] Test chat interface: List tasks via "list my tasks"
- [ ] T016 [US1] Test chat interface: Update task via "update task to buy milk and bread"
- [ ] T017 [US1] Test chat interface: Complete task via "mark task as complete"
- [ ] T018 [US1] Test chat interface: Delete task via "delete the task"

**Checkpoint**: User Story 1 complete - backend endpoints removed, chat interface fully functional

---

## Phase 4: User Story 2 - Remove Frontend Legacy Task UI (Priority: P2)

**Goal**: Remove all frontend task UI components and pages, leaving only chat interface for user interaction

**Independent Test**: Navigate to /tasks route and verify 404, verify TaskForm/TaskList/TaskItem components are deleted, use chat interface at /chat to perform all task operations

### Implementation for User Story 2

- [x] T019 [P] [US2] Delete frontend/app/(dashboard)/tasks/page.tsx file (310 lines)
- [x] T020 [P] [US2] Delete frontend/components/TaskForm.tsx file (~100 lines)
- [x] T021 [P] [US2] Delete frontend/components/TaskList.tsx file (~80 lines)
- [x] T022 [P] [US2] Delete frontend/components/TaskItem.tsx file (~120 lines)
- [x] T023 [US2] Check frontend/components/Navbar.tsx for /tasks link and remove if present
- [x] T024 [US2] Restart frontend server with `cd frontend && npm run dev`

### Verification for User Story 2

- [x] T025 [US2] Navigate to http://localhost:3000/tasks and verify 404 page
- [x] T026 [US2] Navigate to http://localhost:3000/chat and verify chat interface loads
- [x] T027 [US2] Verify no TaskForm/TaskList/TaskItem imports exist with `grep -r "TaskForm\|TaskList\|TaskItem" frontend/`
- [x] T028 [US2] Test chat UI: Sign in and access chat interface
- [x] T029 [US2] Test chat UI: Create task conversationally
- [x] T030 [US2] Test chat UI: List tasks conversationally
- [x] T031 [US2] Test chat UI: Update task conversationally
- [x] T032 [US2] Test chat UI: Complete task conversationally
- [x] T033 [US2] Test chat UI: Delete task conversationally

**Checkpoint**: User Story 2 complete - frontend UI removed, chat interface is sole task management UI

---

## Phase 5: User Story 3 - Clean Up API Client Methods (Priority: P3)

**Goal**: Remove unused task API methods from frontend API client

**Independent Test**: Search codebase for removed API method calls and verify none exist, confirm chat API methods still work

### Implementation for User Story 3

- [x] T034 [US3] Read frontend/lib/api.ts to identify task API methods
- [x] T035 [US3] Remove createTask method from frontend/lib/api.ts
- [x] T036 [US3] Remove listTasks method from frontend/lib/api.ts
- [x] T037 [US3] Remove updateTask method from frontend/lib/api.ts
- [x] T038 [US3] Remove deleteTask method from frontend/lib/api.ts
- [x] T039 [US3] Remove toggleComplete method from frontend/lib/api.ts
- [x] T040 [US3] Verify apiRequest helper function remains (used by chat API)
- [x] T041 [US3] Verify authentication-related API methods remain intact

### Verification for User Story 3

- [x] T042 [US3] Search for createTask usage with `grep -r "api.createTask" frontend/` (expect no results)
- [x] T043 [US3] Search for listTasks usage with `grep -r "api.listTasks" frontend/` (expect no results)
- [x] T044 [US3] Search for updateTask usage with `grep -r "api.updateTask" frontend/` (expect no results)
- [x] T045 [US3] Search for deleteTask usage with `grep -r "api.deleteTask" frontend/` (expect no results)
- [x] T046 [US3] Search for toggleComplete usage with `grep -r "api.toggleComplete" frontend/` (expect no results)
- [x] T047 [US3] Test authentication still works by signing in at /signin
- [x] T048 [US3] Test chat API still works by sending message in chat interface

**Checkpoint**: User Story 3 complete - API client cleaned up, no unused methods remain

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across all changes

- [x] T049 [P] Run frontend build with `cd frontend && npm run build` to verify no import errors
- [x] T050 [P] Run backend with `cd backend && python -c "import main"` to verify no import errors
- [x] T051 Verify database task count unchanged with `psql $DATABASE_URL -c "SELECT COUNT(*) FROM tasks;"`
- [x] T052 Calculate lines of code removed with `git diff --stat 002-chatkit-refactor...003-remove-legacy-endpoints`
- [x] T053 [P] Update CLAUDE.md to remove references to tasks REST API if any exist
- [x] T054 [P] Update backend/CLAUDE.md to remove references to routes/tasks.py if any exist
- [x] T055 [P] Update frontend/CLAUDE.md to remove references to tasks page/components if any exist
- [x] T056 Run quickstart.md verification steps (10 phases) to validate all success criteria
- [x] T057 Commit changes with message: "feat: remove legacy task REST API and UI per constitution v2.0.0"

**Checkpoint**: All changes complete, verified, and documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: N/A - no foundational work for removal task
- **User Story 1 (Phase 3)**: Depends on Setup completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (backend must be clean first)
- **User Story 3 (Phase 5)**: Depends on User Story 2 completion (UI must be removed before API cleanup)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup - No dependencies on other stories
- **User Story 2 (P2)**: **DEPENDS ON** User Story 1 - Backend must be clean before removing frontend
- **User Story 3 (P3)**: **DEPENDS ON** User Story 2 - UI must be removed before API method cleanup

**Rationale**: Sequential dependency is intentional. Removing backend first ensures no new code can be written against legacy endpoints. Removing UI second ensures no user-facing breakage. API cleanup last ensures no orphaned method calls.

### Within Each User Story

**User Story 1** (Backend Removal):
1. Delete files first (T005-T007)
2. Restart server (T008)
3. Verify endpoints return 404 (T009-T013)
4. Verify chat interface works (T014-T018)

**User Story 2** (Frontend UI Removal):
1. Delete all component files in parallel (T019-T022 can run in parallel)
2. Check/update Navbar (T023)
3. Restart server (T024)
4. Verify routes and chat interface (T025-T033)

**User Story 3** (API Cleanup):
1. Remove methods sequentially (T034-T041)
2. Verify no usage (T042-T046 can run in parallel)
3. Test auth and chat (T047-T048)

### Parallel Opportunities

- **Setup Phase**: T003 and T004 can run in parallel (different operations)
- **User Story 1**: None - must be sequential for verification
- **User Story 2**: T019-T022 can run in parallel (deleting different files)
- **User Story 3**: T042-T046 can run in parallel (independent grep searches)
- **Polish Phase**: T049-T050 and T053-T055 can run in parallel (independent file operations)

---

## Parallel Example: User Story 2

```bash
# Launch all file deletions together (tasks T019-T022):
Task: "Delete frontend/app/(dashboard)/tasks/page.tsx file"
Task: "Delete frontend/components/TaskForm.tsx file"
Task: "Delete frontend/components/TaskList.tsx file"
Task: "Delete frontend/components/TaskItem.tsx file"

# Then sequentially:
Task: "Check frontend/components/Navbar.tsx for /tasks link and remove if present"
Task: "Restart frontend server"

# Then run verifications
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Backend Removal)
3. **STOP and VALIDATE**: Test all 10 User Story 1 verification tasks
4. Confirm chat interface provides full CRUD functionality
5. **Decision Point**: If US1 works, proceed to US2. If not, rollback and debug.

### Incremental Delivery (Recommended)

1. Complete Setup → Verify prerequisites ready
2. Complete User Story 1 → Verify backend clean, chat works → Commit
3. Complete User Story 2 → Verify frontend clean, chat UI works → Commit
4. Complete User Story 3 → Verify API client clean, auth works → Commit
5. Complete Polish → Final validation → Final commit

Each user story completion is a deployable increment with independent value.

### Parallel Team Strategy

**Not applicable** - This is a cleanup task with sequential dependencies. User Stories 1, 2, and 3 must be completed in order.

However, within User Story 2 and User Story 3, individual developers can work on parallel tasks:
- **US2**: One person deletes files (T019-T022 in parallel)
- **US3**: One person runs verification searches (T042-T046 in parallel)

---

## Notes

- **[P] tasks** = different files, no dependencies - can run in parallel
- **[US#] label** = maps task to specific user story for traceability
- **Sequential by design**: User stories have intentional dependencies (backend → frontend → API cleanup)
- **No tests**: This is removal work - manual verification is sufficient per constitution
- **Easy rollback**: All changes are file deletions - can restore from git if needed
- **Zero data loss**: No database changes - only removing presentation/API layers
- Verify tests work before implementing (n/a for removal task)
- Commit after each task or logical group (recommended: commit after each user story)
- Stop at any checkpoint to validate story independently

---

## Task Count Summary

- **Setup**: 4 tasks
- **Foundational**: 0 tasks (n/a for removal)
- **User Story 1**: 14 tasks (5 implementation + 9 verification)
- **User Story 2**: 15 tasks (6 implementation + 9 verification)
- **User Story 3**: 15 tasks (8 implementation + 7 verification)
- **Polish**: 9 tasks
- **Total**: 57 tasks

**Parallel Opportunities**:
- Setup: 2 tasks (T003, T004)
- User Story 2: 4 tasks (T019-T022)
- User Story 3: 5 tasks (T042-T046)
- Polish: 5 tasks (T049-T050, T053-T055)
- **Total Parallel**: 16 tasks (28% of total)

**Estimated Duration**:
- If executed sequentially: ~2-3 hours (mostly verification)
- If executed with parallel optimization: ~1.5-2 hours
- **Recommendation**: Execute sequentially for safety - this is deletion work where caution is prudent
