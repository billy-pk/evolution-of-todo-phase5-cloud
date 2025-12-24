# Feature: AI Chatbot for Todo Management

## User Stories

### Story 1
As a user, I can chat with an AI assistant to manage my tasks naturally.

### Story 2
As a user, I can see conversation history when I open the chat page.

### Story 3
As a user, I can ask the AI to:
- Add tasks
- List tasks (all, completed, pending)
- Update tasks
- Complete tasks
- Delete tasks

### Story 4
As a user, I want the AI to remember previous messages within a conversation.

### Story 5
As a user, I want the chat to be secure and private.

---

## Acceptance Criteria

### Chat Page
- Located at /chat
- Uses ChatKit for UI
- Shows message history for selected conversation
- Allows creating a new conversation
- Includes message input box

### Chat Endpoint
POST /api/{user_id}/chat

Accepts:
- message: string
- conversation_id (optional)

Returns:
- conversation_id
- assistant_response
- tool_calls (list)
- updated messages

### AI Behavior
- Detects user intent (add/update/delete/list/complete tasks)
- Calls appropriate MCP tools
- Responds in friendly natural language
- Confirms all actions

### Security
- chat endpoint requires JWT
- user_id must match token payload
- conversation_id must belong to the authenticated user

---

## Out-of-Scope
- Voice commands
- Translation features
- Multi-agent orchestration
- Real-time WebSockets
