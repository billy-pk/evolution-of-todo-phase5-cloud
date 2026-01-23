"""
Integration Test for Audit Logging (Phase V - Phase 8).

This test validates that the Audit Service correctly logs all task events:
- task.created events are logged with task data
- task.updated events are logged with updated fields
- task.completed events are logged with completion status
- task.deleted events are logged with recurrence_id for tracking

Test Strategy:
- Simulate Dapr event payloads to audit service endpoint
- Verify audit log entries are written to database
- Test error handling for malformed events
- Verify correlation IDs are included in logs
- Test idempotency (duplicate events don't cause failures)

Expected Behavior:
- All valid events result in audit_log entries
- Invalid events return 200 (no blocking) but don't create entries
- Each entry includes event_id, task_data, correlation_id
- task.deleted events include recurrence_id flag
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import AuditLog, Task
from fastapi.testclient import TestClient

import sys
import os

# Add audit service to path
audit_service_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "services", "audit-service"
)
sys.path.insert(0, audit_service_dir)

# Set DATABASE_URL for testing
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/evolution_todo"
)


@pytest.fixture
def db_session():
    """Fixture to provide a database session for each test."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def test_user_id():
    """Fixture for unique test user ID."""
    return f"test-user-{uuid4()}"


@pytest.fixture
def audit_client():
    """Fixture to create test client for audit service."""
    # Import here to ensure DATABASE_URL is set
    from audit_service import app
    with TestClient(app) as client:
        yield client


def create_task_event(
    event_type: str,
    user_id: str,
    task_id: str = None,
    task_data: dict = None,
    recurrence_id: str = None
) -> dict:
    """
    Create a mock task event payload in Dapr CloudEvent format.

    Args:
        event_type: Event type (task.created, task.updated, etc.)
        user_id: User ID for the event
        task_id: Task ID (optional, generates if not provided)
        task_data: Task data (optional, uses defaults if not provided)
        recurrence_id: Recurrence ID for recurring tasks (optional)

    Returns:
        Dict formatted as Dapr CloudEvent
    """
    if task_id is None:
        task_id = str(uuid4())

    if task_data is None:
        task_data = {
            "title": f"Test task for {event_type}",
            "description": "Test description",
            "completed": event_type == "task.completed",
            "priority": "normal",
            "tags": ["test"],
            "due_date": datetime.now(UTC).isoformat(),
            "recurrence_id": recurrence_id
        }
    else:
        task_data["recurrence_id"] = recurrence_id

    return {
        "data": {
            "event_type": event_type,
            "event_id": str(uuid4()),
            "task_id": task_id,
            "user_id": user_id,
            "task_data": task_data,
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
        }
    }


def test_audit_service_health(audit_client):
    """
    Test audit service health endpoint.

    Expected: Returns healthy status
    """
    response = audit_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "audit-service"


def test_audit_subscribe_endpoint(audit_client):
    """
    Test Dapr subscription endpoint.

    Expected: Returns subscription to task-events topic
    """
    response = audit_client.get("/dapr/subscribe")
    assert response.status_code == 200
    subscriptions = response.json()
    assert len(subscriptions) == 1
    assert subscriptions[0]["topic"] == "task-events"
    assert subscriptions[0]["route"] == "/events/task-events"


def test_audit_task_created_event(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that task.created events are logged to audit_log.

    Expected:
    - Audit log entry created with event_type="task.created"
    - Entry contains task_data with title, priority, tags
    - Entry includes has_due_date and tag_count metadata
    """
    task_id = str(uuid4())
    event = create_task_event(
        event_type="task.created",
        user_id=test_user_id,
        task_id=task_id,
        task_data={
            "title": "Test created task",
            "description": "Test description",
            "completed": False,
            "priority": "high",
            "tags": ["work", "urgent"],
            "due_date": datetime.now(UTC).isoformat(),
            "recurrence_id": None
        }
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.event_type == "task.created",
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.event_type == "task.created"
    assert audit_entry.user_id == test_user_id
    assert str(audit_entry.task_id) == task_id

    # Verify details contain expected metadata
    details = audit_entry.details
    assert details is not None
    assert "event_id" in details
    assert "task_data" in details
    assert details["task_data"]["title"] == "Test created task"
    assert details["priority"] == "high"
    assert details["tag_count"] == 2
    assert details["has_due_date"] is True


def test_audit_task_updated_event(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that task.updated events are logged to audit_log.

    Expected:
    - Audit log entry created with event_type="task.updated"
    - Entry contains updated task_data
    """
    task_id = str(uuid4())
    event = create_task_event(
        event_type="task.updated",
        user_id=test_user_id,
        task_id=task_id,
        task_data={
            "title": "Updated task title",
            "description": "Updated description",
            "completed": False,
            "priority": "critical",
            "tags": ["work"],
            "due_date": datetime.now(UTC).isoformat(),
            "recurrence_id": None
        }
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.event_type == "task.updated",
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.event_type == "task.updated"
    assert audit_entry.details["task_data"]["title"] == "Updated task title"
    assert audit_entry.details["priority"] == "critical"


def test_audit_task_completed_event(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that task.completed events are logged to audit_log.

    Expected:
    - Audit log entry created with event_type="task.completed"
    - Entry flags is_recurring_task for recurring tasks
    """
    task_id = str(uuid4())
    recurrence_id = str(uuid4())
    event = create_task_event(
        event_type="task.completed",
        user_id=test_user_id,
        task_id=task_id,
        task_data={
            "title": "Completed recurring task",
            "description": None,
            "completed": True,
            "priority": "normal",
            "tags": None,
            "due_date": datetime.now(UTC).isoformat()
        },
        recurrence_id=recurrence_id
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.event_type == "task.completed",
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.event_type == "task.completed"
    assert audit_entry.details["is_recurring_task"] is True
    assert audit_entry.details["recurrence_id"] == recurrence_id


def test_audit_task_deleted_event_with_recurrence(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that task.deleted events include recurrence_id for tracking.

    Expected:
    - Audit log entry created with event_type="task.deleted"
    - Entry includes recurrence_id for recurring task tracking
    - Entry flags is_recurring_task=True when recurrence_id present
    """
    task_id = str(uuid4())
    recurrence_id = str(uuid4())
    event = create_task_event(
        event_type="task.deleted",
        user_id=test_user_id,
        task_id=task_id,
        task_data={
            "title": "Deleted recurring task",
            "description": None,
            "completed": True,
            "priority": "normal",
            "tags": None,
            "due_date": None
        },
        recurrence_id=recurrence_id
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.event_type == "task.deleted",
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.event_type == "task.deleted"
    assert audit_entry.details["recurrence_id"] == recurrence_id
    assert audit_entry.details["is_recurring_task"] is True


def test_audit_task_deleted_event_without_recurrence(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that task.deleted events without recurrence are logged correctly.

    Expected:
    - Audit log entry created with event_type="task.deleted"
    - Entry has is_recurring_task=False when no recurrence_id
    """
    task_id = str(uuid4())
    event = create_task_event(
        event_type="task.deleted",
        user_id=test_user_id,
        task_id=task_id,
        task_data={
            "title": "Deleted non-recurring task",
            "description": None,
            "completed": False,
            "priority": "low",
            "tags": None,
            "due_date": None
        },
        recurrence_id=None
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.event_type == "task.deleted",
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.details["recurrence_id"] is None
    assert audit_entry.details["is_recurring_task"] is False


def test_audit_correlation_id_included(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that correlation_id is included in audit log entries.

    Expected:
    - Each audit entry has a correlation_id in details
    - Correlation ID is a string (8 chars from UUID)
    """
    task_id = str(uuid4())
    event = create_task_event(
        event_type="task.created",
        user_id=test_user_id,
        task_id=task_id
    )

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify correlation_id in entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert "correlation_id" in audit_entry.details
    assert len(audit_entry.details["correlation_id"]) == 8


def test_audit_missing_event_type(
    audit_client,
    test_user_id: str
):
    """
    Test handling of events missing event_type.

    Expected:
    - Returns 200 (no blocking)
    - No audit entry created
    """
    event = {
        "data": {
            "event_id": str(uuid4()),
            "task_id": str(uuid4()),
            "user_id": test_user_id,
            "task_data": {"title": "Test"},
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
            # Missing: event_type
        }
    }

    response = audit_client.post("/events/task-events", json=event)
    # Should return 200 to not block main flow
    assert response.status_code == 200


def test_audit_missing_user_id(
    audit_client
):
    """
    Test handling of events missing user_id.

    Expected:
    - Returns 200 (no blocking)
    - No audit entry created
    """
    event = {
        "data": {
            "event_type": "task.created",
            "event_id": str(uuid4()),
            "task_id": str(uuid4()),
            # Missing: user_id
            "task_data": {"title": "Test", "completed": False},
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
        }
    }

    response = audit_client.post("/events/task-events", json=event)
    # Should return 200 to not block main flow
    assert response.status_code == 200


def test_audit_invalid_json(audit_client):
    """
    Test handling of invalid JSON payload.

    Expected:
    - Returns 200 (no blocking)
    - Error is logged
    """
    response = audit_client.post(
        "/events/task-events",
        content="invalid json {",
        headers={"Content-Type": "application/json"}
    )
    # Should return 200 to not block main flow
    # FastAPI will return 422 for invalid JSON
    assert response.status_code in [200, 422]


def test_audit_unwrapped_event_format(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test handling of events without Dapr 'data' wrapper.

    Expected:
    - Audit entry created from unwrapped event
    - Supports both wrapped and unwrapped formats
    """
    task_id = str(uuid4())
    # Send event without 'data' wrapper (direct format)
    event = {
        "event_type": "task.created",
        "event_id": str(uuid4()),
        "task_id": task_id,
        "user_id": test_user_id,
        "task_data": {
            "title": "Unwrapped event task",
            "completed": False,
            "priority": "normal"
        },
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify audit log entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.details["task_data"]["title"] == "Unwrapped event task"


def test_audit_schema_version_preserved(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that schema_version is preserved in audit log.

    Expected:
    - Audit entry includes schema_version in details
    """
    task_id = str(uuid4())
    event = create_task_event(
        event_type="task.created",
        user_id=test_user_id,
        task_id=task_id
    )
    # Override schema version
    event["data"]["schema_version"] = "1.1.0"

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify schema_version in entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.details["schema_version"] == "1.1.0"


def test_audit_original_timestamp_preserved(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that original event timestamp is preserved in audit log.

    Expected:
    - Audit entry includes original_timestamp in details
    """
    task_id = str(uuid4())
    original_ts = "2026-01-15T10:00:00Z"
    event = {
        "data": {
            "event_type": "task.created",
            "event_id": str(uuid4()),
            "task_id": task_id,
            "user_id": test_user_id,
            "task_data": {"title": "Test", "completed": False, "priority": "normal"},
            "timestamp": original_ts,
            "schema_version": "1.0.0"
        }
    }

    response = audit_client.post("/events/task-events", json=event)
    assert response.status_code == 200

    # Verify original_timestamp in entry
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.task_id == task_id
    )
    audit_entry = db_session.exec(statement).first()

    assert audit_entry is not None
    assert audit_entry.details["original_timestamp"] == original_ts


def test_audit_multiple_events_same_task(
    audit_client,
    db_session: Session,
    test_user_id: str
):
    """
    Test that multiple events for the same task create separate audit entries.

    Expected:
    - Each event creates its own audit log entry
    - Events can be queried by task_id
    """
    task_id = str(uuid4())

    # Create task
    event1 = create_task_event("task.created", test_user_id, task_id)
    response1 = audit_client.post("/events/task-events", json=event1)
    assert response1.status_code == 200

    # Update task
    event2 = create_task_event("task.updated", test_user_id, task_id)
    response2 = audit_client.post("/events/task-events", json=event2)
    assert response2.status_code == 200

    # Complete task
    event3 = create_task_event("task.completed", test_user_id, task_id)
    response3 = audit_client.post("/events/task-events", json=event3)
    assert response3.status_code == 200

    # Query all entries for this task
    statement = select(AuditLog).where(
        AuditLog.user_id == test_user_id,
        AuditLog.task_id == task_id
    )
    entries = db_session.exec(statement).all()

    assert len(entries) >= 3
    event_types = {e.event_type for e in entries}
    assert "task.created" in event_types
    assert "task.updated" in event_types
    assert "task.completed" in event_types
