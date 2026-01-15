"""
Integration Test for Task Search (Phase V - User Story 3).

This test validates that tasks can be searched by title and description:
- Case-insensitive text search in title
- Case-insensitive text search in description
- Combined title/description search (OR logic)
- Empty search returns all tasks
- No matches returns empty list

Test Strategy:
- Create multiple tasks with different titles and descriptions
- Use list_tasks with search_query parameter
- Verify correct tasks are returned based on search criteria
- Test edge cases (partial match, case variations, special characters)

Expected Behavior:
- search_query="report" matches tasks with "report" in title OR description
- Search is case-insensitive ("Report" matches "report")
- Partial matches work ("rep" matches "report")
- User isolation is enforced (only searches user's own tasks)
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
def sample_tasks(db_session: Session, test_user_id: str):
    """Fixture to create sample tasks for search testing."""
    tasks = [
        Task(
            user_id=test_user_id,
            title="Submit quarterly report",
            description="Q4 2025 financial report for stakeholders",
            completed=False,
            priority="high",
            tags=["work", "finance"]
        ),
        Task(
            user_id=test_user_id,
            title="Review team performance",
            description="Annual performance reviews for team members",
            completed=False,
            priority="normal",
            tags=["work", "hr"]
        ),
        Task(
            user_id=test_user_id,
            title="Buy groceries",
            description="Milk, eggs, bread, vegetables",
            completed=False,
            priority="low",
            tags=["personal", "shopping"]
        ),
        Task(
            user_id=test_user_id,
            title="Schedule dentist appointment",
            description="Annual checkup and cleaning",
            completed=True,
            priority="normal",
            tags=["personal", "health"]
        ),
        Task(
            user_id=test_user_id,
            title="Prepare presentation",
            description="Slides for quarterly report meeting",
            completed=False,
            priority="high",
            tags=["work", "presentation"]
        ),
    ]

    for task in tasks:
        db_session.add(task)
    db_session.commit()

    # Refresh to get IDs
    for task in tasks:
        db_session.refresh(task)

    return tasks


def test_search_by_title(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test searching tasks by title.

    Expected: "report" matches "Submit quarterly report"
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="report",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Should match "Submit quarterly report" and "Prepare presentation" (has "report" in description)
    assert len(tasks) >= 1
    titles = [t["title"] for t in tasks]
    assert "Submit quarterly report" in titles


def test_search_by_description(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test searching tasks by description.

    Expected: "stakeholders" matches task with that word in description
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="stakeholders",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Submit quarterly report"


def test_search_case_insensitive(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test that search is case-insensitive.

    Expected: "REPORT" matches "Submit quarterly report"
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="REPORT",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) >= 1
    titles = [t["title"] for t in tasks]
    assert "Submit quarterly report" in titles


def test_search_partial_match(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test that partial matches work.

    Expected: "dent" matches "Schedule dentist appointment"
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="dent",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Schedule dentist appointment"


def test_search_no_matches(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test search with no matching results.

    Expected: "xyz123nonexistent" returns empty list
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="xyz123nonexistent",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 0


def test_search_empty_query_returns_all(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test that empty/None search query returns all tasks.

    Expected: No search_query returns all 5 sample tasks
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query=None,
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 5


def test_search_user_isolation(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test that search only returns tasks for the requesting user.

    Expected: Different user_id returns no tasks
    """
    other_user_id = f"other-user-{uuid4()}"

    result = list_tasks(
        user_id=other_user_id,
        search_query="report",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    # Other user should not see test_user's tasks
    assert len(tasks) == 0


def test_search_with_status_filter(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test combining search with status filter.

    Expected: search="check" + status="completed" returns dentist appointment
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="check",
        status="completed",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) == 1
    assert tasks[0]["title"] == "Schedule dentist appointment"
    assert tasks[0]["completed"] is True


def test_search_with_sorting(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test combining search with sorting.

    Expected: Results are sorted by specified field
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="work",  # Matches tasks with "work" tag description won't match, but title might
        sort_by="title",
        sort_order="asc",
        _session=db_session
    )

    assert result["status"] == "success"
    # Verify results are sorted alphabetically by title
    tasks = result["data"]["tasks"]
    if len(tasks) > 1:
        titles = [t["title"] for t in tasks]
        assert titles == sorted(titles)


def test_search_response_includes_all_fields(db_session: Session, test_user_id: str, sample_tasks: list):
    """
    Test that search results include all task fields.

    Expected: Response includes priority, tags, due_date, updated_at
    """
    result = list_tasks(
        user_id=test_user_id,
        search_query="report",
        _session=db_session
    )

    assert result["status"] == "success"
    tasks = result["data"]["tasks"]

    assert len(tasks) >= 1
    task = tasks[0]

    # Verify all fields are present
    assert "task_id" in task
    assert "title" in task
    assert "description" in task
    assert "completed" in task
    assert "priority" in task
    assert "tags" in task
    assert "due_date" in task
    assert "created_at" in task
    assert "updated_at" in task
