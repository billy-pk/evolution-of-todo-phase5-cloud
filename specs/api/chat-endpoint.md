# API Specification: Chat Endpoint

## Endpoint
POST /api/{user_id}/chat

## Purpose
Provide a stateless API for sending and receiving chat messages with an AI agent capable of performing task operations.

## Authentication
Required:
Authorization: Bearer <jwt_token>

Backend must:
- Verify JWT signature
- Extract user_id
- Reject mismatched user_id in path

## Request Body
{
  "message": "string, required",
  "conversation_id": "integer, optional"
}

## Response Body
{
  "conversation_id": integer,
  "response": string,
  "tool_calls": [
    {
      "tool": "add_task | list_tasks | update_task | delete_task | complete_task",
      "arguments": object
    }
  ],
  "messages": [
    { "role": "user" | "assistant", "content": "string" }
  ]
}

## Error Responses
401 Unauthorized
403 Forbidden (user mismatch)
404 Conversation not found
500 Internal error
