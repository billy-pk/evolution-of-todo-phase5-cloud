"""
Integration Test for Due Date Validation (Phase V - User Story 2).

This test validates that tasks with due dates are properly validated:
- Future due dates are accepted
- Past due dates are rejected (unless allow_past=True)
- Timezone-aware dates are required
- Natural language date parsing works correctly

Test Strategy:
- Use ReminderService to validate due dates
- Test both absolute (ISO8601) and natural language dates
- Verify error messages for invalid dates
- Test allow_past flag behavior

Expected Behavior (TDD - these tests should FAIL before implementation):
- ReminderService.validate_due_date() rejects past dates by default
- ReminderService.validate_due_date() accepts past dates when allow_past=True
- ReminderService.parse_natural_language_date() converts "tomorrow" to ISO8601
- Timezone-naive dates are rejected with clear error message
"""

import pytest
from datetime import datetime, timedelta, UTC, timezone
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import Task, Reminder
from services.reminder_service import ReminderService


@pytest.fixture
def db_session():
    """Fixture to provide a clean database session for each test."""
    with Session(engine) as session:
        yield session
        # Cleanup after test
        session.rollback()


@pytest.fixture
def test_user_id():
    """Fixture for test user ID."""
    return f"test-user-{uuid4()}"


def test_validate_future_due_date(test_user_id: str):
    """
    Test that future due dates are accepted.

    Expected: validate_due_date returns (True, None) for future dates
    """
    # Create a future due date (tomorrow at 5pm)
    future_due_date = datetime.now(UTC) + timedelta(days=1)
    future_due_date = future_due_date.replace(hour=17, minute=0, second=0, microsecond=0)

    # Validate
    is_valid, error_message = ReminderService.validate_due_date(future_due_date)

    # Assertions
    assert is_valid is True, f"Future due date should be valid, got error: {error_message}"
    assert error_message is None, "No error message should be returned for valid date"


def test_validate_past_due_date_rejected(test_user_id: str):
    """
    Test that past due dates are rejected by default.

    Expected: validate_due_date returns (False, "Due date must be in the future")
    """
    # Create a past due date (yesterday)
    past_due_date = datetime.now(UTC) - timedelta(days=1)

    # Validate
    is_valid, error_message = ReminderService.validate_due_date(past_due_date)

    # Assertions
    assert is_valid is False, "Past due date should be rejected"
    assert error_message == "Due date must be in the future", f"Expected specific error message, got: {error_message}"


def test_validate_past_due_date_allowed(test_user_id: str):
    """
    Test that past due dates are accepted when allow_past=True.

    Expected: validate_due_date returns (True, None) when allow_past=True
    """
    # Create a past due date (yesterday)
    past_due_date = datetime.now(UTC) - timedelta(days=1)

    # Validate with allow_past=True
    is_valid, error_message = ReminderService.validate_due_date(past_due_date, allow_past=True)

    # Assertions
    assert is_valid is True, f"Past due date should be valid when allow_past=True, got error: {error_message}"
    assert error_message is None, "No error message should be returned when allow_past=True"


def test_validate_timezone_naive_date_rejected(test_user_id: str):
    """
    Test that timezone-naive dates are rejected with clear error message.

    Expected: validate_due_date returns (False, "Due date must be timezone-aware...")
    """
    # Create a timezone-naive datetime
    naive_date = datetime.now()  # No tzinfo

    # Validate
    is_valid, error_message = ReminderService.validate_due_date(naive_date)

    # Assertions
    assert is_valid is False, "Timezone-naive date should be rejected"
    assert "timezone-aware" in error_message, f"Error message should mention timezone requirement, got: {error_message}"


def test_parse_natural_language_date_tomorrow(test_user_id: str):
    """
    Test parsing natural language date "tomorrow at 5pm".

    Expected: Returns timezone-aware datetime for tomorrow at 17:00 UTC
    """
    # Parse natural language date
    parsed_date = ReminderService.parse_natural_language_date("tomorrow at 5pm")

    # Assertions
    assert parsed_date is not None, "Should successfully parse 'tomorrow at 5pm'"
    assert parsed_date.tzinfo is not None, "Parsed date should be timezone-aware"
    assert parsed_date > datetime.now(UTC), "Parsed date should be in the future"
    assert parsed_date.hour == 17, f"Hour should be 17 (5pm), got {parsed_date.hour}"


def test_parse_natural_language_date_next_week(test_user_id: str):
    """
    Test parsing natural language date "next Friday at 3pm".

    Expected: Returns timezone-aware datetime for next Friday at 15:00
    """
    # Parse natural language date
    parsed_date = ReminderService.parse_natural_language_date("next Friday at 3pm")

    # Assertions
    assert parsed_date is not None, "Should successfully parse 'next Friday at 3pm'"
    assert parsed_date.tzinfo is not None, "Parsed date should be timezone-aware"
    assert parsed_date > datetime.now(UTC), "Parsed date should be in the future"
    assert parsed_date.hour == 15, f"Hour should be 15 (3pm), got {parsed_date.hour}"
    assert parsed_date.weekday() == 4, f"Should be Friday (weekday 4), got {parsed_date.weekday()}"


def test_parse_natural_language_date_iso8601_passthrough(test_user_id: str):
    """
    Test that ISO8601 dates are parsed correctly (passthrough).

    Expected: ISO8601 string "2026-01-15T17:00:00Z" is parsed to datetime
    """
    # ISO8601 date string
    iso_date_str = "2026-01-15T17:00:00Z"

    # Parse
    parsed_date = ReminderService.parse_natural_language_date(iso_date_str)

    # Assertions
    assert parsed_date is not None, "Should successfully parse ISO8601 date"
    assert parsed_date.tzinfo is not None, "Parsed date should be timezone-aware"
    assert parsed_date.year == 2026, f"Year should be 2026, got {parsed_date.year}"
    assert parsed_date.month == 1, f"Month should be 1, got {parsed_date.month}"
    assert parsed_date.day == 15, f"Day should be 15, got {parsed_date.day}"
    assert parsed_date.hour == 17, f"Hour should be 17, got {parsed_date.hour}"


def test_parse_natural_language_date_invalid(test_user_id: str):
    """
    Test that invalid date strings return None.

    Expected: Returns None for unparseable strings
    """
    # Invalid date string
    invalid_str = "not a valid date format xyz"

    # Parse
    parsed_date = ReminderService.parse_natural_language_date(invalid_str)

    # Assertions
    assert parsed_date is None, "Should return None for invalid date string"


def test_integration_create_task_with_future_due_date(db_session: Session, test_user_id: str):
    """
    Integration test: Create a task with a future due date in database.

    Expected: Task is successfully created with due_date field populated
    """
    # Parse natural language due date
    due_date = ReminderService.parse_natural_language_date("tomorrow at 5pm")
    assert due_date is not None, "Should parse 'tomorrow at 5pm'"

    # Validate due date
    is_valid, error_msg = ReminderService.validate_due_date(due_date)
    assert is_valid is True, f"Due date should be valid: {error_msg}"

    # Create task in database
    task = Task(
        user_id=test_user_id,
        title="Submit quarterly report",
        description="Q4 2025 financial report",
        completed=False,
        priority="high",
        tags=["work", "urgent"],
        due_date=due_date
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify task was created
    assert task.id is not None, "Task should have an ID after commit"
    assert task.due_date == due_date, f"Due date should match, expected {due_date}, got {task.due_date}"
    assert task.due_date.tzinfo is not None, "Stored due date should be timezone-aware"

    # Query task from database
    retrieved_task = db_session.get(Task, task.id)
    assert retrieved_task is not None, "Should retrieve task from database"
    assert retrieved_task.due_date == due_date, "Retrieved due date should match"


def test_integration_reject_task_with_past_due_date(db_session: Session, test_user_id: str):
    """
    Integration test: Validate that application logic rejects past due dates.

    Expected: validate_due_date returns False for past dates
    """
    # Create past due date
    past_due_date = datetime.now(UTC) - timedelta(days=1)

    # Validate (should fail)
    is_valid, error_msg = ReminderService.validate_due_date(past_due_date)
    assert is_valid is False, "Past due date should be rejected"
    assert "future" in error_msg.lower(), f"Error should mention 'future': {error_msg}"

    # Application logic should NOT create task with past due date
    # This simulates what the MCP tool add_task should do
    if not is_valid:
        # Don't create task, validation failed
        logger_msg = f"Skipped task creation due to validation error: {error_msg}"
        assert True, logger_msg
    else:
        pytest.fail("Should not reach here - past due date should be rejected")


def test_validate_due_date_with_custom_reference_time(test_user_id: str):
    """
    Test validate_due_date with custom reference time (for testing).

    Expected: Can override reference time for deterministic tests
    """
    # Fixed reference time (2026-01-10 12:00:00 UTC)
    reference_time = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)

    # Due date before reference time (should fail)
    past_due = datetime(2026, 1, 9, 12, 0, 0, tzinfo=UTC)
    is_valid, error_msg = ReminderService.validate_due_date(past_due, reference_time=reference_time)
    assert is_valid is False, "Due date before reference time should be rejected"

    # Due date after reference time (should pass)
    future_due = datetime(2026, 1, 11, 12, 0, 0, tzinfo=UTC)
    is_valid, error_msg = ReminderService.validate_due_date(future_due, reference_time=reference_time)
    assert is_valid is True, f"Due date after reference time should be valid: {error_msg}"
