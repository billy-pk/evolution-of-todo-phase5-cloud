"""
Audit Service - Phase V Event-Driven Microservices
Subscribes to task-events topic and logs all operations to audit_log table
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlmodel import Session, create_engine
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Audit Service", version="1.0.0")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    raise ValueError("DATABASE_URL must be set")

engine = create_engine(DATABASE_URL, echo=False)

# Dapr configuration
DAPR_PUBSUB_NAME = os.getenv("DAPR_PUBSUB_NAME", "pubsub")
TASK_EVENTS_TOPIC = "task-events"


# Event models
class TaskEventPayload(BaseModel):
    """Task event payload from task-events topic"""
    event_type: str
    event_id: str
    task_id: str
    user_id: str
    task_data: Dict[str, Any]
    timestamp: str
    schema_version: str = "1.0.0"


class CloudEvent(BaseModel):
    """Dapr CloudEvent wrapper"""
    id: str
    source: str
    type: str
    specversion: str = "1.0"
    datacontenttype: str = "application/json"
    data: TaskEventPayload


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return {"status": "healthy", "service": "audit-service"}


# Dapr Pub/Sub subscription endpoint
@app.get("/dapr/subscribe")
async def subscribe():
    """
    Dapr calls this endpoint to discover pub/sub subscriptions
    Returns list of topics this service subscribes to
    """
    subscriptions = [
        {
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": TASK_EVENTS_TOPIC,
            "route": "/events/task-events"
        }
    ]
    logger.info(f"Dapr subscribe endpoint called, returning {len(subscriptions)} subscriptions")
    return subscriptions


# Task events handler
@app.post("/events/task-events")
async def handle_task_event(request: Request):
    """
    Handle task events from task-events topic
    Writes all events to audit_log table for compliance and debugging
    """
    try:
        # Parse CloudEvent
        body = await request.json()
        logger.info(f"Received event from {TASK_EVENTS_TOPIC} topic")

        # Extract event data
        if "data" in body:
            event_data = body["data"]
        else:
            event_data = body

        event_type = event_data.get("event_type")
        event_id = event_data.get("event_id")
        task_id = event_data.get("task_id")
        user_id = event_data.get("user_id")
        task_data = event_data.get("task_data", {})
        timestamp_str = event_data.get("timestamp")

        logger.info(f"Processing event: {event_type} - Event ID: {event_id}, Task ID: {task_id}, User: {user_id}")

        # Write to audit_log table
        with Session(engine) as session:
            # Use raw SQL to avoid importing models (which might have circular dependencies)
            insert_query = """
                INSERT INTO audit_log (id, event_type, user_id, task_id, details, timestamp)
                VALUES (:id, :event_type, :user_id, :task_id, :details, :timestamp)
            """

            from sqlalchemy import text
            import json

            session.execute(
                text(insert_query),
                {
                    "id": str(uuid4()),
                    "event_type": event_type,
                    "user_id": user_id,
                    "task_id": task_id,
                    "details": json.dumps({
                        "event_id": event_id,
                        "task_data": task_data,
                        "original_timestamp": timestamp_str
                    }),
                    "timestamp": datetime.utcnow()
                }
            )
            session.commit()

        logger.info(f"✓ Audit log entry created: {event_type} for task {task_id}")

        # Return success response for Dapr
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"✗ Error processing event: {str(e)}", exc_info=True)
        # Log error but don't block main flow
        # Return 200 to Dapr to acknowledge receipt (we don't want retries for logging failures)
        return Response(status_code=200)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log service startup"""
    logger.info("=" * 50)
    logger.info("Audit Service Starting")
    logger.info("=" * 50)
    logger.info(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    logger.info(f"Dapr Pub/Sub: {DAPR_PUBSUB_NAME}")
    logger.info(f"Subscribing to topic: {TASK_EVENTS_TOPIC}")
    logger.info("=" * 50)


# Main entry point
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
