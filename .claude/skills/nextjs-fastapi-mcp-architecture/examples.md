---
name: nextjs-fastapi-mcp-architecture-examples
description: Complete working examples of Next.js + FastAPI + MCP architecture with full request flows, deployment configurations, and real-world patterns from production applications.
---

# Next.js + FastAPI + MCP Architecture - Complete Examples

## Example 1: Complete Working Application

This example shows all three tiers working together for a task management app.

### Project Structure

```
project/
├── frontend/                 # Next.js (Port 3000)
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── signin/page.tsx
│   │   │   └── signup/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── tasks/page.tsx
│   │   │   └── chat/page.tsx
│   │   └── api/auth/[...all]/route.ts
│   ├── lib/
│   │   ├── auth.ts
│   │   ├── auth-client.ts
│   │   └── api.ts
│   └── middleware.ts
│
├── backend/                  # FastAPI (Port 8000)
│   ├── main.py
│   ├── models.py
│   ├── middleware.py
│   ├── routes/
│   │   ├── tasks.py
│   │   └── chat.py
│   ├── services/
│   │   └── agent.py
│   └── tools/
│       └── server.py         # MCP Server (Port 8001)
│
└── docker-compose.yml
```

### Tier 1: MCP Server (backend/tools/server.py)

```python
"""
MCP Server - Provides task management tools to AI agents.
Port: 8001
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server import FastMCP
from sqlmodel import Session, select, create_engine
from models import Task
from uuid import UUID
from datetime import datetime, UTC

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Initialize MCP server
mcp = FastMCP(
    "TaskMCPServer",
    stateless_http=True,
    json_response=True
)


@mcp.tool()
def add_task_tool(user_id: str, title: str, description: str = None) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID from authentication
        title: Task title (1-200 characters)
        description: Optional description

    Returns:
        Task creation result
    """
    # Validate inputs
    if not title or len(title.strip()) == 0:
        return {"status": "error", "error": "Title required"}

    if len(title) > 200:
        return {"status": "error", "error": "Title too long"}

    try:
        with Session(engine) as session:
            # Create task scoped to user
            task = Task(
                user_id=user_id,
                title=title.strip(),
                description=description
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed
                }
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def list_tasks_tool(user_id: str, status: str = "all") -> dict:
    """List tasks for a user.

    Args:
        user_id: User ID from authentication
        status: Filter by status (all, pending, completed)

    Returns:
        List of tasks
    """
    if status not in ["all", "pending", "completed"]:
        return {"status": "error", "error": "Invalid status"}

    try:
        with Session(engine) as session:
            # Query scoped to user
            statement = select(Task).where(Task.user_id == user_id)

            if status == "pending":
                statement = statement.where(Task.completed == False)
            elif status == "completed":
                statement = statement.where(Task.completed == True)

            tasks = session.exec(statement).all()

            return {
                "status": "success",
                "data": {
                    "tasks": [
                        {
                            "task_id": str(t.id),
                            "title": t.title,
                            "description": t.description,
                            "completed": t.completed,
                            "created_at": t.created_at.isoformat()
                        }
                        for t in tasks
                    ]
                }
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def complete_task_tool(user_id: str, task_id: str) -> dict:
    """Mark a task as completed.

    Args:
        user_id: User ID from authentication
        task_id: Task ID (UUID)

    Returns:
        Updated task
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return {"status": "error", "error": "Invalid task ID"}

    try:
        with Session(engine) as session:
            task = session.get(Task, task_uuid)

            if not task:
                return {"status": "error", "error": "Task not found"}

            # Verify ownership
            if task.user_id != user_id:
                return {"status": "error", "error": "Unauthorized"}

            task.completed = True
            task.updated_at = datetime.now(UTC)
            session.add(task)
            session.commit()

            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "completed": task.completed
                }
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print("🚀 Starting MCP Server on http://localhost:8001/mcp")
    mcp.run(transport="streamable-http")
```

### Tier 2: FastAPI Backend (backend/main.py)

```python
"""
FastAPI Backend - Handles authentication, REST API, and AI agent coordination.
Port: 8000
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from typing import Optional
from agents import Agent
from mcp.client import MCPServerStreamableHttp

app = FastAPI(title="Task Manager API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT validation (using JWKS from Better Auth)
from middleware import verify_token


# Singleton MCP server connection (reused across requests)
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
            cache_tools_list=True,  # Cache tool definitions
            max_retry_attempts=3,
        )
    return _mcp_server


# Dependency: Extract user from JWT
async def get_current_user(request: Request) -> str:
    """Extract user_id from JWT token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix
    user_id = verify_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id


# REST Endpoints
@app.get("/api/{user_id}/tasks")
async def get_tasks(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get all tasks for a user."""
    # Verify path user_id matches JWT user_id
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Query tasks directly (not via agent)
    from sqlmodel import Session, select
    from models import Task
    from db import engine

    with Session(engine) as session:
        statement = select(Task).where(Task.user_id == user_id)
        tasks = session.exec(statement).all()

        return [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ]


@app.post("/api/chat")
async def chat(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Chat with AI agent to manage tasks."""
    body = await request.json()
    message = body.get("message")

    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # Create agent with MCP tools
    mcp_server = await get_mcp_server()

    agent = Agent(
        name="TaskAssistant",
        instructions=f"""You are a helpful assistant that manages tasks for users.
        Current user ID: {current_user}

        CRITICAL - User Context:
        - ALWAYS pass user_id='{current_user}' to ALL tool calls
        - Never use a different user_id
        - Users can only access their own tasks

        Available Tools:
        - add_task_tool: Create new tasks
        - list_tasks_tool: List all tasks (filter by status)
        - complete_task_tool: Mark task as completed

        Response Style:
        - Be concise and friendly
        - Confirm actions clearly
        """,
        mcp_servers=[mcp_server],
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )

    # Run agent with MCP server
    async with mcp_server:
        result = await agent.run(message)
        return {"response": result}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Tier 3: Next.js Frontend (frontend/lib/api.ts)

```typescript
/**
 * API Client - Handles all backend communication with automatic JWT injection.
 */

import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function getAuthToken(): Promise<string> {
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new APIError("Not authenticated", 401);
  }

  return data.token;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    // Get JWT token from Better Auth
    const token = await getAuthToken();

    // Make request with JWT
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    // Parse response
    const data = await response.json();

    // Handle errors
    if (!response.ok) {
      throw new APIError(
        data.detail || data.message || "Request failed",
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error instanceof Error ? error.message : "Unknown error",
      500
    );
  }
}

// Convenience methods
export const api = {
  // Task management
  getTasks: (userId: string) =>
    apiRequest<Task[]>(`/api/${userId}/tasks`),

  // AI chat
  chat: (message: string) =>
    apiRequest<{ response: string }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};

// Types
export interface Task {
  id: string;
  title: string;
  description: string | null;
  completed: boolean;
  created_at: string;
}
```

### Frontend: Tasks Page (frontend/app/(dashboard)/tasks/page.tsx)

```tsx
/**
 * Tasks Page - Shows user's tasks with ability to create new ones.
 */

"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-client";
import { api, APIError, Task } from "@/lib/api";

export default function TasksPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch tasks on mount
  useEffect(() => {
    if (user) {
      fetchTasks();
    }
  }, [user]);

  const fetchTasks = async () => {
    if (!user) return;

    try {
      setLoading(true);
      setError(null);
      const data = await api.getTasks(user.id);
      setTasks(data);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError("Failed to load tasks");
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading tasks...</div>;
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg bg-red-50 p-4 text-red-800">
          <p className="font-semibold">Error loading tasks</p>
          <p className="text-sm">{error}</p>
          <button
            onClick={fetchTasks}
            className="mt-2 text-sm underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">My Tasks</h1>

      {/* Task List */}
      {tasks.length === 0 ? (
        <p className="text-gray-500">
          No tasks yet. Go to the Chat page to create some!
        </p>
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => (
            <li
              key={task.id}
              className="flex items-center gap-3 rounded-lg border bg-white p-4"
            >
              <input
                type="checkbox"
                checked={task.completed}
                readOnly
                className="h-5 w-5"
              />
              <div className="flex-1">
                <p
                  className={
                    task.completed ? "line-through text-gray-500" : ""
                  }
                >
                  {task.title}
                </p>
                {task.description && (
                  <p className="text-sm text-gray-600">{task.description}</p>
                )}
              </div>
              <span className="text-xs text-gray-400">
                {new Date(task.created_at).toLocaleDateString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Frontend: Chat Page (frontend/app/(dashboard)/chat/page.tsx)

```tsx
/**
 * Chat Page - AI chat interface for managing tasks.
 */

"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-client";
import { api, APIError } from "@/lib/api";

export default function ChatPage() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!message.trim()) return;

    const userMessage = message;
    setMessage("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    try {
      setLoading(true);
      const { response } = await api.chat(userMessage);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    } catch (err) {
      if (err instanceof APIError) {
        setMessages((prev) => [
          ...prev,
          { role: "error", content: err.message },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-xs rounded-lg px-4 py-2 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.role === "error"
                  ? "bg-red-50 text-red-800"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask me to manage your tasks..."
            className="flex-1 rounded-md border px-3 py-2"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
```

## Example 2: Complete Request Flow (Step-by-Step)

Let's trace a complete request: User asks "Create a task to buy groceries"

### Step 1: Frontend Sends Request

```typescript
// User types message and clicks Send
const { response } = await api.chat("Create a task to buy groceries");

// api.chat internally does:
const token = await authClient.token(); // Get JWT from Better Auth

fetch("http://localhost:8000/api/chat", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,  // JWT attached
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message: "Create a task to buy groceries" })
});
```

**JWT Payload:**
```json
{
  "sub": "user_abc123",           // user_id
  "email": "john@example.com",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### Step 2: Backend Validates JWT

```python
# FastAPI receives request
@app.post("/api/chat")
async def chat(request: Request, current_user: str = Depends(get_current_user)):
    # ...

# get_current_user dependency validates JWT
async def get_current_user(request: Request) -> str:
    token = request.headers["Authorization"][7:]  # Remove "Bearer "

    # Validate JWT using JWKS from Better Auth
    user_id = verify_token(token)  # Returns "user_abc123"

    return user_id  # "user_abc123"
```

### Step 3: Backend Creates Agent

```python
# Backend creates agent with user context
agent = Agent(
    instructions=f"""You help user user_abc123 manage tasks.
    ALWAYS pass user_id='user_abc123' to ALL tool calls.
    """,
    mcp_servers=[mcp_server],
    model="gpt-4o",
)

# Run agent
result = await agent.run("Create a task to buy groceries")
```

### Step 4: Agent Calls MCP Tool

```python
# Agent internally calls:
mcp_server.call_tool(
    tool_name="add_task_tool",
    arguments={
        "user_id": "user_abc123",  # From agent instructions
        "title": "Buy groceries",
        "description": None
    }
)
```

**HTTP Request to MCP Server:**
```http
POST http://localhost:8001/mcp
Content-Type: application/json

{
  "tool": "add_task_tool",
  "arguments": {
    "user_id": "user_abc123",
    "title": "Buy groceries"
  }
}
```

### Step 5: MCP Server Executes Tool

```python
@mcp.tool()
def add_task_tool(user_id: str, title: str, description: str = None) -> dict:
    with Session(engine) as session:
        # Create task in database
        task = Task(
            user_id="user_abc123",  # From parameter
            title="Buy groceries",
            description=None
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "status": "success",
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Buy groceries",
                "completed": False
            }
        }
```

**SQL Executed:**
```sql
INSERT INTO tasks (id, user_id, title, description, completed, created_at)
VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  'user_abc123',
  'Buy groceries',
  NULL,
  FALSE,
  '2025-01-15 10:30:00'
);
```

### Step 6: Response Flows Back

```
MCP Server → Agent → Backend → Frontend

MCP: {"status": "success", "data": {"task_id": "...", "title": "Buy groceries"}}
  ↓
Agent: "I've created the task 'Buy groceries' for you."
  ↓
Backend: {"response": "I've created the task 'Buy groceries' for you."}
  ↓
Frontend: Displays message in chat UI
```

## Example 3: Production Deployment with Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  # MCP Server (Tier 3)
  mcp-server:
    build:
      context: ./backend
      dockerfile: Dockerfile.mcp
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # FastAPI Backend (Tier 2)
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
      MCP_SERVER_URL: http://mcp-server:8001/mcp
      BETTER_AUTH_JWKS_URL: http://frontend:3000/api/auth/jwks
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      FRONTEND_URL: http://localhost:3000
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      mcp-server:
        condition: service_started
    restart: unless-stopped
    networks:
      - app-network

  # Next.js Frontend (Tier 1)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
      BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET}
      BETTER_AUTH_URL: http://localhost:3000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### Environment File (.env)

```env
# Database
DB_USER=myapp_user
DB_PASSWORD=secure_password_here

# OpenAI
OPENAI_API_KEY=sk-proj-xxx

# Better Auth
BETTER_AUTH_SECRET=<32+ character secret>

# Optional: Production URLs
# FRONTEND_URL=https://app.example.com
# BACKEND_URL=https://api.example.com
# MCP_URL=https://mcp.example.com
```

### Start Everything

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
docker-compose ps

# Stop everything
docker-compose down
```

## Example 4: Development Scripts

### start-dev.sh

```bash
#!/bin/bash
# Start all development servers

echo "🚀 Starting development environment..."

# Start PostgreSQL (if using Docker)
echo "📦 Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for database
echo "⏳ Waiting for database..."
sleep 3

# Start MCP Server
echo "🔧 Starting MCP Server (Port 8001)..."
cd backend/tools
python server.py &
MCP_PID=$!

# Start Backend
echo "🔧 Starting Backend (Port 8000)..."
cd ../..
cd backend
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "🔧 Starting Frontend (Port 3000)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Development environment started!"
echo "   Frontend:    http://localhost:3000"
echo "   Backend:     http://localhost:8000"
echo "   MCP Server:  http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap "echo '\n🛑 Stopping servers...'; kill $MCP_PID $BACKEND_PID $FRONTEND_PID; docker-compose down; exit 0" INT
wait
```

Make it executable:
```bash
chmod +x start-dev.sh
./start-dev.sh
```

## Example 5: Testing the Complete Flow

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_complete_flow():
    """Test complete flow from auth to task creation."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Sign up user (via Better Auth)
        signup_response = await client.post(
            "/api/auth/sign-up/email",
            json={
                "email": "test@example.com",
                "password": "password123",
                "name": "Test User"
            }
        )
        assert signup_response.status_code == 200

        # 2. Get JWT token
        token_response = await client.get("/api/auth/session")
        token = token_response.cookies.get("better-auth.session_token")

        # 3. Create task via chat
        chat_response = await client.post(
            "/api/chat",
            json={"message": "Create a task to test integration"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert chat_response.status_code == 200
        assert "task" in chat_response.json()["response"].lower()

        # 4. Verify task exists
        tasks_response = await client.get(
            "/api/test-user/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        assert len(tasks) == 1
        assert "test" in tasks[0]["title"].lower()
```

Run tests:
```bash
pytest tests/test_integration.py -v
```
