from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, JSON, text
from datetime import datetime, UTC
from uuid import UUID, uuid4
from typing import Optional
from pydantic import validator


class Task(SQLModel, table=True):
    """
    Task model for database table.
    Represents a todo item belonging to a specific user.
    """
    __tablename__ = "tasks"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique task identifier"
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID from Better Auth"
    )

    title: str = Field(
        max_length=200,
        min_length=1,
        description="Task title (required)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description (optional)"
    )

    completed: bool = Field(
        default=False,
        description="Completion status"
    )

    # Phase V: Advanced task management fields
    priority: str = Field(
        default="normal",
        max_length=20,
        index=True,
        description="Task priority: low, normal, high, critical"
    )

    tags: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="Task tags for categorization"
    )

    due_date: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Task due date (ISO8601 with timezone)"
    )

    recurrence_id: Optional[UUID] = Field(
        default=None,
        foreign_key="recurrence_rules.id",
        description="FK to recurrence_rules table for recurring tasks"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            "updated_at",
            server_default=text("NOW()"),
            onupdate=text("NOW()")
        ),
        description="Last update timestamp (UTC) - auto-updated on modification"
    )


class Conversation(SQLModel, table=True):
    """
    Conversation model for database table.
    Represents a chat thread between a user and the AI assistant.
    """
    __tablename__ = "conversations"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique conversation identifier"
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID from Better Auth"
    )

    title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional conversation title (e.g., first user message)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last message timestamp (UTC)"
    )


class Message(SQLModel, table=True):
    """
    Message model for database table.
    Represents a single message within a conversation (user or assistant).
    """
    __tablename__ = "messages"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique message identifier"
    )

    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        description="Conversation FK"
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID for isolation"
    )

    role: str = Field(
        max_length=20,
        description="Message role: 'user' or 'assistant'"
    )

    content: str = Field(
        description="Message text content"
    )

    tool_calls: Optional[str] = Field(
        default=None,
        description="JSON array of tool calls (for assistant messages)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Message timestamp (UTC)"
    )

    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError('role must be "user" or "assistant"')
        return v


class RecurrenceRule(SQLModel, table=True):
    """
    RecurrenceRule model for database table.
    Defines how a task repeats (daily, weekly, monthly).
    One recurrence rule can generate multiple task instances.
    """
    __tablename__ = "recurrence_rules"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique recurrence rule identifier"
    )

    task_id: UUID = Field(
        foreign_key="tasks.id",
        index=True,
        description="Original template task ID"
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID for isolation"
    )

    pattern: str = Field(
        max_length=50,
        index=True,
        description="Recurrence pattern: daily, weekly, monthly, custom"
    )

    interval: int = Field(
        default=1,
        description="Every N days/weeks/months (must be positive)"
    )

    rule_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSON),
        description="JSON metadata preserving task attributes (priority, tags, description)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)"
    )


class Reminder(SQLModel, table=True):
    """
    Reminder model for database table.
    Scheduled notifications for tasks with due dates.
    Managed by Dapr Jobs API for reliable delivery.
    """
    __tablename__ = "reminders"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique reminder identifier"
    )

    task_id: UUID = Field(
        foreign_key="tasks.id",
        index=True,
        description="Task ID for this reminder"
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID for isolation"
    )

    reminder_time: datetime = Field(
        index=True,
        description="Scheduled time for reminder delivery (ISO8601 with timezone)"
    )

    status: str = Field(
        default="pending",
        max_length=20,
        index=True,
        description="Reminder status: pending, sent, failed"
    )

    delivery_method: str = Field(
        default="webhook",
        max_length=50,
        description="Delivery method: webhook, email (future)"
    )

    retry_count: int = Field(
        default=0,
        description="Number of delivery retry attempts (max 3)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)"
    )

    sent_at: Optional[datetime] = Field(
        default=None,
        description="Actual delivery timestamp (UTC)"
    )


class AuditLog(SQLModel, table=True):
    """
    AuditLog model for database table.
    Immutable audit trail of all task operations for compliance and debugging.
    Populated by Audit Service subscribing to task-events topic.
    """
    __tablename__ = "audit_log"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique audit log entry identifier"
    )

    event_type: str = Field(
        max_length=50,
        index=True,
        description="Event type: task.created, task.updated, task.completed, task.deleted, etc."
    )

    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID for isolation"
    )

    task_id: Optional[UUID] = Field(
        default=None,
        index=True,
        description="Task ID (nullable for non-task events)"
    )

    details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Full event payload (task data, changes, metadata)"
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        index=True,
        description="Event timestamp (UTC) - immutable"
    )