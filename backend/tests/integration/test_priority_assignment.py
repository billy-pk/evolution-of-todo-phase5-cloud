"""
Integration Test for Priority Assignment (Phase V - User Story 4).

This test validates that priorities can be assigned and updated on tasks:
- Create task with priority (low, normal, high, critical)
- Update task priority
- Default priority is "normal"
- Invalid priorities are rejected
- Priority preserved through recurrence

Test Strategy:
- Create tasks with different priorities using add_task
- Update task priorities using update_task
- Verify priority is stored and returned correctly
- Test validation for invalid priority values

Expected Behavior:
- priority parameter accepts: low, normal, high, critical
- Default priority is "normal" when not specified
- Invalid priority values return error
- Priority is preserved in task responses
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import Task
from tools.server import add_task, update_task, list_tasks


@pytest.fixture
def db_session():
    """Fixture to provide a clean database session for each test."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def test_user_id():
    """Fixture for unique test user ID."""
    return f"test-user-{uuid4()}"


def test_create_task_with_low_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task with low priority.

    Expected: Task is created with priority="low"
    """
    result = add_task(
        user_id=test_user_id,
        title="Low priority task",
        priority="low",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["priority"] == "low"


def test_create_task_with_normal_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task with normal priority.

    Expected: Task is created with priority="normal"
    """
    result = add_task(
        user_id=test_user_id,
        title="Normal priority task",
        priority="normal",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["priority"] == "normal"


def test_create_task_with_high_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task with high priority.

    Expected: Task is created with priority="high"
    """
    result = add_task(
        user_id=test_user_id,
        title="High priority task",
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["priority"] == "high"


def test_create_task_with_critical_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task with critical priority.

    Expected: Task is created with priority="critical"
    """
    result = add_task(
        user_id=test_user_id,
        title="Critical priority task",
        priority="critical",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["priority"] == "critical"


def test_create_task_default_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task without specifying priority.

    Expected: Task is created with default priority="normal"
    """
    result = add_task(
        user_id=test_user_id,
        title="Task without priority",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["priority"] == "normal"


def test_create_task_invalid_priority(db_session: Session, test_user_id: str):
    """
    Test creating a task with invalid priority.

    Expected: Returns error
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with invalid priority",
        priority="urgent",  # Invalid - should be low/normal/high/critical
        _session=db_session
    )

    assert result["status"] == "error"
    assert "priority" in result["error"].lower()


def test_update_task_priority(db_session: Session, test_user_id: str):
    """
    Test updating task priority.

    Expected: Priority is updated successfully
    """
    # Create task with normal priority
    create_result = add_task(
        user_id=test_user_id,
        title="Task to update priority",
        priority="normal",
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Update to high priority
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        priority="high",
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert update_result["data"]["priority"] == "high"


def test_update_task_priority_to_critical(db_session: Session, test_user_id: str):
    """
    Test updating task priority to critical.

    Expected: Priority is updated to critical
    """
    # Create task
    create_result = add_task(
        user_id=test_user_id,
        title="Task for critical update",
        priority="low",
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Update to critical priority
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        priority="critical",
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert update_result["data"]["priority"] == "critical"


def test_update_task_invalid_priority(db_session: Session, test_user_id: str):
    """
    Test updating task with invalid priority.

    Expected: Returns error
    """
    # Create task
    create_result = add_task(
        user_id=test_user_id,
        title="Task for invalid priority update",
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Try to update with invalid priority
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        priority="medium",  # Invalid
        _session=db_session
    )

    assert update_result["status"] == "error"
    assert "priority" in update_result["error"].lower()


def test_priority_persisted_in_database(db_session: Session, test_user_id: str):
    """
    Test that priority is correctly persisted in the database.

    Expected: Database record has correct priority value
    """
    result = add_task(
        user_id=test_user_id,
        title="Task to verify persistence",
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    task_id = result["data"]["task_id"]

    # Query database directly
    statement = select(Task).where(Task.id == task_id)
    task = db_session.exec(statement).first()

    assert task is not None
    assert task.priority == "high"


def test_priority_in_list_tasks_response(db_session: Session, test_user_id: str):
    """
    Test that priority is included in list_tasks response.

    Expected: Each task in response includes priority field
    """
    # Create task with priority
    add_task(
        user_id=test_user_id,
        title="Task with priority for list",
        priority="critical",
        _session=db_session
    )

    # List tasks
    result = list_tasks(
        user_id=test_user_id,
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]
    assert len(tasks) >= 1

    # Verify priority is in response
    task = next(t for t in tasks if t["title"] == "Task with priority for list")
    assert task["priority"] == "critical"


def test_priority_preserved_through_update(db_session: Session, test_user_id: str):
    """
    Test that priority is preserved when updating other fields.

    Expected: Priority remains unchanged when not explicitly updated
    """
    # Create task with high priority
    create_result = add_task(
        user_id=test_user_id,
        title="Task to preserve priority",
        priority="high",
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Update title only (not priority)
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        title="Updated title",
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert update_result["data"]["priority"] == "high"  # Priority preserved
    assert update_result["data"]["title"] == "Updated title"
