---
name: fastmcp-database-tools-reference
description: Technical API reference for FastMCP server implementation, SQLModel database patterns, user isolation, error handling, and performance optimization.
---

# FastMCP and Database Tools - Technical Reference

## FastMCP API Reference

### FastMCP Class

```python
class FastMCP:
    def __init__(
        self,
        name: str,
        stateless_http: bool = False,
        json_response: bool = False
    ):
        """Initialize FastMCP server.

        Args:
            name: Server name (used in logs and metadata)
            stateless_http: Use stateless HTTP transport (recommended for production)
            json_response: Return JSON responses instead of MCP protocol format
        """
```

**Parameters:**
- `name` (str, required): Identifier for your MCP server
- `stateless_http` (bool, default=False): When True, uses HTTP transport without persistent connections
- `json_response` (bool, default=False): When True, returns plain JSON instead of MCP-wrapped responses

**Best Practice:**
```python
# Production configuration
mcp = FastMCP(
    "MyServer",
    stateless_http=True,  # Scalable, no persistent state
    json_response=True    # Easier to debug and integrate
)
```

### @mcp.tool() Decorator

```python
@mcp.tool()
def tool_name(param1: str, param2: int = 0) -> dict:
    """Tool description shown to the LLM.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2

    Returns:
        Description of return value
    """
    return {"status": "success", "data": {}}
```

**How it works:**
1. Decorator registers the function as an MCP tool
2. Function docstring becomes tool description for the LLM
3. Type hints are converted to JSON schema for validation
4. Function is exposed via HTTP endpoint at `/mcp`

**Type Annotations:**
- `str`, `int`, `float`, `bool` - Primitive types
- `Optional[str]` - Optional parameters (must have default value)
- `dict`, `list` - Complex types (use with caution, prefer structured types)
- Return type should be `dict` for JSON responses

### mcp.run()

```python
mcp.run(
    transport: str = "streamable-http",
    host: str = "0.0.0.0",
    port: int = 8000
)
```

**Parameters:**
- `transport` (str): Transport type, use `"streamable-http"` for HTTP servers
- `host` (str): Host to bind to (use `"0.0.0.0"` for external access)
- `port` (int): Port to listen on

**Production Deployment:**
```bash
# Don't use mcp.run() in production - use ASGI server instead
uvicorn server:mcp.asgi_app --host 0.0.0.0 --port 8001 --workers 4
```

### mcp.asgi_app

```python
# Access ASGI application for production deployment
app = mcp.asgi_app
```

Use this with production ASGI servers like uvicorn, gunicorn, or hypercorn.

## SQLModel Database Patterns

### Session Management

**Pattern 1: Context Manager (Recommended)**

```python
from sqlmodel import Session
from db import engine

def my_operation(user_id: str) -> dict:
    with Session(engine) as session:
        # Operations here
        task = Task(user_id=user_id, title="Example")
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"task_id": str(task.id)}
    # Session automatically closed
```

**Pattern 2: Dependency Injection (For Testing)**

```python
def my_operation(user_id: str, _session: Session = None) -> dict:
    session = _session or Session(engine)

    try:
        task = Task(user_id=user_id, title="Example")
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"task_id": str(task.id)}
    finally:
        if not _session:
            session.close()
```

**When to use each:**
- Context manager: Simple operations, production code
- Dependency injection: Testing, transaction management, complex operations

### Query Patterns

**Select Single Record:**

```python
from sqlmodel import select
from uuid import UUID

def get_task(task_id: str, user_id: str) -> dict:
    with Session(engine) as session:
        task_uuid = UUID(task_id)
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {"status": "error", "error": "Task not found"}

        if task.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        return {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "completed": task.completed
            }
        }
```

**Select Multiple Records with Filtering:**

```python
def list_tasks(user_id: str, status: str = "all") -> dict:
    with Session(engine) as session:
        # Base query
        statement = select(Task).where(Task.user_id == user_id)

        # Apply filters
        if status == "pending":
            statement = statement.where(Task.completed == False)
        elif status == "completed":
            statement = statement.where(Task.completed == True)

        # Execute
        tasks = session.exec(statement).all()

        return {
            "status": "success",
            "data": {
                "tasks": [
                    {
                        "task_id": str(task.id),
                        "title": task.title,
                        "completed": task.completed
                    }
                    for task in tasks
                ]
            }
        }
```

**Update Record:**

```python
from datetime import datetime, UTC

def update_task(user_id: str, task_id: str, title: str) -> dict:
    with Session(engine) as session:
        task_uuid = UUID(task_id)
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {"status": "error", "error": "Task not found"}

        if task.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        # Update fields
        task.title = title
        task.updated_at = datetime.now(UTC)

        session.add(task)
        session.commit()
        session.refresh(task)

        return {
            "status": "success",
            "data": {"task_id": str(task.id), "title": task.title}
        }
```

**Delete Record:**

```python
def delete_task(user_id: str, task_id: str) -> dict:
    with Session(engine) as session:
        task_uuid = UUID(task_id)
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {"status": "error", "error": "Task not found"}

        if task.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        session.delete(task)
        session.commit()

        return {
            "status": "success",
            "data": {"task_id": str(task_uuid), "deleted": True}
        }
```

## User Isolation Patterns

### Pattern 1: User ID in All Queries

**Always filter by user_id:**

```python
# CORRECT
statement = select(Task).where(
    Task.user_id == user_id,
    Task.id == task_id
)

# WRONG - Missing user_id filter
statement = select(Task).where(Task.id == task_id)
```

### Pattern 2: Ownership Verification

**Two-step verification:**

```python
def update_task(user_id: str, task_id: str, title: str) -> dict:
    # Step 1: Find record
    task = session.exec(select(Task).where(Task.id == task_id)).first()

    if not task:
        return {"status": "error", "error": "Task not found"}

    # Step 2: Verify ownership
    if task.user_id != user_id:
        return {"status": "error", "error": "Unauthorized"}

    # Step 3: Proceed with operation
    task.title = title
    session.add(task)
    session.commit()
```

### Pattern 3: Database-Level Constraints

**Add Row-Level Security (PostgreSQL):**

```sql
-- Enable RLS on tasks table
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own tasks
CREATE POLICY tasks_isolation ON tasks
    FOR ALL
    USING (user_id = current_setting('app.user_id')::text);

-- Set user context before each query
SET app.user_id = 'user123';
```

**In Python:**

```python
def with_user_context(user_id: str, session: Session):
    """Set user context for RLS policies."""
    session.exec(f"SET LOCAL app.user_id = '{user_id}'")

# Usage
with Session(engine) as session:
    with_user_context(user_id, session)
    # All queries now automatically filtered by user_id
    tasks = session.exec(select(Task)).all()
```

## Error Handling Reference

### Standard Error Response Format

```python
{
    "status": "error",
    "error": "Human-readable error message"
}
```

### Error Categories

**Validation Errors:**
```python
if not title or len(title) == 0:
    return {"status": "error", "error": "Title required"}

if len(title) > 200:
    return {"status": "error", "error": "Title must be 200 characters or less"}
```

**Not Found Errors:**
```python
if not task:
    return {"status": "error", "error": "Task not found"}
```

**Authorization Errors:**
```python
if task.user_id != user_id:
    return {"status": "error", "error": "Unauthorized: Task does not belong to user"}
```

**Database Errors:**
```python
try:
    session.add(task)
    session.commit()
except IntegrityError as e:
    return {"status": "error", "error": "Database constraint violation"}
except OperationalError as e:
    return {"status": "error", "error": "Database connection failed"}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"status": "error", "error": "Internal server error"}
```

## Input Validation Patterns

### String Validation

```python
# Required string
if not title or len(title.strip()) == 0:
    return {"status": "error", "error": "Title required"}

# Max length
if len(title) > 200:
    return {"status": "error", "error": "Title too long"}

# Min length
if len(title) < 3:
    return {"status": "error", "error": "Title too short"}

# Always strip whitespace
title = title.strip()
```

### UUID Validation

```python
from uuid import UUID

try:
    task_uuid = UUID(task_id)
except ValueError:
    return {"status": "error", "error": "Invalid task ID format"}
```

### Enum Validation

```python
VALID_STATUSES = ["all", "pending", "completed"]

if status not in VALID_STATUSES:
    return {
        "status": "error",
        "error": f"Status must be one of: {', '.join(VALID_STATUSES)}"
    }
```

### Optional Parameter Validation

```python
def update_task(user_id: str, task_id: str, title: str = None, description: str = None):
    # At least one field required
    if not title and description is None:
        return {"status": "error", "error": "Must provide title or description"}

    # Validate provided fields
    if title and len(title) > 200:
        return {"status": "error", "error": "Title too long"}

    if description and len(description) > 1000:
        return {"status": "error", "error": "Description too long"}
```

## OpenAI Agents SDK Integration

### MCPServerStreamableHttp Configuration

```python
from mcp.client import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="Task MCP Server",
    params={
        "url": "http://localhost:8001/mcp",  # MCP server URL
        "timeout": 30                         # Request timeout in seconds
    },
    cache_tools_list=True,      # Cache tool definitions (performance)
    max_retry_attempts=3        # Retry failed requests
)
```

### Agent Configuration

```python
from openai_agents import Agent

agent = Agent(
    name="TaskAssistant",
    instructions=f"""You are a helpful assistant that manages tasks for users.
    Current user ID: {user_id}

    IMPORTANT - Task ID Handling:
    - Task IDs are UUIDs (e.g., "550e8400-e29b-41d4-a716-446655440000")
    - Users refer to tasks by TITLE, not by ID
    - When updating/completing/deleting tasks:
      1. FIRST call list_tasks_tool to find the task by title
      2. THEN use the task_id from the results
    - Always pass the user_id parameter to all tools
    """,
    mcp_servers=[mcp_server],
    model="gpt-4o"
)
```

### Singleton Pattern for MCP Server

**Problem:** Creating new MCP connections for each request is slow.

**Solution:** Reuse a single MCP server instance:

```python
_mcp_server = None

async def get_mcp_server():
    """Get or create singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="Task MCP Server",
            params={"url": settings.MCP_SERVER_URL, "timeout": 30},
            cache_tools_list=True,
            max_retry_attempts=3
        )
    return _mcp_server

# Usage
async def create_agent(user_id: str):
    server = await get_mcp_server()
    agent = Agent(
        name="TaskAssistant",
        instructions=f"User: {user_id}",
        mcp_servers=[server],
        model="gpt-4"
    )
    return agent, server

# In request handler
agent, server = await create_agent(user_id)
async with server:
    result = await agent.run(user_message)
```

## Performance Optimization

### Database Connection Pooling

```python
from sqlmodel import create_engine

engine = create_engine(
    DATABASE_URL,
    echo=False,              # Disable SQL logging in production
    pool_size=5,             # Number of connections to maintain
    max_overflow=10,         # Additional connections when pool is full
    pool_pre_ping=True,      # Test connections before use
    pool_recycle=3600        # Recycle connections after 1 hour
)
```

### Index Strategy

```python
class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)  # Index for filtering
    completed: bool = Field(default=False, index=True)  # Index for status queries
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
```

**Composite Indexes:**

```python
from sqlalchemy import Index

class Task(SQLModel, table=True):
    # ... fields ...

    __table_args__ = (
        Index('idx_user_completed', 'user_id', 'completed'),  # For filtered lists
        Index('idx_user_created', 'user_id', 'created_at'),   # For sorted lists
    )
```

### Response Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache user context for 5 minutes
@lru_cache(maxsize=1000)
def get_user_context(user_id: str, timestamp: int):
    """Get user context with cache invalidation every 5 minutes."""
    # timestamp changes every 5 minutes, invalidating cache
    with Session(engine) as session:
        return session.exec(select(User).where(User.id == user_id)).first()

# Usage
timestamp = int(datetime.now().timestamp() / 300)  # 5-minute buckets
user = get_user_context(user_id, timestamp)
```

## Security Best Practices

### 1. Never Trust LLM Inputs

```python
# WRONG - Direct string interpolation (SQL injection risk)
statement = f"SELECT * FROM tasks WHERE user_id = '{user_id}'"

# CORRECT - Parameterized queries
statement = select(Task).where(Task.user_id == user_id)
```

### 2. Validate All Parameters

```python
# Check bounds
if len(title) > 200:
    return error

# Check format
UUID(task_id)  # Raises ValueError if invalid

# Check allowed values
if status not in ALLOWED_VALUES:
    return error
```

### 3. Sanitize Output

```python
# Don't leak sensitive data
return {
    "status": "success",
    "data": {
        "task_id": str(task.id),
        "title": task.title
        # Don't include: task.user_id, internal fields, etc.
    }
}
```

### 4. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("100/minute")
async def chatkit_endpoint(request: Request):
    # Process request
    pass
```

## Logging Best Practices

### Structured Logging

```python
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def log_tool_call(tool_name: str, user_id: str, params: dict, result: dict):
    """Log tool execution with structured data."""
    log_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": tool_name,
        "user_id": user_id,
        "params": params,
        "status": result.get("status"),
        "error": result.get("error")
    }
    logging.info(json.dumps(log_data))

# Usage in tool
@mcp.tool()
def add_task_tool(user_id: str, title: str):
    result = add_task(user_id, title)
    log_tool_call("add_task", user_id, {"title": title}, result)
    return result
```

### Error Logging

```python
import traceback

try:
    # Operation
    pass
except Exception as e:
    logging.error({
        "error": str(e),
        "traceback": traceback.format_exc(),
        "context": {"user_id": user_id, "task_id": task_id}
    })
    return {"status": "error", "error": "Internal error"}
```

## Testing Reference

### Pytest Fixtures

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def session(engine):
    """Create database session for testing."""
    with Session(engine) as session:
        yield session
        session.rollback()  # Rollback after each test

@pytest.fixture(scope="function")
def sample_task(session):
    """Create a sample task for testing."""
    task = Task(user_id="test_user", title="Test Task")
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
```

### Test Patterns

```python
def test_successful_operation(session):
    """Test successful path."""
    result = add_task("user123", "Test", _session=session)

    assert result["status"] == "success"
    assert "task_id" in result["data"]

def test_validation_error(session):
    """Test validation failure."""
    result = add_task("user123", "", _session=session)

    assert result["status"] == "error"
    assert "Title" in result["error"]

def test_authorization_error(session, sample_task):
    """Test unauthorized access."""
    result = delete_task("other_user", str(sample_task.id), _session=session)

    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]
```

## Production Deployment - Host Validation

### DNS Rebinding Protection Overview

**Added:** December 2025 to MCP SDK

**What it is:** A security feature that validates the `Host` header in HTTP requests to prevent DNS rebinding attacks. DNS rebinding is a technique where attackers manipulate DNS records to trick your server into accepting requests from malicious origins.

**How it works:** The MCP server checks the incoming `Host` header against a whitelist of allowed hostnames. If the header doesn't match, the server returns a `421 Misdirected Request` error.

**Why you need it:** Without this validation, an attacker could:
1. Point a malicious domain to your server's IP
2. Send requests with that domain's `Host` header
3. Bypass CORS and origin validation
4. Access your MCP tools without authorization

### Common Error Messages

**Error 1: Invalid Host Header**
```
WARNING - Invalid Host header: your-service.onrender.com
INFO: "GET / HTTP/1.1" 421 Misdirected Request
```

**Cause:** The `Host` header in the request (`your-service.onrender.com`) is not in the `allowed_hosts` list.

**Solution:** Add the exact hostname to `allowed_hosts`:
```python
allowed_hosts_list.append("your-service.onrender.com")
allowed_hosts_list.append("your-service.onrender.com:*")
```

**Error 2: Host Header Mismatch After Redeployment**
```
WARNING - Invalid Host header: myapp-abc123.platform.com
# (previously worked with: myapp-xyz789.platform.com)
```

**Cause:** Your platform changed the hostname during redeployment, but the code has a hardcoded old hostname.

**Solution:** Use environment variable for dynamic hostname resolution:
```python
HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")  # or RAILWAY_PUBLIC_DOMAIN, etc.
```

### TransportSecuritySettings API Reference

```python
from mcp.server.transport_security import TransportSecuritySettings

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection: bool = True,
    allowed_hosts: list[str] = None,
    allowed_origins: list[str] = None,
)
```

**Parameters:**

1. `enable_dns_rebinding_protection` (bool, default=True)
   - Enables Host header validation
   - Set to `False` to disable (NOT recommended for production)

2. `allowed_hosts` (list[str], optional)
   - Whitelist of allowed `Host` header values
   - Supports exact matches and port wildcards
   - **No wildcard domain support** (e.g., `*.onrender.com` will NOT work)
   - Patterns:
     - `"example.com"` - Exact match (HTTPS default port)
     - `"example.com:*"` - Match with any port
     - `"example.com:8080"` - Match with specific port

3. `allowed_origins` (list[str], optional)
   - Whitelist of allowed `Origin` header values
   - Used for CORS validation
   - Supports wildcards for ports: `"http://localhost:*"`

### Platform-Specific Examples

#### Render

Render provides `RENDER_EXTERNAL_HOSTNAME` environment variable automatically.

```python
import os
from mcp.server import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

allowed_hosts_list = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]

if RENDER_HOSTNAME:
    allowed_hosts_list.extend([
        RENDER_HOSTNAME,        # e.g., "myapp.onrender.com"
        f"{RENDER_HOSTNAME}:*", # e.g., "myapp.onrender.com:443"
    ])

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=allowed_hosts_list,
    allowed_origins=[
        "http://localhost:*",
        "https://localhost:*",
        f"https://{RENDER_HOSTNAME}" if RENDER_HOSTNAME else "",
    ],
)

mcp = FastMCP(
    "TaskMCPServer",
    stateless_http=True,
    transport_security=transport_security,
)
```

#### Railway

Railway provides `RAILWAY_PUBLIC_DOMAIN` environment variable.

```python
RAILWAY_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

allowed_hosts_list = ["localhost", "localhost:*"]

if RAILWAY_DOMAIN:
    allowed_hosts_list.extend([
        RAILWAY_DOMAIN,
        f"{RAILWAY_DOMAIN}:*",
    ])

# Same TransportSecuritySettings pattern as above
```

#### Fly.io

Fly.io uses `FLY_APP_NAME` to construct the hostname.

```python
FLY_APP_NAME = os.environ.get("FLY_APP_NAME")

allowed_hosts_list = ["localhost", "localhost:*"]

if FLY_APP_NAME:
    fly_hostname = f"{FLY_APP_NAME}.fly.dev"
    allowed_hosts_list.extend([
        fly_hostname,
        f"{fly_hostname}:*",
    ])

# Same TransportSecuritySettings pattern as above
```

#### Custom Domain

If you use a custom domain:

```python
CUSTOM_DOMAIN = os.environ.get("CUSTOM_DOMAIN", "api.myapp.com")

allowed_hosts_list = [
    "localhost",
    "localhost:*",
    CUSTOM_DOMAIN,
    f"{CUSTOM_DOMAIN}:*",
]

# Same TransportSecuritySettings pattern as above
```

### Troubleshooting Guide

#### Problem: Still getting "Invalid Host header" after adding hostname

**Check 1: Verify exact hostname**
```bash
# Look at server logs for the actual Host header value
# Example log:
# WARNING - Invalid Host header: myapp-abc123.onrender.com:443

# Make sure your allowed_hosts includes the EXACT value:
allowed_hosts_list.append("myapp-abc123.onrender.com:443")
# OR use port wildcard:
allowed_hosts_list.append("myapp-abc123.onrender.com:*")
```

**Check 2: Port suffix matters**

HTTPS requests on default port (443) may or may not include `:443` in the Host header depending on the client. Always include both patterns:

```python
allowed_hosts_list.extend([
    "myapp.onrender.com",      # For Host: myapp.onrender.com
    "myapp.onrender.com:*",    # For Host: myapp.onrender.com:443
])
```

**Check 3: Wildcard domains don't work**

```python
# WRONG - Wildcards not supported
allowed_hosts_list.append("*.onrender.com")

# CORRECT - Use exact hostname
allowed_hosts_list.append("myapp.onrender.com")
```

#### Problem: Works locally but fails in production

**Cause:** Environment variable not set or different hostname between environments.

**Solution:**
```python
# Add fallback for local development
HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")

# Log the configuration at startup
logger.info(f"Configured allowed_hosts: {allowed_hosts_list}")
```

#### Problem: Hostname changes after every deployment

**Cause:** Platform assigns random subdomains for preview/staging deployments.

**Solution 1:** Use custom domain for production
**Solution 2:** Set hostname via environment variable in deployment settings
**Solution 3:** For development/staging, disable validation (NOT recommended):

```python
# ONLY for development - DO NOT use in production
if os.environ.get("ENVIRONMENT") == "development":
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
```

#### Problem: Health check endpoint returns 421

**Cause:** Health check service sends requests with different Host header.

**Solution:** Add health check hostname to allowed_hosts:

```python
# Render health checks come from internal hostname
RENDER_INTERNAL_HOSTNAME = os.environ.get("RENDER_INTERNAL_HOSTNAME")
if RENDER_INTERNAL_HOSTNAME:
    allowed_hosts_list.append(RENDER_INTERNAL_HOSTNAME)
    allowed_hosts_list.append(f"{RENDER_INTERNAL_HOSTNAME}:*")
```

### Testing Host Validation

#### Test 1: Verify Configuration

```python
# Add logging to verify configuration at startup
def log_transport_security():
    logger.info("=== TransportSecuritySettings ===")
    logger.info(f"DNS Rebinding Protection: Enabled")
    logger.info(f"Allowed Hosts: {allowed_hosts_list}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    logger.info(f"Hostname: {HOSTNAME}")
    logger.info("================================")

# Call at startup
log_transport_security()
```

#### Test 2: Test with curl

```bash
# Test with correct Host header
curl -H "Host: myapp.onrender.com" https://myapp.onrender.com/health
# Should return 200 OK

# Test with incorrect Host header
curl -H "Host: evil.com" https://myapp.onrender.com/health
# Should return 421 Misdirected Request
```

#### Test 3: Automated Testing

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_host_validation():
    """Test that only allowed hosts are accepted."""
    async with httpx.AsyncClient() as client:
        # Valid host
        response = await client.get(
            "http://localhost:8001/health",
            headers={"Host": "localhost"}
        )
        assert response.status_code == 200

        # Invalid host (should be rejected)
        response = await client.get(
            "http://localhost:8001/health",
            headers={"Host": "evil.com"}
        )
        assert response.status_code == 421
```

### Common Mistakes

#### Mistake 1: Using wildcard domains

```python
# WRONG - Wildcards are not supported
allowed_hosts_list = ["*.onrender.com", "*.railway.app"]

# CORRECT - Use exact hostnames
allowed_hosts_list = [
    os.environ.get("RENDER_EXTERNAL_HOSTNAME"),
    os.environ.get("RAILWAY_PUBLIC_DOMAIN"),
]
```

#### Mistake 2: Hardcoding production hostname

```python
# WRONG - Hostname will change on redeployment
allowed_hosts_list = ["myapp-abc123.onrender.com"]

# CORRECT - Use environment variable
allowed_hosts_list = [os.environ.get("RENDER_EXTERNAL_HOSTNAME")]
```

#### Mistake 3: Missing port wildcard

```python
# WRONG - Only matches default port
allowed_hosts_list = ["myapp.com"]

# CORRECT - Include port wildcard
allowed_hosts_list = ["myapp.com", "myapp.com:*"]
```

#### Mistake 4: Forgetting localhost for development

```python
# WRONG - Production only
allowed_hosts_list = [os.environ.get("RENDER_EXTERNAL_HOSTNAME")]

# CORRECT - Include localhost for local development
allowed_hosts_list = [
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    allowed_hosts_list.append(os.environ.get("RENDER_EXTERNAL_HOSTNAME"))
    allowed_hosts_list.append(f"{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}:*")
```

#### Mistake 5: Not logging configuration

```python
# WRONG - No visibility into what's configured
mcp = FastMCP(
    "Server",
    transport_security=transport_security
)

# CORRECT - Log configuration for debugging
logger.info(f"Allowed hosts: {allowed_hosts_list}")
mcp = FastMCP(
    "Server",
    transport_security=transport_security
)
```

### Production Deployment Checklist

Before deploying to production, verify:

- [ ] `TransportSecuritySettings` configured with `enable_dns_rebinding_protection=True`
- [ ] Hostname resolution uses environment variable (not hardcoded)
- [ ] Both `"hostname"` and `"hostname:*"` patterns included
- [ ] `localhost` and `127.0.0.1` included for local development
- [ ] Configuration logged at startup for visibility
- [ ] Health check endpoint returns 200 OK (not 421)
- [ ] MCP endpoint accepts POST requests from client
- [ ] No "Invalid Host header" warnings in logs
- [ ] Tested with actual production hostname

### Migration Guide

If you have an existing MCP server without host validation:

**Step 1:** Update imports
```python
from mcp.server.transport_security import TransportSecuritySettings
```

**Step 2:** Create configuration
```python
HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")

allowed_hosts_list = [
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
]

if HOSTNAME and HOSTNAME != "localhost":
    allowed_hosts_list.extend([HOSTNAME, f"{HOSTNAME}:*"])

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=allowed_hosts_list,
)
```

**Step 3:** Update FastMCP initialization
```python
# Before
mcp = FastMCP("Server", stateless_http=True)

# After
mcp = FastMCP(
    "Server",
    stateless_http=True,
    transport_security=transport_security,
)
```

**Step 4:** Set environment variable in deployment platform
- Render: `RENDER_EXTERNAL_HOSTNAME` (automatic)
- Railway: `RAILWAY_PUBLIC_DOMAIN` (automatic)
- Other: Set `CUSTOM_DOMAIN` manually

**Step 5:** Test deployment
```bash
# Check health endpoint
curl https://your-service.platform.com/health

# Check logs for "Invalid Host header" warnings
# Should see: "Allowed hosts: ['localhost', 'your-service.platform.com', ...]"
```

