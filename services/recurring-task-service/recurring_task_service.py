"""
Recurring Task Service (Phase V - User Story 1).

This microservice listens for task.completed events and automatically generates
the next instance for recurring tasks.

Architecture:
- Subscribes to task-events topic via Dapr Pub/Sub
- Processes task.completed events
- Checks if task has recurrence_id
- Calculates next occurrence date
- Creates new task instance with same attributes
- Publishes task.created event for the new instance
- Idempotent: Checks if next instance already exists before creating

Technology Stack:
- FastAPI for HTTP server (required for Dapr Pub/Sub)
- Dapr Pub/Sub for event subscription
- SQLModel for database operations
- PostgreSQL for state storage
- Logging for observability
"""

import os
import sys
import logging
from datetime import datetime, UTC
from uuid import uuid4
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, create_engine, select
from dapr.clients import DaprClient
import uvicorn

# Add backend directory to path for shared modules
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from models import Task, RecurrenceRule
from services.recurrence_service import RecurrenceService
from services.event_publisher import EventPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Recurring Task Service")

# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/evolution_todo"
)
engine = create_engine(DATABASE_URL)

# Dapr client (initialized at startup)
dapr_client: Optional[DaprClient] = None
event_publisher: Optional[EventPublisher] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Dapr client on startup."""
    global dapr_client, event_publisher
    try:
        dapr_client = DaprClient()
        event_publisher = EventPublisher(dapr_client)
        logger.info("✓ Dapr client initialized successfully")
        logger.info("✓ Recurring Task Service started and listening for task-events")
    except Exception as e:
        logger.warning(f"⚠ Failed to initialize Dapr client: {e}")
        dapr_client = None
        event_publisher = None


@app.on_event("shutdown")
async def shutdown_event():
    """Close Dapr client on shutdown."""
    global dapr_client, event_publisher
    if event_publisher:
        event_publisher.close()
    if dapr_client:
        dapr_client.close()
    logger.info("✓ Recurring Task Service shut down gracefully")


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "service": "recurring-task-service"}


@app.get("/dapr/subscribe")
async def subscribe():
    """
    Dapr subscription endpoint.

    Tells Dapr which topics this service subscribes to.
    """
    subscriptions = [
        {
            "pubsubname": "pubsub",
            "topic": "task-events",
            "route": "/events/task-events"
        }
    ]
    logger.info(f"Subscriptions registered: {subscriptions}")
    return subscriptions


@app.post("/events/task-events")
async def handle_task_event(request: Request):
    """
    Handle task-events from Dapr Pub/Sub.

    Processes task.completed events and generates next instance for recurring tasks.

    Event Payload Schema:
    {
        "event_id": "uuid",
        "event_type": "task.completed",
        "timestamp": "ISO8601",
        "user_id": "string",
        "task_data": {
            "id": "uuid",
            "title": "string",
            "recurrence_id": "uuid",  # Only present for recurring tasks
            ...
        },
        "metadata": {...}
    }
    """
    try:
        # Parse event payload
        event = await request.json()
        
        # Extract event data (Dapr wraps payload in 'data' field)
        event_data = event.get("data", event)  # Handle both wrapped and unwrapped
        event_type = event_data.get("event_type")
        task_id = event_data.get("task_data", {}).get("id") or event_data.get("id")
        
        logger.info(f"Received event: {event_type} for task {task_id}")

        event_id = event_data.get("event_id")

        # Only process task.completed events
        if event_type != "task.completed":
            logger.debug(f"Ignoring non-task.completed event: {event_type}")
            return {"status": "SUCCESS", "message": "Event ignored (not task.completed)"}

        # Extract task data
        task_data = event_data.get("task_data", {})
        user_id = event_data.get("user_id")
        recurrence_id = task_data.get("recurrence_id")

        # Check if task has recurrence
        if not recurrence_id:
            logger.debug(f"Task {task_data.get('id')} is not recurring, skipping")
            return {"status": "SUCCESS", "message": "Task is not recurring"}

        # Process recurring task
        result = await process_recurring_task(
            event_id=event_id,
            user_id=user_id,
            task_data=task_data,
            recurrence_id=recurrence_id
        )

        return result

    except Exception as e:
        logger.error(f"Error handling task event: {str(e)}", exc_info=True)
        # Return DROP to prevent Dapr retry loop on bad data
        return {"status": "DROP", "message": str(e)}


async def process_recurring_task(
    event_id: str,
    user_id: str,
    task_data: Dict[str, Any],
    recurrence_id: str
) -> Dict[str, str]:
    """
    Process a completed recurring task and generate the next instance.

    Args:
        event_id: Original event ID (for correlation)
        user_id: User ID who owns the task
        task_data: Task data from event payload
        recurrence_id: UUID of the RecurrenceRule

    Returns:
        Dict with status and message

    Algorithm:
    1. Load RecurrenceRule from database
    2. Calculate next occurrence date based on pattern/interval
    3. Check if next instance already exists (idempotency)
    4. Create new task instance with same attributes
    5. Publish task.created event
    """
    logger.info(f"Processing recurring task: {task_data.get('id')} with recurrence: {recurrence_id}")

    with Session(engine) as session:
        try:
            # Load RecurrenceRule
            statement = select(RecurrenceRule).where(RecurrenceRule.id == recurrence_id)
            recurrence_rule = session.exec(statement).first()

            if not recurrence_rule:
                logger.warning(f"RecurrenceRule {recurrence_id} not found, skipping")
                return {"status": "DROP", "message": "RecurrenceRule not found"}

            # Get current due_date (base for next occurrence)
            current_due_date_str = task_data.get("due_date")
            if not current_due_date_str:
                logger.warning(f"Task {task_data.get('id')} has no due_date, cannot calculate next occurrence")
                return {"status": "DROP", "message": "Task has no due_date"}

            # Parse due_date
            current_due_date = datetime.fromisoformat(current_due_date_str.replace('Z', '+00:00'))

            # Calculate next occurrence
            next_due_date = RecurrenceService.calculate_next_occurrence(
                current_date=current_due_date,
                pattern=recurrence_rule.pattern,
                interval=recurrence_rule.interval,
                metadata=recurrence_rule.rule_metadata
            )

            logger.info(
                f"Calculated next occurrence: {next_due_date.isoformat()} "
                f"(pattern={recurrence_rule.pattern}, interval={recurrence_rule.interval})"
            )

            # Check for existing next instance (idempotency)
            # Query for task with same recurrence_id, user_id, and due_date
            statement = select(Task).where(
                Task.recurrence_id == recurrence_id,
                Task.user_id == user_id,
                Task.due_date == next_due_date,
                Task.completed == False
            )
            existing_task = session.exec(statement).first()

            if existing_task:
                logger.info(
                    f"Next instance already exists (task_id={existing_task.id}), skipping creation "
                    f"(idempotency check passed)"
                )
                return {"status": "SUCCESS", "message": "Next instance already exists (idempotent)"}

            # Create new task instance
            new_task = Task(
                id=uuid4(),
                user_id=user_id,
                title=task_data.get("title"),
                description=task_data.get("description"),
                completed=False,  # Next instance starts uncompleted
                priority=task_data.get("priority", "normal"),
                tags=task_data.get("tags"),
                due_date=next_due_date,
                recurrence_id=recurrence_id,  # Link to same RecurrenceRule
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )

            session.add(new_task)
            session.commit()
            session.refresh(new_task)

            logger.info(
                f"✓ Created next task instance: {new_task.id} with due_date={next_due_date.isoformat()}"
            )

            # Publish task.created event for the new instance
            if event_publisher:
                try:
                    event_publisher.publish_task_created(
                        task_data={
                            "id": str(new_task.id),
                            "title": new_task.title,
                            "description": new_task.description,
                            "completed": new_task.completed,
                            "priority": new_task.priority,
                            "tags": new_task.tags,
                            "due_date": new_task.due_date.isoformat(),
                            "recurrence_id": str(new_task.recurrence_id),
                            "created_at": new_task.created_at.isoformat(),
                            "updated_at": new_task.updated_at.isoformat()
                        },
                        user_id=user_id,
                        source="recurring_task_service"
                    )
                    logger.info(f"✓ Published task.created event for next instance: {new_task.id}")
                except Exception as e:
                    logger.error(f"Failed to publish task.created event: {str(e)}")
                    # Non-blocking: task created successfully, event publish failed but logged

            return {
                "status": "SUCCESS",
                "message": f"Next task instance created: {new_task.id}",
                "next_task_id": str(new_task.id),
                "next_due_date": next_due_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing recurring task: {str(e)}", exc_info=True)
            session.rollback()
            return {"status": "RETRY", "message": str(e)}


if __name__ == "__main__":
    # Run service with uvicorn
    port = int(os.environ.get("PORT", 8002))
    logger.info(f"Starting Recurring Task Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
