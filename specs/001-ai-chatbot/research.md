# Phase 0: Research & Technology Decisions

**Feature**: AI-Powered Chatbot (001-ai-chatbot)
**Date**: 2025-12-12
**Status**: Complete

## Overview

This document consolidates research findings and technology decisions for implementing the AI-powered chatbot feature. All unknowns from the Technical Context section have been resolved through research of official documentation, best practices, and architectural patterns.

---

## 1. OpenAI Agents SDK Integration

### Decision
Use the official **OpenAI Agents SDK for Python** with GPT-4o model for natural language understanding and task operation orchestration.

### Rationale
- Official SDK provides first-class support for tool calling (essential for MCP tools)
- GPT-4o offers strong natural language understanding with good cost/performance balance
- Python SDK integrates seamlessly with FastAPI backend
- Built-in conversation history management (can be externalized to database)
- Streaming support available for future UI enhancements

### Implementation Pattern
```python
from openai import OpenAI
from openai.agents import Agent

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Create agent with tools
agent = Agent(
    name="TaskAssistant",
    instructions="You are a helpful assistant that manages todo tasks...",
    tools=[add_task_tool, list_tasks_tool, update_task_tool, complete_task_tool, delete_task_tool],
    model="gpt-4o"
)

# Process user message (stateless - pass conversation history from database)
response = agent.run(
    messages=conversation_history,  # Loaded from database
    additional_instructions=f"Current user_id: {user_id}"
)
```

### Best Practices
- Always pass user_id as context to the agent
- Load conversation history from database for each request (stateless design)
- Use structured tool outputs for consistent parsing
- Implement retry logic for transient API failures
- Set reasonable timeout (30 seconds for chat endpoint)

### Alternatives Considered
- **LangChain with OpenAI**: More complex, higher abstraction overhead, unnecessary for our use case
- **Direct OpenAI API calls**: Lower-level, would require manual tool orchestration and conversation management
- **Anthropic Claude**: No direct tool calling support at the time, would require function calling workarounds

---

## 2. MCP (Model Context Protocol) Server Integration

### Decision
Build an **MCP server using FastMCP** (official MCP Python SDK) and connect it to the OpenAI Agent using **MCPServerStreamableHttp** (OpenAI Agents SDK MCP integration).

### Rationale
- MCP provides a standardized protocol for exposing tools to AI agents
- FastMCP simplifies server implementation with decorators and automatic schema generation
- OpenAI Agents SDK has built-in MCP integration (MCPServerStdio, MCPServerStreamableHttp, MCPServerSse)
- Streamable HTTP transport enables scalable, stateless server deployment
- Clear separation of concerns: MCP server handles task operations, Agent handles AI logic
- Supports future extensibility (can add more MCP tools without changing agent code)

### Implementation Pattern

**MCP Server (backend/mcp/server.py)**:
```python
from mcp.server.fastmcp import FastMCP
from backend.models import Task
from backend.db import engine
from sqlmodel import Session

# Create MCP server with stateless HTTP configuration
mcp = FastMCP("TaskMCPServer", stateless_http=True, json_response=True)

@mcp.tool()
def add_task(user_id: str, title: str, description: str = None) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)

    Returns:
        Dict with status and task data
    """
    with Session(engine) as session:
        task = Task(user_id=user_id, title=title, description=description, completed=False)
        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "description": task.description
            }
        }

# Run MCP server with streamable-http transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    # Server runs at http://localhost:8000/mcp
```

**Agent Integration (backend/services/agent.py)**:
```python
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from backend.config import settings

async def create_agent():
    """Create agent connected to MCP server."""
    async with MCPServerStreamableHttp(
        name="Task MCP Server",
        params={
            "url": "http://localhost:8000/mcp",
            "timeout": 10,
        },
        cache_tools_list=True,
    ) as server:
        agent = Agent(
            name="TaskAssistant",
            instructions="You are a helpful assistant that manages todo tasks...",
            mcp_servers=[server],
            model="gpt-4o"
        )
        return agent, server

# Usage in chat endpoint
async with create_agent() as (agent, server):
    result = await Runner.run(agent, user_message)
```

### Tool Definitions (5 tools)
1. **add_task**: Create new task (requires: user_id, title; optional: description)
2. **list_tasks**: List user's tasks (requires: user_id, status filter)
3. **update_task**: Modify task (requires: user_id, task_id; optional: title, description)
4. **complete_task**: Mark task complete (requires: user_id, task_id)
5. **delete_task**: Remove task (requires: user_id, task_id)

### Security Pattern
Every tool MUST:
1. Accept user_id as first parameter
2. Verify task ownership before operations (SELECT with WHERE user_id=?)
3. Return structured errors for unauthorized access
4. Log all operations for audit trail

### Best Practices
- Use FastMCP `@mcp.tool()` decorator for automatic schema generation
- Return consistent JSON structure (dict) from all tools
- Include task_id in all responses for confirmation
- Provide clear error messages in docstrings
- Validate user_id matches JWT token in chat endpoint before calling agent
- Run MCP server as separate process (enables scaling and isolation)

### Transport Options
- **Streamable HTTP** (chosen): Stateless, scalable, supports load balancing
- **Stdio**: Subprocess communication, simpler but less scalable
- **SSE**: Server-Sent Events, good for real-time streaming

### Alternatives Considered
- **OpenAI Agents native function_tool**: Less separation of concerns, harder to scale tools independently
- **LangChain Tools**: Tied to LangChain ecosystem, unnecessary dependency
- **Custom tool protocol**: Reinventing MCP standard, less interoperability

---

## 3. Database Schema for Conversations

### Decision
Add two new tables: **conversations** and **messages**, using SQLModel with PostgreSQL.

### Rationale
- Maintains consistency with Phase 2 database patterns (SQLModel ORM)
- Supports stateless server design (all context in database)
- Enables conversation history persistence across sessions
- Allows future features (search, export, analytics)
- Neon PostgreSQL handles concurrent access efficiently

### Schema Design

#### Conversations Table
```python
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True, max_length=255)  # Better Auth user ID
    title: str | None = Field(None, max_length=200)  # Optional conversation title
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

#### Messages Table
```python
class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    user_id: str = Field(index=True, max_length=255)  # For user isolation
    role: str = Field(max_length=20)  # "user" or "assistant"
    content: str = Field()  # Message text
    tool_calls: str | None = Field(None)  # JSON array of tool calls (if role=assistant)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Migration Strategy
- Create migration script: `backend/scripts/migrate_conversations.py`
- Use Alembic or SQLModel's create_all() for table creation
- No changes to existing `tasks` table
- Add indexes on user_id and conversation_id for query performance

### Query Patterns
```python
# Load conversation history for chat endpoint
def get_conversation_messages(conversation_id: UUID, user_id: str) -> List[Message]:
    with Session(engine) as session:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id  # Enforce user isolation
        ).order_by(Message.created_at)
        return session.exec(statement).all()
```

### Best Practices
- Always filter by user_id for security
- Use UTC timestamps consistently
- Index conversation_id and user_id for performance
- Limit message history loaded (e.g., last 100 messages) for large conversations
- Implement soft delete if needed (add deleted_at column in future)

### Alternatives Considered
- **Redis for session storage**: Violates stateless design principle, complicates scaling
- **File-based storage**: Poor concurrent access, hard to query, no ACID guarantees
- **MongoDB**: Introduces second database, unnecessary complexity for structured data

---

## 4. ChatKit UI Integration

### Decision
Use **OpenAI ChatKit** React components for the frontend chat interface.

### Rationale
- Pre-built, production-ready chat UI components
- Designed for OpenAI agent interactions
- Integrates seamlessly with Next.js App Router
- Supports streaming responses (future enhancement)
- Handles message rendering, input, loading states automatically
- TypeScript support for type safety

### Implementation Pattern
```typescript
// frontend/src/app/chat/page.tsx
import { ChatView, useChatMessages } from '@openai/chatkit';

export default function ChatPage() {
  const { messages, sendMessage, isLoading } = useChatMessages({
    apiEndpoint: `${API_URL}/api/${userId}/chat`,
    headers: {
      'Authorization': `Bearer ${jwtToken}`
    }
  });

  return (
    <ChatView
      messages={messages}
      onSendMessage={sendMessage}
      isLoading={isLoading}
      placeholder="Ask me to create, list, update, or complete tasks..."
    />
  );
}
```

### Component Structure
```
frontend/src/app/chat/
├── page.tsx              # Main chat page
├── layout.tsx            # Chat-specific layout (if needed)
└── components/
    ├── ChatContainer.tsx # Wrapper for ChatKit components
    └── MessageList.tsx   # Custom message rendering (if needed)
```

### Best Practices
- Store JWT token securely (httpOnly cookie or secure session storage)
- Include user_id in API endpoint path for consistent routing
- Handle 401 errors (token expiration) with redirect to login
- Show loading indicator while AI processes request
- Disable input while message is being processed
- Display tool calls visually (e.g., "Creating task: Buy milk...")
- Implement error boundaries for graceful error handling

### Alternatives Considered
- **Custom React chat UI**: Significantly more development time, reinventing the wheel
- **react-chat-widget**: Less feature-rich, not designed for AI agents
- **ChatGPT-style custom UI**: Beautiful but time-consuming to build, defers focus from core functionality

---

## 5. Stateless Chat Endpoint Design

### Decision
Implement chat endpoint as **POST /api/{user_id}/chat** that reconstructs full context from database on every request.

### Rationale
- Aligns with Constitution principle II (Stateless Server Design)
- Enables horizontal scaling without session affinity
- Simplifies debugging (no hidden state)
- Prepares for Kubernetes deployment (Phase 4)
- Each request is independently testable

### Endpoint Contract
```python
# Request
POST /api/{user_id}/chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "message": "Create a task to buy groceries",
  "conversation_id": "optional-uuid-for-existing-conversation"
}

# Response
{
  "conversation_id": "uuid-of-conversation",
  "response": "Task created successfully! I've added 'Buy groceries' to your task list.",
  "tool_calls": [
    {
      "tool": "add_task",
      "parameters": {"title": "Buy groceries", "user_id": "user-123"},
      "result": {"task_id": "task-uuid", "status": "created"}
    }
  ],
  "messages": [
    {"role": "user", "content": "Create a task to buy groceries"},
    {"role": "assistant", "content": "Task created successfully!...", "tool_calls": [...]}
  ]
}
```

### Request Flow
1. **Validate JWT**: Extract user_id from token, verify matches path user_id
2. **Load conversation**: If conversation_id provided, load from database; otherwise create new
3. **Load messages**: Retrieve conversation history (up to last 100 messages)
4. **Call agent**: Pass messages + new user message to OpenAI Agents SDK
5. **Execute tools**: Agent calls MCP tools as needed (add_task, list_tasks, etc.)
6. **Save messages**: Store user message and assistant response in database
7. **Return response**: Send assistant response with conversation_id and tool_calls

### Error Handling
- 401 Unauthorized: Invalid/missing JWT token
- 403 Forbidden: user_id mismatch (path vs token)
- 404 Not Found: conversation_id doesn't exist or doesn't belong to user
- 429 Too Many Requests: Rate limit exceeded (100/hour per user)
- 500 Internal Server Error: OpenAI API failure, database error, or tool execution failure

### Performance Considerations
- Load only last 100 messages (configurable via settings)
- Use database connection pooling (already configured in Phase 2)
- Set timeout for OpenAI API calls (30 seconds)
- Implement caching for user authentication (JWT validation)
- Use async/await for non-blocking I/O

### Best Practices
- Log all requests with user_id, conversation_id, and tool calls for debugging
- Implement request_id for distributed tracing
- Use transaction for saving user message + assistant response (atomicity)
- Return partial response if tool execution fails but agent responds
- Include timestamps in all responses

### Alternatives Considered
- **WebSocket-based chat**: More complex, requires connection management, violates stateless principle
- **Server-Sent Events (SSE)**: Good for streaming but adds complexity for MVP
- **In-memory conversation storage**: Violates stateless principle, doesn't scale

---

## 6. Rate Limiting Strategy

### Decision
Implement **100 requests per hour per user** rate limit using simple in-memory counter with Redis fallback for production.

### Rationale
- Prevents abuse and manages OpenAI API costs
- Simple in-memory implementation sufficient for development
- Redis-based distributed rate limiting for production (Phase 4+)
- Aligns with stateless design (rate limit state is not session state)

### Implementation Pattern
```python
# Development: in-memory with sliding window
from collections import defaultdict
from datetime import datetime, timedelta

rate_limits = defaultdict(list)

def check_rate_limit(user_id: str, limit: int = 100, window: int = 3600) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(seconds=window)

    # Remove old requests
    rate_limits[user_id] = [ts for ts in rate_limits[user_id] if ts > cutoff]

    if len(rate_limits[user_id]) >= limit:
        return False

    rate_limits[user_id].append(now)
    return True
```

### Production Pattern (Phase 4+)
- Use Redis with sliding window algorithm
- Distributed across multiple backend instances
- Configurable limits per user tier (free vs paid)

### Best Practices
- Return 429 with Retry-After header
- Include rate limit info in response headers (X-RateLimit-Limit, X-RateLimit-Remaining)
- Log rate limit violations for monitoring
- Allow higher limits for testing/development environments

### Alternatives Considered
- **Token bucket algorithm**: More complex, overkill for simple hourly limit
- **No rate limiting**: Risk of abuse and runaway costs
- **Per-request cost-based limiting**: More accurate but significantly more complex

---

## 7. Testing Strategy

### Decision
Implement **3-tier testing strategy**: Unit tests for MCP tools, Integration tests for chat endpoint, E2E tests for full flow.

### Rationale
- TDD discipline required by Constitution principle V
- Unit tests validate tool logic in isolation
- Integration tests verify stateless chat endpoint behavior
- E2E tests ensure UI-to-database flow works end-to-end
- Fast feedback loop (unit tests < 1s, integration tests < 5s)

### Test Structure

#### Unit Tests (pytest)
```python
# backend/tests/test_mcp_tools.py
def test_add_task_tool_creates_task():
    """Unit test: add_task tool creates task in database"""
    result = add_task_tool.function(user_id="test-user", title="Test task")
    assert result["status"] == "created"
    assert result["task_id"] is not None

def test_list_tasks_tool_filters_by_user():
    """Unit test: list_tasks tool enforces user isolation"""
    # Setup: Create tasks for two different users
    # Assert: list_tasks only returns current user's tasks
```

#### Integration Tests (pytest + TestClient)
```python
# backend/tests/test_chat_endpoint.py
def test_chat_endpoint_creates_conversation():
    """Integration test: POST /chat creates new conversation"""
    response = client.post("/api/test-user/chat",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={"message": "Hello"})
    assert response.status_code == 200
    assert "conversation_id" in response.json()

def test_chat_endpoint_requires_jwt():
    """Integration test: Chat endpoint rejects requests without JWT"""
    response = client.post("/api/test-user/chat", json={"message": "Hello"})
    assert response.status_code == 401
```

#### E2E Tests (Jest + React Testing Library)
```typescript
// frontend/__tests__/chat/chat-flow.test.tsx
test('user can create task via chat', async () => {
  render(<ChatPage />);
  const input = screen.getByPlaceholderText(/ask me to create/i);
  fireEvent.change(input, { target: { value: 'Create a task to test e2e' } });
  fireEvent.click(screen.getByRole('button', { name: /send/i }));

  await waitFor(() => {
    expect(screen.getByText(/task created successfully/i)).toBeInTheDocument();
  });
});
```

### Test Coverage Goals
- Unit tests: 90%+ coverage for MCP tools and agent service
- Integration tests: 100% coverage for chat endpoint flows
- E2E tests: Critical user journeys (create, list, update, complete, delete tasks via chat)

### Best Practices
- Mock OpenAI API calls in unit/integration tests (use responses library)
- Use test database for integration tests (clean up after each test)
- Run tests in CI/CD pipeline before deployment
- Write tests BEFORE implementation (Red-Green-Refactor)
- Keep tests fast (unit tests < 100ms each, integration tests < 1s each)

### Alternatives Considered
- **Only integration tests**: Slower feedback, harder to debug, less granular
- **Manual testing only**: Not scalable, no regression protection, violates TDD principle
- **Playwright for E2E**: More powerful but heavier, Jest sufficient for MVP

---

## 8. Environment Configuration

### Decision
Add the following environment variables to `backend/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_API_TIMEOUT=30

# MCP Configuration (optional, for external MCP server)
# MCP_SERVER_URL=http://localhost:8001

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=100

# Existing Phase 2 variables (no changes)
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=...
BETTER_AUTH_URL=http://localhost:3000
```

### Rationale
- Keeps secrets out of codebase
- Allows different configurations per environment (dev, staging, prod)
- Aligns with Constitution principle VI (Extensibility)
- Backward compatible with Phase 2

### Best Practices
- Never commit .env files to git
- Use .env.example for documentation
- Validate required env vars on startup
- Use Pydantic Settings for type-safe configuration
- Rotate OpenAI API keys regularly

---

## Summary

All technical unknowns have been resolved. The research establishes:

1. ✅ OpenAI Agents SDK with GPT-4o for AI agent
2. ✅ MCP SDK for standardized tool definitions
3. ✅ SQLModel database schema for conversations and messages
4. ✅ OpenAI ChatKit for frontend UI
5. ✅ Stateless REST endpoint for chat
6. ✅ Simple rate limiting strategy
7. ✅ Comprehensive testing strategy (Unit + Integration + E2E)
8. ✅ Environment configuration approach

**Next Step**: Proceed to Phase 1 (Design & Contracts) to create data-model.md, API contracts, and quickstart.md.
