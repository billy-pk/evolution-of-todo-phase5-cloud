# API Contracts: Remove Legacy Task API and UI

**Feature**: 003-remove-legacy-endpoints
**Date**: 2025-12-15

## Overview

This feature **removes** existing API contracts and does not introduce new ones. This document catalogs what contracts are being removed and what remains active.

## Contracts Being Removed

### Legacy REST Task Endpoints

The following REST API endpoints are being removed:

#### 1. Create Task
**Endpoint**: `POST /api/{user_id}/tasks`

**Status**: ❌ REMOVED

**Request**:
```json
{
  "title": "string (required)",
  "description": "string (optional)"
}
```

**Response** (200):
```json
{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string | null",
  "completed": false,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Replacement**: MCP tool `add_task_tool` via chat interface

---

#### 2. List Tasks
**Endpoint**: `GET /api/{user_id}/tasks?status={all|pending|completed}`

**Status**: ❌ REMOVED

**Query Parameters**:
- `status`: "all" | "pending" | "completed" (optional, default: "all")

**Response** (200):
```json
{
  "tasks": [
    {
      "id": "uuid",
      "user_id": "string",
      "title": "string",
      "description": "string | null",
      "completed": boolean,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": number
}
```

**Replacement**: MCP tool `list_tasks_tool` via chat interface

---

#### 3. Get Single Task
**Endpoint**: `GET /api/{user_id}/tasks/{task_id}`

**Status**: ❌ REMOVED

**Response** (200):
```json
{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string | null",
  "completed": boolean,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Replacement**: MCP tool `list_tasks_tool` + filtering via chat

---

#### 4. Update Task
**Endpoint**: `PUT /api/{user_id}/tasks/{task_id}`

**Status**: ❌ REMOVED

**Request**:
```json
{
  "title": "string (optional)",
  "description": "string (optional)"
}
```

**Response** (200):
```json
{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string | null",
  "completed": boolean,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Replacement**: MCP tool `update_task_tool` via chat interface

---

#### 5. Toggle Task Completion
**Endpoint**: `PATCH /api/{user_id}/tasks/{task_id}/complete`

**Status**: ❌ REMOVED

**Response** (200):
```json
{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string | null",
  "completed": boolean,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Replacement**: MCP tool `complete_task_tool` via chat interface

---

#### 6. Delete Task
**Endpoint**: `DELETE /api/{user_id}/tasks/{task_id}`

**Status**: ❌ REMOVED

**Response**: 204 No Content

**Replacement**: MCP tool `delete_task_tool` via chat interface

---

## Contracts Remaining Active

### Chat Endpoint

**Endpoint**: `POST /api/{user_id}/chat`

**Status**: ✅ ACTIVE (unchanged)

**Authentication**: Required - JWT Bearer token

**Request**:
```json
{
  "message": "string (required)",
  "conversation_id": "uuid | null (optional)"
}
```

**Response** (200):
```json
{
  "conversation_id": "uuid",
  "response": "string",
  "timestamp": "datetime"
}
```

**Purpose**: Processes natural language chat messages and executes task operations via MCP tools

---

### ChatKit Integration Endpoints

**Endpoints**: `POST /api/chatkit/*`

**Status**: ✅ ACTIVE (unchanged)

**Purpose**: ChatKit-specific endpoints for streaming and protocol handling

---

### Authentication Endpoints

**Endpoints**: `GET/POST /api/auth/*`

**Status**: ✅ ACTIVE (unchanged)

**Managed By**: Better Auth

**Purpose**: User authentication, registration, JWT token generation

---

### Health Check

**Endpoint**: `GET /health`

**Status**: ✅ ACTIVE (unchanged)

**Response** (200):
```json
{
  "status": "healthy",
  "environment": "string",
  "database": "connected"
}
```

**Purpose**: System health monitoring

---

## MCP Tool Contracts (Active)

While not HTTP endpoints, the following MCP tools provide the replacement functionality:

### add_task_tool

**Function**: Creates a new task

**Parameters**:
- `user_id`: string (required)
- `title`: string (required)
- `description`: string (optional, default: "")

**Returns**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "user_id": "string",
    "title": "string",
    "description": "string",
    "completed": false,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Invoked Via**: Natural language chat (e.g., "add a task to buy milk")

---

### list_tasks_tool

**Function**: Lists user's tasks with optional status filter

**Parameters**:
- `user_id`: string (required)
- `status`: "all" | "pending" | "completed" (optional, default: "all")

**Returns**:
```json
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string",
      "completed": boolean,
      "created_at": "datetime"
    }
  ]
}
```

**Invoked Via**: Natural language chat (e.g., "list my tasks", "show pending tasks")

---

### update_task_tool

**Function**: Updates task title and/or description

**Parameters**:
- `user_id`: string (required)
- `task_id`: string (required)
- `title`: string (optional)
- `description`: string (optional)

**Returns**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "title": "string",
    "description": "string",
    "completed": boolean,
    "updated_at": "datetime"
  }
}
```

**Invoked Via**: Natural language chat (e.g., "update task 'buy milk' to 'buy milk and bread'")

---

### complete_task_tool

**Function**: Toggles task completion status

**Parameters**:
- `user_id`: string (required)
- `task_id`: string (required)

**Returns**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "title": "string",
    "completed": boolean,
    "updated_at": "datetime"
  }
}
```

**Invoked Via**: Natural language chat (e.g., "mark 'buy milk' as complete")

---

### delete_task_tool

**Function**: Deletes a task

**Parameters**:
- `user_id`: string (required)
- `task_id`: string (required)

**Returns**:
```json
{
  "status": "success",
  "message": "Task deleted successfully"
}
```

**Invoked Via**: Natural language chat (e.g., "delete task 'buy milk'")

---

## Migration Guide for API Consumers

### For External API Consumers (if any)

**Impact**: HIGH - All task REST endpoints removed

**Action Required**:
1. Transition to chat endpoint at `POST /api/{user_id}/chat`
2. Send natural language task commands instead of structured REST calls
3. Parse chat responses for task operation results

**Example Migration**:

**Before** (REST API):
```bash
# Create task
curl -X POST http://api.example.com/api/user123/tasks \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk","description":"From store"}'
```

**After** (Chat Interface):
```bash
# Create task via chat
curl -X POST http://api.example.com/api/user123/chat \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"message":"add a task to buy milk from store","conversation_id":null}'
```

### For Internal Frontend Consumers

**Impact**: COMPLETE - All task UI and API methods removed

**Action Required**:
1. Use chat interface at `/chat` for all task operations
2. Remove all imports of task-related components (TaskForm, TaskList, TaskItem)
3. Remove all calls to api.createTask, api.listTasks, api.updateTask, api.deleteTask, api.toggleComplete

**Replacement**: Direct user interaction via chat interface

---

## Error Handling Changes

### Before Removal

Legacy REST endpoints returned structured error responses:
```json
{
  "detail": "Task not found",
  "status_code": 404
}
```

### After Removal

**Accessing Removed Endpoints**: Returns FastAPI default 404:
```json
{
  "detail": "Not Found"
}
```

**Task Operations via Chat**: Returns natural language error messages from OpenAI Agent:
```
"I couldn't find a task with that title. Here are your current tasks: ..."
```

---

## Breaking Changes Summary

| Endpoint | Method | Status | Replacement |
|----------|--------|--------|-------------|
| `/api/{user_id}/tasks` | POST | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/tasks` | GET | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/tasks/{task_id}` | GET | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/tasks/{task_id}` | PUT | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/tasks/{task_id}/complete` | PATCH | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/tasks/{task_id}` | DELETE | ❌ REMOVED | MCP tool via chat |
| `/api/{user_id}/chat` | POST | ✅ ACTIVE | No change |
| `/api/auth/*` | * | ✅ ACTIVE | No change |
| `/health` | GET | ✅ ACTIVE | No change |

**Total Removed**: 6 endpoints

**Total Remaining**: 10+ endpoints (chat, chatkit, auth, health)

---

## Notes

- **No new OpenAPI/Swagger contracts** needed (removal only)
- **No new GraphQL schemas** needed (removal only)
- **MCP tools are internal** and accessed via chat endpoint, not direct HTTP calls
- **Chat endpoint contract unchanged** - continues to accept natural language messages

This refactoring simplifies the API surface while maintaining full task management functionality through the conversational interface.
