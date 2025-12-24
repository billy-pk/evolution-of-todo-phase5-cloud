"""
MCP Server for Task Operations

This module implements an MCP (Model Context Protocol) server using FastMCP
from the official MCP Python SDK. The server exposes tools for task operations
that the AI agent can call.

Architecture:
- Built with FastMCP (stateless HTTP server)
- Exposes tools via @mcp.tool() decorator
- Connects to PostgreSQL via SQLModel
- Used by OpenAI Agent via MCPServerStreamableHttp
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from mcp.server import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from models import Task
from db import engine
from sqlmodel import Session, select
from pydantic import ValidationError
from uuid import UUID
from datetime import datetime, UTC


# Configure transport security for production deployment
# NOTE: No wildcard domain support (*.onrender.com doesn't work)
# Must list exact hostnames. Include both with and without port.
# Dynamically get hostname from Render's RENDER_EXTERNAL_HOSTNAME or use default
RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "evolution-todo-mcp.onrender.com")

allowed_hosts_list = [
    "localhost",  # Exact match for localhost (no port)
    "localhost:*",  # localhost with any port
    "127.0.0.1",  # Exact match for loopback (no port)
    "127.0.0.1:*",  # loopback with any port
]

# Add Render hostname if available (both with and without port)
if RENDER_HOSTNAME:
    allowed_hosts_list.extend([
        RENDER_HOSTNAME,  # Exact match (HTTPS default port)
        f"{RENDER_HOSTNAME}:*",  # Match with explicit port
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

# Initialize FastMCP server with stateless HTTP transport
mcp = FastMCP(
    "TaskMCPServer",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",  # Path where MCP will be accessible
    transport_security=transport_security,
)


def add_task(user_id: str, title: str, description: str = None, _session: Session = None) -> dict:
    """Create a new task for the user. Returns the created task with its ID.

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
        if _session:
            # Create task
            task = Task(
                user_id=user_id,
                title=title.strip(),
                description=description
            )
            _session.add(task)
            _session.commit()
            _session.refresh(task)

            # Return success response
            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "created_at": task.created_at.isoformat()
                }
            }
        else:
            with Session(engine) as session:
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
                return {
                    "status": "success",
                    "data": {
                        "task_id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "created_at": task.created_at.isoformat()
                    }
                }
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
        # Use provided session or create new one
        if _session:
            # Build query
            statement = select(Task).where(Task.user_id == user_id)

            # Apply status filter
            if status == "pending":
                statement = statement.where(Task.completed == False)
            elif status == "completed":
                statement = statement.where(Task.completed == True)

            # Execute query
            tasks = _session.exec(statement).all()

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

            return {
                "status": "success",
                "data": {
                    "tasks": tasks_data
                }
            }
        else:
            with Session(engine) as session:
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

                return {
                    "status": "success",
                    "data": {
                        "tasks": tasks_data
                    }
                }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list tasks: {str(e)}"
        }


# Register the tools with MCP
@mcp.tool()
def add_task_tool(user_id: str, title: str, description: str = None) -> dict:
    """MCP tool wrapper for add_task. Create a new task for the user.

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
    """MCP tool wrapper for list_tasks. List user's tasks with optional status filter.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        status: Filter by status - "all", "pending", or "completed" (default: "all")

    Returns:
        Dict with status and list of tasks
    """
    return list_tasks(user_id, status)


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
        # Use provided session or create new one
        if _session:
            # Find task
            statement = select(Task).where(Task.id == task_uuid)
            task = _session.exec(statement).first()

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
            _session.add(task)
            _session.commit()
            _session.refresh(task)

            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "completed": task.completed,
                    "updated_at": task.updated_at.isoformat()
                }
            }
        else:
            with Session(engine) as session:
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

                return {
                    "status": "success",
                    "data": {
                        "task_id": str(task.id),
                        "title": task.title,
                        "completed": task.completed,
                        "updated_at": task.updated_at.isoformat()
                    }
                }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to complete task: {str(e)}"
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
        # Use provided session or create new one
        if _session:
            # Find task
            statement = select(Task).where(Task.id == task_uuid)
            task = _session.exec(statement).first()

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

            _session.add(task)
            _session.commit()
            _session.refresh(task)

            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "updated_at": task.updated_at.isoformat()
                }
            }
        else:
            with Session(engine) as session:
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

                return {
                    "status": "success",
                    "data": {
                        "task_id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "updated_at": task.updated_at.isoformat()
                    }
                }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to update task: {str(e)}"
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
        # Use provided session or create new one
        if _session:
            # Find task
            statement = select(Task).where(Task.id == task_uuid)
            task = _session.exec(statement).first()

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
            _session.delete(task)
            _session.commit()

            return {
                "status": "success",
                "data": {
                    "task_id": str(task_uuid),
                    "deleted": True
                }
            }
        else:
            with Session(engine) as session:
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

                return {
                    "status": "success",
                    "data": {
                        "task_id": str(task_uuid),
                        "deleted": True
                    }
                }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to delete task: {str(e)}"
        }


@mcp.tool()
def complete_task_tool(user_id: str, task_id: str) -> dict:
    """MCP tool wrapper for complete_task. Mark a task as completed.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)

    Returns:
        Dict with status and updated task data
    """
    return complete_task(user_id, task_id)


@mcp.tool()
def update_task_tool(user_id: str, task_id: str, title: str = None, description: str = None) -> dict:
    """MCP tool wrapper for update_task. Update a task's title and/or description.

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
def delete_task_tool(user_id: str, task_id: str) -> dict:
    """MCP tool wrapper for delete_task. Delete a task.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)

    Returns:
        Dict with status and deletion confirmation
    """
    return delete_task(user_id, task_id)
