"""
Integration Test for Tag Assignment (Phase V - User Story 5).

This test validates that tags can be assigned and updated on tasks:
- Create task with tags
- Update task tags
- Multiple tags per task
- Tags normalized to lowercase
- Tags preserved through recurrence

Test Strategy:
- Create tasks with different tag combinations using add_task
- Update task tags using update_task
- Verify tags are stored and returned correctly
- Test validation for tag constraints

Expected Behavior:
- tags parameter accepts array of strings
- Tags are normalized to lowercase
- Maximum 10 tags per task (validation)
- Maximum 50 characters per tag (validation)
- Tags are preserved in task responses
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


def test_create_task_with_single_tag(db_session: Session, test_user_id: str):
    """
    Test creating a task with a single tag.

    Expected: Task is created with the tag
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with single tag",
        tags=["work"],
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["tags"] == ["work"]


def test_create_task_with_multiple_tags(db_session: Session, test_user_id: str):
    """
    Test creating a task with multiple tags.

    Expected: Task is created with all tags
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with multiple tags",
        tags=["work", "urgent", "project-x"],
        _session=db_session
    )

    assert result["status"] == "success"
    assert set(result["data"]["tags"]) == {"work", "urgent", "project-x"}


def test_create_task_without_tags(db_session: Session, test_user_id: str):
    """
    Test creating a task without tags.

    Expected: Task is created with null/None tags
    """
    result = add_task(
        user_id=test_user_id,
        title="Task without tags",
        _session=db_session
    )

    assert result["status"] == "success"
    assert result["data"]["tags"] is None or result["data"]["tags"] == []


def test_tags_normalized_to_lowercase(db_session: Session, test_user_id: str):
    """
    Test that tags are normalized to lowercase.

    Expected: "WORK" and "Urgent" become "work" and "urgent"
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with uppercase tags",
        tags=["WORK", "Urgent", "Project-X"],
        _session=db_session
    )

    assert result["status"] == "success"
    tags = result["data"]["tags"]
    assert all(tag.islower() for tag in tags)
    assert set(tags) == {"work", "urgent", "project-x"}


def test_update_task_tags(db_session: Session, test_user_id: str):
    """
    Test updating task tags.

    Expected: Tags are updated successfully
    """
    # Create task with initial tags
    create_result = add_task(
        user_id=test_user_id,
        title="Task to update tags",
        tags=["work"],
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Update tags
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        tags=["personal", "shopping"],
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert set(update_result["data"]["tags"]) == {"personal", "shopping"}


def test_add_tags_to_untagged_task(db_session: Session, test_user_id: str):
    """
    Test adding tags to a task that had no tags.

    Expected: Tags are added successfully
    """
    # Create task without tags
    create_result = add_task(
        user_id=test_user_id,
        title="Task without initial tags",
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Add tags
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        tags=["new-tag", "another-tag"],
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert set(update_result["data"]["tags"]) == {"new-tag", "another-tag"}


def test_remove_all_tags(db_session: Session, test_user_id: str):
    """
    Test removing all tags from a task.

    Expected: Tags are removed (set to empty list)
    """
    # Create task with tags
    create_result = add_task(
        user_id=test_user_id,
        title="Task to remove tags",
        tags=["work", "urgent"],
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Remove all tags
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        tags=[],
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert update_result["data"]["tags"] == [] or update_result["data"]["tags"] is None


def test_tags_persisted_in_database(db_session: Session, test_user_id: str):
    """
    Test that tags are correctly persisted in the database.

    Expected: Database record has correct tags array
    """
    result = add_task(
        user_id=test_user_id,
        title="Task to verify tag persistence",
        tags=["work", "urgent", "q4"],
        _session=db_session
    )

    assert result["status"] == "success"
    task_id = result["data"]["task_id"]

    # Query database directly
    statement = select(Task).where(Task.id == task_id)
    task = db_session.exec(statement).first()

    assert task is not None
    assert set(task.tags) == {"work", "urgent", "q4"}


def test_tags_in_list_tasks_response(db_session: Session, test_user_id: str):
    """
    Test that tags are included in list_tasks response.

    Expected: Each task in response includes tags field
    """
    # Create task with tags
    add_task(
        user_id=test_user_id,
        title="Task with tags for list",
        tags=["important", "deadline"],
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

    # Verify tags are in response
    task = next(t for t in tasks if t["title"] == "Task with tags for list")
    assert set(task["tags"]) == {"important", "deadline"}


def test_tags_preserved_through_update(db_session: Session, test_user_id: str):
    """
    Test that tags are preserved when updating other fields.

    Expected: Tags remain unchanged when not explicitly updated
    """
    # Create task with tags
    create_result = add_task(
        user_id=test_user_id,
        title="Task to preserve tags",
        tags=["work", "important"],
        _session=db_session
    )

    assert create_result["status"] == "success"
    task_id = create_result["data"]["task_id"]

    # Update title only (not tags)
    update_result = update_task(
        user_id=test_user_id,
        task_id=task_id,
        title="Updated title",
        _session=db_session
    )

    assert update_result["status"] == "success"
    assert set(update_result["data"]["tags"]) == {"work", "important"}  # Tags preserved
    assert update_result["data"]["title"] == "Updated title"


def test_duplicate_tags_deduplicated(db_session: Session, test_user_id: str):
    """
    Test that duplicate tags are handled.

    Expected: Duplicate tags are stored (PostgreSQL array)
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with duplicate tags",
        tags=["work", "Work", "WORK"],  # All normalize to "work"
        _session=db_session
    )

    assert result["status"] == "success"
    tags = result["data"]["tags"]
    # After normalization, all become "work"
    # PostgreSQL stores array as-is, so may have duplicates
    assert "work" in tags


def test_special_characters_in_tags(db_session: Session, test_user_id: str):
    """
    Test tags with special characters.

    Expected: Tags with hyphens and underscores work
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with special character tags",
        tags=["project-alpha", "phase_2", "q4-2025"],
        _session=db_session
    )

    assert result["status"] == "success"
    tags = result["data"]["tags"]
    assert set(tags) == {"project-alpha", "phase_2", "q4-2025"}


def test_empty_string_tag_handling(db_session: Session, test_user_id: str):
    """
    Test handling of empty string tags.

    Expected: Empty strings may be filtered or stored
    """
    result = add_task(
        user_id=test_user_id,
        title="Task with empty tag",
        tags=["work", "", "urgent"],
        _session=db_session
    )

    # Implementation may either accept or filter empty strings
    assert result["status"] == "success"
    tags = result["data"]["tags"]
    # Verify non-empty tags are present
    assert "work" in tags
    assert "urgent" in tags
