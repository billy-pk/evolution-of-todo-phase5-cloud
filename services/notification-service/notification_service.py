"""
Notification Service (Phase V - User Story 2).

This microservice handles reminder delivery for tasks with due dates.

Architecture:
- Subscribes to reminders topic via Dapr Pub/Sub (optional manual trigger)
- Receives scheduled jobs from Dapr Jobs API at reminder_time
- Delivers notifications via webhook (POST to notification URL)
- Updates Reminder status in database (pending → sent/failed)
- Implements retry logic with exponential backoff (max 3 retries)
- Idempotent: Skips delivery if task completed or deleted

Technology Stack:
- FastAPI for HTTP server (required for Dapr Pub/Sub and Jobs API)
- Dapr Pub/Sub for event subscription
- Dapr Jobs API for scheduled job triggers
- SQLModel for database operations
- PostgreSQL for state storage
- httpx for webhook HTTP requests
- Logging for observability
"""

import os
import sys
import logging
import json
import time
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, create_engine, select
from dapr.clients import DaprClient
import httpx
import uvicorn

# Add backend directory to path for shared modules
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from models import Task, Reminder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Notification Service")

# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/evolution_todo"
)
engine = create_engine(DATABASE_URL)

# Dapr client (initialized at startup)
dapr_client: Optional[DaprClient] = None

# Webhook configuration
WEBHOOK_URL = os.environ.get("NOTIFICATION_WEBHOOK_URL", "http://localhost:3000/api/notifications")
WEBHOOK_TIMEOUT = int(os.environ.get("WEBHOOK_TIMEOUT", "10"))  # seconds


@app.on_event("startup")
async def startup_event():
    """Initialize Dapr client on startup."""
    global dapr_client
    try:
        dapr_client = DaprClient()
        logger.info("✓ Dapr client initialized successfully")
        logger.info("✓ Notification Service started and ready to handle reminders")
        logger.info(f"✓ Webhook URL: {WEBHOOK_URL}")
    except Exception as e:
        logger.warning(f"⚠ Failed to initialize Dapr client: {e}")
        dapr_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Close Dapr client on shutdown."""
    global dapr_client
    if dapr_client:
        dapr_client.close()
    logger.info("✓ Notification Service shut down gracefully")


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "service": "notification-service"}


@app.post("/dapr/subscribe")
async def subscribe():
    """
    Dapr subscription endpoint.

    Tells Dapr which topics this service subscribes to.
    Optional: Subscribe to reminders topic for manual trigger.
    """
    subscriptions = [
        {
            "pubsubname": "pubsub",
            "topic": "reminders",
            "route": "/events/reminders"
        }
    ]
    logger.info(f"Subscriptions registered: {subscriptions}")
    return subscriptions


@app.post("/events/reminders")
async def handle_reminder_event(request: Request):
    """
    Handle reminder events from Dapr Pub/Sub.

    Optional endpoint for manual reminder triggering via Pub/Sub.
    Primary delivery mechanism is via Dapr Jobs API (/api/jobs/reminder).

    Event Payload Schema:
    {
        "event_id": "uuid",
        "event_type": "reminder.trigger",
        "timestamp": "ISO8601",
        "reminder_id": "uuid",
        "task_id": "uuid",
        "user_id": "string",
        "task_title": "string"
    }
    """
    try:
        event = await request.json()
        logger.info(f"Received reminder event: {event.get('event_type')} for reminder {event.get('data', {}).get('reminder_id')}")

        # Extract event data (Dapr wraps payload in 'data' field)
        event_data = event.get("data", event)
        reminder_id = event_data.get("reminder_id")

        if not reminder_id:
            logger.warning("Reminder event missing reminder_id, skipping")
            return {"status": "error", "message": "Missing reminder_id"}

        # Process reminder delivery
        result = await process_reminder_delivery(reminder_id=reminder_id)
        return result

    except Exception as e:
        logger.error(f"Error handling reminder event: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/api/jobs/reminder")
async def handle_reminder_job(request: Request):
    """
    Handle reminder jobs from Dapr Jobs API.

    This is the primary endpoint for scheduled reminder delivery.
    Dapr Jobs API invokes this endpoint at the scheduled reminder_time.

    Job Payload Schema (from schedule_reminder_job in backend/tools/server.py):
    {
        "reminder_id": "uuid",
        "task_id": "uuid",
        "user_id": "string",
        "task_title": "string",
        "reminder_time": "ISO8601"
    }
    """
    try:
        job_data = await request.json()
        logger.info(f"Received reminder job for reminder {job_data.get('reminder_id')}")

        reminder_id = job_data.get("reminder_id")
        if not reminder_id:
            logger.warning("Reminder job missing reminder_id, skipping")
            return {"status": "error", "message": "Missing reminder_id"}

        # Process reminder delivery
        result = await process_reminder_delivery(reminder_id=reminder_id)
        return result

    except Exception as e:
        logger.error(f"Error handling reminder job: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def process_reminder_delivery(reminder_id: str) -> Dict[str, Any]:
    """
    Process reminder delivery with idempotency check and retry logic.

    Args:
        reminder_id: UUID of the Reminder record

    Returns:
        Dict with status and message

    Algorithm:
    1. Load Reminder from database
    2. Idempotency check: Skip if already sent or task completed/deleted
    3. Deliver notification via webhook with retry logic (max 3 retries, exponential backoff)
    4. Update Reminder status (sent or failed)
    5. Log delivery result
    """
    logger.info(f"Processing reminder delivery: {reminder_id}")

    with Session(engine) as session:
        try:
            # Load Reminder from database
            statement = select(Reminder).where(Reminder.id == reminder_id)
            reminder = session.exec(statement).first()

            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found, skipping")
                return {"status": "error", "message": "Reminder not found"}

            # Idempotency check: Skip if already sent
            if reminder.status == "sent":
                logger.info(f"Reminder {reminder_id} already sent, skipping (idempotency check)")
                return {"status": "success", "message": "Reminder already sent (idempotent)"}

            # Load associated Task for idempotency check
            statement = select(Task).where(Task.id == reminder.task_id)
            task = session.exec(statement).first()

            if not task:
                logger.warning(f"Task {reminder.task_id} not found, skipping reminder delivery")
                # Update reminder status to failed (task deleted)
                reminder.status = "failed"
                session.commit()
                return {"status": "error", "message": "Task not found (deleted)"}

            # Idempotency check: Skip if task completed
            if task.completed:
                logger.info(f"Task {reminder.task_id} already completed, skipping reminder delivery")
                # Update reminder status to sent (task completed, no need to remind)
                reminder.status = "sent"
                reminder.sent_at = datetime.now(UTC)
                session.commit()
                return {"status": "success", "message": "Task already completed, reminder skipped"}

            # Deliver notification with retry logic
            delivery_success = await deliver_notification_with_retry(
                reminder=reminder,
                task=task,
                max_retries=3
            )

            if delivery_success:
                # Update Reminder status to sent
                reminder.status = "sent"
                reminder.sent_at = datetime.now(UTC)
                session.commit()
                session.refresh(reminder)

                logger.info(f"✓ Reminder {reminder_id} delivered successfully")
                return {
                    "status": "success",
                    "message": f"Reminder delivered successfully",
                    "reminder_id": str(reminder.id),
                    "task_id": str(reminder.task_id),
                    "sent_at": reminder.sent_at.isoformat()
                }
            else:
                # Update Reminder status to failed
                reminder.status = "failed"
                session.commit()

                logger.error(f"✗ Reminder {reminder_id} delivery failed after retries")
                return {
                    "status": "error",
                    "message": "Reminder delivery failed after retries",
                    "reminder_id": str(reminder.id)
                }

        except Exception as e:
            logger.error(f"Error processing reminder delivery: {str(e)}", exc_info=True)
            session.rollback()
            return {"status": "error", "message": str(e)}


async def deliver_notification_with_retry(
    reminder: Reminder,
    task: Task,
    max_retries: int = 3
) -> bool:
    """
    Deliver notification via webhook with exponential backoff retry logic.

    Args:
        reminder: Reminder database record
        task: Task database record
        max_retries: Maximum number of retry attempts (default 3)

    Returns:
        bool: True if delivery succeeded, False if all retries failed

    Retry Logic:
    - Retry 0: Immediate delivery
    - Retry 1: Wait 2^1 = 2 seconds, then retry
    - Retry 2: Wait 2^2 = 4 seconds, then retry
    - Retry 3: Wait 2^3 = 8 seconds, then retry
    - Total retries: 4 attempts (1 initial + 3 retries)

    Webhook Payload:
    {
        "reminder_id": "uuid",
        "task_id": "uuid",
        "user_id": "string",
        "task_title": "string",
        "task_description": "string",
        "due_date": "ISO8601",
        "reminder_time": "ISO8601",
        "message": "Reminder: <task_title> is due at <due_date>"
    }
    """
    # Prepare webhook payload
    payload = {
        "reminder_id": str(reminder.id),
        "task_id": str(reminder.task_id),
        "user_id": reminder.user_id,
        "task_title": task.title,
        "task_description": task.description,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "reminder_time": reminder.reminder_time.isoformat(),
        "message": f"Reminder: {task.title} is due at {task.due_date.isoformat() if task.due_date else 'unknown time'}"
    }

    # Retry loop with exponential backoff
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            logger.info(f"Delivery attempt {attempt + 1}/{max_retries + 1} for reminder {reminder.id}")

            # Send webhook POST request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=WEBHOOK_TIMEOUT
                )

                # Check if delivery succeeded (2xx status code)
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"✓ Webhook delivery succeeded (status {response.status_code})")
                    # Update retry_count in database
                    with Session(engine) as session:
                        db_reminder = session.get(Reminder, reminder.id)
                        if db_reminder:
                            db_reminder.retry_count = attempt
                            session.commit()
                    return True
                else:
                    logger.warning(f"Webhook delivery failed (status {response.status_code}): {response.text}")

        except httpx.TimeoutException:
            logger.warning(f"Webhook delivery timeout (attempt {attempt + 1})")
        except Exception as e:
            logger.warning(f"Webhook delivery error (attempt {attempt + 1}): {str(e)}")

        # If not last attempt, wait with exponential backoff
        if attempt < max_retries:
            backoff_seconds = 2 ** (attempt + 1)  # 2, 4, 8 seconds
            logger.info(f"Waiting {backoff_seconds}s before retry...")
            time.sleep(backoff_seconds)

    # All retries failed
    logger.error(f"All {max_retries + 1} delivery attempts failed for reminder {reminder.id}")

    # Update retry_count in database
    with Session(engine) as session:
        db_reminder = session.get(Reminder, reminder.id)
        if db_reminder:
            db_reminder.retry_count = max_retries + 1
            session.commit()

    return False


if __name__ == "__main__":
    # Run service with uvicorn
    port = int(os.environ.get("PORT", 8003))
    logger.info(f"Starting Notification Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
