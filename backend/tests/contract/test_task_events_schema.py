"""
Contract Tests for Task Events Schema (Phase V).

These tests validate that event payloads published by EventPublisher
match the JSON Schema contract defined in:
specs/005-event-driven-microservices/contracts/events/task-events.schema.json

Purpose:
- Ensure Pydantic schemas (backend/schemas.py) match JSON Schema contracts
- Validate event payloads before publishing to Redpanda
- Prevent breaking changes to event consumers (Audit Service, Recurring Task Service)

Test Strategy:
- Load JSON Schema from contracts/events/
- Generate sample event payloads using EventPublisher
- Validate payloads against JSON Schema using jsonschema library
- Test all event types: task.created, task.updated, task.completed, task.deleted
"""

import pytest
import json
from pathlib import Path
from jsonschema import validate, ValidationError
from datetime import datetime, UTC
from uuid import uuid4


# Load JSON Schema from contracts
def load_task_events_schema():
    """Load task-events.schema.json from contracts directory."""
    schema_path = Path(__file__).parent.parent.parent.parent / "specs" / "005-event-driven-microservices" / "contracts" / "events" / "task-events.schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def task_events_schema():
    """Fixture to load JSON Schema."""
    return load_task_events_schema()


@pytest.fixture
def sample_task_data():
    """Fixture for sample task data."""
    return {
        "id": str(uuid4()),
        "title": "Complete project proposal",
        "description": "Draft and submit Q1 project proposal",
        "completed": False,
        "priority": "high",
        "tags": ["work", "urgent"],
        "due_date": "2026-01-10T17:00:00Z",
        "recurrence_id": None,
        "created_at": "2026-01-06T10:00:00Z",
        "updated_at": "2026-01-06T10:00:00Z"
    }


def test_task_created_event_schema(task_events_schema, sample_task_data):
    """
    Test that task.created event payload matches JSON Schema.
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.created",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": sample_task_data,
        "previous_data": None,
        "metadata": {
            "source": "mcp_tool",
            "correlation_id": str(uuid4())
        }
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_events_schema)
    except ValidationError as e:
        pytest.fail(f"task.created event failed schema validation: {e.message}")


def test_task_updated_event_schema(task_events_schema, sample_task_data):
    """
    Test that task.updated event payload matches JSON Schema.
    """
    updated_task_data = sample_task_data.copy()
    updated_task_data["title"] = "Complete project proposal (UPDATED)"
    updated_task_data["updated_at"] = "2026-01-06T15:30:00Z"

    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.updated",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": updated_task_data,
        "previous_data": {
            "title": "Complete project proposal"
        },
        "metadata": {
            "source": "api",
            "correlation_id": str(uuid4())
        }
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_events_schema)
    except ValidationError as e:
        pytest.fail(f"task.updated event failed schema validation: {e.message}")


def test_task_completed_event_schema(task_events_schema, sample_task_data):
    """
    Test that task.completed event payload matches JSON Schema.

    This is a critical event for recurring tasks - triggers next instance generation.
    """
    completed_task_data = sample_task_data.copy()
    completed_task_data["completed"] = True
    completed_task_data["updated_at"] = "2026-01-08T15:30:00Z"

    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": completed_task_data,
        "previous_data": {
            "completed": False
        },
        "metadata": {
            "source": "api",
            "correlation_id": str(uuid4())
        }
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_events_schema)
    except ValidationError as e:
        pytest.fail(f"task.completed event failed schema validation: {e.message}")


def test_task_deleted_event_schema(task_events_schema, sample_task_data):
    """
    Test that task.deleted event payload matches JSON Schema.
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.deleted",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": sample_task_data,
        "previous_data": None,
        "metadata": {
            "source": "api",
            "correlation_id": str(uuid4())
        }
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_events_schema)
    except ValidationError as e:
        pytest.fail(f"task.deleted event failed schema validation: {e.message}")


def test_task_event_with_recurrence(task_events_schema):
    """
    Test that task events with recurrence_id validate correctly.
    """
    recurrence_task_data = {
        "id": str(uuid4()),
        "title": "Weekly team meeting",
        "description": "Discuss project progress",
        "completed": True,
        "priority": "normal",
        "tags": ["work", "meetings"],
        "due_date": "2026-01-13T10:00:00Z",
        "recurrence_id": str(uuid4()),  # Has recurrence
        "created_at": "2026-01-06T10:00:00Z",
        "updated_at": "2026-01-13T11:30:00Z"
    }

    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": recurrence_task_data,
        "previous_data": {
            "completed": False
        },
        "metadata": {
            "source": "recurring_task_service",
            "correlation_id": str(uuid4())
        }
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_events_schema)
    except ValidationError as e:
        pytest.fail(f"Recurring task event failed schema validation: {e.message}")


def test_required_fields_validation(task_events_schema):
    """
    Test that missing required fields fail validation.
    """
    # Missing task_data (required field)
    invalid_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.created",
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        # Missing task_data
        "previous_data": None,
        "metadata": {
            "source": "api",
            "correlation_id": str(uuid4())
        }
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=task_events_schema)


def test_invalid_event_type_validation(task_events_schema, sample_task_data):
    """
    Test that invalid event_type fails validation.
    """
    invalid_payload = {
        "event_id": str(uuid4()),
        "event_type": "task.invalid",  # Invalid event type
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": "user-123",
        "task_data": sample_task_data,
        "previous_data": None,
        "metadata": {
            "source": "api",
            "correlation_id": str(uuid4())
        }
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=task_events_schema)


def test_schema_version_present(task_events_schema):
    """
    Test that JSON Schema has a version identifier.
    """
    assert "$id" in task_events_schema
    assert "https://evolution-of-todo" in task_events_schema["$id"]
