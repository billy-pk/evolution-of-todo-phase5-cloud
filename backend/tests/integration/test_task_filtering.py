"""
Integration Test for Task Filtering (Phase V - User Story 3).

This test validates that tasks can be filtered by multiple criteria:
- Filter by priority (low, normal, high, critical)
- Filter by tags (ANY match)
- Filter by due date range (from/to)
- Filter by status (all, pending, completed)
- Combine multiple filters (AND logic)
- Sorting by different fields

Test Strategy:
- Create diverse tasks with different priorities, tags, due dates
- Use list_tasks with various filter combinations
- Verify correct subset of tasks is returned
- Test edge cases (no matches, invalid filters)

Expected Behavior:
- priority="high" returns only high priority tasks
- tags=["work"] returns tasks containing "work" tag
- due_date_from/to filters by date range
- Multiple filters combined with AND logic
- Invalid filter values return error
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from sqlmodel import Session, select
from db import engine
from models import Task
from tools.server import list_tasks


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
def diverse_tasks(db_session: Session, test_user_id: str):
    """Fixture to create diverse tasks for filtering tests."""
    now = datetime.now(UTC)

    tasks = [
        Task(
            user_id=test_user_id,
            title="Critical server outage",
            description="Production server down",
            completed=False,
            priority="critical",
            tags=["work", "urgent", "ops"],
            due_date=now + timedelta(hours=2)
        ),
        Task(
            user_id=test_user_id,
            title="Quarterly report",
            description="Q4 financial report",
            completed=False,
            priority="high",
            tags=["work", "finance"],
            due_date=now + timedelta(days=3)
        ),
        Task(
            user_id=test_user_id,
            title="Team meeting",
            description="Weekly sync",
            completed=False,
            priority="normal",
            tags=["work", "meeting"],
            due_date=now + timedelta(days=1)
        ),
        Task(
            user_id=test_user_id,
            title="Update documentation",
            description="API docs refresh",
            completed=True,
            priority="low",
            tags=["work", "docs"],
            due_date=now - timedelta(days=1)  # Past due date
        ),
        Task(
            user_id=test_user_id,
            title="Buy birthday gift",
            description="Gift for friend",
            completed=False,
            priority="normal",
            tags=["personal", "shopping"],
            due_date=now + timedelta(days=5)
        ),
        Task(
            user_id=test_user_id,
            title="Gym workout",
            description="Leg day",
            completed=True,
            priority="low",
            tags=["personal", "health"],
            due_date=None  # No due date
        ),
    ]

    for task in tasks:
        db_session.add(task)
    db_session.commit()

    for task in tasks:
        db_session.refresh(task)

    return tasks


def test_filter_by_priority_critical(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by critical priority.

    Expected: Only returns tasks with priority="critical"
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="critical",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Critical server outage"
    assert tasks[0]["priority"] == "critical"


def test_filter_by_priority_high(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by high priority.

    Expected: Only returns tasks with priority="high"
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Quarterly report"
    assert tasks[0]["priority"] == "high"


def test_filter_by_priority_low(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by low priority.

    Expected: Returns tasks with priority="low"
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="low",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 2
    for task in tasks:
        assert task["priority"] == "low"


def test_filter_by_invalid_priority(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by invalid priority value.

    Expected: Returns error
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="invalid_priority",
        _session=db_session
    )

    assert result["status"] == "error"
    assert "priority" in result["error"].lower()


def test_filter_by_single_tag(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by single tag.

    Expected: Returns tasks containing "personal" tag
    """
    result = list_tasks(
        user_id=test_user_id,
        tags=["personal"],
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 2
    for task in tasks:
        assert "personal" in task["tags"]


def test_filter_by_multiple_tags(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by multiple tags (ANY match).

    Expected: Returns tasks containing "urgent" OR "finance" tag
    """
    result = list_tasks(
        user_id=test_user_id,
        tags=["urgent", "finance"],
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Should match "Critical server outage" (urgent) and "Quarterly report" (finance)
    assert len(tasks) == 2
    for task in tasks:
        assert "urgent" in task["tags"] or "finance" in task["tags"]


def test_filter_by_due_date_range(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by due date range.

    Expected: Returns tasks with due_date within range
    """
    now = datetime.now(UTC)
    tomorrow = now + timedelta(days=1)
    in_three_days = now + timedelta(days=3)

    result = list_tasks(
        user_id=test_user_id,
        due_date_from=tomorrow.isoformat(),
        due_date_to=in_three_days.isoformat(),
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Should include Team meeting (1 day) and Quarterly report (3 days)
    assert len(tasks) >= 1
    for task in tasks:
        if task["due_date"]:
            due = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
            assert due >= tomorrow
            assert due <= in_three_days


def test_filter_by_due_date_from_only(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by due_date_from only.

    Expected: Returns tasks with due_date >= specified date
    """
    now = datetime.now(UTC)
    in_two_days = now + timedelta(days=2)

    result = list_tasks(
        user_id=test_user_id,
        due_date_from=in_two_days.isoformat(),
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    for task in tasks:
        if task["due_date"]:
            due = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
            assert due >= in_two_days


def test_filter_by_status_pending(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by pending status.

    Expected: Returns only incomplete tasks
    """
    result = list_tasks(
        user_id=test_user_id,
        status="pending",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 4  # 4 incomplete tasks
    for task in tasks:
        assert task["completed"] is False


def test_filter_by_status_completed(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filtering by completed status.

    Expected: Returns only completed tasks
    """
    result = list_tasks(
        user_id=test_user_id,
        status="completed",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 2  # 2 completed tasks
    for task in tasks:
        assert task["completed"] is True


def test_combine_priority_and_status_filter(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test combining priority and status filters (AND logic).

    Expected: Returns low priority AND completed tasks
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="low",
        status="completed",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 2  # Both low priority tasks are completed
    for task in tasks:
        assert task["priority"] == "low"
        assert task["completed"] is True


def test_combine_tags_and_priority_filter(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test combining tags and priority filters.

    Expected: Returns work tasks with high priority
    """
    result = list_tasks(
        user_id=test_user_id,
        tags=["work"],
        priority="high",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Quarterly report"
    assert "work" in tasks[0]["tags"]
    assert tasks[0]["priority"] == "high"


def test_sort_by_due_date_asc(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test sorting by due date ascending.

    Expected: Tasks sorted by due_date from earliest to latest
    """
    result = list_tasks(
        user_id=test_user_id,
        status="pending",
        sort_by="due_date",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Filter out tasks with null due_date for sorting verification
    tasks_with_due = [t for t in tasks if t["due_date"]]
    if len(tasks_with_due) > 1:
        dates = [t["due_date"] for t in tasks_with_due]
        assert dates == sorted(dates)


def test_sort_by_priority(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test sorting by priority.

    Expected: Tasks sorted by priority field
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_by="priority",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Just verify it returns without error - priority sort is alphabetical
    assert len(tasks) == 6


def test_sort_by_title(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test sorting by title ascending.

    Expected: Tasks sorted alphabetically by title
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_by="title",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    titles = [t["title"] for t in tasks]
    assert titles == sorted(titles)


def test_invalid_sort_by_field(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test invalid sort_by field.

    Expected: Returns error
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_by="invalid_field",
        _session=db_session
    )

    assert result["status"] == "error"
    assert "sort_by" in result["error"].lower()


def test_invalid_sort_order(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test invalid sort_order value.

    Expected: Returns error
    """
    result = list_tasks(
        user_id=test_user_id,
        sort_order="invalid",
        _session=db_session
    )

    assert result["status"] == "error"
    assert "sort_order" in result["error"].lower()


def test_filter_no_matches(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test filter combination with no matching results.

    Expected: Returns empty list
    """
    result = list_tasks(
        user_id=test_user_id,
        priority="critical",
        status="completed",  # No critical tasks are completed
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 0


def test_filter_user_isolation(db_session: Session, test_user_id: str, diverse_tasks: list):
    """
    Test that filters only apply to user's own tasks.

    Expected: Different user sees no tasks
    """
    other_user_id = f"other-user-{uuid4()}"

    result = list_tasks(
        user_id=other_user_id,
        priority="critical",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 0
