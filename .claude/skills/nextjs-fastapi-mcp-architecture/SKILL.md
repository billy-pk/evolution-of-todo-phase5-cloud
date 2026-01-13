---
name: nextjs-fastapi-mcp-architecture
description: Build production-ready AI applications with Next.js frontend, FastAPI backend, and MCP tools. Includes JWT authentication flow, user isolation, and multi-server deployment patterns. Supports Kubernetes deployment with Helm charts, Minikube local development, and multi-service microservices architecture.
---

# Next.js + FastAPI + MCP Architecture

## Overview

Three-tier architecture for AI-powered applications:
- **Frontend**: Next.js 15 App Router + Better Auth
- **Backend**: FastAPI + JWT validation
- **MCP Server**: FastMCP + PostgreSQL tools

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Next.js        │───▶│  FastAPI        │───▶│  MCP Server     │
│  Port 3000      │JWT │  Port 8000      │HTTP│  Port 8001      │
│  Better Auth    │    │  Agent + JWT    │    │  Database Tools │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                              ┌─────────────────┐
                                              │  PostgreSQL     │
                                              └─────────────────┘
```

## User Context Flow

```
1. User signs in → JWT with user_id
2. Frontend sends JWT in Authorization header
3. Backend validates JWT (JWKS)
4. Backend extracts user_id, passes to Agent
5. Agent calls MCP tools with user_id parameter
6. MCP tools filter queries by user_id
```

**Key Principle**: Every operation is scoped to user_id at every tier.

---

## Quick Start

### 1. MCP Server

```python
# backend/tools/server.py
from mcp.server import FastMCP
from sqlmodel import Session, select, create_engine
from models import Task

engine = create_engine(os.getenv("DATABASE_URL"))
mcp = FastMCP("TaskMCP", stateless_http=True, json_response=True)

@mcp.tool()
def add_task_tool(user_id: str, title: str) -> dict:
    with Session(engine) as session:
        task = Task(user_id=user_id, title=title)  # Always scope to user
        session.add(task)
        session.commit()
        return {"status": "success", "task_id": str(task.id)}

@mcp.tool()
def list_tasks_tool(user_id: str) -> dict:
    with Session(engine) as session:
        tasks = session.exec(select(Task).where(Task.user_id == user_id)).all()
        return {"tasks": [{"id": str(t.id), "title": t.title} for t in tasks]}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # Port 8001
```

### 2. FastAPI Backend

```python
# backend/main.py
from fastapi import FastAPI, Request, Depends, HTTPException
from middleware import verify_token
from agents import Agent
from mcp.client import MCPServerStreamableHttp

app = FastAPI()

async def get_current_user(request: Request) -> str:
    token = request.headers.get("Authorization", "")[7:]
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    return user_id

@app.post("/api/chat")
async def chat(request: Request, user_id: str = Depends(get_current_user)):
    body = await request.json()
    mcp = MCPServerStreamableHttp(params={"url": "http://localhost:8001/mcp"})

    agent = Agent(
        instructions=f"Help user {user_id}. Always use user_id='{user_id}' in tools.",
        mcp_servers=[mcp]
    )

    async with mcp:
        return {"response": await agent.run(body["message"])}
```

### 3. Frontend API Client

```typescript
// lib/api.ts
import { authClient } from "./auth-client";

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const { data } = await authClient.token();
  if (!data?.token) throw new Error("Not authenticated");

  return fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${data.token}`,
      "Content-Type": "application/json",
    },
  }).then(r => r.json());
}
```

**For complete implementation, see [reference.md](reference.md).**

---

## Kubernetes Deployment

For deploying to Kubernetes (Minikube, EKS, GKE), see **[kubernetes.md](kubernetes.md)**.

### Quick Deploy to Minikube

```bash
# Create secrets
kubectl create secret generic postgres-credentials --from-literal=database-url="..."
kubectl create secret generic better-auth-secret --from-literal=better-auth-secret="..."
kubectl create secret generic openai-credentials --from-literal=openai-api-key="..."

# Build images
eval $(minikube docker-env)
docker build -t frontend:latest ./frontend
docker build -t backend-api:latest ./backend

# Deploy with Helm
helm upgrade --install frontend ./infrastructure/helm/frontend -f values-local.yaml
helm upgrade --install backend-api ./infrastructure/helm/backend-api -f values-local.yaml

# Access
kubectl port-forward svc/frontend 3000:3000 &
kubectl port-forward svc/backend-api 8000:8000 &
open http://localhost:3000
```

### Helm Values (Backend)

```yaml
env:
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"
  - name: BETTER_AUTH_JWKS_URL
    value: "http://frontend:3000/api/auth/jwks"
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url
```

---

## Security Patterns

### User Isolation at Every Tier

```python
# ❌ WRONG - No user filtering
@mcp.tool()
def list_tasks_tool() -> dict:
    return session.exec(select(Task)).all()  # Leaks all data!

# ✅ CORRECT - Always filter by user_id
@mcp.tool()
def list_tasks_tool(user_id: str) -> dict:
    return session.exec(select(Task).where(Task.user_id == user_id)).all()
```

### Path Parameter Validation

```python
# ❌ WRONG - Trust path parameter
@app.get("/api/{user_id}/tasks")
async def get_tasks(user_id: str):
    return query_tasks(user_id)

# ✅ CORRECT - Validate against JWT
@app.get("/api/{user_id}/tasks")
async def get_tasks(user_id: str, current_user: str = Depends(get_current_user)):
    if user_id != current_user:
        raise HTTPException(403, "Forbidden")
    return query_tasks(user_id)
```

### Agent Instructions with User Context

```python
agent = Agent(
    instructions=f"""Help user {user_id} manage tasks.
    CRITICAL: ALWAYS pass user_id='{user_id}' to ALL tool calls.""",
    mcp_servers=[mcp_server]
)
```

---

## Environment Variables

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=<32+ char secret>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://...
```

### Backend (.env)
```env
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=<same as frontend>
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
MCP_SERVER_URL=http://localhost:8001/mcp
OPENAI_API_KEY=sk-...
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Connection refused | Service not running | Check all 3 services are up |
| 401 Unauthorized | JWT invalid | Verify JWKS URL accessible |
| User can't see data | user_id mismatch | Check JWT payload, DB records |
| CORS errors | Origin not allowed | Add frontend URL to allow_origins |
| MCP timeout | Deadlock (mounted mode) | Run MCP as separate service |

### MCP Deployment Decision

**Problem:** Mounting MCP on FastAPI (`app.mount("/mcp", mcp)`) causes HTTP deadlock.

**Solution:** Run MCP as separate service OR use MOUNT_MCP_SERVER=true carefully.

---

## Development Workflow

### Start All Services

```bash
# Terminal 1: MCP Server
cd backend/tools && python server.py

# Terminal 2: Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Kubernetes

```bash
# Deploy
./infrastructure/deploy-local.sh

# Access
kubectl port-forward svc/frontend 3000:3000 &
kubectl port-forward svc/backend-api 8000:8000 &

# Logs
kubectl logs -l app.kubernetes.io/name=frontend
kubectl logs -l app.kubernetes.io/name=backend-api

# Restart
kubectl rollout restart deployment frontend backend-api
```

---

## Reference Files

| File | Content |
|------|---------|
| [reference.md](reference.md) | Complete implementation, deployment guides |
| [kubernetes.md](kubernetes.md) | Helm charts, Minikube, secrets, troubleshooting |
| [examples.md](examples.md) | Working code examples |
| [templates.md](templates.md) | Copy-paste ready code |

---

## Key Takeaways

- ✅ User isolation at every tier
- ✅ JWT flows frontend → backend (JWKS validation)
- ✅ user_id flows backend → MCP (tool parameter)
- ✅ Three separate services (independent scaling)
- ✅ Connection reuse (singleton pattern)
- ✅ Kubernetes-ready with Helm charts

## Related Skills

- **better-auth-next-app-router** - Frontend auth
- **fastapi-jwt-auth-setup** - Backend JWT
- **fastmcp-database-tools** - MCP implementation
- **openai-chatkit-integration** - ChatKit UI
