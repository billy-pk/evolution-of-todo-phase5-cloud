---
name: nextjs-fastapi-mcp-architecture
description: Build production-ready AI applications with Next.js frontend, FastAPI backend, and MCP tools. Includes JWT authentication flow, user isolation, and multi-server deployment patterns.
---

# Next.js + FastAPI + MCP Architecture

## Overview

This skill documents a complete three-tier architecture for building AI-powered applications with:
- **Frontend**: Next.js 15 App Router with Better Auth
- **Backend**: FastAPI with JWT validation
- **MCP Server**: FastMCP with PostgreSQL tools

This architecture provides complete user isolation, scalable deployment, and seamless integration between AI agents and databases.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                          │
│  - Better Auth (JWT generation)                             │
│  - React components                                          │
│  - ChatKit UI                                                │
│  Port: 3000                                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP + JWT Bearer Token
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  - JWT validation (JWKS)                                    │
│  - REST endpoints                                            │
│  - OpenAI Agent integration                                  │
│  - ChatKit server                                            │
│  Port: 8000                                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP (MCP Protocol)
                 │
┌────────────────▼────────────────────────────────────────────┐
│                    MCP Server                                │
│  - FastMCP tools (CRUD operations)                          │
│  - Direct PostgreSQL access                                  │
│  - User-scoped operations                                    │
│  Port: 8001                                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ SQL Queries
                 │
┌────────────────▼────────────────────────────────────────────┐
│                 PostgreSQL Database                          │
│  - User data                                                 │
│  - Task data                                                 │
│  - Conversation/message data                                 │
│  Port: 5432                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

**Separation of Concerns:**
- Frontend: UI/UX and client-side state
- Backend: Business logic and authentication
- MCP Server: Data access and tool execution
- Database: Data persistence

**Benefits:**
- ✅ Independent scaling of each tier
- ✅ Clear security boundaries
- ✅ AI agents isolated from direct DB access
- ✅ Reusable MCP tools across multiple backends
- ✅ Easy to test each tier independently

## User Context Flow

The critical pattern is how user identity flows through all tiers:

```
1. User signs in via Better Auth
   ↓
2. Frontend receives JWT with user_id claim
   ↓
3. Frontend sends JWT in Authorization header
   ↓
4. Backend validates JWT (JWKS)
   ↓
5. Backend extracts user_id from JWT
   ↓
6. Backend passes user_id to Agent
   ↓
7. Agent calls MCP tools with user_id parameter
   ↓
8. MCP tools filter database queries by user_id
   ↓
9. Response flows back up the chain
```

**Key Principle**: Every operation is scoped to a user at every tier.

## Complete Setup Guide

### Step 1: Set Up Database

```sql
-- Create database
CREATE DATABASE myapp;

-- User table (Better Auth)
CREATE TABLE "user" (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Your application tables (all must have user_id)
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES "user"(id),
  title VARCHAR(200) NOT NULL,
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for user isolation queries
CREATE INDEX idx_tasks_user ON tasks(user_id);
```

### Step 2: Set Up MCP Server

**File**: `backend/tools/server.py`

```python
from mcp.server import FastMCP
from sqlmodel import Session, select, create_engine
from models import Task

# Database connection
engine = create_engine(os.getenv("DATABASE_URL"))

# Initialize MCP server
mcp = FastMCP("TaskMCPServer", stateless_http=True, json_response=True)

@mcp.tool()
def add_task_tool(user_id: str, title: str) -> dict:
    """Create a task for user."""
    with Session(engine) as session:
        # CRITICAL: Always scope to user_id
        task = Task(user_id=user_id, title=title)
        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "status": "success",
            "data": {"task_id": str(task.id), "title": task.title}
        }

@mcp.tool()
def list_tasks_tool(user_id: str) -> dict:
    """List all tasks for user."""
    with Session(engine) as session:
        # CRITICAL: Filter by user_id
        statement = select(Task).where(Task.user_id == user_id)
        tasks = session.exec(statement).all()

        return {
            "status": "success",
            "data": {"tasks": [{"id": str(t.id), "title": t.title} for t in tasks]}
        }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # Runs on port 8001
```

**Run it:**
```bash
cd backend/tools
python server.py
# Server running on http://localhost:8001/mcp
```

### Step 3: Set Up FastAPI Backend

**File**: `backend/main.py`

```python
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from middleware import verify_token  # JWT validation
from agents import Agent
from mcp.client import MCPServerStreamableHttp

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton MCP server connection
_mcp_server = None

async def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="Task MCP Server",
            params={"url": "http://localhost:8001/mcp", "timeout": 30},
            cache_tools_list=True,
        )
    return _mcp_server

# Dependency: Extract user_id from JWT
async def get_current_user(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header[7:]
    user_id = verify_token(token)  # Validates JWT via JWKS

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id

# Chat endpoint
@app.post("/api/chat")
async def chat(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    body = await request.json()
    message = body.get("message")

    # Create agent with MCP tools
    mcp_server = await get_mcp_server()
    agent = Agent(
        name="TaskAssistant",
        instructions=f"You help user {user_id} manage tasks. Always use user_id='{user_id}' when calling tools.",
        mcp_servers=[mcp_server],
        model="gpt-4o",
    )

    # Run agent
    async with mcp_server:
        result = await agent.run(message)
        return {"response": result}
```

**Run it:**
```bash
cd backend
uvicorn main:app --reload --port 8000
# Server running on http://localhost:8000
```

### Step 4: Set Up Next.js Frontend

**File**: `lib/api.ts`

```typescript
import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  // Get JWT from Better Auth
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new Error("Not authenticated");
  }

  // Make request with JWT
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${data.token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

// Usage
export const api = {
  chat: async (message: string) =>
    apiRequest("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
```

**Run it:**
```bash
cd frontend
npm run dev
# Server running on http://localhost:3000
```

## Development Workflow

### Starting All Services

```bash
# Terminal 1: Database (if using Docker)
docker-compose up postgres

# Terminal 2: MCP Server
cd backend/tools
python server.py

# Terminal 3: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 4: Frontend
cd frontend
npm run dev
```

### Environment Variables

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=<32+ char secret>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
```

**Backend** (`.env`):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
BETTER_AUTH_SECRET=<same as frontend>
BETTER_AUTH_ISSUER=http://localhost:3000
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
MCP_SERVER_URL=http://localhost:8001/mcp
OPENAI_API_KEY=sk-proj-xxx
```

**MCP Server** (uses backend `.env`):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
```

## Common Request Flows

### Flow 1: User Creates Task via Chat

```
1. User types "Create a task to buy groceries" in ChatKit
   ↓
2. ChatKit sends message to Backend via custom fetch (with JWT)
   ↓
3. Backend validates JWT → extracts user_id="user123"
   ↓
4. Backend creates Agent with user_id in instructions
   ↓
5. Agent processes message → decides to call add_task_tool
   ↓
6. Agent calls MCP: add_task_tool(user_id="user123", title="Buy groceries")
   ↓
7. MCP server creates task with user_id="user123" in database
   ↓
8. MCP returns success to Agent
   ↓
9. Agent generates response: "I've created the task 'Buy groceries'"
   ↓
10. Response streams back to ChatKit UI
```

### Flow 2: User Views Tasks in Dashboard

```
1. User visits /tasks page (protected route)
   ↓
2. Middleware checks session (Better Auth)
   ↓
3. Page component fetches: api.get("/api/user123/tasks")
   ↓
4. Frontend attaches JWT to request
   ↓
5. Backend validates JWT → extracts user_id="user123"
   ↓
6. Backend validates path user_id matches JWT user_id
   ↓
7. Backend queries database: SELECT * FROM tasks WHERE user_id='user123'
   ↓
8. Backend returns tasks to frontend
   ↓
9. Frontend renders task list
```

## Security Patterns

### Pattern 1: User Isolation at Every Tier

```python
# ❌ WRONG - No user filtering
@mcp.tool()
def list_tasks_tool() -> dict:
    tasks = session.exec(select(Task)).all()
    return {"tasks": tasks}  # Leaks all users' tasks!

# ✅ CORRECT - Always filter by user_id
@mcp.tool()
def list_tasks_tool(user_id: str) -> dict:
    tasks = session.exec(
        select(Task).where(Task.user_id == user_id)
    ).all()
    return {"tasks": tasks}
```

### Pattern 2: Path Parameter Validation

```python
# ❌ WRONG - Trust path parameter
@app.get("/api/{user_id}/tasks")
async def get_tasks(user_id: str):
    # Anyone can access any user's tasks!
    return query_tasks(user_id)

# ✅ CORRECT - Validate against JWT
@app.get("/api/{user_id}/tasks")
async def get_tasks(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    return query_tasks(user_id)
```

### Pattern 3: Agent Instructions with User Context

```python
# ❌ WRONG - Generic instructions
agent = Agent(
    instructions="You help users manage tasks.",
    mcp_servers=[mcp_server]
)

# ✅ CORRECT - Include user_id in instructions
agent = Agent(
    instructions=f"""You help user {user_id} manage tasks.

    CRITICAL: ALWAYS pass user_id='{user_id}' to ALL tool calls.
    Never use a different user_id.
    """,
    mcp_servers=[mcp_server]
)
```

## Performance Optimization

### 1. MCP Server Connection Reuse

**Problem:** Creating new MCP connection per request is slow (100-200ms overhead).

**Solution:** Singleton pattern (shown in Step 3 above).

**Performance gain:** 10x faster response times.

### 2. Database Connection Pooling

```python
# MCP Server - backend/tools/server.py
from sqlmodel import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Maintain 5 connections
    max_overflow=10,      # Allow 10 more when needed
    pool_pre_ping=True    # Verify connections before use
)
```

### 3. Frontend API Response Caching

```typescript
// Use SWR or React Query for caching
import useSWR from 'swr';

export function useTasks(userId: string) {
  const { data, error } = useSWR(
    `/api/${userId}/tasks`,
    (url) => apiRequest(url),
    { refreshInterval: 30000 }  // Refresh every 30s
  );

  return { tasks: data, isLoading: !error && !data, error };
}
```

## Common Pitfalls

### 1. Forgetting to Start All Three Servers

**Symptom:** "Connection refused" errors

**Solution:** Check all three services are running:
```bash
# Check ports
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :8001  # MCP Server
```

### 2. User ID Mismatch

**Symptom:** User can't see their data

**Solution:** Ensure user_id flows consistently:
```bash
# Check JWT payload
echo "<jwt_token>" | cut -d'.' -f2 | base64 -d | jq

# Verify user_id in database
psql -d myapp -c "SELECT id, email FROM \"user\";"
```

### 3. CORS Issues

**Symptom:** Frontend can't call backend

**Solution:** Verify CORS settings match frontend URL:
```python
allow_origins=["http://localhost:3000"]  # Must match exactly
```

### 4. Missing Environment Variables

**Symptom:** Auth fails or MCP connection errors

**Solution:** Verify all required env vars:
```bash
# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend
MCP_SERVER_URL=http://localhost:8001/mcp
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
```

## Critical: MCP Deployment Decision

### HTTP Deadlock Problem

**Issue:** Mounting MCP on FastAPI (`app.mount("/mcp", mcp.asgi_app)`) causes HTTP deadlock in production.

**Why:** Backend makes HTTP call to itself → both processes wait forever.

**Solution:** Run MCP as **separate standalone service**.

```yaml
# render.yaml - 2 services
services:
  - name: backend
    startCommand: "uvicorn main:app --host 0.0.0.0 --port 8000"
    envVars:
      - key: MCP_SERVER_URL
        value: https://mcp-server.onrender.com  # External URL!

  - name: mcp-server
    startCommand: "python tools/mcp_standalone.py"  # Separate process
    envVars:
      - key: PORT
        value: 8001
```

**Critical Environment Variables:**
- Frontend: `NEXT_PUBLIC_API_URL` → Backend URL
- Backend: `MCP_SERVER_URL` → MCP Server URL (must be external!)
- MCP: `RENDER_EXTERNAL_HOSTNAME` → Auto-set by platform

See `reference.md` for complete deployment guide, troubleshooting, and multi-service patterns.

## Production Deployment

### Option 1: Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  mcp-server:
    build:
      context: ./backend
      dockerfile: Dockerfile.mcp
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
    ports:
      - "8001:8001"
    depends_on:
      - postgres

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
      MCP_SERVER_URL: http://mcp-server:8001/mcp
      BETTER_AUTH_JWKS_URL: http://frontend:3000/api/auth/jwks
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - mcp-server

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
      BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET}
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Option 2: Separate Deployments

- **Frontend**: Vercel/Netlify
- **Backend**: Railway/Render/Fly.io
- **MCP Server**: Railway/Render/Fly.io (separate service)
- **Database**: Neon/Supabase/Railway

**Key:** Update URLs in environment variables for production domains.

## Testing Strategy

### Unit Tests (Each Tier)

```python
# Test MCP tools in isolation
def test_add_task_tool(session):
    result = add_task_tool(user_id="test", title="Test", _session=session)
    assert result["status"] == "success"

# Test Backend endpoint
async def test_chat_endpoint(client):
    response = await client.post(
        "/api/chat",
        json={"message": "Add task"},
        headers={"Authorization": "Bearer <test_jwt>"}
    )
    assert response.status_code == 200
```

### Integration Tests (Full Flow)

```typescript
// Test complete flow from frontend
test('user can create task via chat', async () => {
  // 1. Sign in
  await signIn({ email: 'test@example.com', password: 'password' });

  // 2. Send chat message
  const response = await api.chat('Create a task to test');

  // 3. Verify task exists
  const tasks = await api.get('/api/test-user/tasks');
  expect(tasks).toContainEqual(expect.objectContaining({
    title: expect.stringContaining('test')
  }));
});
```

## Next Steps

1. See `examples.md` for complete working implementations
2. Check `templates.md` for copy-paste ready code
3. Review related skills:
   - `better-auth-next-app-router` - Frontend auth setup
   - `fastapi-jwt-auth-setup` - Backend JWT validation
   - `fastmcp-database-tools` - MCP server implementation
   - `openai-chatkit-integration` - ChatKit UI integration

## Key Takeaways

✅ **User isolation at every tier** - Never trust client input
✅ **JWT flows from frontend to backend** - JWKS validation
✅ **user_id flows from backend to MCP** - Tool parameter
✅ **Three separate services** - Independent scaling
✅ **Connection reuse** - Singleton pattern for performance
✅ **Environment configuration** - Different per tier
✅ **Complete separation of concerns** - Clear boundaries
