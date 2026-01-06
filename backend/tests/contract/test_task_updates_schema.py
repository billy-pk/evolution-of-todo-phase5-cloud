"""
Contract Tests for Task Updates Schema (Phase V).

These tests validate that WebSocket update payloads match the JSON Schema contract:
specs/005-event-driven-microservices/contracts/events/task-updates.schema.json

Purpose:
- Ensure real-time UI update events match schema
- Validate WebSocket Service can consume and broadcast events
- Test all update types for different task operations

Test Strategy:
- Load JSON Schema from contracts/events/
- Generate sample task update events
- Validate all update_type values: task_created, task_updated, task_completed, task_deleted, task_recurring_generated
- Test source attribution (user_action, system_generated, recurring_task_service)
"""

import pytest
import json
from pathlib import Path
from jsonschema import validate, ValidationError
from datetime import datetime, UTC
from uuid import uuid4


def load_task_updates_schema():
    """Load task-updates.schema.json from contracts directory."""
    schema_path = Path(__file__).parent.parent.parent.parent / "specs" / "005-event-driven-microservices" / "contracts" / "events" / "task-updates.schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def task_updates_schema():
    """Fixture to load JSON Schema."""
    return load_task_updates_schema()


@pytest.fixture
def sample_task_data():
    """Fixture for full task object in update events."""
    return {
        "id": str(uuid4()),
        "title": "Submit quarterly report",
        "description": "Q4 2025 financial report",
        "completed": False,
        "priority": "high",
        "tags": ["work", "urgent"],
        "due_date": "2026-01-13T17:00:00Z",
        "recurrence_id": None,
        "created_at": "2026-01-06T10:00:00Z",
        "updated_at": "2026-01-06T10:00:00Z"
    }


def test_task_created_update_schema(task_updates_schema, sample_task_data):
    """
    Test that task_created update event matches JSON Schema.

    Broadcast to WebSocket clients when a new task is created.
    """
    event_payload = {
        "update_type": "task_created",
        "event_id": str(uuid4()),
        "task_id": sample_task_data["id"],
        "user_id": "user-123",
        "task_data": sample_task_data,
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_updates_schema)
    except ValidationError as e:
        pytest.fail(f"task_created update failed schema validation: {e.message}")


def test_task_updated_update_schema(task_updates_schema, sample_task_data):
    """
    Test that task_updated update event matches JSON Schema.

    Broadcast to WebSocket clients when a task is modified.
    """
    updated_task_data = sample_task_data.copy()
    updated_task_data["title"] = "Submit quarterly report (UPDATED)"
    updated_task_data["updated_at"] = "2026-01-06T15:30:00Z"

    event_payload = {
        "update_type": "task_updated",
        "event_id": str(uuid4()),
        "task_id": updated_task_data["id"],
        "user_id": "user-123",
        "task_data": updated_task_data,
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_updates_schema)
    except ValidationError as e:
        pytest.fail(f"task_updated update failed schema validation: {e.message}")


def test_task_completed_update_schema(task_updates_schema, sample_task_data):
    """
    Test that task_completed update event matches JSON Schema.

    Broadcast to WebSocket clients when a task is marked complete.
    """
    completed_task_data = sample_task_data.copy()
    completed_task_data["completed"] = True
    completed_task_data["updated_at"] = "2026-01-13T16:45:00Z"

    event_payload = {
        "update_type": "task_completed",
        "event_id": str(uuid4()),
        "task_id": completed_task_data["id"],
        "user_id": "user-123",
        "task_data": completed_task_data,
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_updates_schema)
    except ValidationError as e:
        pytest.fail(f"task_completed update failed schema validation: {e.message}")


def test_task_deleted_update_schema(task_updates_schema):
    """
    Test that task_deleted update event matches JSON Schema.

    Broadcast to WebSocket clients when a task is deleted.
    Note: task_data is null for delete events.
    """
    event_payload = {
        "update_type": "task_deleted",
        "event_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "task_data": None,  # Null for delete
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_updates_schema)
    except ValidationError as e:
        pytest.fail(f"task_deleted update failed schema validation: {e.message}")


def test_task_recurring_generated_update_schema(task_updates_schema):
    """
    Test that task_recurring_generated update event matches JSON Schema.

    Broadcast when Recurring Task Service generates next instance.
    Source is 'recurring_task_service' to differentiate from user actions.
    """
    recurring_task_data = {
        "id": str(uuid4()),
        "title": "Weekly team meeting",
        "description": "Discuss project progress",
        "completed": False,
        "priority": "normal",
        "tags": ["work", "meetings"],
        "due_date": "2026-01-20T10:00:00Z",
        "recurrence_id": str(uuid4()),  # Has recurrence
        "created_at": "2026-01-13T11:30:00Z",
        "updated_at": "2026-01-13T11:30:00Z"
    }

    event_payload = {
        "update_type": "task_recurring_generated",
        "event_id": str(uuid4()),
        "task_id": recurring_task_data["id"],
        "user_id": "user-123",
        "task_data": recurring_task_data,
        "source": "recurring_task_service",  # System-generated
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=task_updates_schema)
    except ValidationError as e:
        pytest.fail(f"task_recurring_generated update failed schema validation: {e.message}")


def test_source_types(task_updates_schema, sample_task_data):
    """
    Test all valid source types: user_action, system_generated, recurring_task_service.
    """
    sources = ["user_action", "system_generated", "recurring_task_service"]

    for source in sources:
        event_payload = {
            "update_type": "task_created",
            "event_id": str(uuid4()),
            "task_id": sample_task_data["id"],
            "user_id": "user-123",
            "task_data": sample_task_data,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
        }

        # Validate against JSON Schema
        try:
            validate(instance=event_payload, schema=task_updates_schema)
        except ValidationError as e:
            pytest.fail(f"Update event with source='{source}' failed schema validation: {e.message}")


def test_required_fields_validation(task_updates_schema):
    """
    Test that missing required fields fail validation.
    """
    # Missing user_id (required field)
    invalid_payload = {
        "update_type": "task_created",
        "event_id": str(uuid4()),
        "task_id": str(uuid4()),
        # Missing user_id
        "task_data": {},
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=task_updates_schema)


def test_invalid_update_type_validation(task_updates_schema, sample_task_data):
    """
    Test that invalid update_type fails validation.
    """
    invalid_payload = {
        "update_type": "task_invalid",  # Invalid update type
        "event_id": str(uuid4()),
        "task_id": sample_task_data["id"],
        "user_id": "user-123",
        "task_data": sample_task_data,
        "source": "user_action",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=task_updates_schema)


def test_invalid_source_validation(task_updates_schema, sample_task_data):
    """
    Test that invalid source value fails validation.
    """
    invalid_payload = {
        "update_type": "task_created",
        "event_id": str(uuid4()),
        "task_id": sample_task_data["id"],
        "user_id": "user-123",
        "task_data": sample_task_data,
        "source": "invalid_source",  # Invalid source
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=task_updates_schema)


def test_schema_version_present(task_updates_schema):
    """
    Test that JSON Schema has a version identifier.
    """
    assert "$id" in task_updates_schema
    assert "https://evolution-of-todo" in task_updates_schema["$id"]
