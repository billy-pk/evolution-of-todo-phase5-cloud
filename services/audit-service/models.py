"""
AuditLog model for the Audit Service.

This is a copy of the AuditLog model from backend/models.py,
required for the microservice to write audit entries to the database.
"""

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


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

    correlation_id: Optional[str] = Field(
        default=None,
        max_length=255,
        index=True,
        description="Correlation ID for distributed tracing"
    )
