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