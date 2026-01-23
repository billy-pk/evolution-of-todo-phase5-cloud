#!/usr/bin/env python3
"""
Trigger Event Test - Create a task via MCP server to test event flow
This script will be run inside the MCP server pod to test Dapr pub/sub
"""

import os
import sys
from sqlmodel import Session, create_engine, select
from datetime import datetime, UTC
from uuid import uuid4
import json

# Import backend models
sys.path.insert(0, '/app')
from models import Task
from dapr.clients import DaprClient

def trigger_test_event():
    """Create a task and publish event via Dapr"""

    task_id = str(uuid4())
    user_id = "test-event-flow"
    task_title = f"Event-Flow-Test-{datetime.now(UTC).strftime('%H:%M:%S')}"

    # Create task in database
    engine = create_engine(os.getenv('DATABASE_URL'))
    with Session(engine) as session:
        task = Task(
            id=task_id,
            user_id=user_id,
            title=task_title,
            description="Auto-generated for event flow testing via Dapr",
            completed=False,
            created_at=datetime.now(UTC)
        )
        session.add(task)
        session.commit()
        print(f"✓ Created task in database: {task_id}")

    # Publish event via Dapr
    with DaprClient() as dapr:
        event_id = str(uuid4())
        event_payload = {
            "event_id": event_id,
            "event_type": "task.created",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "task_data": {
                "id": task_id,
                "title": task_title,
                "description": "Auto-generated for event flow testing via Dapr",
                "completed": False,
                "user_id": user_id,
                "created_at": datetime.now(UTC).isoformat()
            },
            "previous_data": None,
            "metadata": {
                "source": "test_script",
                "correlation_id": str(uuid4())
            }
        }

        try:
            dapr.publish_event(
                pubsub_name="pubsub",
                topic_name="task-events",
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            print(f"✓ Published event to task-events topic: {event_id}")
            print(f"  Task: {task_title}")
            print(f"  Event ID: {event_id}")
            return True
        except Exception as e:
            print(f"✗ Failed to publish event: {e}")
            return False

if __name__ == "__main__":
    success = trigger_test_event()
    sys.exit(0 if success else 1)
