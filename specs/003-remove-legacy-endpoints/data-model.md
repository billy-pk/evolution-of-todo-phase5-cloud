# Data Model: Remove Legacy Task API and UI

**Feature**: 003-remove-legacy-endpoints
**Date**: 2025-12-15

## Overview

This feature involves **no changes to the data model**. All database tables, models, and schemas remain unchanged. This document confirms that data integrity is maintained during the removal of legacy REST endpoints and UI components.

## Existing Data Model (Unchanged)

### Task Entity

**Status**: RETAINED - No changes

```
Task
├── id: UUID (Primary Key)
├── user_id: String (Indexed, Foreign Key to User)
├── title: String (Required)
├── description: String (Optional)
├── completed: Boolean (Default: false)
├── created_at: DateTime (Auto-generated)
└── updated_at: DateTime (Auto-updated)
```

**Access Methods**:
- ~~Legacy: REST API endpoints (backend/routes/tasks.py)~~ ← REMOVED
- Current: MCP tools (backend/tools/server.py) ← ACTIVE
- Current: Chat interface (frontend/app/(dashboard)/chat/page.tsx) ← ACTIVE

**Validation Rules** (unchanged):
- `title`: Required, non-empty string
- `user_id`: Required, must match authenticated user
- `completed`: Boolean only (true/false)
- `id`: Auto-generated UUID, immutable

**Relationships**:
- Belongs to User (via user_id)
- User isolation enforced at query level

### User Entity

**Status**: RETAINED - No changes

```
User
├── id: String (Primary Key)
├── name: String
├── email: String (Unique)
├── emailVerified: Boolean
├── created_at: DateTime
└── updated_at: DateTime
```

**Note**: Managed by Better Auth, not affected by this feature.

### Conversation Entity

**Status**: RETAINED - No changes

```
Conversation
├── id: UUID (Primary Key)
├── user_id: String (Foreign Key to User)
├── title: String (Optional)
├── created_at: DateTime
└── updated_at: DateTime
```

**Note**: Used by chat interface, not affected by this feature.

### Message Entity

**Status**: RETAINED - No changes

```
Message
├── id: UUID (Primary Key)
├── conversation_id: UUID (Foreign Key to Conversation)
├── role: String (Enum: "user" | "assistant")
├── content: String
└── created_at: DateTime
```

**Note**: Used by chat interface, not affected by this feature.

## Schema Migration

**Migration Required**: NO

**Reason**: This feature only removes application layer code (REST endpoints and UI components). The data layer remains completely unchanged.

**Migration Script**: N/A

## Data Access Patterns

### Before Removal

Tasks could be accessed via two pathways:

1. **Legacy REST API** (being removed):
   - GET /api/{user_id}/tasks
   - POST /api/{user_id}/tasks
   - PUT /api/{user_id}/tasks/{task_id}
   - PATCH /api/{user_id}/tasks/{task_id}/complete
   - DELETE /api/{user_id}/tasks/{task_id}

2. **MCP Tools** (retained):
   - add_task_tool(user_id, title, description)
   - list_tasks_tool(user_id, status)
   - update_task_tool(user_id, task_id, title, description)
   - complete_task_tool(user_id, task_id)
   - delete_task_tool(user_id, task_id)

### After Removal

Tasks accessible via single pathway:

**MCP Tools Only** (via chat interface):
- add_task_tool(user_id, title, description)
- list_tasks_tool(user_id, status)
- update_task_tool(user_id, task_id, title, description)
- complete_task_tool(user_id, task_id)
- delete_task_tool(user_id, task_id)

**Access Method**: Natural language chat commands routed through OpenAI Agent to MCP tools

## Data Integrity Guarantees

### User Isolation

**Before**: Enforced at REST API level via JWT middleware and user_id path parameter

**After**: Enforced at MCP tool level via user_id parameter passed from chat endpoint

**Status**: ✅ Maintained - User isolation unchanged

### Validation

**Before**: Pydantic schemas in backend/schemas.py validated REST API requests

**After**: MCP tools perform their own validation on parameters

**Status**: ✅ Maintained - Validation still enforced

### Transactions

**Before**: SQLModel session transactions in routes/tasks.py

**After**: SQLModel session transactions in tools/server.py

**Status**: ✅ Maintained - Same transaction handling

### Data Persistence

**Before**: Direct database writes via SQLModel in routes/tasks.py

**After**: Direct database writes via SQLModel in tools/server.py

**Status**: ✅ Maintained - Same database access mechanism

## State Transitions

Task state transitions remain unchanged:

```
[New Task]
   ↓ (created via add_task_tool)
[Pending Task] (completed = false)
   ↓ (complete_task_tool)
[Completed Task] (completed = true)
   ↓ (complete_task_tool - toggle)
[Pending Task] (completed = false)
   ↓ (delete_task_tool)
[Deleted] (removed from database)
```

**No changes to state machine** - only the API interface changes (REST → MCP)

## Indexes

**Existing Indexes** (unchanged):
- tasks.user_id (for user isolation queries)
- users.email (for authentication lookups)
- conversations.user_id (for user isolation)
- messages.conversation_id (for message retrieval)

**New Indexes**: None required

**Reason**: Query patterns remain identical. MCP tools query the same tables with the same filters.

## Query Performance

### Expected Impact

**Before Removal**:
- REST API: Direct SQLModel queries with user_id filter
- MCP Tools: Direct SQLModel queries with user_id filter

**After Removal**:
- MCP Tools: Direct SQLModel queries with user_id filter

**Performance Change**: Neutral or slight improvement
- Same query patterns
- Fewer total endpoints reduces server overhead
- No additional query complexity

### Example Queries (Unchanged)

**List Tasks**:
```sql
-- Before and After (same query)
SELECT * FROM tasks
WHERE user_id = $1
ORDER BY created_at DESC;
```

**Create Task**:
```sql
-- Before and After (same query)
INSERT INTO tasks (id, user_id, title, description, completed, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING *;
```

**Update Task**:
```sql
-- Before and After (same query)
UPDATE tasks
SET title = $1, description = $2, updated_at = NOW()
WHERE id = $3 AND user_id = $4
RETURNING *;
```

## Data Model Compliance

### Constitution Check: Single Source of Truth ✅

**Status**: PASS

- Database remains single source of truth
- No data duplication introduced
- Single pathway (MCP tools) for data access
- Eliminates competing access methods (REST API removed)

**Improvement**: This change strengthens the Single Source of Truth principle by removing duplicate access pathways.

## Summary

**Data Model Changes**: NONE

**Schema Migrations**: NOT REQUIRED

**Data Integrity**: MAINTAINED - All guarantees preserved

**Access Patterns**: SIMPLIFIED - Single pathway via MCP tools

**Performance**: NEUTRAL or IMPROVED - Same queries, less overhead

**State Transitions**: UNCHANGED

**Validation**: MAINTAINED - Enforced at MCP tool level

**User Isolation**: MAINTAINED - Enforced via user_id parameter

This feature is purely a refactoring of the presentation and API layers. The data model remains stable and unchanged.
