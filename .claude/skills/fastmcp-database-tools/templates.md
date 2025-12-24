---
name: fastmcp-database-tools-templates
description: Ready-to-use code templates for MCP server setup, CRUD operations, database models, testing, agent integration, and production deployment configurations.
---

# FastMCP Database Tools - Code Templates

## Template 1: Basic MCP Server Setup

Copy this template to quickly set up a new MCP server.

```python
"""
MCP Server Template

Replace [YOUR_DOMAIN] with your domain (e.g., tasks, users, products)
Replace [YOUR_MODEL] with your SQLModel model class
"""

from mcp.server import FastMCP
from sqlmodel import Session, select
from db import engine
from models import [YOUR_MODEL]
from uuid import UUID

# Initialize FastMCP server
mcp = FastMCP(
    "[YOUR_DOMAIN]MCPServer",
    stateless_http=True,
    json_response=True
)


# Business logic function template
def sample_operation(user_id: str, param: str, _session: Session = None) -> dict:
    """Sample operation description.

    Args:
        user_id: User ID from authentication
        param: Description of parameter
        _session: Optional database session (for testing)

    Returns:
        Dict with status and data
    """
    # Validate inputs
    if not param or len(param) == 0:
        return {"status": "error", "error": "Parameter required"}

    try:
        session = _session or Session(engine)

        # Your database operation here
        # ...

        result = {
            "status": "success",
            "data": {}
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"Operation failed: {str(e)}"}


# MCP tool wrapper template
@mcp.tool()
def sample_tool(user_id: str, param: str) -> dict:
    """Tool description for the LLM.

    Args:
        user_id: User ID from authentication
        param: Description of parameter

    Returns:
        Operation result
    """
    return sample_operation(user_id, param)


# Server entry point
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## Template 2: CRUD Operations Set

Complete CRUD template for a new resource.

```python
"""CRUD Operations Template"""

from sqlmodel import Session, select
from models import [YOUR_MODEL]
from db import engine
from uuid import UUID
from datetime import datetime, UTC


# ==================== CREATE ====================

def create_[resource](user_id: str, field1: str, field2: str = None, _session: Session = None) -> dict:
    """Create a new [resource].

    Args:
        user_id: User ID (1-255 characters)
        field1: Required field (1-200 characters)
        field2: Optional field (max 1000 characters)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and created resource
    """
    # Validate inputs
    if not field1 or len(field1.strip()) == 0:
        return {"status": "error", "error": "Field1 is required"}

    if len(field1) > 200:
        return {"status": "error", "error": "Field1 too long (max 200 chars)"}

    if field2 and len(field2) > 1000:
        return {"status": "error", "error": "Field2 too long (max 1000 chars)"}

    try:
        session = _session or Session(engine)

        # Create record
        record = [YOUR_MODEL](
            user_id=user_id,
            field1=field1.strip(),
            field2=field2
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        result = {
            "status": "success",
            "data": {
                "id": str(record.id),
                "field1": record.field1,
                "field2": record.field2,
                "created_at": record.created_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"Create failed: {str(e)}"}


# ==================== READ (List) ====================

def list_[resources](user_id: str, filter_param: str = "all", _session: Session = None) -> dict:
    """List all [resources] for a user with optional filtering.

    Args:
        user_id: User ID (1-255 characters)
        filter_param: Filter value (default: "all")
        _session: Optional database session (for testing)

    Returns:
        Dict with status and list of resources
    """
    # Validate inputs
    if not user_id or len(user_id) > 255:
        return {"status": "error", "error": "Invalid user_id"}

    ALLOWED_FILTERS = ["all", "value1", "value2"]
    if filter_param not in ALLOWED_FILTERS:
        return {"status": "error", "error": f"Filter must be one of: {ALLOWED_FILTERS}"}

    try:
        session = _session or Session(engine)

        # Build query
        statement = select([YOUR_MODEL]).where([YOUR_MODEL].user_id == user_id)

        # Apply filters
        if filter_param == "value1":
            statement = statement.where([YOUR_MODEL].some_field == "value1")
        elif filter_param == "value2":
            statement = statement.where([YOUR_MODEL].some_field == "value2")

        # Execute query
        records = session.exec(statement).all()

        # Format response
        data = [
            {
                "id": str(record.id),
                "field1": record.field1,
                "field2": record.field2,
                "created_at": record.created_at.isoformat()
            }
            for record in records
        ]

        result = {
            "status": "success",
            "data": {"items": data, "count": len(data)}
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"List failed: {str(e)}"}


# ==================== READ (Single) ====================

def get_[resource](user_id: str, resource_id: str, _session: Session = None) -> dict:
    """Get a single [resource] by ID.

    Args:
        user_id: User ID (1-255 characters)
        resource_id: Resource ID (UUID string)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and resource data
    """
    # Validate inputs
    if not user_id or len(user_id) > 255:
        return {"status": "error", "error": "Invalid user_id"}

    try:
        uuid = UUID(resource_id)
    except ValueError:
        return {"status": "error", "error": "Invalid resource ID format"}

    try:
        session = _session or Session(engine)

        # Find record
        statement = select([YOUR_MODEL]).where([YOUR_MODEL].id == uuid)
        record = session.exec(statement).first()

        if not record:
            return {"status": "error", "error": "Resource not found"}

        # Verify ownership
        if record.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        result = {
            "status": "success",
            "data": {
                "id": str(record.id),
                "field1": record.field1,
                "field2": record.field2,
                "created_at": record.created_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"Get failed: {str(e)}"}


# ==================== UPDATE ====================

def update_[resource](user_id: str, resource_id: str, field1: str = None, field2: str = None, _session: Session = None) -> dict:
    """Update a [resource]'s fields.

    Args:
        user_id: User ID (1-255 characters)
        resource_id: Resource ID (UUID string)
        field1: New value for field1 (optional, 1-200 characters)
        field2: New value for field2 (optional, max 1000 characters)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and updated resource
    """
    # Validate inputs
    if not user_id or len(user_id) > 255:
        return {"status": "error", "error": "Invalid user_id"}

    if not field1 and field2 is None:
        return {"status": "error", "error": "Must provide at least one field to update"}

    if field1 and len(field1) > 200:
        return {"status": "error", "error": "Field1 too long"}

    if field2 and len(field2) > 1000:
        return {"status": "error", "error": "Field2 too long"}

    try:
        uuid = UUID(resource_id)
    except ValueError:
        return {"status": "error", "error": "Invalid resource ID format"}

    try:
        session = _session or Session(engine)

        # Find record
        statement = select([YOUR_MODEL]).where([YOUR_MODEL].id == uuid)
        record = session.exec(statement).first()

        if not record:
            return {"status": "error", "error": "Resource not found"}

        # Verify ownership
        if record.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        # Update fields
        if field1:
            record.field1 = field1.strip()
        if field2 is not None:
            record.field2 = field2
        record.updated_at = datetime.now(UTC)

        session.add(record)
        session.commit()
        session.refresh(record)

        result = {
            "status": "success",
            "data": {
                "id": str(record.id),
                "field1": record.field1,
                "field2": record.field2,
                "updated_at": record.updated_at.isoformat()
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"Update failed: {str(e)}"}


# ==================== DELETE ====================

def delete_[resource](user_id: str, resource_id: str, _session: Session = None) -> dict:
    """Delete a [resource].

    Args:
        user_id: User ID (1-255 characters)
        resource_id: Resource ID (UUID string)
        _session: Optional database session (for testing)

    Returns:
        Dict with status and deletion confirmation
    """
    # Validate inputs
    if not user_id or len(user_id) > 255:
        return {"status": "error", "error": "Invalid user_id"}

    try:
        uuid = UUID(resource_id)
    except ValueError:
        return {"status": "error", "error": "Invalid resource ID format"}

    try:
        session = _session or Session(engine)

        # Find record
        statement = select([YOUR_MODEL]).where([YOUR_MODEL].id == uuid)
        record = session.exec(statement).first()

        if not record:
            return {"status": "error", "error": "Resource not found"}

        # Verify ownership
        if record.user_id != user_id:
            return {"status": "error", "error": "Unauthorized"}

        # Delete record
        session.delete(record)
        session.commit()

        result = {
            "status": "success",
            "data": {
                "id": str(uuid),
                "deleted": True
            }
        }

        if not _session:
            session.close()

        return result

    except Exception as e:
        return {"status": "error", "error": f"Delete failed: {str(e)}"}
```

---

## Template 3: SQLModel Model Definition

```python
"""SQLModel Model Template"""

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional


class [YourModel](SQLModel, table=True):
    """[Model description]"""

    __tablename__ = "[table_name]"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # User isolation (always include for multi-tenant)
    user_id: str = Field(max_length=255, index=True, nullable=False)

    # Required fields
    required_field: str = Field(max_length=200, nullable=False)

    # Optional fields
    optional_field: Optional[str] = Field(default=None, max_length=1000)

    # Boolean flags
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Indexes (for frequently queried fields)
    # Add this for composite indexes:
    # __table_args__ = (
    #     Index('idx_user_active', 'user_id', 'is_active'),
    # )
```

---

## Template 4: Database Configuration

```python
"""Database Configuration Template"""

from sqlmodel import create_engine, Session
import os
from contextlib import contextmanager


# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/dbname"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,              # Set to True for SQL logging during development
    pool_size=5,             # Number of connections to maintain
    max_overflow=10,         # Additional connections when pool is full
    pool_pre_ping=True,      # Verify connections before use (prevents stale connections)
    pool_recycle=3600        # Recycle connections after 1 hour
)


# Context manager for database sessions
@contextmanager
def get_session():
    """Context manager for database sessions."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# Usage example:
# with get_session() as session:
#     task = Task(user_id="123", title="Example")
#     session.add(task)
```

---

## Template 5: Test Suite

```python
"""Test Suite Template"""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from uuid import uuid4
from models import [YOUR_MODEL]
from server import [your_functions]


# ==================== Fixtures ====================

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


@pytest.fixture(scope="function")
def sample_record(session):
    """Create a sample record for testing."""
    record = [YOUR_MODEL](
        user_id="test_user",
        field1="Test Value"
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


# ==================== Success Tests ====================

def test_create_success(session):
    """Test successful record creation."""
    result = create_[resource]("user123", "Test", _session=session)

    assert result["status"] == "success"
    assert "id" in result["data"]
    assert result["data"]["field1"] == "Test"


def test_list_success(session, sample_record):
    """Test successful list operation."""
    result = list_[resources]("test_user", _session=session)

    assert result["status"] == "success"
    assert len(result["data"]["items"]) == 1


def test_get_success(session, sample_record):
    """Test successful get operation."""
    result = get_[resource]("test_user", str(sample_record.id), _session=session)

    assert result["status"] == "success"
    assert result["data"]["id"] == str(sample_record.id)


def test_update_success(session, sample_record):
    """Test successful update operation."""
    result = update_[resource](
        "test_user",
        str(sample_record.id),
        field1="Updated",
        _session=session
    )

    assert result["status"] == "success"
    assert result["data"]["field1"] == "Updated"


def test_delete_success(session, sample_record):
    """Test successful delete operation."""
    result = delete_[resource]("test_user", str(sample_record.id), _session=session)

    assert result["status"] == "success"
    assert result["data"]["deleted"] is True


# ==================== Validation Tests ====================

def test_create_validation_empty_field(session):
    """Test validation error for empty required field."""
    result = create_[resource]("user123", "", _session=session)

    assert result["status"] == "error"
    assert "required" in result["error"].lower()


def test_create_validation_too_long(session):
    """Test validation error for field too long."""
    long_value = "x" * 201
    result = create_[resource]("user123", long_value, _session=session)

    assert result["status"] == "error"
    assert "too long" in result["error"].lower()


def test_invalid_uuid_format(session):
    """Test operations with invalid UUID format."""
    result = get_[resource]("user123", "not-a-uuid", _session=session)

    assert result["status"] == "error"
    assert "Invalid" in result["error"]


# ==================== Authorization Tests ====================

def test_unauthorized_access(session, sample_record):
    """Test accessing record belonging to another user."""
    result = get_[resource]("other_user", str(sample_record.id), _session=session)

    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]


def test_unauthorized_update(session, sample_record):
    """Test updating record belonging to another user."""
    result = update_[resource](
        "other_user",
        str(sample_record.id),
        field1="Hacked",
        _session=session
    )

    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]


def test_unauthorized_delete(session, sample_record):
    """Test deleting record belonging to another user."""
    result = delete_[resource]("other_user", str(sample_record.id), _session=session)

    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]


# ==================== Edge Case Tests ====================

def test_not_found(session):
    """Test operations on non-existent record."""
    fake_id = str(uuid4())
    result = get_[resource]("user123", fake_id, _session=session)

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


def test_list_empty(session):
    """Test listing when no records exist."""
    result = list_[resources]("user123", _session=session)

    assert result["status"] == "success"
    assert len(result["data"]["items"]) == 0


def test_update_no_fields(session, sample_record):
    """Test update with no fields provided."""
    result = update_[resource]("test_user", str(sample_record.id), _session=session)

    assert result["status"] == "error"
    assert "Must provide" in result["error"]
```

---

## Template 6: Agent Integration

```python
"""OpenAI Agent Integration Template"""

from openai_agents import Agent
from mcp.client import MCPServerStreamableHttp
import os


# Singleton MCP server instance
_mcp_server = None


async def get_mcp_server():
    """Get or create singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServerStreamableHttp(
            name="[Your Domain] MCP Server",
            params={
                "url": os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"),
                "timeout": 30
            },
            cache_tools_list=True,
            max_retry_attempts=3
        )
    return _mcp_server


async def create_agent(user_id: str):
    """Create an AI agent with MCP tools.

    Args:
        user_id: Current user's ID for context

    Returns:
        Tuple of (agent, mcp_server)
    """
    server = await get_mcp_server()

    agent = Agent(
        name="[YourAssistant]",
        instructions=f"""You are a helpful assistant that [does something] for users.
        Current user ID: {user_id}

        IMPORTANT - ID Handling:
        - IDs are UUIDs (e.g., "550e8400-e29b-41d4-a716-446655440000")
        - Users refer to items by NAME/TITLE, not by ID
        - When updating/deleting items:
          1. FIRST call list_[resources]_tool to find the item
          2. THEN use the ID from the results

        IMPORTANT - User Context:
        - ALWAYS pass user_id="{user_id}" to ALL tool calls
        - Users can only access their own data
        - Never use a different user_id

        Available Tools:
        - create_[resource]_tool: Create new items
        - list_[resources]_tool: List all items (with optional filters)
        - get_[resource]_tool: Get a single item by ID
        - update_[resource]_tool: Update item fields
        - delete_[resource]_tool: Delete an item

        Response Style:
        - Be concise and friendly
        - Confirm actions clearly
        - If an item isn't found, ask the user to clarify
        - Provide helpful suggestions when appropriate
        """,
        mcp_servers=[server],
        model=os.getenv("OPENAI_MODEL", "gpt-4o")
    )

    return agent, server


# Usage in endpoint
async def handle_message(user_id: str, message: str):
    """Handle user message with AI agent.

    Args:
        user_id: Current user's ID
        message: User's message

    Returns:
        Agent's response
    """
    agent, server = await create_agent(user_id)

    async with server:
        result = await agent.run(message)
        return {"response": result}
```

---

## Template 7: Production Deployment Configuration

### .env.production

```bash
# Database
DATABASE_URL=postgresql://user:password@db.example.com:5432/production_db

# MCP Server
MCP_SERVER_URL=http://mcp-server:8001/mcp
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8001

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
RATE_LIMIT_PER_MINUTE=100
```

### systemd Service File

```ini
[Unit]
Description=MCP Server - [Your Domain]
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/app
EnvironmentFile=/app/.env.production

# Run with uvicorn
ExecStart=/usr/bin/uvicorn server:mcp.asgi_app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 4 \
    --log-level info

# Restart configuration
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/app/logs

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
upstream mcp_server {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name mcp.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # MCP endpoint
    location /mcp {
        proxy_pass http://mcp_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://mcp_server;
        access_log off;
    }
}
```

---

## Template 8: Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')"

# Run server
CMD ["uvicorn", "server:mcp.asgi_app", "--host", "0.0.0.0", "--port", "8001"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-myapp}
      POSTGRES_USER: ${DB_USER:-myuser}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-mypassword}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-myuser}"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp_server:
    build: .
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql://${DB_USER:-myuser}:${DB_PASSWORD:-mypassword}@postgres:5432/${DB_NAME:-myapp}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
```

---

## Quick Copy-Paste Snippets

### Input Validation

```python
# String validation
if not value or len(value.strip()) == 0:
    return {"status": "error", "error": "Value required"}

if len(value) > MAX_LENGTH:
    return {"status": "error", "error": f"Value too long (max {MAX_LENGTH})"}

# UUID validation
try:
    uuid = UUID(id_string)
except ValueError:
    return {"status": "error", "error": "Invalid ID format"}

# Enum validation
ALLOWED_VALUES = ["value1", "value2", "value3"]
if value not in ALLOWED_VALUES:
    return {"status": "error", "error": f"Must be one of: {', '.join(ALLOWED_VALUES)}"}
```

### User Isolation Check

```python
# Find record
record = session.exec(select(Model).where(Model.id == uuid)).first()

if not record:
    return {"status": "error", "error": "Not found"}

# Verify ownership
if record.user_id != user_id:
    return {"status": "error", "error": "Unauthorized"}
```

### Session Management

```python
# With context manager
with Session(engine) as session:
    # operations
    session.commit()

# With dependency injection (for testing)
session = _session or Session(engine)
try:
    # operations
    session.commit()
finally:
    if not _session:
        session.close()
```

### Error Response

```python
# Standard error format
return {
    "status": "error",
    "error": "Human-readable error message"
}

# Standard success format
return {
    "status": "success",
    "data": {
        # your data here
    }
}
```
