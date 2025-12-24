---
name: nextjs-fastapi-mcp-architecture-templates
description: Ready-to-use code templates for Next.js + FastAPI + MCP architecture including all three tiers, deployment configs, and common patterns.
---

# Next.js + FastAPI + MCP Architecture - Templates

## Template 1: MCP Server Template

```python
# backend/tools/server.py
import os
import sys
from pathlib import Path

# Add parent directory for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server import FastMCP
from sqlmodel import Session, select, create_engine
from models import [YourModel]

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)

# MCP Server
mcp = FastMCP("[YourServerName]", stateless_http=True, json_response=True)


@mcp.tool()
def [your_tool](user_id: str, param: str) -> dict:
    """Tool description for the AI.

    Args:
        user_id: User ID from authentication
        param: Parameter description

    Returns:
        Operation result
    """
    # Validate inputs
    if not param:
        return {"status": "error", "error": "Parameter required"}

    try:
        with Session(engine) as session:
            # Your database operation (ALWAYS filter by user_id)
            result = session.exec(
                select([YourModel]).where([YourModel].user_id == user_id)
            ).all()

            return {
                "status": "success",
                "data": {/* your data */}
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print("🚀 Starting MCP Server on http://localhost:8001/mcp")
    mcp.run(transport="streamable-http")
```

## Template 2: FastAPI Backend Template

```python
# backend/main.py
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional
from agents import Agent
from mcp.client import MCPServerStreamableHttp

app = FastAPI(title="[Your App] API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton MCP server
_mcp_server: Optional[MCPServerStreamableHttp] = None

async def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="[Your] MCP Server",
            params={"url": os.getenv("MCP_SERVER_URL"), "timeout": 30},
            cache_tools_list=True,
        )
    return _mcp_server


# Auth dependency
async def get_current_user(request: Request) -> str:
    from middleware import verify_token

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth")

    token = auth_header[7:]
    user_id = verify_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id


# Endpoints
@app.post("/api/[endpoint]")
async def [endpoint](
    request: Request,
    current_user: str = Depends(get_current_user)
):
    body = await request.json()

    # Create agent with user context
    mcp_server = await get_mcp_server()
    agent = Agent(
        instructions=f"You help user {current_user}. ALWAYS pass user_id='{current_user}' to tools.",
        mcp_servers=[mcp_server],
        model="gpt-4o",
    )

    async with mcp_server:
        result = await agent.run(body["message"])
        return {"response": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Template 3: Frontend API Client

```typescript
// lib/api.ts
import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(public message: string, public status: number, public data?: any) {
    super(message);
  }
}

async function getToken(): Promise<string> {
  const { data, error } = await authClient.token();
  if (error || !data?.token) throw new APIError("Not authenticated", 401);
  return data.token;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new APIError(data.detail || "Request failed", response.status, data);
  }

  return data;
}

// Export convenience methods
export const api = {
  get: <T>(url: string) => apiRequest<T>(url),
  post: <T>(url: string, body: any) =>
    apiRequest<T>(url, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(url: string, body: any) =>
    apiRequest<T>(url, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(url: string) => apiRequest<T>(url, { method: "DELETE" }),
};
```

## Template 4: Environment Variables

### Frontend (.env.local)

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth
BETTER_AUTH_SECRET=<generate with: openssl rand -base64 32>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# MCP
MCP_SERVER_URL=http://localhost:8001/mcp

# Auth
BETTER_AUTH_SECRET=<same as frontend>
BETTER_AUTH_ISSUER=http://localhost:3000
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks

# OpenAI
OPENAI_API_KEY=sk-proj-xxx
OPENAI_MODEL=gpt-4o

# CORS
FRONTEND_URL=http://localhost:3000
```

## Template 5: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
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
    networks:
      - app-network

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
    networks:
      - app-network

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/myapp
      MCP_SERVER_URL: http://mcp-server:8001/mcp
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - mcp-server
    networks:
      - app-network

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
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## Template 6: Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Template 7: MCP Server Dockerfile

```dockerfile
# backend/Dockerfile.mcp
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run MCP server
WORKDIR /app/tools
CMD ["python", "server.py"]
```

## Template 8: Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]
```

## Template 9: JWT Validation Middleware

```python
# backend/middleware.py
import os
import httpx
from jose import jwt, JWTError

JWKS_URL = os.getenv("BETTER_AUTH_JWKS_URL", "http://localhost:3000/api/auth/jwks")

# Cache JWKS keys
_jwks_cache = None


async def get_jwks():
    """Fetch JWKS keys (cached)."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            _jwks_cache = response.json()
    return _jwks_cache


def verify_token(token: str) -> str | None:
    """Validate JWT and return user_id.

    Args:
        token: JWT token string

    Returns:
        user_id if valid, None otherwise
    """
    try:
        # Get JWKS
        import asyncio
        jwks = asyncio.run(get_jwks())

        # Decode and verify JWT
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["EdDSA"],  # Better Auth uses EdDSA
        )

        # Extract user_id from 'sub' claim
        return payload.get("sub")

    except JWTError:
        return None
```

## Template 10: Development Start Script

```bash
#!/bin/bash
# start-dev.sh

echo "🚀 Starting development servers..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Start database
echo -e "${BLUE}Starting PostgreSQL...${NC}"
docker-compose up -d postgres
sleep 2

# Start MCP Server
echo -e "${BLUE}Starting MCP Server (Port 8001)...${NC}"
cd backend/tools
python server.py &
MCP_PID=$!
cd ../..

# Start Backend
echo -e "${BLUE}Starting Backend (Port 8000)...${NC}"
cd backend
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start Frontend
echo -e "${BLUE}Starting Frontend (Port 3000)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✅ All servers started!${NC}"
echo "   Frontend:   http://localhost:3000"
echo "   Backend:    http://localhost:8000"
echo "   MCP Server: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop all servers"

# Cleanup on exit
trap "echo 'Stopping...'; kill $MCP_PID $BACKEND_PID $FRONTEND_PID; docker-compose down; exit" INT
wait
```

## Template 11: SQLModel Model with User Isolation

```python
# backend/models.py
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional


class [YourModel](SQLModel, table=True):
    """[Description]"""

    __tablename__ = "[table_name]"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # User isolation (REQUIRED for multi-tenant)
    user_id: str = Field(max_length=255, index=True, nullable=False)

    # Your fields
    field1: str = Field(max_length=200)
    field2: Optional[str] = Field(default=None, max_length=1000)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

## Template 12: Protected Frontend Page

```tsx
// app/(dashboard)/[page]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-client";
import { api, APIError } from "@/lib/api";

export default function [Page]() {
  const { user, isLoading } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user]);

  const fetchData = async () => {
    try {
      const result = await api.get(`/api/${user!.id}/[endpoint]`);
      setData(result);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      }
    }
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">[Page Title]</h1>
      {/* Your content */}
    </div>
  );
}
```

## Template 13: Agent with MCP Tools

```python
# backend/services/agent.py
from agents import Agent
from mcp.client import MCPServerStreamableHttp
import os

_mcp_server = None


async def get_mcp_server():
    """Get singleton MCP server."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="[Your] MCP Server",
            params={"url": os.getenv("MCP_SERVER_URL"), "timeout": 30},
            cache_tools_list=True,
            max_retry_attempts=3,
        )
    return _mcp_server


async def create_agent(user_id: str):
    """Create agent with MCP tools.

    Args:
        user_id: Current user ID

    Returns:
        Tuple of (agent, mcp_server)
    """
    server = await get_mcp_server()

    agent = Agent(
        name="[Your]Assistant",
        instructions=f"""You are a helpful assistant for user {user_id}.

        CRITICAL - User Context:
        - ALWAYS pass user_id='{user_id}' to ALL tool calls
        - Never use a different user_id
        - Users can only access their own data

        Available Tools:
        - [list your tools]

        Response Style:
        - Be concise and friendly
        - Confirm actions clearly
        """,
        mcp_servers=[server],
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )

    return agent, server
```

## Template 14: Health Check Endpoints

```python
# Add to backend/main.py
@app.get("/health")
async def health_check():
    """Backend health check."""
    return {"status": "healthy", "service": "backend"}


# Add to backend/tools/server.py
@mcp.tool()
def health_check_tool() -> dict:
    """MCP server health check."""
    return {"status": "healthy", "service": "mcp-server"}
```

## Template 15: Database Migration Script

```python
# backend/migrations/create_tables.py
from sqlmodel import create_engine, SQLModel
import os

# Import all models
from models import [YourModel1], [YourModel2]

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def create_tables():
    """Create all database tables."""
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tables created successfully!")


if __name__ == "__main__":
    create_tables()
```

Run it:
```bash
python migrations/create_tables.py
```

## Template 16: Testing Template

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_[endpoint]():
    """Test [description]."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get auth token (mocked)
        token = "test_jwt_token"

        # Make request
        response = await client.post(
            "/api/[endpoint]",
            json={[params]},
            headers={"Authorization": f"Bearer {token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert [condition]
```

## Quick Copy-Paste Snippets

### Start All Services

```bash
# Terminal 1: Database
docker-compose up postgres

# Terminal 2: MCP Server
cd backend/tools && python server.py

# Terminal 3: Backend
cd backend && uvicorn main:app --reload

# Terminal 4: Frontend
cd frontend && npm run dev
```

### Check All Ports

```bash
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :8001  # MCP Server
lsof -i :5432  # PostgreSQL
```

### Generate Auth Secret

```bash
openssl rand -base64 32
```

### User Isolation Pattern

```python
# ALWAYS filter by user_id in database queries
statement = select(Model).where(Model.user_id == user_id)

# ALWAYS pass user_id to MCP tools
@mcp.tool()
def tool(user_id: str, ...):
    # Filter by user_id
    pass

# ALWAYS include user_id in agent instructions
agent = Agent(instructions=f"ALWAYS use user_id='{user_id}'")
```

### JWT Flow

```
Frontend → authClient.token() → JWT
  ↓
Backend → verify_token(jwt) → user_id
  ↓
Agent → instructions with user_id
  ↓
MCP Tool → filter by user_id
```
