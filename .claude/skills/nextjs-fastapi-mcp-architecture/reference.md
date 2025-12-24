---
name: nextjs-fastapi-mcp-architecture-reference
description: Technical reference for multi-service deployment, HTTP deadlock troubleshooting, environment variable coordination, and production patterns for Next.js + FastAPI + MCP architecture.
---

# Next.js + FastAPI + MCP Architecture - Technical Reference

## HTTP Deadlock Deep Dive

### Understanding the Deadlock

**Scenario:** You mount MCP server on FastAPI and call it via HTTP from the same process.

```python
# backend/main.py
from fastapi import FastAPI
from tools.server import mcp

app = FastAPI()

# Mount MCP at /mcp endpoint
app.mount("/mcp", mcp.asgi_app)

# Create MCP client pointing to localhost
mcp_client = MCPServerStreamableHttp(
    name="MCP",
    params={"url": "http://localhost:8000/mcp"}  # Same process!
)
```

**What happens when a request arrives:**

```
1. User sends chat message to POST /api/chat
   ↓
2. FastAPI worker thread handles request
   ↓
3. Backend creates agent with MCP client
   ↓
4. Agent calls tool → MCP client makes HTTP request to http://localhost:8000/mcp
   ↓
5. HTTP request arrives at FastAPI
   ↓
6. FastAPI tries to route to /mcp endpoint
   ↓
7. ⚠️ PROBLEM: FastAPI worker is blocked waiting for agent to finish
   ↓
8. ⚠️ PROBLEM: Agent is blocked waiting for MCP HTTP response
   ↓
9. 🔴 DEADLOCK: Both waiting for each other indefinitely
```

**Result:** Request hangs forever, eventually times out.

**Why this happens:**
- FastAPI uses worker threads/processes
- Single worker can't handle nested HTTP requests to itself
- Even with multiple workers, connection pool exhaustion occurs under load

### Why It Works in Development

During development, you might see this work intermittently because:
- Low request volume
- Python's asyncio event loop might process requests in lucky order
- Development server (uvicorn with reload) uses single worker

**Don't be fooled:** It will fail in production under load.

### The Solution: Separate Services

Run MCP as a completely separate process with its own HTTP server:

```
Backend Process (Port 8000)         MCP Process (Port 8001)
┌─────────────────────────┐        ┌──────────────────────┐
│  FastAPI App            │        │  FastMCP Server      │
│  - REST endpoints       │  HTTP  │  - Tool endpoints    │
│  - Agent orchestration  │───────>│  - Database access   │
│  - JWT validation       │        │  - User isolation    │
└─────────────────────────┘        └──────────────────────┘
```

**Benefits:**
- No deadlock - separate HTTP servers
- Independent scaling
- Better resource isolation
- Clearer separation of concerns

## Complete Render Deployment Guide

### Step 1: Create Standalone MCP Entry Point

**File:** `backend/tools/mcp_standalone.py`

```python
#!/usr/bin/env python3
"""
Standalone MCP Server for Separate Deployment

This script runs the MCP server as a standalone service.
Use this for 2-service deployment (Backend + MCP as separate services).
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import MCP server
from tools.server import mcp

def main():
    """Run the standalone MCP server."""
    import uvicorn
    import contextlib
    from typing import AsyncIterator

    port = int(os.environ.get("PORT", 8001))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting standalone MCP server on {host}:{port}")
    logger.info(f"   MCP endpoint will be at: http://{host}:{port}/")
    logger.info(f"   Database: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")

    # Create lifespan context manager to initialize MCP session manager
    @contextlib.asynccontextmanager
    async def lifespan_wrapper(app) -> AsyncIterator[None]:
        """Initialize MCP session manager on startup."""
        logger.info("🔌 Initializing MCP session manager...")
        async with mcp.session_manager.run():
            logger.info("✅ MCP session manager initialized")
            yield
        logger.info("🔌 MCP session manager shutdown")

    # Get the streamable HTTP ASGI app from FastMCP
    mcp_app = mcp.streamable_http_app()

    # Add health check endpoint
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def health_check(request):
        """Health check endpoint for monitoring."""
        from sqlmodel import text
        from tools.server import engine

        try:
            # Test database connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return JSONResponse({
                "status": "healthy",
                "service": "mcp-standalone",
                "database": "connected"
            })
        except Exception as e:
            return JSONResponse({
                "status": "unhealthy",
                "service": "mcp-standalone",
                "database": f"error: {str(e)}"
            }, status_code=503)

    # Add health check route
    mcp_app.routes.append(Route("/health", endpoint=health_check, methods=["GET", "HEAD"]))

    # Wrap with lifespan
    mcp_app.router.lifespan_context = lifespan_wrapper

    # Run with uvicorn
    uvicorn.run(mcp_app, host=host, port=port)

if __name__ == "__main__":
    main()
```

### Step 2: Create render.yaml Blueprint

**File:** `render.yaml` (in project root)

```yaml
services:
  # FastAPI Backend
  - type: web
    name: backend
    runtime: python
    region: oregon
    plan: starter
    buildCommand: |
      cd backend
      pip install --upgrade pip
      pip install -r requirements.txt
    startCommand: "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"
    envVars:
      - key: DATABASE_URL
        sync: false  # Set manually in Render dashboard
      - key: MCP_SERVER_URL
        value: https://mcp-server.onrender.com  # Update with your MCP URL
      - key: OPENAI_API_KEY
        sync: false
      - key: BETTER_AUTH_SECRET
        sync: false
      - key: BETTER_AUTH_ISSUER
        value: https://yourapp.vercel.app  # Update with your frontend URL
      - key: BETTER_AUTH_JWKS_URL
        value: https://yourapp.vercel.app/api/auth/jwks
      - key: ENVIRONMENT
        value: production
    healthCheckPath: /health

  # MCP Server (Standalone)
  - type: web
    name: mcp-server
    runtime: python
    region: oregon
    plan: starter
    buildCommand: |
      cd backend
      pip install --upgrade pip
      pip install -r requirements.txt
    startCommand: "cd backend && python tools/mcp_standalone.py"
    envVars:
      - key: DATABASE_URL
        sync: false  # Same database as backend
      - key: PORT
        value: 8001
      - key: HOST
        value: 0.0.0.0
      - key: ENVIRONMENT
        value: production
    healthCheckPath: /health
```

### Step 3: Deploy to Render

```bash
# 1. Connect repository to Render
# - Go to render.com dashboard
# - Click "New" → "Blueprint"
# - Connect your GitHub repository
# - Render will detect render.yaml automatically

# 2. Set environment variables
# In Render dashboard for each service:
# - DATABASE_URL (from Neon or other provider)
# - OPENAI_API_KEY
# - BETTER_AUTH_SECRET (same as frontend)

# 3. Deploy
# Render will automatically deploy both services

# 4. Get service URLs
# - Backend URL: https://backend.onrender.com
# - MCP URL: https://mcp-server.onrender.com

# 5. Update environment variables with actual URLs
# Backend:
#   MCP_SERVER_URL=https://mcp-server.onrender.com
# Frontend (Vercel):
#   NEXT_PUBLIC_API_URL=https://backend.onrender.com
```

### Step 4: Update Frontend Deployment

**Vercel Environment Variables:**

```env
NEXT_PUBLIC_API_URL=https://backend.onrender.com
BETTER_AUTH_SECRET=<same-as-backend>
BETTER_AUTH_URL=https://yourapp.vercel.app
DATABASE_URL=<same-database-url>
```

## Environment Variable Coordination

### The Critical Pattern

Each service needs to know how to reach other services. URLs must match actual deployment URLs.

```
Frontend (yourapp.vercel.app)
  ├─ NEXT_PUBLIC_API_URL → Backend URL
  └─ BETTER_AUTH_URL → Frontend URL (self)

Backend (backend.onrender.com)
  ├─ MCP_SERVER_URL → MCP Server URL
  ├─ BETTER_AUTH_JWKS_URL → Frontend JWKS endpoint
  └─ DATABASE_URL → Database connection string

MCP Server (mcp-server.onrender.com)
  ├─ DATABASE_URL → Database connection string
  └─ RENDER_EXTERNAL_HOSTNAME → Auto-set by Render
```

### Common URL Mistakes

#### Mistake 1: Using localhost in Production

```yaml
# ❌ WRONG - localhost doesn't work across services
envVars:
  - key: MCP_SERVER_URL
    value: http://localhost:8001

# ✅ CORRECT - use external service URL
envVars:
  - key: MCP_SERVER_URL
    value: https://mcp-server.onrender.com
```

#### Mistake 2: Using Old Deployment URLs

**Problem:** After redeploying, hostname changed from `backend-abc123.onrender.com` to `backend.onrender.com`.

**Symptom:** Frontend can't reach backend, shows "Network error".

**Solution:** Update `NEXT_PUBLIC_API_URL` in Vercel:
```bash
# In Vercel dashboard → Settings → Environment Variables
NEXT_PUBLIC_API_URL=https://backend.onrender.com  # Updated!
```

**Important:** Redeploy frontend after changing environment variables.

#### Mistake 3: Mismatched CORS Origins

```python
# Backend CORS must include actual frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://yourapp.vercel.app",  # Production ✅
        "https://yourapp-git-main-xyz.vercel.app",  # Preview deployments
    ],
    allow_credentials=True,
)
```

### Dynamic Hostname Resolution

For platforms that change hostnames:

```python
# backend/config.py
import os

class Settings:
    # MCP Server URL - use environment variable
    MCP_SERVER_URL: str = os.getenv(
        "MCP_SERVER_URL",
        "http://localhost:8001/mcp"  # Fallback for development
    )

    # Better Auth JWKS URL
    BETTER_AUTH_JWKS_URL: str = os.getenv(
        "BETTER_AUTH_JWKS_URL",
        "http://localhost:3000/api/auth/jwks"
    )

    @property
    def mcp_server_url(self) -> str:
        """Get MCP server URL with validation."""
        url = self.MCP_SERVER_URL
        if not url:
            raise ValueError("MCP_SERVER_URL not set")
        if "localhost" in url and self.ENVIRONMENT == "production":
            raise ValueError("Cannot use localhost in production")
        return url
```

## Health Check Strategy

### Multi-Service Health Checks

Each service should verify its dependencies in health checks.

#### Backend Health Check

```python
# backend/main.py
from fastapi import FastAPI
from sqlmodel import text
import httpx

@app.get("/health")
async def health_check():
    """
    Health check endpoint that verifies:
    1. Database connectivity
    2. MCP server availability
    """
    health_status = {
        "status": "healthy",
        "service": "backend",
        "database": "disconnected",
        "mcp_server": "disconnected"
    }

    # Test database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    # Test MCP server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            mcp_health = await client.get(f"{settings.MCP_SERVER_URL}/health")
            if mcp_health.status_code == 200:
                health_status["mcp_server"] = "connected"
            else:
                health_status["mcp_server"] = f"status: {mcp_health.status_code}"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["mcp_server"] = f"error: {str(e)}"

    # Return 503 if unhealthy
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(health_status, status_code=status_code)
```

#### MCP Server Health Check

```python
# backend/tools/mcp_standalone.py (in health_check function)
async def health_check(request):
    """Health check for MCP server."""
    from sqlmodel import text
    from tools.server import engine

    health_status = {
        "status": "healthy",
        "service": "mcp-server",
        "database": "disconnected"
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(health_status, status_code=status_code)
```

#### Frontend Health Check (Optional)

```typescript
// app/api/health/route.ts
export async function GET() {
  const health = {
    status: 'healthy',
    service: 'frontend',
    backend: 'disconnected',
  };

  try {
    // Test backend connectivity
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, {
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      health.backend = 'connected';
    } else {
      health.backend = `status: ${response.status}`;
    }
  } catch (error) {
    health.status = 'unhealthy';
    health.backend = `error: ${error.message}`;
  }

  const statusCode = health.status === 'healthy' ? 200 : 503;
  return Response.json(health, { status: statusCode });
}
```

### Monitoring Health Checks

**Render:** Configure health check path in `render.yaml`:
```yaml
healthCheckPath: /health
```

**Manual Testing:**
```bash
# Test all services
curl https://backend.onrender.com/health
curl https://mcp-server.onrender.com/health
curl https://yourapp.vercel.app/api/health

# Expected: All return 200 OK with {"status": "healthy"}
```

## End-to-End Error Handling

### Error Propagation Chain

```
User Action → Frontend → Backend → MCP → Database
                ↓          ↓         ↓        ↓
              Error     Error     Error    Error
                ↓          ↓         ↓        ↓
            Display ← Response ← Result ← Exception
```

### Error Handling at Each Tier

#### Tier 1: MCP Server

```python
# backend/tools/server.py
@mcp.tool()
def add_task_tool(user_id: str, title: str) -> dict:
    """Create task with comprehensive error handling."""
    try:
        # Validate inputs
        if not user_id or len(user_id) > 255:
            return {"status": "error", "error": "Invalid user_id"}

        if not title or len(title.strip()) == 0:
            return {"status": "error", "error": "Title required"}

        if len(title) > 200:
            return {"status": "error", "error": "Title too long (max 200 chars)"}

        # Database operation
        with Session(engine) as session:
            task = Task(user_id=user_id, title=title.strip())
            session.add(task)
            session.commit()
            session.refresh(task)

            return {
                "status": "success",
                "data": {"task_id": str(task.id), "title": task.title}
            }

    except IntegrityError as e:
        logger.error(f"Database constraint violation: {e}")
        return {"status": "error", "error": "Database constraint violation"}

    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        return {"status": "error", "error": "Database connection failed"}

    except Exception as e:
        logger.error(f"Unexpected error in add_task: {e}", exc_info=True)
        return {"status": "error", "error": "Failed to create task"}
```

**Key:** Return structured errors, never raise exceptions to Agent.

#### Tier 2: Backend (Agent Layer)

```python
# backend/services/agent.py
async def process_message(user_id: str, message: str) -> dict:
    """Process message with error handling."""
    try:
        # Create agent
        agent, server = await create_task_agent(user_id)

        async with server:
            # Run agent
            result = await Runner.run(agent, [{"role": "user", "content": message}])

            return {
                "response": result.final_output,
                "status": "success"
            }

    except httpx.ConnectError as e:
        logger.error(f"MCP server connection failed: {e}")
        return {
            "response": "Service temporarily unavailable. Please try again.",
            "status": "error",
            "error": "mcp_connection_failed"
        }

    except httpx.TimeoutException as e:
        logger.error(f"MCP server timeout: {e}")
        return {
            "response": "Request timed out. Please try again.",
            "status": "error",
            "error": "mcp_timeout"
        }

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return {
            "response": "I encountered an error. Please try again.",
            "status": "error",
            "error": "internal_error"
        }
```

**Key:** Catch MCP connection errors and provide user-friendly messages.

#### Tier 3: Backend (API Layer)

```python
# backend/routes/chat.py
@router.post("/api/chat")
async def chat_endpoint(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """Chat endpoint with error handling."""
    try:
        body = await request.json()
        message = body.get("message")

        if not message:
            raise HTTPException(status_code=400, detail="Message required")

        # Process through agent
        result = await process_message(user_id, message)

        return result

    except HTTPException:
        raise  # Re-raise HTTP exceptions

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Key:** Convert exceptions to proper HTTP status codes.

#### Tier 4: Frontend

```typescript
// lib/api.ts
export async function chat(message: string): Promise<ChatResponse> {
  try {
    const response = await apiRequest('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });

    return response;
  } catch (error) {
    if (error instanceof HTTPError) {
      // HTTP error from backend
      if (error.status === 401) {
        // Redirect to login
        window.location.href = '/signin';
        throw new Error('Authentication required');
      } else if (error.status === 503) {
        throw new Error('Service temporarily unavailable');
      } else if (error.status >= 500) {
        throw new Error('Server error. Please try again.');
      }
    } else if (error instanceof TypeError && error.message.includes('fetch')) {
      // Network error - backend unreachable
      throw new Error('Cannot connect to server. Please check your connection.');
    }

    // Generic error
    throw new Error('An unexpected error occurred');
  }
}

// Usage in component
async function handleSendMessage(message: string) {
  try {
    const response = await api.chat(message);
    setMessages([...messages, { role: 'assistant', content: response.response }]);
  } catch (error) {
    toast.error(error.message);  // Show user-friendly error
    console.error('Chat error:', error);
  }
}
```

**Key:** Provide clear error messages to users.

## Common Multi-Service Issues

### Issue 1: Service Can't Reach Other Service

**Symptom:**
```
httpx.ConnectError: [Errno 111] Connection refused
```

**Diagnosis:**
```bash
# 1. Check if service is running
curl https://mcp-server.onrender.com/health
# Should return 200 OK

# 2. Check environment variable
echo $MCP_SERVER_URL
# Should show external URL, not localhost

# 3. Check from backend logs
# Look for "MCP_SERVER_URL=..." log line
```

**Fixes:**
- Verify `MCP_SERVER_URL` is set to external URL
- Check service is deployed and healthy
- Verify no firewall blocking requests
- Ensure both services in same region (reduces latency)

### Issue 2: Circular Startup Dependencies

**Symptom:** Services fail to start because they check each other's health during startup.

**Problem:**
```python
# ❌ BAD - Backend checks MCP health during startup
@app.on_event("startup")
async def startup():
    # Fails if MCP not ready yet
    mcp_health = await client.get(f"{MCP_SERVER_URL}/health")
    if mcp_health.status_code != 200:
        raise Exception("MCP not available")
```

**Solution:** Lazy initialization, fail gracefully:
```python
# ✅ GOOD - Check health on first request, not startup
_mcp_server = None

async def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        try:
            _mcp_server = MCPServerStreamableHttp(...)
        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            raise HTTPException(status_code=503, detail="MCP unavailable")
    return _mcp_server
```

### Issue 3: Database Connection Pool Exhaustion

**Symptom:** Random "too many connections" errors under load.

**Cause:** Both backend and MCP connect to same database, pool limits reached.

**Solution:**
```python
# Adjust pool sizes based on service load

# Backend (handles many chat requests)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,      # Higher for backend
    max_overflow=20,
)

# MCP Server (fewer but longer-running queries)
engine = create_engine(
    DATABASE_URL,
    pool_size=5,       # Lower for MCP
    max_overflow=10,
)

# Database: Increase max_connections if needed
# PostgreSQL config: max_connections=100
```

### Issue 4: JWT Validation Failure

**Symptom:** Backend returns 401 Unauthorized even with valid token.

**Cause:** JWKS URL points to wrong frontend.

**Diagnosis:**
```bash
# Check JWKS endpoint is accessible
curl https://yourapp.vercel.app/api/auth/jwks
# Should return public keys

# Verify backend can reach it
curl -v https://yourapp.vercel.app/api/auth/jwks
# Check for SSL errors, redirects, etc.
```

**Fix:**
```python
# backend/.env
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks

# Verify in logs
logger.info(f"JWKS URL: {settings.BETTER_AUTH_JWKS_URL}")
```

### Issue 5: CORS Preflight Failures

**Symptom:** Browser shows CORS error, but backend logs show no request.

**Cause:** Preflight OPTIONS request failing.

**Diagnosis:**
```bash
# Test preflight manually
curl -X OPTIONS https://backend.onrender.com/api/chat \
  -H "Origin: https://yourapp.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Should return:
# Access-Control-Allow-Origin: https://yourapp.vercel.app
# Access-Control-Allow-Credentials: true
```

**Fix:** Ensure CORS middleware configured correctly:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourapp.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Must include OPTIONS
    allow_headers=["*"],
)
```

## Production Deployment Checklist

### Before Deployment

- [ ] Created `mcp_standalone.py` entry point
- [ ] Created `render.yaml` with 2 services
- [ ] Set all environment variables in Render dashboard
- [ ] Verified health check endpoints work locally
- [ ] Tested 3-service architecture locally (Frontend + Backend + MCP)

### After Deployment

- [ ] All services show "Live" in Render dashboard
- [ ] Health checks return 200 OK for all services
- [ ] Frontend can reach backend (`/api/health`)
- [ ] Backend can reach MCP (`/health`)
- [ ] MCP can reach database
- [ ] JWT authentication works end-to-end
- [ ] Chat functionality works (agent can call tools)
- [ ] Logs show no connection errors
- [ ] CORS configured correctly (no browser errors)
- [ ] Environment variables match actual URLs

### Monitoring

- [ ] Set up Render health check monitoring
- [ ] Configure uptime monitoring (UptimeRobot, etc.)
- [ ] Set up log aggregation
- [ ] Monitor database connection pool usage
- [ ] Track API response times
- [ ] Alert on health check failures

## Performance Considerations

### Connection Reuse

**MCP Client Singleton:**
```python
# Reuse across requests - saves 100-200ms per request
_mcp_server = None

async def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            cache_tools_list=True,  # Cache tool definitions
            max_retry_attempts=3,
        )
    return _mcp_server
```

### Database Connection Pooling

```python
# Both backend and MCP should use pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,     # Verify connections
    pool_recycle=3600,      # Recycle after 1 hour
)
```

### Service Latency

**Typical latencies:**
- Frontend → Backend: 50-100ms (depends on geography)
- Backend → MCP: 10-20ms (same datacenter)
- MCP → Database: 5-10ms (depends on database location)

**Optimization:**
- Deploy backend and MCP in same region
- Use database in same region as backend/MCP
- Use connection pooling
- Cache frequently accessed data

## Troubleshooting Tools

### Testing Service Connectivity

```bash
# From your local machine
curl https://backend.onrender.com/health
curl https://mcp-server.onrender.com/health

# Test backend can reach MCP (from backend logs)
# Look for MCP health check in backend /health response

# Test with authentication
curl https://backend.onrender.com/api/chat \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"message": "list tasks"}'
```

### Debugging Environment Variables

```python
# Add to backend startup
@app.on_event("startup")
async def log_config():
    logger.info("=== Service Configuration ===")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"MCP Server URL: {settings.MCP_SERVER_URL}")
    logger.info(f"Database URL: {settings.DATABASE_URL[:30]}...")
    logger.info(f"JWKS URL: {settings.BETTER_AUTH_JWKS_URL}")
    logger.info("============================")
```

### Log Analysis

**Look for these in logs:**
- "🚀 Starting..." - Service startup
- "✅ ... initialized" - Successful initialization
- "🔌 Initializing MCP..." - MCP connection attempt
- "⚠️ Invalid Host header" - DNS rebinding protection issue
- "Connection refused" - Service can't reach another service
- "Unauthorized" - JWT validation failure

## Migration from Mounted to Standalone

If you have an existing deployment with mounted MCP:

**Step 1:** Create standalone entry point (see above)

**Step 2:** Update render.yaml to add MCP service

**Step 3:** Update backend environment variables:
```bash
# Before
MCP_SERVER_URL=http://localhost:8000/mcp  # Mounted

# After
MCP_SERVER_URL=https://mcp-server.onrender.com  # Standalone
```

**Step 4:** Remove mounting code from backend:
```python
# backend/main.py

# ❌ Remove this
# from tools.server import mcp
# app.mount("/mcp", mcp.asgi_app)
```

**Step 5:** Deploy both services

**Step 6:** Verify health checks work

**Step 7:** Test end-to-end functionality
