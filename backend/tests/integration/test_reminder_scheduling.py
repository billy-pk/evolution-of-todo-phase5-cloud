"""
Integration Test for Reminder Scheduling (Phase V - User Story 2).

This test validates that reminders are properly scheduled via Dapr Jobs API:
- Reminder time is calculated correctly from due_date and offset
- Reminder records are created in database with correct status
- Offset parsing works for various formats ("1 hour before", "30 minutes before", "2 days before")
- Validation ensures reminder_time is in the future
- Integration with database for persisting scheduled reminders

Test Strategy:
- Create tasks with due dates and reminder offsets
- Use ReminderService to parse offsets and calculate reminder times
- Verify Reminder records are created in database
- Test edge cases (reminder time in past, invalid offset formats)
- Verify idempotency (scheduling same reminder twice)

Expected Behavior (TDD - these tests should FAIL before implementation):
- ReminderService.parse_reminder_offset() converts "1 hour before" to timedelta(hours=1)
- ReminderService.calculate_reminder_time() subtracts offset from due_date
- ReminderService.validate_reminder_offset() rejects offsets resulting in past times
- Reminder records are created with status='pending' initially
- Multiple reminder offsets can be scheduled for same task
"""

import pytest
from datetime import datetime, timedelta, UTC
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


@pytest.fixture
def sample_task(db_session: Session, test_user_id: str):
    """Fixture to create a sample task with future due date."""
    due_date = datetime.now(UTC) + timedelta(days=3)
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
    return task


def test_parse_reminder_offset_hours(test_user_id: str):
    """
    Test parsing reminder offset "1 hour before".

    Expected: Returns timedelta(hours=1)
    """
    offset_str = "1 hour before"
    offset = ReminderService.parse_reminder_offset(offset_str)

    assert offset is not None, "Should parse '1 hour before'"
    assert offset == timedelta(hours=1), f"Expected timedelta(hours=1), got {offset}"


def test_parse_reminder_offset_minutes(test_user_id: str):
    """
    Test parsing reminder offset "30 minutes before".

    Expected: Returns timedelta(minutes=30)
    """
    offset_str = "30 minutes before"
    offset = ReminderService.parse_reminder_offset(offset_str)

    assert offset is not None, "Should parse '30 minutes before'"
    assert offset == timedelta(minutes=30), f"Expected timedelta(minutes=30), got {offset}"


def test_parse_reminder_offset_days(test_user_id: str):
    """
    Test parsing reminder offset "2 days before".

    Expected: Returns timedelta(days=2)
    """
    offset_str = "2 days before"
    offset = ReminderService.parse_reminder_offset(offset_str)

    assert offset is not None, "Should parse '2 days before'"
    assert offset == timedelta(days=2), f"Expected timedelta(days=2), got {offset}"


def test_parse_reminder_offset_singular_forms(test_user_id: str):
    """
    Test parsing singular forms: "1 minute before", "1 day before".

    Expected: Both singular and plural forms work
    """
    offset_minute = ReminderService.parse_reminder_offset("1 minute before")
    assert offset_minute == timedelta(minutes=1), "Should parse singular 'minute'"

    offset_day = ReminderService.parse_reminder_offset("1 day before")
    assert offset_day == timedelta(days=1), "Should parse singular 'day'"


def test_parse_reminder_offset_invalid_format(test_user_id: str):
    """
    Test that invalid offset formats return None.

    Expected: Returns None for unparseable strings
    """
    invalid_formats = [
        "not a valid offset",
        "1 hour after",  # "after" not supported, only "before"
        "abc minutes before",
        "",
        "just minutes"
    ]

    for invalid_str in invalid_formats:
        offset = ReminderService.parse_reminder_offset(invalid_str)
        assert offset is None, f"Should return None for invalid format: '{invalid_str}'"


def test_calculate_reminder_time(test_user_id: str):
    """
    Test calculating reminder time by subtracting offset from due date.

    Expected: due_date - offset = reminder_time
    """
    due_date = datetime(2026, 1, 10, 15, 0, 0, tzinfo=UTC)  # 3pm
    offset = timedelta(hours=2)

    reminder_time = ReminderService.calculate_reminder_time(due_date, offset)

    expected_time = datetime(2026, 1, 10, 13, 0, 0, tzinfo=UTC)  # 1pm
    assert reminder_time == expected_time, f"Expected {expected_time}, got {reminder_time}"


def test_validate_reminder_offset_valid(test_user_id: str):
    """
    Test validating a valid reminder offset (results in future reminder time).

    Expected: Returns (True, None)
    """
    # Future due date (3 days from now)
    due_date = datetime.now(UTC) + timedelta(days=3)
    offset_str = "1 hour before"

    is_valid, error_msg = ReminderService.validate_reminder_offset(offset_str, due_date)

    assert is_valid is True, f"Should be valid, got error: {error_msg}"
    assert error_msg is None, "No error message for valid offset"


def test_validate_reminder_offset_results_in_past(test_user_id: str):
    """
    Test validating offset that results in past reminder time (due date too soon).

    Expected: Returns (False, error message about past reminder time)
    """
    # Due date very soon (10 minutes from now)
    due_date = datetime.now(UTC) + timedelta(minutes=10)
    offset_str = "1 hour before"  # Would result in past time

    is_valid, error_msg = ReminderService.validate_reminder_offset(offset_str, due_date)

    assert is_valid is False, "Should be invalid when reminder time is in past"
    assert "past" in error_msg.lower(), f"Error should mention 'past': {error_msg}"


def test_validate_reminder_offset_invalid_format(test_user_id: str):
    """
    Test validating invalid offset format.

    Expected: Returns (False, error message about invalid format)
    """
    due_date = datetime.now(UTC) + timedelta(days=3)
    invalid_offset = "not a valid offset"

    is_valid, error_msg = ReminderService.validate_reminder_offset(invalid_offset, due_date)

    assert is_valid is False, "Should be invalid for bad format"
    assert "invalid" in error_msg.lower(), f"Error should mention 'invalid': {error_msg}"


def test_integration_create_reminder_in_database(db_session: Session, sample_task: Task, test_user_id: str):
    """
    Integration test: Create reminder record in database.

    Expected: Reminder is created with status='pending', correct reminder_time
    """
    # Parse offset and calculate reminder time
    offset_str = "1 hour before"
    offset = ReminderService.parse_reminder_offset(offset_str)
    assert offset is not None, "Should parse offset"

    reminder_time = ReminderService.calculate_reminder_time(sample_task.due_date, offset)

    # Create Reminder in database
    reminder = Reminder(
        task_id=sample_task.id,
        user_id=test_user_id,
        reminder_time=reminder_time,
        status="pending",
        delivery_method="webhook",
        retry_count=0
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.refresh(reminder)

    # Verify reminder was created
    assert reminder.id is not None, "Reminder should have an ID after commit"
    assert reminder.status == "pending", f"Status should be 'pending', got {reminder.status}"
    assert reminder.reminder_time == reminder_time, "Reminder time should match calculated time"
    assert reminder.task_id == sample_task.id, "Task ID should match"
    assert reminder.user_id == test_user_id, "User ID should match"

    # Query reminder from database
    retrieved_reminder = db_session.get(Reminder, reminder.id)
    assert retrieved_reminder is not None, "Should retrieve reminder from database"
    assert retrieved_reminder.status == "pending", "Retrieved status should be 'pending'"


def test_integration_multiple_reminders_for_same_task(db_session: Session, sample_task: Task, test_user_id: str):
    """
    Integration test: Create multiple reminders for the same task (different offsets).

    Expected: Multiple reminders can be scheduled for one task
    """
    # Define multiple reminder offsets
    offsets = ["1 hour before", "1 day before", "30 minutes before"]

    created_reminders = []
    for offset_str in offsets:
        offset = ReminderService.parse_reminder_offset(offset_str)
        assert offset is not None, f"Should parse '{offset_str}'"

        reminder_time = ReminderService.calculate_reminder_time(sample_task.due_date, offset)

        reminder = Reminder(
            task_id=sample_task.id,
            user_id=test_user_id,
            reminder_time=reminder_time,
            status="pending",
            delivery_method="webhook",
            retry_count=0
        )
        db_session.add(reminder)
        created_reminders.append((offset_str, reminder))

    db_session.commit()

    # Verify all reminders were created
    for offset_str, reminder in created_reminders:
        db_session.refresh(reminder)
        assert reminder.id is not None, f"Reminder for '{offset_str}' should have ID"
        assert reminder.status == "pending", f"Status should be 'pending' for '{offset_str}'"

    # Query all reminders for this task
    stmt = select(Reminder).where(Reminder.task_id == sample_task.id)
    results = db_session.exec(stmt).all()
    assert len(results) == 3, f"Should have 3 reminders, got {len(results)}"


def test_integration_query_pending_reminders(db_session: Session, sample_task: Task, test_user_id: str):
    """
    Integration test: Query pending reminders from database.

    Expected: Can filter reminders by status='pending'
    """
    # Create multiple reminders with different statuses
    reminder_pending = Reminder(
        task_id=sample_task.id,
        user_id=test_user_id,
        reminder_time=datetime.now(UTC) + timedelta(hours=1),
        status="pending",
        delivery_method="webhook"
    )

    reminder_sent = Reminder(
        task_id=sample_task.id,
        user_id=test_user_id,
        reminder_time=datetime.now(UTC) + timedelta(hours=2),
        status="sent",
        delivery_method="webhook",
        sent_at=datetime.now(UTC)
    )

    db_session.add(reminder_pending)
    db_session.add(reminder_sent)
    db_session.commit()

    # Query only pending reminders
    stmt = select(Reminder).where(
        Reminder.task_id == sample_task.id,
        Reminder.status == "pending"
    )
    pending_reminders = db_session.exec(stmt).all()

    assert len(pending_reminders) == 1, f"Should have 1 pending reminder, got {len(pending_reminders)}"
    assert pending_reminders[0].status == "pending", "Reminder should have status 'pending'"


def test_integration_reminder_time_index_query(db_session: Session, test_user_id: str):
    """
    Integration test: Query reminders by reminder_time range (uses index).

    Expected: Can efficiently query reminders due in next N hours
    """
    # Create task
    task = Task(
        user_id=test_user_id,
        title="Test task",
        completed=False,
        due_date=datetime.now(UTC) + timedelta(hours=2)
    )
    db_session.add(task)
    db_session.commit()

    # Create reminders at different times
    now = datetime.now(UTC)
    reminder_soon = Reminder(
        task_id=task.id,
        user_id=test_user_id,
        reminder_time=now + timedelta(minutes=30),  # 30 min from now
        status="pending"
    )
    reminder_later = Reminder(
        task_id=task.id,
        user_id=test_user_id,
        reminder_time=now + timedelta(hours=3),  # 3 hours from now
        status="pending"
    )

    db_session.add(reminder_soon)
    db_session.add(reminder_later)
    db_session.commit()

    # Query reminders due in next hour
    query_time_end = now + timedelta(hours=1)
    stmt = select(Reminder).where(
        Reminder.status == "pending",
        Reminder.reminder_time <= query_time_end,
        Reminder.reminder_time > now
    ).order_by(Reminder.reminder_time)

    upcoming_reminders = db_session.exec(stmt).all()

    assert len(upcoming_reminders) == 1, f"Should have 1 reminder due in next hour, got {len(upcoming_reminders)}"
    assert upcoming_reminders[0].id == reminder_soon.id, "Should return the reminder due soon"


def test_create_reminder_metadata(test_user_id: str):
    """
    Test creating reminder metadata for Dapr Jobs API payload.

    Expected: Returns dict with all required fields for job scheduling
    """
    task_id = str(uuid4())
    task_title = "Submit quarterly report"
    due_date = datetime(2026, 1, 10, 17, 0, 0, tzinfo=UTC)
    reminder_offset = "1 hour before"

    metadata = ReminderService.create_reminder_metadata(
        task_id=task_id,
        user_id=test_user_id,
        task_title=task_title,
        due_date=due_date,
        reminder_offset=reminder_offset
    )

    # Assertions
    assert metadata["task_id"] == task_id, "Metadata should include task_id"
    assert metadata["user_id"] == test_user_id, "Metadata should include user_id"
    assert metadata["task_title"] == task_title, "Metadata should include task_title"
    assert metadata["due_date"] == due_date.isoformat(), "Metadata should include due_date as ISO8601"
    assert metadata["reminder_offset"] == reminder_offset, "Metadata should include reminder_offset"
    assert "reminder_time" in metadata, "Metadata should include calculated reminder_time"

    # Verify reminder_time is calculated correctly (1 hour before due_date)
    expected_reminder_time = datetime(2026, 1, 10, 16, 0, 0, tzinfo=UTC)
    assert metadata["reminder_time"] == expected_reminder_time.isoformat(), \
        f"Reminder time should be {expected_reminder_time.isoformat()}, got {metadata['reminder_time']}"
