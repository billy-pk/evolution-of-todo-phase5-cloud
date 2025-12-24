---
name: fastmcp-database-tools-examples
description: Complete working examples for MCP servers with database integration, including full CRUD implementation, testing, OpenAI agent integration, and production deployment.
---

# FastMCP Database Tools - Complete Examples

## Example 1: Complete CRUD MCP Server

This is a production-ready MCP server implementing full CRUD operations for a task management system.

### File Structure

```
backend/
├── tools/
│   └── server.py          # MCP server (this example)
├── models.py              # Database models
├── db.py                  # Database connection
└── .env                   # Environment variables
```

### models.py

```python
"""Database models using SQLModel."""

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional


class Task(SQLModel, table=True):
    """Task model for todo items."""

    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### db.py

```python
"""Database connection and session management."""

from sqlmodel import create_engine
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/tasks")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,              # Disable SQL logging
    pool_size=5,             # Maintain 5 connections
    max_overflow=10,         # Allow 10 additional connections
    pool_pre_ping=True       # Verify connections before use
)
```

### server.py - Complete Implementation

```python
"""
MCP Server for Task Operations

This module implements a production-ready MCP server using FastMCP
from the official MCP Python SDK. The server exposes tools for task
CRUD operations that AI agents can call.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server import FastMCP
from models import Task
from db import engine
from sqlmodel import Session, select
from pydantic import ValidationError
from uuid import UUID
from datetime import datetime, UTC


# Initialize FastMCP server with stateless HTTP transport
mcp = FastMCP(
    "TaskMCPServer",
    stateless_http=True,  # Scalable, no persistent connections
    json_response=True    # Return JSON instead of MCP protocol format
)


# ==================== Business Logic Functions ====================

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
    # Validate input parameters
    if not title or len(title.strip()) == 0:
        return {
            "status": "error",
            "error": "Title must be between 1 and 200 characters"
        }

    if len(title) > 200:
        return {
            "status": "error",
            "error": "Title must be between 1 and 200 characters"
        }

    if description and len(description) > 1000:
        return {
            "status": "error",
            "error": "Description must be 1000 characters or less"
        }

    if not user_id or len(user_id) > 255:
        return {
            "status": "error",
            "error": "User ID must be between 1 and 255 characters"
        }

    try:
        # Use provided session or create new one
        session = _session or Session(engine)

        # Create task
        task = Task(
            user_id=user_id,
            title=title.strip(),
            description=description
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Return success response
        result = {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "created_at": task.created_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except ValidationError as e:
        return {
            "status": "error",
            "error": f"Validation error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create task: {str(e)}"
        }


def list_tasks(user_id: str, status: str = "all", _session: Session = None) -> dict:
    """List tasks for a user, optionally filtered by completion status.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        status: Filter by status - "all", "pending", or "completed" (default: "all")
        _session: Optional database session (for testing)

    Returns:
        Dict with status and list of tasks
    """
    # Validate input parameters
    if not user_id or len(user_id) > 255:
        return {
            "status": "error",
            "error": "User ID must be between 1 and 255 characters"
        }

    if status not in ["all", "pending", "completed"]:
        return {
            "status": "error",
            "error": "Status must be 'all', 'pending', or 'completed'"
        }

    try:
        session = _session or Session(engine)

        # Build query
        statement = select(Task).where(Task.user_id == user_id)

        # Apply status filter
        if status == "pending":
            statement = statement.where(Task.completed == False)
        elif status == "completed":
            statement = statement.where(Task.completed == True)

        # Execute query
        tasks = session.exec(statement).all()

        # Format response
        tasks_data = [
            {
                "task_id": str(task.id),
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
        ]

        result = {
            "status": "success",
            "data": {
                "tasks": tasks_data
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list tasks: {str(e)}"
        }


def update_task(user_id: str, task_id: str, title: str = None, description: str = None, _session: Session = None) -> dict:
    """Update a task's title and/or description.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        title: New task title (optional, 1-200 characters)
        description: New task description (optional, max 1000 characters)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and updated task data
    """
    # Validate input parameters
    if not user_id or len(user_id) > 255:
        return {
            "status": "error",
            "error": "User ID must be between 1 and 255 characters"
        }

    if not title and description is None:
        return {
            "status": "error",
            "error": "Must provide at least title or description to update"
        }

    if title and len(title) > 200:
        return {
            "status": "error",
            "error": "Title must be 200 characters or less"
        }

    if description and len(description) > 1000:
        return {
            "status": "error",
            "error": "Description must be 1000 characters or less"
        }

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return {
            "status": "error",
            "error": "Invalid task ID format"
        }

    try:
        session = _session or Session(engine)

        # Find task
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {
                "status": "error",
                "error": "Task not found"
            }

        # Verify ownership
        if task.user_id != user_id:
            return {
                "status": "error",
                "error": "Unauthorized: Task does not belong to user"
            }

        # Update fields
        if title:
            task.title = title.strip()
        if description is not None:
            task.description = description
        task.updated_at = datetime.now(UTC)

        session.add(task)
        session.commit()
        session.refresh(task)

        result = {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "updated_at": task.updated_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to update task: {str(e)}"
        }


def complete_task(user_id: str, task_id: str, _session: Session = None) -> dict:
    """Mark a task as completed.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and updated task data
    """
    # Validate input parameters
    if not user_id or len(user_id) > 255:
        return {
            "status": "error",
            "error": "User ID must be between 1 and 255 characters"
        }

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return {
            "status": "error",
            "error": "Invalid task ID format"
        }

    try:
        session = _session or Session(engine)

        # Find task
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {
                "status": "error",
                "error": "Task not found"
            }

        # Verify ownership
        if task.user_id != user_id:
            return {
                "status": "error",
                "error": "Unauthorized: Task does not belong to user"
            }

        # Mark as completed
        task.completed = True
        task.updated_at = datetime.now(UTC)
        session.add(task)
        session.commit()
        session.refresh(task)

        result = {
            "status": "success",
            "data": {
                "task_id": str(task.id),
                "title": task.title,
                "completed": task.completed,
                "updated_at": task.updated_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to complete task: {str(e)}"
        }


def delete_task(user_id: str, task_id: str, _session: Session = None) -> dict:
    """Delete a task.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and deletion confirmation
    """
    # Validate input parameters
    if not user_id or len(user_id) > 255:
        return {
            "status": "error",
            "error": "User ID must be between 1 and 255 characters"
        }

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        return {
            "status": "error",
            "error": "Invalid task ID format"
        }

    try:
        session = _session or Session(engine)

        # Find task
        statement = select(Task).where(Task.id == task_uuid)
        task = session.exec(statement).first()

        if not task:
            return {
                "status": "error",
                "error": "Task not found"
            }

        # Verify ownership
        if task.user_id != user_id:
            return {
                "status": "error",
                "error": "Unauthorized: Task does not belong to user"
            }

        # Delete task
        session.delete(task)
        session.commit()

        result = {
            "status": "success",
            "data": {
                "task_id": str(task_uuid),
                "deleted": True
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to delete task: {str(e)}"
        }


# ==================== MCP Tool Wrappers ====================

@mcp.tool()
def add_task_tool(user_id: str, title: str, description: str = None) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)

    Returns:
        Dict with status and task data
    """
    return add_task(user_id, title, description)


@mcp.tool()
def list_tasks_tool(user_id: str, status: str = "all") -> dict:
    """List user's tasks with optional status filter.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        status: Filter by status - "all", "pending", or "completed" (default: "all")

    Returns:
        Dict with status and list of tasks
    """
    return list_tasks(user_id, status)


@mcp.tool()
def update_task_tool(user_id: str, task_id: str, title: str = None, description: str = None) -> dict:
    """Update a task's title and/or description.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        title: New task title (optional, 1-200 characters)
        description: New task description (optional, max 1000 characters)

    Returns:
        Dict with status and updated task data
    """
    return update_task(user_id, task_id, title, description)


@mcp.tool()
def complete_task_tool(user_id: str, task_id: str) -> dict:
    """Mark a task as completed.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)

    Returns:
        Dict with status and updated task data
    """
    return complete_task(user_id, task_id)


@mcp.tool()
def delete_task_tool(user_id: str, task_id: str) -> dict:
    """Delete a task.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)

    Returns:
        Dict with status and deletion confirmation
    """
    return delete_task(user_id, task_id)


# ==================== Server Entry Point ====================

if __name__ == "__main__":
    # Run MCP server on HTTP transport
    # This will start the server at http://localhost:8000/mcp
    mcp.run(transport="streamable-http")
```

### Running the Server

```bash
# Development
cd backend/tools
python server.py

# Production with uvicorn
uvicorn server:mcp.asgi_app --host 0.0.0.0 --port 8001 --workers 4
```

### Testing the Server

```bash
# Test with curl
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_task_tool",
    "arguments": {
      "user_id": "user123",
      "title": "Test Task",
      "description": "This is a test"
    }
  }'
```

---

## Example 2: Testing MCP Tools

### test_server.py

```python
"""Tests for MCP server tools."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from uuid import uuid4
from models import Task
from server import (
    add_task,
    list_tasks,
    update_task,
    complete_task,
    delete_task
)


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
        session.rollback()


def test_add_task_success(session):
    """Test successful task creation."""
    result = add_task("user123", "Buy groceries", "Milk and eggs", _session=session)

    assert result["status"] == "success"
    assert "task_id" in result["data"]
    assert result["data"]["title"] == "Buy groceries"
    assert result["data"]["description"] == "Milk and eggs"
    assert result["data"]["completed"] is False


def test_add_task_validation_empty_title(session):
    """Test validation error for empty title."""
    result = add_task("user123", "", _session=session)

    assert result["status"] == "error"
    assert "Title" in result["error"]


def test_add_task_validation_long_title(session):
    """Test validation error for title too long."""
    long_title = "x" * 201
    result = add_task("user123", long_title, _session=session)

    assert result["status"] == "error"
    assert "Title" in result["error"]


def test_list_tasks_empty(session):
    """Test listing tasks when none exist."""
    result = list_tasks("user123", _session=session)

    assert result["status"] == "success"
    assert result["data"]["tasks"] == []


def test_list_tasks_with_data(session):
    """Test listing tasks with existing data."""
    # Add tasks
    add_task("user123", "Task 1", _session=session)
    add_task("user123", "Task 2", _session=session)
    add_task("other_user", "Task 3", _session=session)

    # List tasks for user123
    result = list_tasks("user123", _session=session)

    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 2
    assert all(t["title"] in ["Task 1", "Task 2"] for t in result["data"]["tasks"])


def test_list_tasks_filter_pending(session):
    """Test listing only pending tasks."""
    # Add tasks
    task1 = add_task("user123", "Pending Task", _session=session)
    task2 = add_task("user123", "Completed Task", _session=session)

    # Complete second task
    complete_task("user123", task2["data"]["task_id"], _session=session)

    # List pending tasks
    result = list_tasks("user123", status="pending", _session=session)

    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 1
    assert result["data"]["tasks"][0]["title"] == "Pending Task"


def test_update_task_success(session):
    """Test successful task update."""
    # Create task
    create_result = add_task("user123", "Old Title", _session=session)
    task_id = create_result["data"]["task_id"]

    # Update task
    result = update_task("user123", task_id, title="New Title", _session=session)

    assert result["status"] == "success"
    assert result["data"]["title"] == "New Title"


def test_update_task_unauthorized(session):
    """Test updating task belonging to another user."""
    # User1 creates task
    create_result = add_task("user1", "Task", _session=session)
    task_id = create_result["data"]["task_id"]

    # User2 tries to update
    result = update_task("user2", task_id, title="Hacked", _session=session)

    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]


def test_complete_task_success(session):
    """Test marking task as completed."""
    # Create task
    create_result = add_task("user123", "Task", _session=session)
    task_id = create_result["data"]["task_id"]

    # Complete task
    result = complete_task("user123", task_id, _session=session)

    assert result["status"] == "success"
    assert result["data"]["completed"] is True


def test_delete_task_success(session):
    """Test deleting a task."""
    # Create task
    create_result = add_task("user123", "Task to delete", _session=session)
    task_id = create_result["data"]["task_id"]

    # Delete task
    result = delete_task("user123", task_id, _session=session)

    assert result["status"] == "success"
    assert result["data"]["deleted"] is True

    # Verify deletion
    list_result = list_tasks("user123", _session=session)
    assert len(list_result["data"]["tasks"]) == 0


def test_delete_task_not_found(session):
    """Test deleting non-existent task."""
    fake_id = str(uuid4())
    result = delete_task("user123", fake_id, _session=session)

    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_invalid_task_id_format(session):
    """Test operations with invalid UUID format."""
    result = complete_task("user123", "not-a-uuid", _session=session)

    assert result["status"] == "error"
    assert "Invalid task ID" in result["error"]
```

### Running Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run all tests
pytest test_server.py -v

# Run with coverage
pytest test_server.py --cov=server --cov-report=html
```

---

## Example 3: OpenAI Agent Integration

### agent.py

```python
"""OpenAI Agent with MCP tools."""

from openai_agents import Agent
from mcp.client import MCPServerStreamableHttp
import os


# Singleton MCP server instance (reuse across requests)
_mcp_server = None


async def get_mcp_server():
    """Get or create singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="Task MCP Server",
            params={
                "url": os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"),
                "timeout": 30
            },
            cache_tools_list=True,
            max_retry_attempts=3
        )
    return _mcp_server


async def create_task_agent(user_id: str):
    """Create an AI agent with task management tools.

    Args:
        user_id: Current user's ID for context

    Returns:
        Tuple of (agent, mcp_server)
    """
    server = await get_mcp_server()

    agent = Agent(
        name="TaskAssistant",
        instructions=f"""You are a helpful assistant that manages todo tasks for users.
        Current user ID: {user_id}

        IMPORTANT - Task ID Handling:
        - Task IDs are UUIDs (e.g., "550e8400-e29b-41d4-a716-446655440000")
        - Users refer to tasks by TITLE, not by ID
        - When updating/completing/deleting tasks:
          1. FIRST call list_tasks_tool to find the task by title
          2. THEN use the task_id from the results

        IMPORTANT - User Context:
        - ALWAYS pass user_id="{user_id}" to ALL tool calls
        - Users can only access their own tasks
        - Never use a different user_id

        Available Tools:
        - add_task_tool: Create new tasks
        - list_tasks_tool: List all tasks (or filter by status)
        - update_task_tool: Update task title/description
        - complete_task_tool: Mark task as done
        - delete_task_tool: Delete a task

        Response Style:
        - Be concise and friendly
        - Confirm actions clearly
        - If a task isn't found, ask the user to clarify
        """,
        mcp_servers=[server],
        model=os.getenv("OPENAI_MODEL", "gpt-4o")
    )

    return agent, server


# Example usage in FastAPI endpoint
async def chat_endpoint(user_id: str, message: str):
    """Handle chat message from user."""
    agent, server = await create_task_agent(user_id)

    async with server:
        result = await agent.run(message)
        return {"response": result}
```

### Example Conversations

**Creating a task:**
```
User: Create a task to buy groceries
Agent: [calls add_task_tool(user_id="user123", title="Buy groceries")]
Agent: I've created a task "Buy groceries" for you.
```

**Listing tasks:**
```
User: Show me my pending tasks
Agent: [calls list_tasks_tool(user_id="user123", status="pending")]
Agent: You have 3 pending tasks:
1. Buy groceries
2. Finish report
3. Call dentist
```

**Completing a task:**
```
User: Mark "Buy groceries" as done
Agent: [calls list_tasks_tool to find task ID]
Agent: [calls complete_task_tool(user_id="user123", task_id="550e8400...")]
Agent: Done! I've marked "Buy groceries" as completed.
```

---

## Example 4: Alternative Database Backends

### Using Raw SQLAlchemy

```python
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(255), index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    completed = Column(Boolean, default=False)

engine = create_engine("postgresql://localhost/tasks")
SessionLocal = sessionmaker(bind=engine)

def add_task(user_id: str, title: str):
    session = SessionLocal()
    try:
        task = Task(user_id=user_id, title=title)
        session.add(task)
        session.commit()
        return {"status": "success", "task_id": task.id}
    finally:
        session.close()
```

### Using Django ORM

```python
from django.db import models
from uuid import uuid4

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    user_id = models.CharField(max_length=255, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    class Meta:
        db_table = "tasks"

def add_task(user_id: str, title: str):
    try:
        task = Task.objects.create(user_id=user_id, title=title)
        return {
            "status": "success",
            "data": {"task_id": str(task.id), "title": task.title}
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

---

## Example 5: Production Deployment

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: tasks
      POSTGRES_USER: taskuser
      POSTGRES_PASSWORD: taskpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mcp_server:
    build: ./backend
    command: uvicorn tools.server:mcp.asgi_app --host 0.0.0.0 --port 8001
    environment:
      DATABASE_URL: postgresql://taskuser:taskpass@postgres:5432/tasks
    ports:
      - "8001:8001"
    depends_on:
      - postgres
    restart: always

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run server
CMD ["uvicorn", "tools.server:mcp.asgi_app", "--host", "0.0.0.0", "--port", "8001"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/mcp-server:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server
spec:
  selector:
    app: mcp-server
  ports:
  - port: 8001
    targetPort: 8001
  type: LoadBalancer
```

### Running in Production

```bash
# With Docker Compose
docker-compose up -d

# With Kubernetes
kubectl apply -f deployment.yaml

# Check status
kubectl get pods
kubectl logs -f deployment/mcp-server
```
