---
name: openai-chatkit-integration
description: Integrate OpenAI ChatKit with custom FastAPI backend for production-ready AI chat UI. Includes authentication, MCP tools integration, database connectivity, and real-time streaming.
---

# OpenAI ChatKit Integration with Custom Backend

## Overview

This skill documents the complete implementation of OpenAI ChatKit with a self-hosted custom backend, including authentication, agent integration with MCP tools, and real database connectivity. ChatKit provides a production-ready chat UI while your backend maintains full control over data, business logic, and agent behavior.

### What is ChatKit?

ChatKit is OpenAI's framework for building AI-powered chat experiences with:
- Production-ready React component with built-in UI
- Streaming response support
- Thread/conversation management
- Widget and tool integration
- Customizable theming

### When to Use This Skill

Use this skill when you need to:
- Add AI chat interface to existing applications
- Integrate chat UI with your own database and authentication
- Connect chat to custom tools and APIs via MCP
- Build multi-tenant chat applications with user isolation
- Deploy production-ready chat without building UI from scratch

## Architecture Decision: Custom Backend vs Hosted

**Two Integration Modes:**

1. **Hosted Mode** (uses OpenAI infrastructure):
   - Uses `getClientSecret` to fetch tokens from OpenAI
   - Messages route through OpenAI servers
   - Requires OpenAI API key
   - Simpler setup but less control

2. **Custom Backend Mode** (self-hosted) - **Recommended for production**:
   - Uses `url` + `domainKey` + custom `fetch`
   - Full control over backend logic
   - Connect to your own databases and services
   - Better for privacy and custom integrations
   - Requires ChatKit Python SDK on backend

**We implement Custom Backend Mode for maximum control.**

## Quick Start

### Prerequisites

**Frontend Dependencies:**
```bash
npm install @openai/chatkit-react
```

**Backend Dependencies:**
```bash
pip install openai-chatkit agents fastapi
```

**Environment Variables:**

Frontend (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CHATKIT_DOMAIN_KEY=localhost-dev  # For production: get from OpenAI
```

Backend (`.env`):
```env
OPENAI_API_KEY=sk-proj-...
MCP_SERVER_URL=http://localhost:8001/mcp  # If using MCP tools
```

## Implementation Steps

### Step 1: Load ChatKit Web Component (Frontend)

ChatKit React requires a web component loaded from OpenAI's CDN.

**File**: `app/layout.tsx`

```tsx
import Script from "next/script";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* ChatKit Web Component - REQUIRED */}
        <Script
          src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
          strategy="beforeInteractive"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

**Why `beforeInteractive`?** Ensures the web component is available before React hydration.

### Step 2: Configure ChatKit React (Frontend)

**File**: `app/(dashboard)/chat/page.tsx`

```tsx
'use client';

import { ChatKit, useChatKit } from '@openai/chatkit-react';
import { authClient } from '@/lib/auth-client';

export default function ChatPage() {
  const { data: session } = useSession();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const { control } = useChatKit({
    api: {
      url: `${apiUrl}/chatkit`,
      domainKey: process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY || 'localhost-dev',

      // Inject authentication headers
      async fetch(input: RequestInfo | URL, init?: RequestInit) {
        const { data, error } = await authClient.token();
        if (error || !data?.token) {
          throw new Error('Not authenticated');
        }

        return fetch(input, {
          ...init,
          headers: {
            ...init?.headers,
            'Authorization': `Bearer ${data.token}`,
          },
        });
      },
    },
    theme: {
      colorScheme: 'light',
      color: { accent: { primary: '#2563eb', level: 2 } },
    },
    startScreen: {
      greeting: 'Welcome to AI Assistant',
      prompts: [
        { label: 'Create a task', prompt: 'Create a new task for me', icon: 'notebook-pencil' },
        { label: 'List tasks', prompt: 'Show me all my tasks', icon: 'search' },
      ],
    },
  });

  if (!session?.user) return null;

  return <ChatKit control={control} className="flex-1 w-full" />;
}
```

**Key Points:**
- Use `url` + `domainKey` for custom backend (NOT `getClientSecret`)
- Custom `fetch` injects your auth token into every request
- `domainKey` validation is skipped on localhost for development

### Step 3: Create ChatKit Backend (Backend)

**File**: `backend/services/chatkit_server.py`

```python
from chatkit.server import ChatKitServer, Store, ThreadMetadata, ThreadItem
from chatkit.agents import stream_agent_response, simple_to_agent_input, AgentContext
from agents import Runner

class TaskManagerChatKitServer(ChatKitServer[dict]):
    """Custom ChatKit server integrating with MCP tools."""

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if input is None:
            return

        user_id = context.get("user_id")

        # Import your existing agent
        from services.agent import create_task_agent

        # Create agent context
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        # Convert ChatKit input to Agent format
        agent_input = await simple_to_agent_input(input)

        # Create agent with MCP tools (connects to PostgreSQL)
        agent, mcp_server = await create_task_agent(user_id)

        async with mcp_server:
            result = Runner.run_streamed(agent, input=agent_input)

            # Stream response back to ChatKit
            async for event in stream_agent_response(agent_context, result):
                yield event
```

**Integration Pattern:**
- Reuse your existing MCP-connected agent
- `simple_to_agent_input()` converts ChatKit → Agent SDK format
- `stream_agent_response()` converts Agent SDK → ChatKit format

### Step 4: Create ChatKit Endpoint (Backend)

**File**: `backend/routes/chatkit.py`

```python
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from chatkit.server import StreamingResult, NonStreamingResult
from services.chatkit_server import TaskManagerChatKitServer, SimpleMemoryStore

chatkit_router = APIRouter()

# Initialize ChatKit server
data_store = SimpleMemoryStore()  # See reference.md for implementation
chatkit_server = TaskManagerChatKitServer(data_store)

@chatkit_router.post("/chatkit")
async def chatkit_endpoint(request: Request):
    # Validate JWT
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:]  # Remove "Bearer "
    user_id = verify_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Pass user context
    context = {"user_id": user_id}
    body = await request.body()

    # Process through ChatKit
    result = await chatkit_server.process(body, context)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    elif isinstance(result, NonStreamingResult):
        return Response(content=result.json, media_type="application/json")
```

**Authentication Flow:**
1. Frontend injects JWT in custom `fetch`
2. Backend validates JWT
3. `user_id` passed as context to ChatKitServer
4. All operations scoped to that user

## Common Pitfalls and Solutions

### 1. "Invalid client secret format" Error

**Problem**: Mixing `getClientSecret` with custom backend.

**Solution**: Use `url` + `domainKey` + `fetch` (NOT `getClientSecret`):

```tsx
// ❌ WRONG - For custom backend
api: {
  url: `${apiUrl}/chatkit`,
  async getClientSecret() { return token; }  // Don't mix these!
}

// ✅ CORRECT - For custom backend
api: {
  url: `${apiUrl}/chatkit`,
  domainKey: 'localhost-dev',
  async fetch(input, init) {
    return fetch(input, {
      ...init,
      headers: { ...init?.headers, 'Authorization': `Bearer ${token}` }
    });
  }
}
```

### 2. ChatKit Shows Empty Box

**Problem**: Web component not loaded or invalid configuration.

**Solutions:**
- Ensure ChatKit script loaded in `<head>` with `beforeInteractive`
- Use valid icon names: `notebook-pencil`, `search`, `lightbulb`, `sparkle`, `square-code`, `chart`
- Don't mix `url` with `getClientSecret`

```tsx
// ❌ Invalid icon
icon: 'pencil'  // Not valid

// ✅ Valid icon
icon: 'notebook-pencil'
```

### 3. Tasks Not Persisting to Database

**Problem**: Using basic Agent without MCP tools.

**Solution**: Connect your existing MCP-backed agent:

```python
# ❌ WRONG - No tools
agent = Agent(model="gpt-4o", instructions="Help user")

# ✅ CORRECT - With MCP tools
from services.agent import create_task_agent
agent, mcp_server = await create_task_agent(user_id)
```

### 4. CORS or 401 Errors

**Problem**: Authentication not properly configured.

**Solutions:**
- Verify custom `fetch` injects auth headers
- Check backend CORS allows credentials
- Ensure JWT validation is correct

```python
# Backend CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Domain Verification (Production)

**Problem**: Domain not registered with OpenAI.

**Solution:**
1. Register at: https://platform.openai.com/settings/organization/security/domain-allowlist
2. Get `domainKey` from OpenAI
3. Set `NEXT_PUBLIC_CHATKIT_DOMAIN_KEY`
4. Wait 20-30 minutes for propagation

**Note**: Localhost skips verification during development.

### 6. Pydantic Validation Errors (Critical)

**Problem**: Error responses fail with `ValidationError: Field required` or wrong content type.

**Common Errors:**
```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for AssistantMessageItem
created_at - Field required
content.0.type - Input should be 'output_text'
```

**Solution**: Always include `created_at` and use `"output_text"` content type in error responses:

```python
from datetime import datetime, UTC
from chatkit.server import AssistantMessageItem, ThreadItemDoneEvent

# ✅ CORRECT - Complete error response
error_item = AssistantMessageItem(
    id=self.store.generate_item_id("message", thread, context),
    thread_id=thread.id,
    content=[{"type": "output_text", "text": "Error message here"}],
    created_at=datetime.now(UTC),  # REQUIRED
)
yield ThreadItemDoneEvent(item=error_item)
```

**Common mistake locations:**
- Empty message validation
- Authentication errors
- Database errors
- Tool execution failures

See `reference.md` for complete error handling patterns.

### 7. CORS Configuration (Production Blocker)

**Problem**: `No 'Access-Control-Allow-Origin' header` or CORS errors in production.

**Common Error:**
```
Access to fetch blocked by CORS policy: No 'Access-Control-Allow-Origin' header
```

**Solution**: Cannot use wildcard origins with credentials - must specify exact domains:

```python
# ❌ WRONG - Incompatible with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # Error: Can't use both!
)

# ✅ CORRECT - Exact origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourapp.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production checklist:**
- Add all Vercel deployment URLs (including preview URLs)
- Use HTTPS in production origins
- Test with browser DevTools Network tab

## Production Deployment Checklist

### Frontend
- [ ] Set `NEXT_PUBLIC_CHATKIT_DOMAIN_KEY` from OpenAI
- [ ] Register domain at OpenAI dashboard
- [ ] Use HTTPS (required in production)
- [ ] Enable error tracking

### Backend
- [ ] Replace `SimpleMemoryStore` with `PostgresStore`
- [ ] Add rate limiting to `/chatkit` endpoint
- [ ] Configure production CORS
- [ ] Add monitoring for MCP server health
- [ ] Use connection pooling

### Infrastructure
- [ ] Run 3 services: Frontend, Backend, MCP Server
- [ ] Use process manager (systemd, PM2)
- [ ] Set up reverse proxy (nginx)
- [ ] Configure SSL certificates
- [ ] Add health checks

## Performance Optimization

### MCP Server Singleton

Reuse MCP connection across requests:

```python
_mcp_server = None

async def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(...)
    return _mcp_server
```

### Database Store

Use `PostgresStore` for production persistence:

```python
from chatkit.stores import PostgresStore

data_store = PostgresStore(
    connection_string="postgresql://...",
    table_prefix="chatkit_",
)
```

## Next Steps

1. See `reference.md` for complete Store implementation and API details
2. Check `examples.md` for full working code examples
3. Use `templates.md` for copy-paste templates
4. Read official docs: https://openai.github.io/chatkit-js/

## Related Skills

- **FastMCP Database Tools** - Building MCP servers with database integration
- **Better Auth JWT Integration** - Setting up authentication
- **OpenAI Agents SDK** - Creating AI agents with tools
- **Multi-Tenant Architecture** - User isolation patterns

## Resources

### Official Documentation
- [ChatKit JS Documentation](https://openai.github.io/chatkit-js/)
- [ChatKit Python SDK](https://openai.github.io/chatkit-python/)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-sdk)

### Community
- [ChatKit GitHub Issues](https://github.com/openai/chatkit-js/issues)
- [ChatKit Advanced Samples](https://github.com/openai/openai-chatkit-advanced-samples)
