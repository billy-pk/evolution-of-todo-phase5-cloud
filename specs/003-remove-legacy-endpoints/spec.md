# Feature Specification: Remove Legacy Task API and UI

**Feature Branch**: `003-remove-legacy-endpoints`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Remove legacy Task API and UI from Phase 2"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Backend Legacy Task Endpoints (Priority: P1)

As a system maintainer, I want to remove all legacy REST API endpoints for task management so that the application uses only the AI chatbot interface for task operations, reducing code complexity and maintenance burden.

**Why this priority**: This is the core backend cleanup that eliminates duplicate task management pathways. It must be done first to prevent any new dependencies on the legacy API.

**Independent Test**: Can be fully tested by attempting to access each legacy endpoint (GET/POST/PUT/PATCH/DELETE /api/{user_id}/tasks) and verifying they return 404 Not Found, while the chat interface continues to create, list, update, and delete tasks successfully through MCP tools.

**Acceptance Scenarios**:

1. **Given** the legacy task API endpoints exist, **When** I remove backend/routes/tasks.py and its import from main.py, **Then** all REST endpoints for tasks return 404 Not Found
2. **Given** the legacy endpoints are removed, **When** I use the chat interface to create a task, **Then** the task is created successfully via MCP tools
3. **Given** existing tasks in the database, **When** I ask the chatbot to list my tasks, **Then** all tasks are displayed correctly through MCP tools

---

### User Story 2 - Remove Frontend Legacy Task UI (Priority: P2)

As a system maintainer, I want to remove all frontend task management UI components and pages so that users interact with tasks exclusively through the conversational chat interface, simplifying the user experience.

**Why this priority**: Frontend cleanup depends on backend removal being complete. This eliminates the old UI while ensuring the chat interface remains the single point of interaction.

**Independent Test**: Can be fully tested by navigating to /tasks route (which should no longer exist or redirect to /chat), verifying TaskForm, TaskList, and TaskItem components are deleted, and confirming all task operations work through the chat interface at /chat.

**Acceptance Scenarios**:

1. **Given** the legacy task UI exists, **When** I remove frontend/app/(dashboard)/tasks/page.tsx, **Then** navigating to /tasks shows a 404 or redirects to /chat
2. **Given** task components exist, **When** I remove TaskForm.tsx, TaskList.tsx, and TaskItem.tsx, **Then** no legacy task UI components remain in the codebase
3. **Given** the UI is removed, **When** I use the chat interface, **Then** I can still create, view, update, and delete tasks conversationally

---

### User Story 3 - Clean Up API Client Methods (Priority: P3)

As a system maintainer, I want to remove legacy task API methods from the frontend API client so that there are no unused API functions remaining in the codebase.

**Why this priority**: This is final cleanup work that can be done after the UI is removed. It ensures the API client only contains methods that are actively used.

**Independent Test**: Can be fully tested by searching the codebase for calls to removed API methods (createTask, listTasks, updateTask, deleteTask, toggleComplete) and verifying none exist, while the chat interface API methods remain functional.

**Acceptance Scenarios**:

1. **Given** legacy task API methods exist in lib/api.ts, **When** I remove createTask, listTasks, updateTask, deleteTask, and toggleComplete methods, **Then** no legacy task API methods remain
2. **Given** the methods are removed, **When** I search the codebase, **Then** no components import or call these removed methods
3. **Given** the cleanup is complete, **When** I use the application, **Then** authentication and chat API methods continue to work

---

### Edge Cases

- What happens when attempting to access removed endpoints after deployment? (Answer: Return 404 Not Found)
- What happens if old bookmarks or links point to /tasks? (Answer: Show 404 or redirect to /chat - default to 404)
- What happens to existing tasks in the database? (Answer: They remain intact and accessible via chat interface)
- What happens if frontend code still tries to call removed API methods? (Answer: Build will fail with import errors - caught during development)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove all REST endpoints for task management from backend
  - DELETE backend/routes/tasks.py file
  - REMOVE tasks import from backend/main.py
  - Endpoints no longer accessible: GET/POST/PUT/PATCH/DELETE /api/{user_id}/tasks*

- **FR-002**: System MUST remove all frontend task UI pages and components
  - DELETE frontend/app/(dashboard)/tasks/page.tsx
  - DELETE frontend/components/TaskForm.tsx
  - DELETE frontend/components/TaskList.tsx
  - DELETE frontend/components/TaskItem.tsx

- **FR-003**: System MUST remove legacy task API methods from frontend API client
  - REMOVE createTask, listTasks, updateTask, deleteTask, toggleComplete from lib/api.ts
  - RETAIN authentication and chat-related API methods

- **FR-004**: System MUST preserve essential infrastructure
  - RETAIN chat endpoint at /api/{user_id}/chat
  - RETAIN ChatKit routes and integration
  - RETAIN authentication endpoints (/api/auth/*)
  - RETAIN database models (Task, User, Conversation, Message)
  - RETAIN MCP server tools and functionality

- **FR-005**: System MUST maintain data integrity
  - NO changes to database schema
  - NO deletion of existing task data
  - ALL existing tasks remain accessible via chat interface

- **FR-006**: Removed endpoints MUST return 404 Not Found when accessed

### Key Entities

- **Task**: User task records stored in database. Properties include id, user_id, title, description, completed status, timestamps. Accessed exclusively through MCP tools via chat interface after removal.

- **Conversation**: Chat conversation records. Continue to function normally with no changes required.

- **Message**: Chat message records. Continue to function normally with no changes required.

- **User**: User authentication records. Continue to function normally with no changes required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero legacy REST task endpoints remain accessible (4 endpoints removed: POST, GET, PUT/PATCH, DELETE)
- **SC-002**: Zero frontend UI components for direct task management remain in codebase (4 files removed: page.tsx, TaskForm, TaskList, TaskItem)
- **SC-003**: All task operations continue to work through chat interface with 100% functional parity
- **SC-004**: Codebase complexity reduces by at least 500 lines of code (backend routes + frontend components)
- **SC-005**: Build succeeds with no import errors or broken references
- **SC-006**: Users can complete all task CRUD operations via chat in under 30 seconds per operation
- **SC-007**: Zero data loss - all existing tasks remain accessible after removal

### Qualitative Outcomes

- Application architecture is simplified with single task management pathway (chat only)
- Technical debt is reduced by eliminating duplicate functionality
- User experience is streamlined through single conversational interface
- Codebase is easier to maintain without Phase 2 legacy code
- Attack surface is reduced by removing unused endpoints

## Non-Functional Requirements

### Performance

- System response time improves by at least 5% after removing unused endpoints and components
- Frontend bundle size decreases by removing unused task UI components
- Backend memory footprint reduces with fewer route handlers loaded

### Security

- Attack surface reduces by removing 4+ unused REST endpoints
- Authentication continues to work for remaining endpoints with no degradation
- User isolation remains enforced for all operations (chat and MCP tools)
- No new security vulnerabilities introduced by removal

### Maintainability

- Code complexity decreases with single task management pathway
- Fewer files to maintain reduces cognitive load
- Documentation updates are easier with simplified architecture

## Assumptions

- Users will access task management exclusively through the chat interface after removal
- MCP tools for task management are fully functional and tested
- Chat interface at /chat provides equivalent or better UX than legacy UI
- Database migrations are not needed as schema remains unchanged
- No external systems or integrations depend on the legacy REST task endpoints
- Current git branch structure supports creating 003-remove-legacy-endpoints branch

## Dependencies

- MCP server tools for task management MUST be operational before removal
- Chat interface at /api/{user_id}/chat MUST be fully functional
- Authentication system MUST continue working (Better Auth with JWT)
- ChatKit integration MUST remain intact
- Database models MUST remain unchanged (no schema modifications)

## Out of Scope

- Removing authentication infrastructure (Better Auth)
- Removing or modifying database models or schema
- Modifying MCP server tools or their functionality
- Changing chat interface functionality or behavior
- Adding new features (this is purely removal and cleanup)
- Creating database migrations (schema unchanged)
- Removing or modifying health check endpoints
