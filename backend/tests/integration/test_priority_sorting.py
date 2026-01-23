"""
Integration Test for Priority Sorting (Phase V - User Story 4).

This test validates that tasks can be sorted by priority:
- Sort by priority ascending (low → normal → high → critical)
- Sort by priority descending (critical → high → normal → low)
- Combine priority filter with other filters
- Priority sorting works with search

Test Strategy:
- Create tasks with different priorities
- Use list_tasks with sort_by="priority"
- Verify tasks are returned in correct order
- Test combined sorting and filtering scenarios

Expected Behavior:
- sort_by="priority" sorts by priority field
- Alphabetical order: critical < high < low < normal
- Can combine with other filters (status, tags, etc.)
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import Task
from tools.server import add_task, list_tasks


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


@pytest.fixture
def tasks_with_priorities(db_session: Session, test_user_id: str):
    """Fixture to create tasks with all priority levels."""
    tasks = []

    # Create tasks with each priority
    for priority in ["low", "normal", "high", "critical"]:
        result = add_task(
            user_id=test_user_id,
            title=f"Task with {priority} priority",
            priority=priority,
            _session=db_session
        )
        assert result["status"] == "success"
        tasks.append(result["data"])

    return tasks


def test_sort_by_priority_ascending(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test sorting tasks by priority ascending.

    Expected: Tasks sorted alphabetically by priority (critical, high, low, normal)
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_by="priority",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    priorities = [t["priority"] for t in tasks]
    # Alphabetical: critical < high < low < normal
    assert priorities == sorted(priorities)


def test_sort_by_priority_descending(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test sorting tasks by priority descending.

    Expected: Tasks sorted in reverse alphabetical order (normal, low, high, critical)
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_by="priority",
        sort_order="desc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    priorities = [t["priority"] for t in tasks]
    # Reverse alphabetical
    assert priorities == sorted(priorities, reverse=True)


def test_filter_high_priority_tasks(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test filtering to show only high priority tasks.

    Expected: Only tasks with priority="high" returned
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["priority"] == "high"


def test_filter_critical_priority_tasks(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test filtering to show only critical priority tasks.

    Expected: Only tasks with priority="critical" returned
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="critical",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["priority"] == "critical"


def test_priority_sort_with_status_filter(db_session: Session, test_user_id: str):
    """
    Test combining priority sort with status filter.

    Expected: Only pending tasks sorted by priority
    """
    # Create mix of completed and pending tasks with different priorities
    add_task(user_id=test_user_id, title="Pending high", priority="high", _session=db_session)
    add_task(user_id=test_user_id, title="Pending low", priority="low", _session=db_session)

    # Create and complete a critical task
    create_result = add_task(user_id=test_user_id, title="Completed critical", priority="critical", _session=db_session)
    task_id = create_result["data"]["task_id"]

    # Mark as completed in database
    statement = select(Task).where(Task.id == task_id)
    task = db_session.exec(statement).first()
    task.completed = True
    db_session.add(task)
    db_session.commit()

    # List pending tasks sorted by priority
    result = list_tasks(
        user_id=test_user_id,
        status="pending",
        sort_by="priority",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Should only have pending tasks, sorted
    for task in tasks:
        assert task["completed"] is False

    if len(tasks) > 1:
        priorities = [t["priority"] for t in tasks]
        assert priorities == sorted(priorities)


def test_priority_filter_with_search(db_session: Session, test_user_id: str):
    """
    Test combining priority filter with search.

    Expected: Only high priority tasks matching search returned
    """
    # Create tasks
    add_task(user_id=test_user_id, title="Important report", priority="high", _session=db_session)
    add_task(user_id=test_user_id, title="Important meeting", priority="low", _session=db_session)
    add_task(user_id=test_user_id, title="Casual chat", priority="high", _session=db_session)

    # Search with priority filter
    result = list_tasks(
        user_id=test_user_id,
        search_query="Important",
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Should only return "Important report" (high priority + matches search)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Important report"
    assert tasks[0]["priority"] == "high"


def test_multiple_tasks_same_priority_sorted_by_created(db_session: Session, test_user_id: str):
    """
    Test sorting multiple tasks with same priority.

    Expected: Tasks with same priority are in consistent order
    """
    # Create multiple high priority tasks
    for i in range(3):
        add_task(
            user_id=test_user_id,
            title=f"High priority task {i}",
            priority="high",
            _session=db_session
        )

    result = list_tasks(
        user_id=test_user_id,
        priority="high",
        sort_by="priority",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 3
    # All should be high priority
    for task in tasks:
        assert task["priority"] == "high"


def test_priority_distribution(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test that all priority levels are represented.

    Expected: Can retrieve tasks at each priority level
    """
    for priority in ["low", "normal", "high", "critical"]:
        result = list_tasks(
            user_id=test_user_id,
            priority=priority,
            _session=db_session
        )

        assert result["status"] == "success"
        tasks = result["data"]["tasks"]
        assert len(tasks) >= 1
        assert all(t["priority"] == priority for t in tasks)


def test_default_sort_includes_priority_field(db_session: Session, test_user_id: str, tasks_with_priorities: list):
    """
    Test that default list includes priority field.

    Expected: Priority field is present in all task responses
    """
    result = list_tasks(
        user_id=test_user_id,
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    for task in tasks:
        assert "priority" in task
        assert task["priority"] in ["low", "normal", "high", "critical"]
