# API Contract: Chat Endpoint

**Endpoint**: `POST /api/{user_id}/chat`
**Feature**: 001-ai-chatbot
**Date**: 2025-12-12
**Status**: Design Complete

---

## Overview

The chat endpoint enables users to interact with the AI assistant for task management through natural language. The endpoint is fully stateless, reconstructing context from the database on each request.

---

## Authentication

**Required**: JWT token in Authorization header
**Format**: `Authorization: Bearer <jwt_token>`
**Validation**:
- Token must be valid (signature verification via BETTER_AUTH_SECRET)
- Token user_id must match path parameter {user_id}
- Token must not be expired

**Errors**:
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Token user_id ≠ path user_id

---

## Request

### Path Parameters

| Parameter | Type   | Required | Description                |
|-----------|--------|----------|----------------------------|
| user_id   | string | Yes      | User ID from Better Auth   |

### Headers

| Header        | Value                         | Required | Description              |
|---------------|-------------------------------|----------|--------------------------|
| Authorization | Bearer `<jwt_token>`          | Yes      | JWT authentication token |
| Content-Type  | application/json              | Yes      | Request body format      |

### Body

```json
{
  "message": "string (required, 1-10000 characters)",
  "conversation_id": "uuid (optional)"
}
```

**Fields**:
- `message`: User's natural language input (required)
  - Min length: 1 character
  - Max length: 10,000 characters
  - Examples: "Create a task to buy groceries", "List my pending tasks", "Mark task #3 as complete"

- `conversation_id`: UUID of existing conversation (optional)
  - If provided: Load conversation history and append new message
  - If omitted: Create new conversation automatically
  - Must belong to the authenticated user (verified via database query)

### Request Examples

#### New Conversation
```http
POST /api/user-123/chat HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "message": "Create a task to buy groceries"
}
```

#### Existing Conversation
```http
POST /api/user-123/chat HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "message": "Show me all my tasks",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Response

### Success Response (200 OK)

```json
{
  "conversation_id": "uuid",
  "response": "string",
  "tool_calls": [
    {
      "tool": "string",
      "parameters": {},
      "result": {}
    }
  ],
  "messages": [
    {
      "role": "user|assistant",
      "content": "string",
      "tool_calls": [],
      "created_at": "ISO8601 timestamp"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "tokens_used": 150,
    "processing_time_ms": 1234
  }
}
```

**Fields**:

- `conversation_id` (string, UUID): Conversation identifier (newly created or existing)
- `response` (string): AI assistant's natural language response
- `tool_calls` (array): Tools called by the AI agent during processing
  - `tool` (string): Tool name (e.g., "add_task", "list_tasks")
  - `parameters` (object): Tool input parameters
  - `result` (object): Tool execution result
- `messages` (array): Full conversation history (including new user message and assistant response)
  - `role` (string): "user" or "assistant"
  - `content` (string): Message text
  - `tool_calls` (array): Tool calls (only for assistant messages)
  - `created_at` (string): ISO8601 timestamp
- `metadata` (object): Request metadata
  - `model` (string): AI model used (e.g., "gpt-4o")
  - `tokens_used` (integer): Approximate token count
  - `processing_time_ms` (integer): Server processing time in milliseconds

### Response Examples

#### Task Creation
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Task created successfully! I've added 'Buy groceries' to your task list.",
  "tool_calls": [
    {
      "tool": "add_task",
      "parameters": {
        "user_id": "user-123",
        "title": "Buy groceries",
        "description": null
      },
      "result": {
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "status": "created",
        "title": "Buy groceries"
      }
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "Create a task to buy groceries",
      "tool_calls": null,
      "created_at": "2025-12-12T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Task created successfully! I've added 'Buy groceries' to your task list.",
      "tool_calls": [
        {
          "tool": "add_task",
          "parameters": {"user_id": "user-123", "title": "Buy groceries"},
          "result": {"task_id": "a1b2c3d4-...", "status": "created"}
        }
      ],
      "created_at": "2025-12-12T10:30:02Z"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "tokens_used": 87,
    "processing_time_ms": 1523
  }
}
```

#### Task Listing
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "You have 3 pending tasks:\n1. Buy groceries\n2. Call dentist\n3. Review presentation\n\nWould you like me to do anything with these tasks?",
  "tool_calls": [
    {
      "tool": "list_tasks",
      "parameters": {
        "user_id": "user-123",
        "status": "pending"
      },
      "result": {
        "tasks": [
          {"id": "...", "title": "Buy groceries", "completed": false},
          {"id": "...", "title": "Call dentist", "completed": false},
          {"id": "...", "title": "Review presentation", "completed": false}
        ],
        "count": 3
      }
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "Show me my pending tasks",
      "tool_calls": null,
      "created_at": "2025-12-12T10:35:00Z"
    },
    {
      "role": "assistant",
      "content": "You have 3 pending tasks:\n1. Buy groceries\n2. Call dentist\n3. Review presentation\n\nWould you like me to do anything with these tasks?",
      "tool_calls": [
        {
          "tool": "list_tasks",
          "parameters": {"user_id": "user-123", "status": "pending"},
          "result": {"tasks": [...], "count": 3}
        }
      ],
      "created_at": "2025-12-12T10:35:01Z"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "tokens_used": 142,
    "processing_time_ms": 876
  }
}
```

---

## Error Responses

### 400 Bad Request

**Cause**: Invalid request body (missing message, invalid JSON, etc.)

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "message",
      "error": "Field required"
    }
  ]
}
```

### 401 Unauthorized

**Cause**: Missing or invalid JWT token

```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden

**Cause**: JWT user_id does not match path user_id

```json
{
  "detail": "User ID mismatch: token user_id does not match path user_id"
}
```

### 404 Not Found

**Cause**: Conversation ID does not exist or does not belong to user

```json
{
  "detail": "Conversation not found or does not belong to user"
}
```

### 429 Too Many Requests

**Cause**: Rate limit exceeded (>100 requests/hour)

```json
{
  "detail": "Rate limit exceeded. Try again later.",
  "retry_after": 1234
}
```

**Headers**:
- `Retry-After: 1234` (seconds until rate limit resets)
- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 0`
- `X-RateLimit-Reset: 1670851200` (Unix timestamp)

### 500 Internal Server Error

**Cause**: OpenAI API failure, database error, or tool execution failure

```json
{
  "detail": "Internal server error",
  "error_code": "OPENAI_API_ERROR",
  "message": "Failed to process request. Please try again."
}
```

**Error Codes**:
- `OPENAI_API_ERROR`: OpenAI API call failed
- `DATABASE_ERROR`: Database query/transaction failed
- `TOOL_EXECUTION_ERROR`: MCP tool execution failed
- `UNKNOWN_ERROR`: Unclassified error

---

## Request Flow

1. **Validate JWT**: Extract user_id from token, verify matches path user_id
2. **Check Rate Limit**: Verify user hasn't exceeded 100 requests/hour
3. **Load Conversation**:
   - If conversation_id provided: Load from database, verify ownership
   - If conversation_id omitted: Create new conversation
4. **Load Message History**: Retrieve last 100 messages from conversation (ordered chronologically)
5. **Call AI Agent**: Pass conversation history + new user message to OpenAI Agents SDK
6. **Execute Tools**: Agent calls MCP tools as needed (add_task, list_tasks, etc.)
7. **Save Messages**: Store user message and assistant response in database (atomic transaction)
8. **Update Conversation**: Set updated_at timestamp
9. **Return Response**: Send assistant response with conversation_id, tool_calls, and full message history

---

## Performance Characteristics

**Target Latency**:
- P50: <2 seconds
- P95: <3 seconds
- P99: <5 seconds

**Timeout**: 30 seconds (hard limit)

**Bottlenecks**:
- OpenAI API call: ~1-2 seconds (external dependency)
- Tool execution: ~100-500ms per tool (database operations)
- Database queries: ~50-100ms (load history, save messages)

**Optimization Strategies**:
- Limit conversation history to last 100 messages
- Use database connection pooling
- Implement caching for JWT validation
- Batch database writes where possible

---

## Security Considerations

### Authentication
- JWT signature verified using BETTER_AUTH_SECRET
- Token expiration checked (reject expired tokens)
- User ID extracted from token payload (`user_id` claim)

### Authorization
- Path user_id MUST match token user_id (403 if mismatch)
- Conversation ownership verified before loading history
- All MCP tools receive user_id and enforce task ownership

### Rate Limiting
- 100 requests per hour per user_id
- Sliding window algorithm (1-hour window)
- Rate limit state stored in memory (development) or Redis (production)

### Data Validation
- Message length: 1-10,000 characters
- Conversation ID: Valid UUID format
- SQL injection prevention: Use parameterized queries
- XSS prevention: Sanitize user input before storing (if rendering in HTML)

### Error Messages
- Never leak sensitive information (e.g., database structure, internal paths)
- Generic error messages for 500 errors
- Detailed validation errors only for 400 (client errors)

---

## Idempotency

**Not Idempotent**: Each POST creates a new message in the conversation.

**Reasoning**: Chat messages are inherently non-idempotent (each message is unique).

**Future Enhancement**: Add `idempotency_key` header for duplicate request detection (Phase 5+).

---

## Versioning

**Current Version**: v1 (implicit, no version in path)

**Future Versioning**: If breaking changes needed, use `/api/v2/{user_id}/chat`

**Backward Compatibility**: Phase 3 endpoint remains stable for Phase 4 and Phase 5.

---

## Testing

### Unit Tests
- Request validation (missing message, invalid conversation_id)
- JWT authentication (valid token, expired token, missing token)
- User ID mismatch detection

### Integration Tests
- End-to-end flow: Create conversation → Send message → Receive response
- Conversation history persistence: Send multiple messages → Verify history loaded
- Tool execution: Request task creation → Verify add_task called and task created
- Error handling: Invalid conversation_id → 404, rate limit exceeded → 429

### Load Tests
- 50 concurrent users sending messages
- Verify P95 latency <3 seconds
- Verify no rate limit false positives

---

## Examples

### Full Request/Response Cycle

**Request**:
```http
POST /api/user-abc123/chat HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidXNlci1hYmMxMjMiLCJleHAiOjE3MDI5OTk5OTl9.signature
Content-Type: application/json

{
  "message": "Create a task called 'Prepare for meeting' with description 'Review slides and demo'"
}
```

**Response** (200 OK):
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1670858400

{
  "conversation_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "response": "I've created the task 'Prepare for meeting' with the description you provided. The task is now in your task list.",
  "tool_calls": [
    {
      "tool": "add_task",
      "parameters": {
        "user_id": "user-abc123",
        "title": "Prepare for meeting",
        "description": "Review slides and demo"
      },
      "result": {
        "task_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "status": "created",
        "title": "Prepare for meeting"
      }
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "Create a task called 'Prepare for meeting' with description 'Review slides and demo'",
      "tool_calls": null,
      "created_at": "2025-12-12T15:30:00.000Z"
    },
    {
      "role": "assistant",
      "content": "I've created the task 'Prepare for meeting' with the description you provided. The task is now in your task list.",
      "tool_calls": [
        {
          "tool": "add_task",
          "parameters": {
            "user_id": "user-abc123",
            "title": "Prepare for meeting",
            "description": "Review slides and demo"
          },
          "result": {
            "task_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "status": "created",
            "title": "Prepare for meeting"
          }
        }
      ],
      "created_at": "2025-12-12T15:30:02.456Z"
    }
  ],
  "metadata": {
    "model": "gpt-4o",
    "tokens_used": 124,
    "processing_time_ms": 2456
  }
}
```

---

## Summary

The chat endpoint provides a stateless, secure, and performant interface for natural language task management. All requirements from the feature spec (FR-007 through FR-011, FR-031 through FR-034, FR-041 through FR-045) are satisfied by this contract.

**Next**: Define MCP tool contracts.
