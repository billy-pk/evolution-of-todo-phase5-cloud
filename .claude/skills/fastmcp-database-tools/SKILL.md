---
name: fastmcp-database-tools
description: Build production-ready MCP servers using FastMCP with PostgreSQL database integration. Connect AI agents to databases with CRUD operations, user isolation, and stateless HTTP transport.
---

# MCP Server with FastMCP and Database Tools

## Overview

This skill teaches how to build production-ready MCP (Model Context Protocol) servers using FastMCP with PostgreSQL database integration. MCP servers expose tools that AI agents can call to interact with databases, APIs, or external systems.

**Use this skill when you need to:**
- Connect an AI agent to a database for CRUD operations
- Build custom tools for OpenAI Agents SDK or other AI frameworks
- Create stateless HTTP-based MCP servers for scalable deployments
- Implement multi-tenant database operations with user isolation
- Expose database operations to LLMs in a safe, validated way

## Key Concepts

### What is MCP?

Model Context Protocol (MCP) is a standard protocol for connecting AI agents to external tools and data sources. Instead of the AI directly accessing databases or APIs, MCP servers expose controlled, validated tools that the AI can invoke.

**Architecture:**
```
AI Agent (OpenAI/Anthropic) → MCP Client → MCP Server → Database/API
```

### Why FastMCP?

FastMCP is the official Python SDK for building MCP servers. It provides:
- **Stateless HTTP transport** - Scalable, no persistent connections
- **Simple decorator-based API** - Define tools with `@mcp.tool()`
- **Automatic validation** - Type hints become tool schemas
- **Built-in error handling** - Standardized error responses
- **JSON response format** - Easy integration with any LLM

### Database Integration Pattern

The recommended pattern separates concerns:
1. **Business logic functions** - Pure Python functions with database operations
2. **Tool wrappers** - Decorated with `@mcp.tool()` for MCP exposure
3. **User context passing** - `user_id` flows through all operations
4. **Validation layer** - Input validation before database access
5. **Testing support** - Optional `_session` parameter for dependency injection

## Quick Start

### Prerequisites

```bash
# Install FastMCP
pip install mcp

# Install database dependencies
pip install sqlmodel  # For SQLModel ORM
# or
pip install sqlalchemy  # For raw SQLAlchemy
```

### Basic MCP Server (5-minute setup)

```python
from mcp.server import FastMCP

# Initialize server
mcp = FastMCP(
    "MyMCPServer",
    stateless_http=True,  # Use HTTP transport (scalable)
    json_response=True    # Return JSON responses
)

# Define a simple tool
@mcp.tool()
def hello(name: str) -> dict:
    """Say hello to someone.

    Args:
        name: Person's name

    Returns:
        Greeting message
    """
    return {
        "status": "success",
        "message": f"Hello, {name}!"
    }

# Run server
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

**Run it:**
```bash
python server.py
# Server runs on http://localhost:8000/mcp by default
```

## Implementation Workflow

Follow these steps to build a production-ready MCP server with database tools:

### Step 1: Set Up Database Connection

```python
from sqlmodel import create_engine, Session, SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4

# Define your model
class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# Create engine
DATABASE_URL = "postgresql://user:pass@host/db"
engine = create_engine(DATABASE_URL, echo=False)

# Create tables
SQLModel.metadata.create_all(engine)
```

### Step 2: Write Business Logic Functions

Separate business logic from MCP tool definitions for better testability:

```python
def add_task(user_id: str, title: str, description: str = None, _session: Session = None) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and task data
    """
    # Validate inputs
    if not title or len(title.strip()) == 0:
        return {"status": "error", "error": "Title required"}

    if len(title) > 200:
        return {"status": "error", "error": "Title too long"}

    # Use provided session or create new one
    session = _session or Session(engine)

    try:
        # Create task
        task = Task(user_id=user_id, title=title.strip(), description=description)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Return success
        return {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "completed": task.completed
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        if not _session:
            session.close()
```

### Step 3: Define MCP Tools

Wrap business logic with `@mcp.tool()` decorator:

```python
from mcp.server import FastMCP

mcp = FastMCP("TaskMCPServer", stateless_http=True, json_response=True)

@mcp.tool()
def add_task_tool(user_id: str, title: str, description: str = None) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID from authentication
        title: Task title (required)
        description: Optional task description

    Returns:
        Task creation result
    """
    return add_task(user_id, title, description)
```

### Step 4: Connect to AI Agent

**Using OpenAI Agents SDK:**

```python
from openai_agents import Agent
from mcp.client import MCPServerStreamableHttp

# Create MCP client
mcp_server = MCPServerStreamableHttp(
    name="Task MCP Server",
    params={"url": "http://localhost:8001/mcp", "timeout": 30},
    cache_tools_list=True,
    max_retry_attempts=3
)

# Create agent with MCP tools
agent = Agent(
    name="TaskAssistant",
    instructions=f"You help manage tasks for user {user_id}",
    mcp_servers=[mcp_server],
    model="gpt-4"
)

# Use agent
async with mcp_server:
    result = await agent.run("Create a task to buy groceries")
```

### Step 5: Run the Server

```bash
# Development
python server.py

# Production (with uvicorn)
uvicorn server:mcp.asgi_app --host 0.0.0.0 --port 8001
```

## Common Pitfalls and Solutions

### Pitfall 1: Missing User Isolation

**Problem:** Tools don't validate that users can only access their own data.

```python
# WRONG - No user validation
@mcp.tool()
def delete_task(task_id: str) -> dict:
    task = session.get(Task, task_id)
    session.delete(task)
    return {"status": "success"}
```

**Solution:** Always validate user ownership:

```python
# CORRECT - User isolation enforced
@mcp.tool()
def delete_task(user_id: str, task_id: str) -> dict:
    task = session.get(Task, task_id)

    if not task:
        return {"status": "error", "error": "Task not found"}

    if task.user_id != user_id:
        return {"status": "error", "error": "Unauthorized"}

    session.delete(task)
    return {"status": "success"}
```

### Pitfall 2: Poor Error Handling

**Problem:** Exceptions crash the server or leak sensitive information.

```python
# WRONG - Unhandled exceptions
@mcp.tool()
def add_task(user_id: str, title: str) -> dict:
    task = Task(user_id=user_id, title=title)
    session.add(task)
    session.commit()  # Could raise IntegrityError, DatabaseError, etc.
    return {"status": "success"}
```

**Solution:** Wrap in try-except with safe error messages:

```python
# CORRECT - Comprehensive error handling
@mcp.tool()
def add_task(user_id: str, title: str) -> dict:
    try:
        task = Task(user_id=user_id, title=title)
        session.add(task)
        session.commit()
        return {"status": "success", "data": {"task_id": str(task.id)}}
    except ValidationError as e:
        return {"status": "error", "error": f"Validation failed: {e}"}
    except IntegrityError:
        return {"status": "error", "error": "Database constraint violation"}
    except Exception as e:
        # Log full error server-side, return safe message to client
        logger.error(f"Failed to add task: {e}", exc_info=True)
        return {"status": "error", "error": "Failed to create task"}
```

### Pitfall 3: Not Using Stateless HTTP

**Problem:** Using stateful connections that don't scale.

```python
# WRONG - Stateful connection (doesn't scale)
mcp = FastMCP("Server", stateless_http=False)
```

**Solution:** Always use stateless HTTP for production:

```python
# CORRECT - Stateless HTTP (scalable)
mcp = FastMCP("Server", stateless_http=True, json_response=True)
```

### Pitfall 4: Missing Input Validation

**Problem:** Trusting LLM-generated inputs without validation.

```python
# WRONG - No validation
@mcp.tool()
def add_task(user_id: str, title: str) -> dict:
    task = Task(user_id=user_id, title=title)
    # What if title is empty? What if it's 10,000 characters?
```

**Solution:** Validate all inputs before database operations:

```python
# CORRECT - Comprehensive validation
@mcp.tool()
def add_task(user_id: str, title: str, description: str = None) -> dict:
    # Validate user_id
    if not user_id or len(user_id) > 255:
        return {"status": "error", "error": "Invalid user_id"}

    # Validate title
    if not title or len(title.strip()) == 0:
        return {"status": "error", "error": "Title required"}

    if len(title) > 200:
        return {"status": "error", "error": "Title too long (max 200 chars)"}

    # Validate description
    if description and len(description) > 1000:
        return {"status": "error", "error": "Description too long (max 1000 chars)"}

    # Proceed with validated inputs
    task = Task(user_id=user_id, title=title.strip(), description=description)
    ...
```

### Pitfall 5: Inconsistent Response Format

**Problem:** Different tools return different response structures.

```python
# WRONG - Inconsistent responses
@mcp.tool()
def add_task(...):
    return {"task_id": "123"}  # Just data

@mcp.tool()
def list_tasks(...):
    return {"status": "ok", "tasks": [...]}  # Different format
```

**Solution:** Use consistent response envelope:

```python
# CORRECT - Consistent format
@mcp.tool()
def add_task(...):
    return {
        "status": "success",
        "data": {"task_id": "123"}
    }

@mcp.tool()
def list_tasks(...):
    return {
        "status": "success",
        "data": {"tasks": [...]}
    }

@mcp.tool()
def error_case(...):
    return {
        "status": "error",
        "error": "Something went wrong"
    }
```

## Testing Strategy

### Unit Tests for Business Logic

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_add_task(session):
    result = add_task("user123", "Buy milk", _session=session)

    assert result["status"] == "success"
    assert "task_id" in result["data"]

    # Verify in database
    task = session.get(Task, UUID(result["data"]["task_id"]))
    assert task.title == "Buy milk"
    assert task.user_id == "user123"

def test_add_task_validation(session):
    result = add_task("user123", "", _session=session)

    assert result["status"] == "error"
    assert "Title" in result["error"]
```

### Integration Tests with MCP Client

```python
import httpx
from openai_agents import Agent
from mcp.client import MCPServerStreamableHttp

async def test_mcp_integration():
    # Start MCP server in background
    # ...

    # Create client
    mcp_server = MCPServerStreamableHttp(
        name="Test Server",
        params={"url": "http://localhost:8001/mcp"}
    )

    # Create agent
    agent = Agent(
        name="TestAgent",
        mcp_servers=[mcp_server],
        model="gpt-4"
    )

    # Test tool execution
    async with mcp_server:
        result = await agent.run("Add a task to test the system")
        assert "task" in result.lower()
```

## Production Deployment

### 1. Environment Configuration

```bash
# .env
DATABASE_URL=postgresql://user:pass@host:5432/db
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8001
LOG_LEVEL=INFO
```

### 2. Run with Process Manager

```bash
# Using systemd
[Unit]
Description=MCP Task Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app
Environment="DATABASE_URL=postgresql://..."
ExecStart=/usr/bin/uvicorn server:mcp.asgi_app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Health Checks

```python
@mcp.tool()
def health_check() -> dict:
    """Check server and database health."""
    try:
        with Session(engine) as session:
            session.exec(select(1)).first()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 4. Monitoring

- **Metrics**: Track tool call counts, errors, latency
- **Logging**: Use structured logging (JSON format)
- **Alerts**: Set up alerts for error rates, database connection issues

### 5. Host Validation (Critical for Production)

**Problem:** In production, you may see `421 Invalid Host header` or `Misdirected Request` errors. This is due to DNS rebinding protection added to MCP SDK in December 2025.

**Solution:** Configure `TransportSecuritySettings` with your production hostname:

```python
import os
from mcp.server import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Get dynamic hostname (Render, Railway, etc.)
HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")

allowed_hosts_list = [
    "localhost",
    "localhost:*",
    HOSTNAME,          # Exact match for HTTPS (default port)
    f"{HOSTNAME}:*",   # Match with explicit port
]

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=allowed_hosts_list,
)

mcp = FastMCP(
    "MyMCPServer",
    stateless_http=True,
    transport_security=transport_security,
)
```

**Key Points:**
- No wildcard domain support (`*.onrender.com` won't work)
- Must include both `"hostname"` and `"hostname:*"` patterns
- Use environment variable for dynamic hostname resolution
- See `reference.md` for detailed troubleshooting and platform-specific examples

## Next Steps

1. Review `reference.md` for complete FastMCP API documentation
2. Check `examples.md` for full CRUD implementation examples
3. Use `templates.md` for copy-paste code templates
4. Read official docs: https://modelcontextprotocol.io/

## Related Skills

- **OpenAI Agents SDK with MCP Integration** - Building AI agents that use MCP tools
- **SQLModel ORM Patterns** - Advanced database modeling
- **Multi-Tenant Architecture** - User isolation strategies
- **Better Auth JWT Integration** - Extracting user context from JWTs
