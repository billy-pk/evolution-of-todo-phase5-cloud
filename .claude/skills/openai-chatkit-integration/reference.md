---
name: openai-chatkit-integration-reference
description: Technical reference for ChatKit Store interface, ChatKitServer API, authentication patterns, and architecture details for custom backend integration.
---

# OpenAI ChatKit Integration - Technical Reference

## Store Interface Reference

The `Store` interface is the core abstraction for persisting ChatKit data (threads, messages, attachments).

### Store[TContext] Abstract Class

```python
from typing import Generic, TypeVar, Literal
from chatkit.server import Store, ThreadMetadata, ThreadItem, Page, Attachment

TContext = TypeVar('TContext')

class Store(Generic[TContext]):
    """Base class for ChatKit storage implementations."""
```

### Required Methods

#### Thread Management

```python
def generate_thread_id(self, context: TContext) -> str:
    """Generate unique thread ID."""

async def load_thread(self, thread_id: str, context: TContext) -> ThreadMetadata:
    """Load thread metadata by ID."""

async def save_thread(self, thread: ThreadMetadata, context: TContext) -> None:
    """Save or update thread metadata."""

async def delete_thread(self, thread_id: str, context: TContext) -> None:
    """Delete thread and all its items."""

async def load_threads(
    self,
    limit: int,
    after: str | None,
    order: str,
    context: TContext
) -> Page[ThreadMetadata]:
    """List threads with pagination."""
```

#### Item Management

```python
def generate_item_id(
    self,
    item_type: Literal["message", "tool_call", "task", "workflow", "attachment"],
    thread: ThreadMetadata,
    context: TContext,
) -> str:
    """Generate unique item ID."""

async def load_thread_items(
    self,
    thread_id: str,
    after: str | None,
    limit: int,
    order: str,
    context: TContext
) -> Page[ThreadItem]:
    """List items in a thread with pagination."""

async def load_item(
    self,
    thread_id: str,
    item_id: str,
    context: TContext
) -> ThreadItem:
    """Load a specific thread item."""

async def save_item(
    self,
    thread_id: str,
    item: ThreadItem,
    context: TContext
) -> None:
    """Save or update a thread item."""

async def add_thread_item(
    self,
    thread_id: str,
    item: ThreadItem,
    context: TContext
) -> None:
    """Add new item to thread."""

async def delete_thread_item(
    self,
    thread_id: str,
    item_id: str,
    context: TContext
) -> None:
    """Delete a specific thread item."""
```

#### Attachment Management

```python
async def load_attachment(
    self,
    attachment_id: str,
    context: TContext
) -> Attachment:
    """Load attachment metadata."""

async def save_attachment(
    self,
    attachment: Attachment,
    context: TContext
) -> None:
    """Save attachment metadata."""

async def delete_attachment(
    self,
    attachment_id: str,
    context: TContext
) -> None:
    """Delete attachment."""
```

## ChatKitServer API Reference

### ChatKitServer[TContext] Abstract Class

```python
from chatkit.server import ChatKitServer, ThreadMetadata, UserMessageItem, ThreadStreamEvent
from typing import AsyncIterator

class ChatKitServer(Generic[TContext]):
    """Base class for ChatKit server implementations."""

    def __init__(self, store: Store[TContext]):
        self.store = store

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: TContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Process user input and stream AI responses.

        Args:
            thread: Current conversation thread
            input: User's message (None for thread creation)
            context: Request context (user_id, session data, etc.)

        Yields:
            ThreadStreamEvent: Events for ChatKit UI to render
        """
        raise NotImplementedError
```

### Response Event Types

```python
from chatkit.server import (
    ThreadItemDoneEvent,
    ThreadItemStreamPartEvent,
    AssistantMessageItem,
)

# Complete message event
ThreadItemDoneEvent(item=AssistantMessageItem(...))

# Streaming text chunk
ThreadItemStreamPartEvent(
    item_id="msg-123",
    delta={"type": "text", "text": "partial response"}
)
```

## Agent Integration API

### Conversion Functions

```python
from chatkit.agents import simple_to_agent_input, stream_agent_response, AgentContext

# Convert ChatKit input to Agent SDK format
agent_input = await simple_to_agent_input(chatkit_user_message)

# Convert Agent SDK events to ChatKit events
async for event in stream_agent_response(agent_context, agent_result):
    yield event
```

### AgentContext

```python
agent_context = AgentContext(
    thread=thread,              # ThreadMetadata
    store=self.store,          # Store instance
    request_context=context,   # User context (dict)
)
```

## Authentication Patterns

### Pattern 1: JWT with Custom Fetch (Recommended)

**Frontend:**
```tsx
const { control } = useChatKit({
  api: {
    url: `${apiUrl}/chatkit`,
    domainKey: process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY || 'localhost-dev',
    async fetch(input, init) {
      const token = await getAuthToken();  // Your auth function
      return fetch(input, {
        ...init,
        headers: {
          ...init?.headers,
          'Authorization': `Bearer ${token}`,
        },
      });
    },
  },
});
```

**Backend:**
```python
@chatkit_router.post("/chatkit")
async def chatkit_endpoint(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user_id = verify_jwt(token)  # Your JWT validation

    context = {"user_id": user_id}
    body = await request.body()
    result = await chatkit_server.process(body, context)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

### Pattern 2: Session Cookies

**Frontend:**
```tsx
const { control } = useChatKit({
  api: {
    url: `${apiUrl}/chatkit`,
    domainKey: 'localhost-dev',
    async fetch(input, init) {
      return fetch(input, {
        ...init,
        credentials: 'include',  // Include cookies
      });
    },
  },
});
```

**Backend:**
```python
from fastapi import Request, Depends

async def get_user_from_session(request: Request):
    session_id = request.cookies.get("session_id")
    user = await verify_session(session_id)
    return user

@chatkit_router.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    user: User = Depends(get_user_from_session)
):
    context = {"user_id": user.id}
    # ... rest of implementation
```

## Architecture Patterns

### Pattern 1: In-Memory Store (Development)

**Use When:**
- Rapid development
- Testing
- Prototyping

**Limitations:**
- Data lost on server restart
- Not suitable for production
- No persistence

**Implementation:** See `examples.md` for `SimpleMemoryStore`

### Pattern 2: PostgreSQL Store (Production)

**Use When:**
- Production deployment
- Need persistence
- Multiple server instances

**Implementation:**
```python
from chatkit.stores import PostgresStore

data_store = PostgresStore(
    connection_string=os.getenv("DATABASE_URL"),
    table_prefix="chatkit_",
)
```

**Database Schema:**
ChatKit automatically creates:
- `chatkit_threads` - Thread metadata
- `chatkit_items` - Messages and other thread items
- `chatkit_attachments` - File attachments

### Pattern 3: Hybrid Store (Custom Integration)

**Use When:**
- Existing database schema
- Custom requirements
- Multi-database architecture

**Implementation:**
```python
class HybridStore(Store[dict]):
    """Integrate with existing Conversation/Message models."""

    def __init__(self, db_engine):
        self.engine = db_engine

    async def save_thread(self, thread: ThreadMetadata, context: dict):
        # Map ChatKit thread to your Conversation model
        with Session(self.engine) as session:
            conversation = Conversation(
                id=thread.id,
                user_id=context["user_id"],
                title=thread.title or "New Chat",
                created_at=datetime.now(UTC),
            )
            session.add(conversation)
            session.commit()

    async def load_thread(self, thread_id: str, context: dict) -> ThreadMetadata:
        # Load from your Conversation model
        with Session(self.engine) as session:
            conv = session.get(Conversation, thread_id)
            if not conv:
                raise ValueError(f"Thread {thread_id} not found")

            return ThreadMetadata(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
            )
```

## Performance Optimization

### 1. MCP Server Connection Pooling

**Problem:** Creating new MCP connection per request is slow.

**Solution:** Singleton pattern with connection reuse.

```python
from typing import Optional
from mcp.client import MCPServerStreamableHttp

_mcp_server: Optional[MCPServerStreamableHttp] = None

async def get_mcp_server() -> MCPServerStreamableHttp:
    """Get or create singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="Task MCP Server",
            params={
                "url": os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"),
                "timeout": 30,
            },
            cache_tools_list=True,      # Cache tool definitions
            max_retry_attempts=3,       # Retry on failure
        )
    return _mcp_server

# Usage in ChatKitServer.respond()
async def respond(self, thread, input, context):
    mcp_server = await get_mcp_server()
    agent = Agent(mcp_servers=[mcp_server], ...)
    async with mcp_server:
        # Use server
        pass
```

### 2. Database Query Optimization

**Pagination:**
```python
async def load_threads(self, limit: int, after: str | None, order: str, context: dict):
    with Session(self.engine) as session:
        query = select(Conversation).where(
            Conversation.user_id == context["user_id"]
        ).order_by(Conversation.created_at.desc()).limit(limit)

        if after:
            # Pagination using cursor
            after_conv = session.get(Conversation, after)
            if after_conv:
                query = query.where(Conversation.created_at < after_conv.created_at)

        conversations = session.exec(query).all()

        return Page(
            data=[thread_metadata_from_conv(c) for c in conversations],
            has_more=len(conversations) == limit
        )
```

**Indexing:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_conversations_user_created ON conversations(user_id, created_at DESC);
CREATE INDEX idx_messages_thread_created ON messages(thread_id, created_at DESC);
```

### 3. Caching

**Thread Metadata Cache:**
```python
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=1000)
def get_cached_thread(thread_id: str, timestamp: int) -> ThreadMetadata:
    """Cache thread metadata for 5 minutes."""
    with Session(engine) as session:
        # Load thread
        return thread_metadata

# Usage with time-based invalidation
timestamp = int(datetime.now().timestamp() / 300)  # 5-minute buckets
thread = get_cached_thread(thread_id, timestamp)
```

## Error Handling

### Error Response Pattern

```python
from chatkit.server import AssistantMessageItem, ThreadItemDoneEvent

async def respond(self, thread, input, context):
    try:
        # Process message
        pass
    except ValidationError as e:
        # User input validation error
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "text",
                "text": f"Invalid input: {str(e)}"
            }],
        )
        yield ThreadItemDoneEvent(item=error_item)
    except PermissionError as e:
        # Authorization error
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "text",
                "text": "You don't have permission to perform this action."
            }],
        )
        yield ThreadItemDoneEvent(item=error_item)
    except Exception as e:
        # Generic error
        logger.error(f"ChatKit error: {e}", exc_info=True)
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "text",
                "text": "Sorry, I encountered an error. Please try again."
            }],
        )
        yield ThreadItemDoneEvent(item=error_item)
```

## Production Error Handling

### Pydantic Validation Errors

ChatKit's `AssistantMessageItem` has strict schema requirements that are easy to violate in error handling code.

#### Error 1: Missing created_at Field

**Symptom:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for AssistantMessageItem
created_at
  Field required [type=missing, input_value={'id': 'msg-123', 'thread_id': 'thread-456', ...}, input_type=dict]
```

**Cause:** Forgot to include `created_at` when creating `AssistantMessageItem`.

**Solution:**
```python
from datetime import datetime, UTC
from chatkit.server import AssistantMessageItem

# ❌ WRONG - Missing created_at
error_item = AssistantMessageItem(
    id=self.store.generate_item_id("message", thread, context),
    thread_id=thread.id,
    content=[{"type": "output_text", "text": "Error"}],
)

# ✅ CORRECT - Include created_at
error_item = AssistantMessageItem(
    id=self.store.generate_item_id("message", thread, context),
    thread_id=thread.id,
    content=[{"type": "output_text", "text": "Error"}],
    created_at=datetime.now(UTC),  # REQUIRED
)
```

#### Error 2: Wrong Content Type

**Symptom:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for AssistantMessageItem
content.0.type
  Input should be 'output_text' [type=literal_error, input_value='text', input_type=str]
```

**Cause:** Used `"type": "text"` instead of `"type": "output_text"`.

**Solution:**
```python
# ❌ WRONG - Invalid content type
content=[{"type": "text", "text": "Error"}]

# ✅ CORRECT - Use output_text
content=[{"type": "output_text", "text": "Error"}]
```

#### Complete Error Response Template

**Use this template for all error responses:**

```python
from datetime import datetime, UTC
from chatkit.server import AssistantMessageItem, ThreadItemDoneEvent

async def respond(self, thread, input, context):
    try:
        # Your logic here
        pass
    except Exception as e:
        # Log error server-side
        logger.error(f"ChatKit error: {e}", exc_info=True)

        # Create error response
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "output_text",  # Must be output_text
                "text": "I encountered an error. Please try again."
            }],
            created_at=datetime.now(UTC),  # Required field
        )
        yield ThreadItemDoneEvent(item=error_item)
```

### Common Error Handling Scenarios

#### Scenario 1: Empty Message

```python
async def respond(self, thread, input, context):
    if input is None or not input.content:
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "output_text",
                "text": "No message provided. Please send a message."
            }],
            created_at=datetime.now(UTC),
        )
        yield ThreadItemDoneEvent(item=error_item)
        return
```

#### Scenario 2: Authentication Error

```python
async def respond(self, thread, input, context):
    user_id = context.get("user_id")
    if not user_id:
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "output_text",
                "text": "Authentication required. Please sign in."
            }],
            created_at=datetime.now(UTC),
        )
        yield ThreadItemDoneEvent(item=error_item)
        return
```

#### Scenario 3: Tool Execution Error

```python
async def respond(self, thread, input, context):
    try:
        # Execute MCP tool
        result = await agent.run(input)
    except ToolExecutionError as e:
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "output_text",
                "text": f"Failed to execute action: {str(e)}"
            }],
            created_at=datetime.now(UTC),
        )
        yield ThreadItemDoneEvent(item=error_item)
        return
```

#### Scenario 4: Database Error

```python
async def respond(self, thread, input, context):
    try:
        # Database operation
        await self.store.save_item(thread.id, item, context)
    except DatabaseError as e:
        logger.error(f"Database error: {e}", exc_info=True)
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{
                "type": "output_text",
                "text": "Failed to save message. Please try again."
            }],
            created_at=datetime.now(UTC),
        )
        yield ThreadItemDoneEvent(item=error_item)
```

### CORS Troubleshooting

#### Problem 1: Wildcard Origin with Credentials

**Error:**
```
Access to fetch at 'https://api.example.com/chatkit' from origin 'https://app.example.com'
has been blocked by CORS policy: Response to preflight request doesn't pass access control
check: The value of the 'Access-Control-Allow-Origin' header must not be the wildcard '*'
when the request's credentials mode is 'include'.
```

**Cause:** Using `allow_origins=["*"]` with `allow_credentials=True` is not allowed by CORS spec.

**Solution:**
```python
# ❌ WRONG - Wildcard with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # Conflict!
)

# ✅ CORRECT - Explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://app.example.com",
        "https://app-preview-xyz.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Problem 2: Missing Vercel Preview URLs

**Error:** CORS works in production but fails on Vercel preview deployments.

**Cause:** Vercel creates unique URLs for each preview deployment (e.g., `app-git-feature-xyz.vercel.app`).

**Solution 1 - Add all preview URLs manually:**
```python
allow_origins=[
    "http://localhost:3000",
    "https://app.vercel.app",  # Production
    "https://app-git-main-xyz.vercel.app",  # Main branch preview
    "https://app-git-feature-abc.vercel.app",  # Feature branch
]
```

**Solution 2 - Pattern matching (custom middleware):**
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")

        # Allow localhost and Vercel domains
        if origin and (
            origin.startswith("http://localhost:") or
            origin.endswith(".vercel.app")
        ):
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        return await call_next(request)

app.add_middleware(DynamicCORSMiddleware)
```

#### Problem 3: Wrong Backend URL in Frontend

**Error:** CORS configured correctly but still getting errors.

**Cause:** Frontend calling old backend URL.

**Check:**
```bash
# Frontend environment
echo $NEXT_PUBLIC_API_URL

# Should match backend deployment URL
# Example: https://api.example.com (not https://api-old-xyz.example.com)
```

**Fix:** Update environment variable in deployment settings:
```env
NEXT_PUBLIC_API_URL=https://api.example.com
```

#### Problem 4: Preflight Request Fails

**Error:**
```
Access to fetch blocked by CORS policy: Response to preflight request doesn't pass
access control check: No 'Access-Control-Allow-Origin' header is present.
```

**Cause:** Backend not handling OPTIONS requests.

**Solution:** FastAPI's CORSMiddleware handles this automatically, but verify:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],  # Must include OPTIONS
    allow_headers=["*"],
    expose_headers=["Authorization"],
)
```

#### Testing CORS Configuration

**Test 1: Browser DevTools**
```javascript
// Run in browser console on your frontend
fetch('https://api.example.com/chatkit', {
    method: 'POST',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token',
    },
    body: JSON.stringify({test: 'data'}),
})
.then(r => console.log('Success:', r))
.catch(e => console.error('Error:', e));
```

**Test 2: curl**
```bash
# Test preflight
curl -X OPTIONS https://api.example.com/chatkit \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization" \
  -v

# Should return:
# Access-Control-Allow-Origin: https://app.example.com
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: *
```

**Test 3: Automated Testing**
```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_cors_headers():
    async with httpx.AsyncClient() as client:
        # Preflight request
        response = await client.options(
            "http://localhost:8000/chatkit",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            }
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"
```

### Production Deployment Checklist - CORS

Before deploying to production:

- [ ] Remove `allow_origins=["*"]` if using `allow_credentials=True`
- [ ] Add all frontend domains to `allow_origins` list
- [ ] Include Vercel preview URLs or use pattern matching
- [ ] Test with browser DevTools Network tab
- [ ] Verify preflight requests return correct headers
- [ ] Check environment variables match deployment URLs
- [ ] Test from production frontend to production backend
- [ ] Monitor CORS errors in backend logs

## Streaming Response Pattern

### Server-Sent Events (SSE)

ChatKit uses SSE for streaming. FastAPI handles this automatically:

```python
from fastapi.responses import StreamingResponse
from chatkit.server import StreamingResult

result = await chatkit_server.process(body, context)

if isinstance(result, StreamingResult):
    return StreamingResponse(
        result,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### Streaming Event Format

```
event: thread.message.delta
data: {"type":"text","text":"Hello"}

event: thread.message.done
data: {"id":"msg-123","content":[{"type":"text","text":"Hello world"}]}
```

## Security Considerations

### 1. User Isolation

Always filter by user_id from context:

```python
async def load_threads(self, limit: int, after: str | None, order: str, context: dict):
    user_id = context.get("user_id")
    if not user_id:
        raise PermissionError("No user context")

    # ALWAYS filter by user_id
    query = select(Conversation).where(Conversation.user_id == user_id)
```

### 2. Input Validation

Validate all user inputs before processing:

```python
async def respond(self, thread, input, context):
    if input is None:
        return

    # Validate message content
    if not input.content:
        raise ValidationError("Empty message")

    # Check message length
    total_length = sum(len(c.get("text", "")) for c in input.content)
    if total_length > 10000:
        raise ValidationError("Message too long")
```

### 3. Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@chatkit_router.post("/chatkit")
@limiter.limit("60/minute")  # 60 requests per minute
async def chatkit_endpoint(request: Request):
    # Process request
    pass
```

## Domain Verification

### Development (Localhost)

Domain verification is **automatically skipped** for `localhost` and `127.0.0.1`.

```tsx
// Works without domain registration
domainKey: 'localhost-dev'
```

### Production

1. **Register Domain:**
   - Go to: https://platform.openai.com/settings/organization/security/domain-allowlist
   - Add your domain (e.g., `app.example.com`)
   - Receive `domainKey`

2. **Configure Frontend:**
   ```env
   NEXT_PUBLIC_CHATKIT_DOMAIN_KEY=dk_xxx...
   ```

3. **Wait for Propagation:**
   - Takes 20-30 minutes
   - Test with: `curl https://yourapp.com/chatkit`

4. **HTTPS Required:**
   - Production ChatKit requires HTTPS
   - HTTP will fail domain verification
