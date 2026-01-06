"""
Integration Test for Recurring Task Creation (Phase V - User Story 1).

This test validates that tasks can be created with recurrence parameters and that
a RecurrenceRule is properly stored in the database.

Test Strategy:
- Create a task with recurrence parameters (pattern: daily, interval: 1)
- Verify task is created with recurrence_id
- Verify RecurrenceRule is created in database
- Verify RecurrenceRule has correct pattern and interval
- Test all recurrence patterns: daily, weekly, monthly

Expected Behavior (TDD - these tests should FAIL before implementation):
- MCP tool add_task should accept recurrence_pattern and recurrence_interval parameters
- Task should have recurrence_id foreign key to RecurrenceRule
- RecurrenceRule should store pattern, interval, and metadata
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import Task, RecurrenceRule


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


def test_create_task_with_daily_recurrence(db_session: Session, test_user_id: str):
    """
    Test creating a task with daily recurrence pattern.

    Expected: Task created with recurrence_id pointing to RecurrenceRule with pattern='daily', interval=1
    """
    # Create RecurrenceRule
    recurrence_rule = RecurrenceRule(
        id=uuid4(),
        pattern="daily",
        interval=1,
        metadata={}
    )
    db_session.add(recurrence_rule)
    db_session.commit()
    db_session.refresh(recurrence_rule)

    # Create Task with recurrence
    task = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="Daily standup meeting",
        description="Team sync every day",
        completed=False,
        priority="normal",
        tags=["work", "meetings"],
        recurrence_id=recurrence_rule.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify task created with recurrence_id
    assert task.recurrence_id is not None
    assert task.recurrence_id == recurrence_rule.id

    # Verify RecurrenceRule exists in database
    statement = select(RecurrenceRule).where(RecurrenceRule.id == recurrence_rule.id)
    result = db_session.exec(statement).first()

    assert result is not None
    assert result.pattern == "daily"
    assert result.interval == 1
    assert result.metadata == {}


def test_create_task_with_weekly_recurrence(db_session: Session, test_user_id: str):
    """
    Test creating a task with weekly recurrence pattern.

    Expected: Task created with recurrence_id pointing to RecurrenceRule with pattern='weekly', interval=2
    """
    # Create RecurrenceRule for bi-weekly recurrence
    recurrence_rule = RecurrenceRule(
        id=uuid4(),
        pattern="weekly",
        interval=2,  # Every 2 weeks
        metadata={"weekday": "Monday"}
    )
    db_session.add(recurrence_rule)
    db_session.commit()
    db_session.refresh(recurrence_rule)

    # Create Task with recurrence
    task = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="Bi-weekly team retrospective",
        description="Review sprint progress",
        completed=False,
        priority="high",
        tags=["work", "retrospective"],
        recurrence_id=recurrence_rule.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify task created with recurrence_id
    assert task.recurrence_id is not None
    assert task.recurrence_id == recurrence_rule.id

    # Verify RecurrenceRule
    statement = select(RecurrenceRule).where(RecurrenceRule.id == recurrence_rule.id)
    result = db_session.exec(statement).first()

    assert result is not None
    assert result.pattern == "weekly"
    assert result.interval == 2
    assert result.metadata == {"weekday": "Monday"}


def test_create_task_with_monthly_recurrence(db_session: Session, test_user_id: str):
    """
    Test creating a task with monthly recurrence pattern.

    Expected: Task created with recurrence_id pointing to RecurrenceRule with pattern='monthly', interval=1
    """
    # Create RecurrenceRule for monthly recurrence
    recurrence_rule = RecurrenceRule(
        id=uuid4(),
        pattern="monthly",
        interval=1,
        metadata={"day_of_month": 1}  # First day of month
    )
    db_session.add(recurrence_rule)
    db_session.commit()
    db_session.refresh(recurrence_rule)

    # Create Task with recurrence
    task = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="Monthly expense report",
        description="Submit expense report to finance",
        completed=False,
        priority="high",
        tags=["work", "finance"],
        recurrence_id=recurrence_rule.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify task created with recurrence_id
    assert task.recurrence_id is not None
    assert task.recurrence_id == recurrence_rule.id

    # Verify RecurrenceRule
    statement = select(RecurrenceRule).where(RecurrenceRule.id == recurrence_rule.id)
    result = db_session.exec(statement).first()

    assert result is not None
    assert result.pattern == "monthly"
    assert result.interval == 1
    assert result.metadata == {"day_of_month": 1}


def test_create_task_without_recurrence(db_session: Session, test_user_id: str):
    """
    Test creating a task without recurrence (null recurrence_id).

    Expected: Task created with recurrence_id=None
    """
    task = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="One-time task",
        description="This task does not repeat",
        completed=False,
        priority="normal",
        tags=["personal"],
        recurrence_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify task created without recurrence
    assert task.recurrence_id is None


def test_multiple_tasks_share_same_recurrence_rule(db_session: Session, test_user_id: str):
    """
    Test that multiple tasks can share the same RecurrenceRule.

    Expected: Multiple tasks can reference the same recurrence_id
    """
    # Create one RecurrenceRule
    recurrence_rule = RecurrenceRule(
        id=uuid4(),
        pattern="daily",
        interval=1,
        metadata={}
    )
    db_session.add(recurrence_rule)
    db_session.commit()
    db_session.refresh(recurrence_rule)

    # Create two tasks with same recurrence
    task1 = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="Daily task 1",
        description="First daily task",
        completed=False,
        recurrence_id=recurrence_rule.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    task2 = Task(
        id=uuid4(),
        user_id=test_user_id,
        title="Daily task 2",
        description="Second daily task",
        completed=False,
        recurrence_id=recurrence_rule.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    db_session.add(task1)
    db_session.add(task2)
    db_session.commit()
    db_session.refresh(task1)
    db_session.refresh(task2)

    # Verify both tasks share same recurrence_id
    assert task1.recurrence_id == recurrence_rule.id
    assert task2.recurrence_id == recurrence_rule.id
    assert task1.recurrence_id == task2.recurrence_id
