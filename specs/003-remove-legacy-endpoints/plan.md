# Implementation Plan: Remove Legacy Task API and UI

**Branch**: `003-remove-legacy-endpoints` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-remove-legacy-endpoints/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Remove all Phase 2 legacy REST API endpoints and frontend UI components for task management, leaving only the conversational AI chat interface as the single pathway for task operations. This cleanup aligns with the updated Phase 3 constitution (v2.0.0) which positions the AI chatbot as the primary task management interface.

**Primary Actions**:
1. Delete backend REST endpoints (backend/routes/tasks.py and import)
2. Delete frontend task UI (page, components)
3. Remove API client methods
4. Verify chat interface continues working with full CRUD functionality via MCP tools

**Technical Approach**: Simple file deletion and import removal. No new code, no migrations, no schema changes. This is pure refactoring to eliminate duplicate task management pathways.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/Next.js 16 (frontend)
**Primary Dependencies**: FastAPI, Next.js App Router, Better Auth, OpenAI Agents SDK, FastMCP
**Storage**: Neon PostgreSQL (no schema changes required)
**Testing**: Manual verification of chat interface functionality
**Target Platform**: Web application (Linux server backend, browser frontend)
**Project Type**: Web (backend + frontend)
**Performance Goals**: N/A (removal only - expect slight performance improvement)
**Constraints**: Must NOT break chat interface or data integrity
**Scale/Scope**: Small refactoring task - removing ~500-700 lines of code across 7 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Conversational Interface Primary ✅

**Status**: PASS - This feature directly supports this principle

- Removes non-conversational task management UI
- Ensures chat interface is the only pathway for task operations
- Aligns with Phase 3 AI-first architecture

### Principle II: Stateless Server Design ✅

**Status**: PASS - No impact

- No changes to chat endpoint or MCP tools
- Removal of legacy endpoints does not affect statelessness
- Chat endpoint remains stateless with database persistence

### Principle III: Security First ✅

**Status**: PASS - Improves security

- Reduces attack surface by removing 4+ unused endpoints
- Maintains authentication for remaining endpoints
- No new security vulnerabilities introduced
- User isolation remains enforced via chat and MCP tools

### Principle IV: Single Source of Truth ✅

**Status**: PASS - Directly supports this principle

- Eliminates duplicate task management pathways
- Database remains single source of truth
- Chat interface is now the only access method

### Principle V: Test-Driven Development ⚠️

**Status**: CONDITIONAL PASS - Manual testing only

- This is removal work, not new functionality
- No new tests required (deleting test files is part of cleanup)
- Manual verification sufficient: test chat interface still works after removal

**Justification**: TDD applies to new features. For removal work, verification that remaining functionality works is appropriate.

### Principle VI: Extensibility and Modularity ✅

**Status**: PASS - Improves modularity

- Simplifies architecture by removing legacy code
- Chat interface and MCP tools remain modular
- No impact on future phases (Kubernetes, microservices)

**Overall Constitution Compliance**: PASS ✅

All principles pass. The removal of legacy endpoints directly supports the updated Phase 3 constitution's vision of conversational interface as primary interaction model.

## Project Structure

### Documentation (this feature)

```text
specs/003-remove-legacy-endpoints/
├── plan.md              # This file (/sp.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (minimal - removal task)
├── data-model.md        # Phase 1 output (N/A - no data model changes)
├── quickstart.md        # Phase 1 output (verification steps)
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── main.py              # MODIFY: Remove tasks import
├── routes/
│   ├── tasks.py         # DELETE: Legacy REST endpoints
│   ├── chat.py          # RETAIN: Chat endpoint
│   └── chatkit.py       # RETAIN: ChatKit integration
├── models.py            # RETAIN: Task, User, Conversation, Message models
├── schemas.py           # RETAIN: Pydantic schemas (may need cleanup)
├── db.py                # RETAIN: Database connection
├── middleware.py        # RETAIN: JWT validation
└── tools/
    └── server.py        # RETAIN: MCP server with task tools

frontend/
├── app/
│   ├── (dashboard)/
│   │   ├── tasks/
│   │   │   └── page.tsx # DELETE: Legacy task UI page
│   │   └── chat/
│   │       └── page.tsx # RETAIN: Chat interface
│   └── (auth)/          # RETAIN: Auth pages
├── components/
│   ├── TaskForm.tsx     # DELETE: Legacy task form component
│   ├── TaskList.tsx     # DELETE: Legacy task list component
│   ├── TaskItem.tsx     # DELETE: Legacy task item component
│   └── Navbar.tsx       # RETAIN: Navigation (may need link cleanup)
└── lib/
    ├── api.ts           # MODIFY: Remove task API methods
    ├── auth.ts          # RETAIN: Better Auth server
    └── auth-client.ts   # RETAIN: Better Auth client
```

**Structure Decision**: Web application structure (Option 2). This is a removal task affecting both backend REST endpoints and frontend UI components. The chat interface and MCP tools remain intact.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - All constitution checks pass. No violations to justify.

## Phase 0: Research

Since this is a removal/cleanup task with no new functionality, research is minimal. The key research areas are:

### Research Task 1: Dependency Analysis

**Question**: Which files import or depend on the files to be deleted?

**Findings**:
- backend/main.py imports tasks router
- frontend/app/(dashboard)/tasks/page.tsx imports TaskForm, TaskList components
- frontend/components/TaskForm.tsx, TaskList.tsx, TaskItem.tsx are only used by tasks page
- frontend/lib/api.ts task methods are only called from tasks page
- Navbar.tsx may have link to /tasks route (needs verification)

**Decision**: Safe to delete files - no external dependencies outside of task management UI

### Research Task 2: Chat Interface Verification

**Question**: Does the chat interface provide full CRUD functionality via MCP tools?

**Findings** (from existing codebase):
- MCP server at backend/tools/server.py has 5 tools: add_task, list_tasks, update_task, complete_task, delete_task
- Chat endpoint at backend/routes/chat.py connects to MCP server
- ChatKit UI at frontend/app/(dashboard)/chat/page.tsx provides conversational interface
- All task operations are available via natural language commands

**Decision**: Chat interface is fully functional - safe to remove legacy UI

### Research Task 3: Data Integrity

**Question**: Will removal affect existing tasks in the database?

**Findings**:
- Task model in backend/models.py is NOT being deleted
- Database schema unchanged
- Only deleting API routes and UI components, not data layer
- MCP tools use the same Task model for database operations

**Decision**: Zero data loss - removal only affects presentation and API layers

## Phase 1: Design & Contracts

### Data Model

**No changes to data model**. This feature only removes presentation and API layers. All database models remain intact:

- Task (id, user_id, title, description, completed, created_at, updated_at) - RETAINED
- User (id, name, email, auth fields) - RETAINED
- Conversation (id, user_id, created_at, updated_at) - RETAINED
- Message (id, conversation_id, role, content, created_at) - RETAINED

### API Contracts

**No new API contracts**. This feature removes existing REST endpoints:

**Endpoints Being Removed**:
- POST /api/{user_id}/tasks - Create task
- GET /api/{user_id}/tasks - List tasks (with status filter)
- GET /api/{user_id}/tasks/{task_id} - Get single task
- PUT /api/{user_id}/tasks/{task_id} - Update task
- PATCH /api/{user_id}/tasks/{task_id}/complete - Toggle completion
- DELETE /api/{user_id}/tasks/{task_id} - Delete task

**Endpoints Being Retained**:
- POST /api/{user_id}/chat - Chat endpoint (conversational task management)
- POST /api/chatkit/* - ChatKit integration endpoints
- GET/POST /api/auth/* - Authentication endpoints
- GET /health - Health check endpoint

### Quickstart: Verification Steps

After implementation, verify the following:

1. **Backend Verification**:
   ```bash
   # Start backend
   cd backend && uvicorn main:app --reload

   # Verify legacy endpoints return 404
   curl http://localhost:8000/api/test-user/tasks
   # Expected: 404 Not Found

   # Verify chat endpoint works
   curl -X POST http://localhost:8000/api/test-user/chat \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"message": "list my tasks"}'
   # Expected: 200 with task list
   ```

2. **Frontend Verification**:
   ```bash
   # Start frontend
   cd frontend && npm run dev

   # Navigate to http://localhost:3000/tasks
   # Expected: 404 or redirect to /chat

   # Navigate to http://localhost:3000/chat
   # Expected: Chat interface loads

   # Test chat operations:
   # - "add a task to buy milk" → task created
   # - "list my tasks" → tasks shown
   # - "mark 'buy milk' as complete" → task completed
   # - "delete 'buy milk'" → task deleted
   ```

3. **Build Verification**:
   ```bash
   # Backend
   cd backend && python -m pytest
   # Expected: All tests pass (if any remain)

   # Frontend
   cd frontend && npm run build
   # Expected: Build succeeds with no import errors
   ```

4. **Data Integrity Verification**:
   ```bash
   # Connect to database and verify tasks table unchanged
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM tasks;"
   # Expected: Same count as before removal
   ```

## Implementation Notes

### Files to Delete

**Backend**:
- `backend/routes/tasks.py` (271 lines)

**Frontend**:
- `frontend/app/(dashboard)/tasks/page.tsx` (310 lines)
- `frontend/components/TaskForm.tsx` (~100 lines)
- `frontend/components/TaskList.tsx` (~80 lines)
- `frontend/components/TaskItem.tsx` (~120 lines)

**Total**: ~881 lines of code removed

### Files to Modify

**Backend**:
- `backend/main.py` - Remove tasks import and router inclusion (~7 lines)

**Frontend**:
- `frontend/lib/api.ts` - Remove task API methods (createTask, listTasks, updateTask, deleteTask, toggleComplete) (~150 lines)
- `frontend/components/Navbar.tsx` - Remove /tasks link if present (~3 lines)

### Files to Retain (No Changes)

**Backend**:
- `backend/models.py` - All models remain
- `backend/schemas.py` - Pydantic schemas remain (may have unused task schemas, but safe to keep)
- `backend/routes/chat.py` - Chat endpoint
- `backend/routes/chatkit.py` - ChatKit integration
- `backend/tools/server.py` - MCP server with task tools
- `backend/middleware.py` - JWT authentication
- `backend/db.py` - Database connection

**Frontend**:
- `frontend/app/(dashboard)/chat/page.tsx` - Chat interface
- `frontend/lib/auth.ts` - Better Auth server
- `frontend/lib/auth-client.ts` - Better Auth client
- All other components and pages

### Deployment Notes

1. **Zero Downtime**: This removal can be deployed without downtime since chat interface continues working
2. **Rollback Plan**: If issues arise, restore deleted files from git history
3. **User Communication**: Inform users that /tasks route is deprecated (if bookmarked)
4. **Monitoring**: Monitor chat endpoint usage to ensure it handles all task operations

## Success Validation

After implementation, verify all success criteria from spec.md:

- [ ] SC-001: Zero legacy REST task endpoints accessible (curl tests return 404)
- [ ] SC-002: Zero frontend task UI components in codebase (verify with file search)
- [ ] SC-003: Chat interface provides 100% functional parity (manual testing)
- [ ] SC-004: Codebase reduced by 500+ lines (git diff --stat)
- [ ] SC-005: Build succeeds (npm run build, backend tests pass)
- [ ] SC-006: Task CRUD operations complete in <30 seconds via chat (manual timing)
- [ ] SC-007: Zero data loss (database count verification)
