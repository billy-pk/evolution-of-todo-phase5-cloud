"""
Audit Service (Phase V - Event-Driven Microservices).

This microservice logs all task operations to the audit_log table for compliance,
debugging, and analytics.

Architecture:
- Subscribes to task-events topic via Dapr Pub/Sub
- Processes all event types: task.created, task.updated, task.completed, task.deleted
- Writes immutable audit log entries to PostgreSQL
- Error handling: logs failures but never blocks main flow (returns 200 to Dapr)
- Includes recurrence_id in deletion events for recurring task tracking

Technology Stack:
- FastAPI for HTTP server (required for Dapr Pub/Sub)
- Dapr Pub/Sub for event subscription
- SQLModel for database operations
- PostgreSQL for audit log storage
- Structured logging with correlation IDs for observability
"""

import os
import sys
import logging
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlmodel import Session, create_engine, select
from pydantic import BaseModel, Field
import uvicorn

# Add backend directory to path for shared modules
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from models import AuditLog

# Configure structured logging with correlation IDs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class CorrelationLogAdapter(logging.LoggerAdapter):
    """Logger adapter that adds correlation_id to log records."""

    def process(self, msg, kwargs):
        # Extract correlation_id from extra or use default
        correlation_id = self.extra.get('correlation_id', 'no-correlation-id')
        kwargs.setdefault('extra', {})['correlation_id'] = correlation_id
        return msg, kwargs


# Create base logger and adapter
_base_logger = logging.getLogger(__name__)
logger = CorrelationLogAdapter(_base_logger, {'correlation_id': 'startup'})

# Initialize FastAPI app
app = FastAPI(
    title="Audit Service",
    version="1.0.0",
    description="Logs all task operations to audit_log table for compliance and debugging"
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Allow startup without DATABASE_URL for testing (will fail on first DB operation)
    engine = None
    _base_logger.warning("DATABASE_URL not set - database operations will fail")

# Dapr configuration
DAPR_PUBSUB_NAME = os.getenv("DAPR_PUBSUB_NAME", "pubsub")
TASK_EVENTS_TOPIC = "task-events"

# Supported event types for explicit handling
SUPPORTED_EVENT_TYPES = [
    "task.created",
    "task.updated",
    "task.completed",
    "task.deleted"
]


class TaskData(BaseModel):
    """Task data schema from event payload."""
    title: str
    description: Optional[str] = None
    completed: bool
    priority: str = "normal"
    tags: Optional[list[str]] = None
    due_date: Optional[str] = None
    recurrence_id: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskEventPayload(BaseModel):
    """Task event payload from task-events topic."""
    event_type: str
    event_id: str
    task_id: str
    user_id: str
    task_data: Dict[str, Any]
    timestamp: str
    schema_version: str = "1.0.0"


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "service": "audit-service"}


@app.get("/readiness")
async def readiness_check():
    """Readiness check endpoint - verifies database connection."""
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "Database not configured"}
        )
    try:
        from sqlalchemy import text
        with Session(engine) as session:
            # Simple query to verify connection
            session.exec(select(1))
        return {"status": "ready", "service": "audit-service"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": str(e)}
        )


@app.get("/dapr/subscribe")
async def subscribe():
    """
    Dapr subscription endpoint.

    Tells Dapr which topics this service subscribes to.
    """
    subscriptions = [
        {
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": TASK_EVENTS_TOPIC,
            "route": "/events/task-events"
        }
    ]
    logger.info(f"Subscriptions registered: {subscriptions}")
    return subscriptions


@app.post("/events/task-events")
async def handle_task_event(request: Request):
    """
    Handle task events from task-events topic.

    Processes all event types and writes to audit_log table:
    - task.created: New task created
    - task.updated: Task modified (title, description, priority, tags, due_date)
    - task.completed: Task marked as complete (triggers recurring task generation)
    - task.deleted: Task deleted (includes recurrence_id for recurring task tracking)

    Error Handling:
    - Logs errors but returns 200 to Dapr to acknowledge receipt
    - Prevents retries for logging failures (audit logging should not block main flow)
    - Structured error logging with correlation IDs for debugging
    """
    correlation_id = str(uuid4())[:8]
    request_logger = CorrelationLogAdapter(_base_logger, {'correlation_id': correlation_id})

    try:
        # Parse CloudEvent/raw event
        body = await request.json()
        request_logger.info(f"Received event from {TASK_EVENTS_TOPIC} topic")

        # Extract event data (Dapr wraps payload in 'data' field)
        event_data = body.get("data", body)

        event_type = event_data.get("event_type")
        event_id = event_data.get("event_id")
        task_id = event_data.get("task_id")
        user_id = event_data.get("user_id")
        task_data = event_data.get("task_data", {})
        timestamp_str = event_data.get("timestamp")
        schema_version = event_data.get("schema_version", "1.0.0")

        # Validate required fields
        if not event_type:
            request_logger.warning("Event missing event_type, skipping audit log")
            return Response(status_code=200)

        if not user_id:
            request_logger.warning(f"Event {event_type} missing user_id, skipping audit log")
            return Response(status_code=200)

        request_logger.info(
            f"Processing event: {event_type} | "
            f"Event ID: {event_id} | Task ID: {task_id} | User: {user_id}"
        )

        # Handle specific event types with appropriate logging
        audit_details = create_audit_details(
            event_type=event_type,
            event_id=event_id,
            task_data=task_data,
            timestamp_str=timestamp_str,
            schema_version=schema_version,
            correlation_id=correlation_id
        )

        # Write to audit_log table
        result = write_audit_log(
            event_type=event_type,
            user_id=user_id,
            task_id=task_id,
            details=audit_details,
            logger=request_logger
        )

        if result:
            request_logger.info(f"✓ Audit log entry created: {event_type} for task {task_id}")
        else:
            request_logger.error(f"✗ Failed to create audit log entry for {event_type}")

        # Return 200 to acknowledge receipt regardless of success/failure
        # Audit logging should not block main flow
        return Response(status_code=200)

    except json.JSONDecodeError as e:
        request_logger.error(f"✗ Invalid JSON in event payload: {str(e)}")
        return Response(status_code=200)
    except Exception as e:
        request_logger.error(f"✗ Unexpected error processing event: {str(e)}", exc_info=True)
        # Return 200 to prevent Dapr retries - audit logging is non-critical
        return Response(status_code=200)


def create_audit_details(
    event_type: str,
    event_id: str,
    task_data: Dict[str, Any],
    timestamp_str: str,
    schema_version: str,
    correlation_id: str
) -> Dict[str, Any]:
    """
    Create audit details payload based on event type.

    For task.deleted events, ensures recurrence_id is included for tracking
    recurring task deletion.

    Args:
        event_type: Type of event (task.created, task.updated, etc.)
        event_id: Unique event identifier
        task_data: Task data from event payload
        timestamp_str: Original event timestamp
        schema_version: Event schema version
        correlation_id: Correlation ID for distributed tracing

    Returns:
        Dict containing audit details
    """
    details = {
        "event_id": event_id,
        "task_data": task_data,
        "original_timestamp": timestamp_str,
        "schema_version": schema_version,
        "correlation_id": correlation_id
    }

    # For deletion events, ensure recurrence_id is explicitly logged
    # This enables tracking of recurring task deletions
    if event_type == "task.deleted":
        recurrence_id = task_data.get("recurrence_id")
        details["recurrence_id"] = recurrence_id
        details["is_recurring_task"] = recurrence_id is not None

    # For completion events, flag recurring tasks
    if event_type == "task.completed":
        recurrence_id = task_data.get("recurrence_id")
        details["recurrence_id"] = recurrence_id
        details["is_recurring_task"] = recurrence_id is not None

    # For created events, track priority and tags
    if event_type == "task.created":
        details["priority"] = task_data.get("priority", "normal")
        details["has_due_date"] = task_data.get("due_date") is not None
        details["has_recurrence"] = task_data.get("recurrence_id") is not None
        details["tag_count"] = len(task_data.get("tags") or [])

    # For updated events, could track what changed (if prev_data available)
    if event_type == "task.updated":
        details["priority"] = task_data.get("priority", "normal")
        details["has_due_date"] = task_data.get("due_date") is not None

    return details


def write_audit_log(
    event_type: str,
    user_id: str,
    task_id: Optional[str],
    details: Dict[str, Any],
    logger: logging.LoggerAdapter
) -> bool:
    """
    Write an entry to the audit_log table.

    Uses SQLModel AuditLog model for type safety.
    Returns True on success, False on failure.

    Args:
        event_type: Type of event
        user_id: User ID for isolation
        task_id: Task ID (nullable for non-task events)
        details: JSON details payload
        logger: Logger with correlation ID

    Returns:
        bool: True if write succeeded, False otherwise
    """
    if engine is None:
        logger.error("Database engine not initialized")
        return False

    try:
        with Session(engine) as session:
            # Create AuditLog entry using SQLModel
            audit_entry = AuditLog(
                id=uuid4(),
                event_type=event_type,
                user_id=user_id,
                task_id=UUID(task_id) if task_id else None,
                details=details,
                timestamp=datetime.now(UTC)
            )

            session.add(audit_entry)
            session.commit()

            logger.debug(f"Audit entry ID: {audit_entry.id}")
            return True

    except Exception as e:
        logger.error(f"Database error writing audit log: {str(e)}", exc_info=True)
        return False


@app.on_event("startup")
async def startup_event():
    """Log service startup with configuration."""
    logger.info("=" * 60)
    logger.info("Audit Service Starting")
    logger.info("=" * 60)
    if DATABASE_URL:
        # Mask password in URL for logging
        masked_url = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'
        logger.info(f"Database: {masked_url}")
    else:
        logger.warning("Database: NOT CONFIGURED")
    logger.info(f"Dapr Pub/Sub: {DAPR_PUBSUB_NAME}")
    logger.info(f"Subscribing to topic: {TASK_EVENTS_TOPIC}")
    logger.info(f"Supported event types: {', '.join(SUPPORTED_EVENT_TYPES)}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Log service shutdown."""
    logger.info("Audit Service shutting down gracefully")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    logger.info(f"Starting Audit Service on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
