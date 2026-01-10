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
from models import Task, RecurrenceRule, Reminder
from db import engine
from sqlmodel import Session, select
from pydantic import ValidationError
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional
from services.recurrence_service import RecurrenceService
from services.reminder_service import ReminderService
from dapr.clients import DaprClient
import json


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
    "mcp-server",  # Kubernetes service name
    "mcp-server:*", # Kubernetes service with port
]

# Add hosts from environment variable if provided (comma-separated)
env_hosts = os.environ.get("ALLOWED_HOSTS")
if env_hosts:
    for host in env_hosts.split(","):
        host = host.strip()
        if host:
            allowed_hosts_list.append(host)
            if ":" not in host:
                allowed_hosts_list.append(f"{host}:*")

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


def schedule_reminder_job(
    reminder_id: str,
    task_id: str,
    user_id: str,
    task_title: str,
    reminder_time: datetime
) -> bool:
    """
    Schedule a reminder job via Dapr Jobs API.

    Args:
        reminder_id: UUID of the Reminder record
        task_id: UUID of the Task
        user_id: User ID for isolation
        task_title: Task title for notification content
        reminder_time: When to trigger the reminder (timezone-aware datetime)

    Returns:
        bool: True if scheduling succeeded, False otherwise

    Dapr Jobs API will invoke the Notification Service at the scheduled time.
    The job payload includes all context needed for reminder delivery.
    """
    try:
        with DaprClient() as dapr:
            # Schedule time must be ISO8601 string
            schedule_time = reminder_time.isoformat()

            # Job payload for Notification Service
            job_data = {
                "reminder_id": reminder_id,
                "task_id": task_id,
                "user_id": user_id,
                "task_title": task_title,
                "reminder_time": schedule_time
            }

            # Schedule job via Dapr Jobs API
            # Job name must be unique - use reminder_id
            dapr.schedule_job(
                job_name=f"reminder-{reminder_id}",
                schedule=schedule_time,  # One-time schedule (ISO8601)
                data=json.dumps(job_data),
                metadata={
                    "ttl": "1h",  # Job expires 1 hour after scheduled time if not delivered
                }
            )

            return True

    except Exception as e:
        # Log error but don't fail task creation - reminder in DB can be rescheduled
        print(f"Warning: Failed to schedule reminder job via Dapr: {str(e)}")
        return False


def add_task(
    user_id: str,
    title: str,
    description: str = None,
    recurrence_pattern: Optional[str] = None,
    recurrence_interval: Optional[int] = None,
    due_date: Optional[str] = None,
    reminder_offset: Optional[str] = None,
    priority: str = "normal",
    tags: Optional[list] = None,
    _session: Session = None
) -> dict:
    """Create a new task for the user. Returns the created task with its ID.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)
        recurrence_pattern: Optional recurrence pattern ("daily", "weekly", "monthly")
        recurrence_interval: Optional recurrence interval (e.g., 2 for bi-weekly)
        due_date: Optional due date (ISO8601 format)
        reminder_offset: Optional reminder offset (e.g., "1 hour before", "30 minutes before", "1 day before")
        priority: Task priority ("low", "normal", "high", "critical", default: "normal")
        tags: Optional list of tags
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

    # Validate priority
    if priority not in ["low", "normal", "high", "critical"]:
        return {
            "status": "error",
            "error": "Priority must be one of: low, normal, high, critical"
        }

    # Default recurrence_interval to 1 if pattern provided but interval missing
    if recurrence_pattern and recurrence_interval is None:
        recurrence_interval = 1

    # Validate recurrence parameters
    if recurrence_pattern and not recurrence_interval:
        # Should not happen due to default above, but keeping for safety
        return {
            "status": "error",
            "error": "recurrence_interval is required when recurrence_pattern is specified"
        }

    if recurrence_interval and not recurrence_pattern:
        return {
            "status": "error",
            "error": "recurrence_pattern is required when recurrence_interval is specified"
        }

    # Validate recurrence pattern using RecurrenceService
    if recurrence_pattern:
        try:
            RecurrenceService.validate_recurrence_pattern(recurrence_pattern, recurrence_interval)
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # Validate tags (max 10 tags, max 50 chars each)
    if tags:
        if len(tags) > 10:
            return {
                "status": "error",
                "error": "Maximum 10 tags allowed"
            }
        for tag in tags:
            if len(tag) > 50:
                return {
                    "status": "error",
                    "error": "Each tag must be 50 characters or less"
                }

    # Normalize tags (case-insensitive)
    normalized_tags = [tag.lower() for tag in tags] if tags else None

    # Parse due_date if provided
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except ValueError:
            return {
                "status": "error",
                "error": "Invalid due_date format. Use ISO8601 format (e.g., '2026-01-10T17:00:00Z')"
            }

    # Validate reminder_offset
    if reminder_offset:
        # Reminder requires due_date to be set
        if not due_date:
            return {
                "status": "error",
                "error": "reminder_offset requires due_date to be specified"
            }

        # Validate reminder_offset format (basic validation - detailed parsing in ReminderService)
        # Expected formats: "1 hour before", "30 minutes before", "1 day before"
        valid_patterns = ["hour before", "hours before", "minute before", "minutes before", "day before", "days before"]
        if not any(pattern in reminder_offset.lower() for pattern in valid_patterns):
            return {
                "status": "error",
                "error": "Invalid reminder_offset format. Use format like '1 hour before', '30 minutes before', or '1 day before'"
            }

    try:
        # Use provided session or create new one
        if _session:
            # Create RecurrenceRule if recurrence specified
            recurrence_rule_id = None
            if recurrence_pattern:
                metadata = RecurrenceService.create_recurrence_metadata(
                    pattern=recurrence_pattern,
                    current_date=parsed_due_date or datetime.now(UTC)
                )
                recurrence_rule = RecurrenceRule(
                    id=uuid4(),
                    pattern=recurrence_pattern,
                    interval=recurrence_interval,
                    metadata=metadata
                )
                _session.add(recurrence_rule)
                _session.flush()  # Get ID without committing
                recurrence_rule_id = recurrence_rule.id

            # Create task
            task = Task(
                user_id=user_id,
                title=title.strip(),
                description=description,
                priority=priority,
                tags=normalized_tags,
                due_date=parsed_due_date,
                recurrence_id=recurrence_rule_id
            )
            _session.add(task)
            _session.flush()  # Get task ID without committing

            # Create Reminder if reminder_offset specified
            reminder_id = None
            reminder_scheduled = False
            if reminder_offset and parsed_due_date:
                # Parse reminder offset
                offset = ReminderService.parse_reminder_offset(reminder_offset)
                if offset:
                    # Calculate reminder time
                    reminder_time = ReminderService.calculate_reminder_time(parsed_due_date, offset)

                    # Validate reminder time is in the future
                    is_valid, error_msg = ReminderService.validate_reminder_offset(reminder_offset, parsed_due_date)
                    if is_valid:
                        # Create Reminder record
                        reminder = Reminder(
                            id=uuid4(),
                            task_id=task.id,
                            user_id=user_id,
                            reminder_time=reminder_time,
                            status="pending",
                            delivery_method="webhook"
                        )
                        _session.add(reminder)
                        _session.flush()  # Get reminder ID
                        reminder_id = reminder.id

                        # Commit both task and reminder
                        _session.commit()
                        _session.refresh(task)
                        _session.refresh(reminder)

                        # Schedule reminder via Dapr Jobs API
                        reminder_scheduled = schedule_reminder_job(
                            reminder_id=str(reminder.id),
                            task_id=str(task.id),
                            user_id=user_id,
                            task_title=task.title,
                            reminder_time=reminder_time
                        )
                    else:
                        # Invalid reminder time - skip reminder creation but create task
                        _session.commit()
                        _session.refresh(task)
                else:
                    # Invalid offset format - skip reminder creation but create task
                    _session.commit()
                    _session.refresh(task)
            else:
                # No reminder - just commit task
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
                    "priority": task.priority,
                    "tags": task.tags,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "reminder_offset": reminder_offset,
                    "recurrence_id": str(task.recurrence_id) if task.recurrence_id else None,
                    "recurrence_pattern": recurrence_pattern,
                    "recurrence_interval": recurrence_interval,
                    "created_at": task.created_at.isoformat()
                }
            }
        else:
            with Session(engine) as session:
                # Create RecurrenceRule if recurrence specified
                recurrence_rule_id = None
                if recurrence_pattern:
                    metadata = RecurrenceService.create_recurrence_metadata(
                        pattern=recurrence_pattern,
                        current_date=parsed_due_date or datetime.now(UTC)
                    )
                    recurrence_rule = RecurrenceRule(
                        id=uuid4(),
                        pattern=recurrence_pattern,
                        interval=recurrence_interval,
                        metadata=metadata
                    )
                    session.add(recurrence_rule)
                    session.flush()  # Get ID without committing
                    recurrence_rule_id = recurrence_rule.id

                # Create task
                task = Task(
                    user_id=user_id,
                    title=title.strip(),
                    description=description,
                    priority=priority,
                    tags=normalized_tags,
                    due_date=parsed_due_date,
                    recurrence_id=recurrence_rule_id
                )
                session.add(task)
                session.flush()  # Get task ID without committing

                # Create Reminder if reminder_offset specified
                reminder_id = None
                reminder_scheduled = False
                if reminder_offset and parsed_due_date:
                    # Parse reminder offset
                    offset = ReminderService.parse_reminder_offset(reminder_offset)
                    if offset:
                        # Calculate reminder time
                        reminder_time = ReminderService.calculate_reminder_time(parsed_due_date, offset)

                        # Validate reminder time is in the future
                        is_valid, error_msg = ReminderService.validate_reminder_offset(reminder_offset, parsed_due_date)
                        if is_valid:
                            # Create Reminder record
                            reminder = Reminder(
                                id=uuid4(),
                                task_id=task.id,
                                user_id=user_id,
                                reminder_time=reminder_time,
                                status="pending",
                                delivery_method="webhook"
                            )
                            session.add(reminder)
                            session.flush()  # Get reminder ID
                            reminder_id = reminder.id

                            # Commit both task and reminder
                            session.commit()
                            session.refresh(task)
                            session.refresh(reminder)

                            # Schedule reminder via Dapr Jobs API
                            reminder_scheduled = schedule_reminder_job(
                                reminder_id=str(reminder.id),
                                task_id=str(task.id),
                                user_id=user_id,
                                task_title=task.title,
                                reminder_time=reminder_time
                            )
                        else:
                            # Invalid reminder time - skip reminder creation but create task
                            session.commit()
                            session.refresh(task)
                    else:
                        # Invalid offset format - skip reminder creation but create task
                        session.commit()
                        session.refresh(task)
                else:
                    # No reminder - just commit task
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
                        "priority": task.priority,
                        "tags": task.tags,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "reminder_offset": reminder_offset,
                        "recurrence_id": str(task.recurrence_id) if task.recurrence_id else None,
                        "recurrence_pattern": recurrence_pattern,
                        "recurrence_interval": recurrence_interval,
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
def add_task_tool(
    user_id: str,
    title: str,
    description: str = None,
    recurrence_pattern: Optional[str] = None,
    recurrence_interval: Optional[int] = None,
    due_date: Optional[str] = None,
    reminder_offset: Optional[str] = None,
    priority: str = "normal",
    tags: Optional[list] = None
) -> dict:
    """MCP tool wrapper for add_task. Create a new task for the user with optional recurrence and reminders.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        title: Task title (required, 1-200 characters)
        description: Optional task description (max 1000 characters)
        recurrence_pattern: Optional recurrence pattern ("daily", "weekly", "monthly")
        recurrence_interval: Optional recurrence interval (e.g., 1 for daily, 2 for bi-weekly)
        due_date: Optional due date in ISO8601 format (e.g., "2026-01-10T17:00:00Z")
        reminder_offset: Optional reminder offset (e.g., "1 hour before", "30 minutes before", "1 day before")
        priority: Task priority ("low", "normal", "high", "critical", default: "normal")
        tags: Optional list of tags for categorization

    Returns:
        Dict with status and task data including recurrence and reminder details if applicable

    Example:
        # Create a task with reminder
        add_task_tool(
            user_id="user-123",
            title="Submit quarterly report",
            due_date="2026-01-13T17:00:00Z",
            reminder_offset="1 hour before",
            priority="high",
            tags=["work", "urgent"]
        )
    """
    return add_task(
        user_id=user_id,
        title=title,
        description=description,
        recurrence_pattern=recurrence_pattern,
        recurrence_interval=recurrence_interval,
        due_date=due_date,
        reminder_offset=reminder_offset,
        priority=priority,
        tags=tags
    )


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


def update_task(
    user_id: str,
    task_id: str,
    title: str = None,
    description: str = None,
    recurrence_pattern: Optional[str] = None,
    recurrence_interval: Optional[int] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[list] = None,
    _session: Session = None
) -> dict:
    """Update a task's fields including recurrence rules.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        title: New task title (optional, 1-200 characters)
        description: New task description (optional, max 1000 characters)
        recurrence_pattern: Update recurrence pattern ("daily", "weekly", "monthly", or None to remove)
        recurrence_interval: Update recurrence interval (required if recurrence_pattern specified)
        due_date: Update due date (ISO8601 format)
        priority: Update priority ("low", "normal", "high", "critical")
        tags: Update tags (list of strings, replaces existing tags)
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

    # Must provide at least one field to update
    if not any([title, description is not None, recurrence_pattern is not None,
                recurrence_interval is not None, due_date, priority, tags is not None]):
        return {
            "status": "error",
            "error": "Must provide at least one field to update"
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

    # Validate priority
    if priority and priority not in ["low", "normal", "high", "critical"]:
        return {
            "status": "error",
            "error": "Priority must be one of: low, normal, high, critical"
        }

    # Default recurrence_interval to 1 if pattern provided but interval missing
    if recurrence_pattern and recurrence_interval is None:
        recurrence_interval = 1

    # Validate recurrence parameters
    if recurrence_pattern and not recurrence_interval:
        # Should not happen due to default above, but keeping for safety
        return {
            "status": "error",
            "error": "recurrence_interval is required when recurrence_pattern is specified"
        }

    if recurrence_interval and not recurrence_pattern:
        return {
            "status": "error",
            "error": "recurrence_pattern is required when recurrence_interval is specified"
        }

    # Validate recurrence pattern using RecurrenceService
    if recurrence_pattern:
        try:
            RecurrenceService.validate_recurrence_pattern(recurrence_pattern, recurrence_interval)
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e)
            }

    # Validate tags (max 10 tags, max 50 chars each)
    if tags is not None:
        if len(tags) > 10:
            return {
                "status": "error",
                "error": "Maximum 10 tags allowed"
            }
        for tag in tags:
            if len(tag) > 50:
                return {
                    "status": "error",
                    "error": "Each tag must be 50 characters or less"
                }

    # Normalize tags (case-insensitive)
    normalized_tags = [tag.lower() for tag in tags] if tags is not None else None

    # Parse due_date if provided
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except ValueError:
            return {
                "status": "error",
                "error": "Invalid due_date format. Use ISO8601 format (e.g., '2026-01-10T17:00:00Z')"
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

            # Handle recurrence rule updates
            if recurrence_pattern is not None or recurrence_interval is not None:
                if recurrence_pattern and recurrence_interval:
                    # Update or create RecurrenceRule
                    if task.recurrence_id:
                        # Update existing RecurrenceRule
                        statement = select(RecurrenceRule).where(RecurrenceRule.id == task.recurrence_id)
                        recurrence_rule = _session.exec(statement).first()
                        if recurrence_rule:
                            recurrence_rule.pattern = recurrence_pattern
                            recurrence_rule.interval = recurrence_interval
                            recurrence_rule.metadata = RecurrenceService.create_recurrence_metadata(
                                pattern=recurrence_pattern,
                                current_date=parsed_due_date or task.due_date or datetime.now(UTC)
                            )
                            _session.add(recurrence_rule)
                    else:
                        # Create new RecurrenceRule
                        metadata = RecurrenceService.create_recurrence_metadata(
                            pattern=recurrence_pattern,
                            current_date=parsed_due_date or task.due_date or datetime.now(UTC)
                        )
                        recurrence_rule = RecurrenceRule(
                            id=uuid4(),
                            pattern=recurrence_pattern,
                            interval=recurrence_interval,
                            metadata=metadata
                        )
                        _session.add(recurrence_rule)
                        _session.flush()
                        task.recurrence_id = recurrence_rule.id

            # Update task fields
            if title:
                task.title = title.strip()
            if description is not None:
                task.description = description
            if priority:
                task.priority = priority
            if normalized_tags is not None:
                task.tags = normalized_tags
            if parsed_due_date:
                task.due_date = parsed_due_date
            task.updated_at = datetime.now(UTC)

            _session.add(task)
            _session.commit()
            _session.refresh(task)

            # Get recurrence details for response
            recurrence_info = {}
            if task.recurrence_id:
                statement = select(RecurrenceRule).where(RecurrenceRule.id == task.recurrence_id)
                recurrence_rule = _session.exec(statement).first()
                if recurrence_rule:
                    recurrence_info = {
                        "recurrence_pattern": recurrence_rule.pattern,
                        "recurrence_interval": recurrence_rule.interval
                    }

            return {
                "status": "success",
                "data": {
                    "task_id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "priority": task.priority,
                    "tags": task.tags,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "recurrence_id": str(task.recurrence_id) if task.recurrence_id else None,
                    **recurrence_info,
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

                # Handle recurrence rule updates
                if recurrence_pattern is not None or recurrence_interval is not None:
                    if recurrence_pattern and recurrence_interval:
                        # Update or create RecurrenceRule
                        if task.recurrence_id:
                            # Update existing RecurrenceRule
                            statement = select(RecurrenceRule).where(RecurrenceRule.id == task.recurrence_id)
                            recurrence_rule = session.exec(statement).first()
                            if recurrence_rule:
                                recurrence_rule.pattern = recurrence_pattern
                                recurrence_rule.interval = recurrence_interval
                                recurrence_rule.metadata = RecurrenceService.create_recurrence_metadata(
                                    pattern=recurrence_pattern,
                                    current_date=parsed_due_date or task.due_date or datetime.now(UTC)
                                )
                                session.add(recurrence_rule)
                        else:
                            # Create new RecurrenceRule
                            metadata = RecurrenceService.create_recurrence_metadata(
                                pattern=recurrence_pattern,
                                current_date=parsed_due_date or task.due_date or datetime.now(UTC)
                            )
                            recurrence_rule = RecurrenceRule(
                                id=uuid4(),
                                pattern=recurrence_pattern,
                                interval=recurrence_interval,
                                metadata=metadata
                            )
                            session.add(recurrence_rule)
                            session.flush()
                            task.recurrence_id = recurrence_rule.id

                # Update task fields
                if title:
                    task.title = title.strip()
                if description is not None:
                    task.description = description
                if priority:
                    task.priority = priority
                if normalized_tags is not None:
                    task.tags = normalized_tags
                if parsed_due_date:
                    task.due_date = parsed_due_date
                task.updated_at = datetime.now(UTC)

                session.add(task)
                session.commit()
                session.refresh(task)

                # Get recurrence details for response
                recurrence_info = {}
                if task.recurrence_id:
                    statement = select(RecurrenceRule).where(RecurrenceRule.id == task.recurrence_id)
                    recurrence_rule = session.exec(statement).first()
                    if recurrence_rule:
                        recurrence_info = {
                            "recurrence_pattern": recurrence_rule.pattern,
                            "recurrence_interval": recurrence_rule.interval
                        }

                return {
                    "status": "success",
                    "data": {
                        "task_id": str(task.id),
                        "title": task.title,
                        "description": task.description,
                        "completed": task.completed,
                        "priority": task.priority,
                        "tags": task.tags,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "recurrence_id": str(task.recurrence_id) if task.recurrence_id else None,
                        **recurrence_info,
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
def update_task_tool(
    user_id: str,
    task_id: str,
    title: str = None,
    description: str = None,
    recurrence_pattern: Optional[str] = None,
    recurrence_interval: Optional[int] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[list] = None
) -> dict:
    """MCP tool wrapper for update_task. Update task fields including recurrence.

    Args:
        user_id: User ID from JWT token (1-255 characters)
        task_id: Task ID (UUID string)
        title: New task title (optional, 1-200 characters)
        description: New task description (optional, max 1000 characters)
        recurrence_pattern: Update recurrence pattern ("daily", "weekly", "monthly")
        recurrence_interval: Update recurrence interval (e.g., 2 for bi-weekly)
        due_date: Update due date in ISO8601 format (e.g., "2026-01-10T17:00:00Z")
        priority: Update priority ("low", "normal", "high", "critical")
        tags: Update tags (list of strings, replaces existing tags)

    Returns:
        Dict with status and updated task data

    Example:
        # Update a task to be recurring
        update_task_tool(
            user_id="user-123",
            task_id="uuid-here",
            recurrence_pattern="weekly",
            recurrence_interval=2,
            priority="high"
        )
    """
    return update_task(
        user_id=user_id,
        task_id=task_id,
        title=title,
        description=description,
        recurrence_pattern=recurrence_pattern,
        recurrence_interval=recurrence_interval,
        due_date=due_date,
        priority=priority,
        tags=tags
    )


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
