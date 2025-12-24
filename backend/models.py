from sqlmodel import Field, SQLModel
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

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp (UTC)"
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