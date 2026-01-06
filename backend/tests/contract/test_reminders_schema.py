"""
Contract Tests for Reminders Schema (Phase V).

These tests validate that reminder event payloads match the JSON Schema contract:
specs/005-event-driven-microservices/contracts/events/reminders.schema.json

Purpose:
- Ensure reminder events from ReminderService match schema
- Validate Notification Service can consume events
- Test reminder lifecycle: scheduled → triggered → delivered/failed

Test Strategy:
- Load JSON Schema from contracts/events/
- Generate sample reminder events
- Validate all reminder event types: reminder.scheduled, reminder.triggered, reminder.delivered, reminder.failed
- Test retry logic (retry_count 0-3)
"""

import pytest
import json
from pathlib import Path
from jsonschema import validate, ValidationError
from datetime import datetime, UTC
from uuid import uuid4


def load_reminders_schema():
    """Load reminders.schema.json from contracts directory."""
    schema_path = Path(__file__).parent.parent.parent.parent / "specs" / "005-event-driven-microservices" / "contracts" / "events" / "reminders.schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def reminders_schema():
    """Fixture to load JSON Schema."""
    return load_reminders_schema()


@pytest.fixture
def sample_task_data():
    """Fixture for task data included in reminder events."""
    return {
        "title": "Submit quarterly report",
        "description": "Q4 2025 financial report",
        "due_date": "2026-01-13T17:00:00Z",
        "priority": "high"
    }


def test_reminder_scheduled_event_schema(reminders_schema, sample_task_data):
    """
    Test that reminder.scheduled event payload matches JSON Schema.

    This event is published when a reminder is created and scheduled via Dapr Jobs API.
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.scheduled",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=reminders_schema)
    except ValidationError as e:
        pytest.fail(f"reminder.scheduled event failed schema validation: {e.message}")


def test_reminder_triggered_event_schema(reminders_schema, sample_task_data):
    """
    Test that reminder.triggered event payload matches JSON Schema.

    This event is published when Dapr Jobs API triggers the reminder at scheduled time.
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.triggered",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=reminders_schema)
    except ValidationError as e:
        pytest.fail(f"reminder.triggered event failed schema validation: {e.message}")


def test_reminder_delivered_event_schema(reminders_schema, sample_task_data):
    """
    Test that reminder.delivered event payload matches JSON Schema.

    This event is published after successful delivery via webhook.
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.delivered",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=reminders_schema)
    except ValidationError as e:
        pytest.fail(f"reminder.delivered event failed schema validation: {e.message}")


def test_reminder_failed_event_schema(reminders_schema, sample_task_data):
    """
    Test that reminder.failed event payload matches JSON Schema.

    This event is published after all retries fail (max 3 retries).
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.failed",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 3,  # Max retries reached
        "error_message": "Webhook endpoint returned 503 Service Unavailable after 3 retries",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=reminders_schema)
    except ValidationError as e:
        pytest.fail(f"reminder.failed event failed schema validation: {e.message}")


def test_reminder_retry_logic(reminders_schema, sample_task_data):
    """
    Test reminder events with different retry counts (0-3).
    """
    for retry_count in range(4):  # 0, 1, 2, 3
        event_payload = {
            "event_id": str(uuid4()),
            "event_type": "reminder.failed" if retry_count == 3 else "reminder.triggered",
            "reminder_id": str(uuid4()),
            "task_id": str(uuid4()),
            "user_id": "user-123",
            "reminder_time": "2026-01-13T09:00:00Z",
            "task_data": sample_task_data,
            "delivery_method": "webhook",
            "retry_count": retry_count,
            "error_message": f"Retry attempt {retry_count} failed" if retry_count > 0 else None,
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
        }

        # Validate against JSON Schema
        try:
            validate(instance=event_payload, schema=reminders_schema)
        except ValidationError as e:
            pytest.fail(f"Reminder event with retry_count={retry_count} failed schema validation: {e.message}")


def test_reminder_email_delivery_method(reminders_schema, sample_task_data):
    """
    Test reminder event with email delivery method (future feature).
    """
    event_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.scheduled",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "email",  # Email delivery
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    # Validate against JSON Schema
    try:
        validate(instance=event_payload, schema=reminders_schema)
    except ValidationError as e:
        pytest.fail(f"Reminder event with email delivery failed schema validation: {e.message}")


def test_required_fields_validation(reminders_schema):
    """
    Test that missing required fields fail validation.
    """
    # Missing reminder_time (required field)
    invalid_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.scheduled",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        # Missing reminder_time
        "task_data": {},
        "delivery_method": "webhook",
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=reminders_schema)


def test_invalid_event_type_validation(reminders_schema, sample_task_data):
    """
    Test that invalid event_type fails validation.
    """
    invalid_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.invalid",  # Invalid event type
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 0,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=reminders_schema)


def test_retry_count_validation(reminders_schema, sample_task_data):
    """
    Test that retry_count outside valid range (0-3) fails validation.
    """
    invalid_payload = {
        "event_id": str(uuid4()),
        "event_type": "reminder.failed",
        "reminder_id": str(uuid4()),
        "task_id": str(uuid4()),
        "user_id": "user-123",
        "reminder_time": "2026-01-13T09:00:00Z",
        "task_data": sample_task_data,
        "delivery_method": "webhook",
        "retry_count": 4,  # Exceeds max (3)
        "error_message": "Too many retries",
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0"
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_payload, schema=reminders_schema)


def test_schema_version_present(reminders_schema):
    """
    Test that JSON Schema has a version identifier.
    """
    assert "$id" in reminders_schema
    assert "https://evolution-of-todo" in reminders_schema["$id"]
