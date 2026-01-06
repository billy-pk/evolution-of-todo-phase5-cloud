from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, List


class TaskCreate(BaseModel):
    """Request schema for creating a new task"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Buy groceries",
                "description": "Milk, eggs, bread"
            }
        }
    )

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class TaskUpdate(BaseModel):
    """Request schema for updating a task"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Buy groceries and cook dinner",
                "description": "Updated description"
            }
        }
    )

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class TaskResponse(BaseModel):
    """Response schema for task data"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user_123",
                "title": "Buy groceries",
                "description": "Milk, eggs, bread",
                "completed": False,
                "created_at": "2025-12-06T12:00:00Z",
                "updated_at": "2025-12-06T12:00:00Z"
            }
        }
    )

    id: UUID
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Response schema for task list"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "user_123",
                        "title": "Buy groceries",
                        "description": "Milk, eggs, bread",
                        "completed": False,
                        "created_at": "2025-12-06T12:00:00Z",
                        "updated_at": "2025-12-06T12:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    )

    tasks: List[TaskResponse]
    total: int


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Add a task to buy groceries",
                "conversation_id": None
            }
        }
    )

    message: str = Field(..., min_length=1, description="User message to send to the AI assistant")
    conversation_id: Optional[UUID] = Field(None, description="Optional conversation ID to continue existing conversation")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "response": "I've added 'Buy groceries' to your task list.",
                "tool_calls": [
                    {
                        "tool": "add_task",
                        "parameters": {"user_id": "user_123", "title": "Buy groceries"},
                        "result": {"task_id": "uuid-...", "status": "created"}
                    }
                ],
                "messages": [
                    {"role": "user", "content": "Add a task to buy groceries"},
                    {"role": "assistant", "content": "I've added 'Buy groceries' to your task list."}
                ],
                "metadata": {"model": "gpt-4o", "tokens_used": 150}
            }
        }
    )

    conversation_id: UUID = Field(..., description="Conversation ID (new or existing)")
    response: str = Field(..., description="AI assistant response text")
    tool_calls: List[dict] = Field(default_factory=list, description="List of tool calls made by the assistant")
    messages: List[dict] = Field(default_factory=list, description="Conversation message history")
    metadata: dict = Field(default_factory=dict, description="Additional metadata (model, tokens, etc.)")


# Phase V: Event Payload Schemas for Event-Driven Architecture

class TaskEventPayload(BaseModel):
    """
    Event payload schema for task lifecycle events.
    Published to task-events topic for Audit Service and Recurring Task Service.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "event_type": "task.created",
                "timestamp": "2026-01-06T10:00:00Z",
                "user_id": "user-123",
                "task_data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Complete project proposal",
                    "description": "Draft Q1 proposal",
                    "completed": False,
                    "priority": "high",
                    "tags": ["work", "urgent"],
                    "due_date": "2026-01-10T17:00:00Z",
                    "recurrence_id": None,
                    "created_at": "2026-01-06T10:00:00Z",
                    "updated_at": "2026-01-06T10:00:00Z"
                },
                "previous_data": None,
                "metadata": {
                    "source": "mcp_tool",
                    "correlation_id": "770e8400-e29b-41d4-a716-446655440002"
                }
            }
        }
    )

    event_id: str = Field(..., description="Unique event identifier (UUID) for idempotency")
    event_type: str = Field(..., description="Event type: task.created, task.updated, task.completed, task.deleted")
    timestamp: str = Field(..., description="Event timestamp (ISO8601 with timezone)")
    user_id: str = Field(..., description="User ID for isolation")
    task_data: dict = Field(..., description="Full task object snapshot")
    previous_data: Optional[dict] = Field(None, description="Previous task state (for updates)")
    metadata: dict = Field(default_factory=dict, description="Event metadata (source, correlation_id)")


class ReminderEventPayload(BaseModel):
    """
    Event payload schema for reminder lifecycle events.
    Published to reminders topic for Notification Service.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "456e7890-h12e-45g6-d789-759947407333",
                "event_type": "reminder.scheduled",
                "reminder_id": "661f9511-f30c-52e5-b827-557766551111",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "reminder_time": "2026-01-13T09:00:00Z",
                "task_data": {
                    "title": "Submit quarterly report",
                    "description": "Q4 2025 financial report",
                    "due_date": "2026-01-13T17:00:00Z",
                    "priority": "high"
                },
                "delivery_method": "webhook",
                "retry_count": 0,
                "timestamp": "2026-01-06T10:00:00Z",
                "schema_version": "1.0.0"
            }
        }
    )

    event_id: str = Field(..., description="Unique event identifier (UUID)")
    event_type: str = Field(..., description="Event type: reminder.scheduled, reminder.triggered, reminder.delivered, reminder.failed")
    reminder_id: str = Field(..., description="Reminder ID (UUID)")
    task_id: str = Field(..., description="Task ID (UUID)")
    user_id: str = Field(..., description="User ID for isolation")
    reminder_time: str = Field(..., description="Scheduled reminder time (ISO8601)")
    task_data: dict = Field(default_factory=dict, description="Relevant task info for notification")
    delivery_method: str = Field(default="webhook", description="Delivery method: webhook, email, sms")
    retry_count: int = Field(default=0, description="Delivery retry count (0-3)")
    error_message: Optional[str] = Field(None, description="Error message for failed deliveries")
    timestamp: str = Field(..., description="Event timestamp (ISO8601)")
    schema_version: str = Field(default="1.0.0", description="Event schema version")


class TaskUpdatePayload(BaseModel):
    """
    Event payload schema for real-time UI updates via WebSocket.
    Published to task-updates topic for WebSocket Service.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "update_type": "task_created",
                "event_id": "890e1234-l56i-89k0-h123-193381841777",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "task_data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Submit quarterly report",
                    "description": "Q4 2025 financial report",
                    "completed": False,
                    "priority": "high",
                    "tags": ["work", "urgent"],
                    "due_date": "2026-01-13T17:00:00Z",
                    "recurrence_id": None,
                    "created_at": "2026-01-06T10:00:00Z",
                    "updated_at": "2026-01-06T10:00:00Z"
                },
                "source": "user_action",
                "timestamp": "2026-01-06T10:00:01Z",
                "schema_version": "1.0.0"
            }
        }
    )

    update_type: str = Field(..., description="Update type: task_created, task_updated, task_completed, task_deleted, task_recurring_generated")
    event_id: str = Field(..., description="Unique event identifier (UUID)")
    task_id: str = Field(..., description="Task ID (UUID)")
    user_id: str = Field(..., description="User ID for isolation")
    task_data: Optional[dict] = Field(None, description="Full task object (null for delete)")
    source: str = Field(default="user_action", description="Event source: user_action, system_generated, recurring_task_service")
    timestamp: str = Field(..., description="Event timestamp (ISO8601)")
    schema_version: str = Field(default="1.0.0", description="Event schema version")