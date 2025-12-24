"""
Unit tests for MCP tools (add_task, list_tasks, complete_task, update_task, delete_task)

Following TDD discipline: Tests written FIRST before implementation
"""
import pytest
from sqlmodel import Session, create_engine, SQLModel, select
from models import Task
from uuid import uuid4, UUID


@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine):
    """Create a database session for testing"""
    with Session(test_engine) as session:
        yield session


# ========================================
# Phase 3: User Story 1 - add_task Tests
# ========================================

def test_add_task_creates_task(session):
    """
    T015: Test that add_task creates a task successfully

    Expected behavior:
    - Creates task with title and user_id
    - Returns success status
    - Task is persisted in database
    - Returns task_id, title, completed=False, created_at
    """
    from tools.server import add_task

    # Arrange
    user_id = "test_user_123"
    title = "Buy groceries"

    # Act
    result = add_task(user_id=user_id, title=title, _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["title"] == title
    assert result["data"]["completed"] is False
    assert "task_id" in result["data"]
    assert "created_at" in result["data"]

    # Verify task exists in database
    task_id_str = result["data"]["task_id"]
    task_id = UUID(task_id_str)  # Convert string to UUID
    statement = select(Task).where(Task.id == task_id)
    task = session.exec(statement).first()
    assert task is not None
    assert task.user_id == user_id
    assert task.title == title
    assert task.description is None


def test_add_task_with_description(session):
    """
    T016: Test that add_task creates a task with description

    Expected behavior:
    - Creates task with title, description, and user_id
    - Returns success status with description
    - Description is persisted in database
    """
    from tools.server import add_task

    # Arrange
    user_id = "test_user_456"
    title = "Write report"
    description = "Q4 financial report with charts"

    # Act
    result = add_task(user_id=user_id, title=title, description=description, _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["title"] == title
    assert result["data"]["description"] == description

    # Verify description is persisted
    task_id_str = result["data"]["task_id"]
    task_id = UUID(task_id_str)  # Convert string to UUID
    statement = select(Task).where(Task.id == task_id)
    task = session.exec(statement).first()
    assert task.description == description


def test_add_task_validation_errors(session):
    """
    T017: Test that add_task validates input parameters

    Expected behavior:
    - Empty title returns error
    - Title >200 characters returns error
    - Description >1000 characters returns error
    """
    from tools.server import add_task

    user_id = "test_user_789"

    # Test 1: Empty title
    result = add_task(user_id=user_id, title="", _session=session)
    assert result["status"] == "error"
    assert "title" in result["error"].lower() or "between 1 and 200" in result["error"].lower()

    # Test 2: Title too long
    long_title = "x" * 201
    result = add_task(user_id=user_id, title=long_title, _session=session)
    assert result["status"] == "error"
    assert "title" in result["error"].lower() or "200" in result["error"]

    # Test 3: Description too long
    long_description = "x" * 1001
    result = add_task(user_id=user_id, title="Valid title", description=long_description, _session=session)
    assert result["status"] == "error"
    assert "description" in result["error"].lower() or "1000" in result["error"]


# ========================================
# Phase 4: User Story 2 - list_tasks Tests
# ========================================

def test_list_tasks_all(session):
    """
    T024: Test that list_tasks returns all tasks for a user

    Expected behavior:
    - Returns all tasks for the specified user_id
    - Includes both pending and completed tasks
    - Returns task_id, title, description, completed, created_at for each task
    - Returns empty list if user has no tasks
    """
    from tools.server import add_task, list_tasks

    # Arrange
    user_id = "test_user_list_all"

    # Create 3 tasks for the user
    add_task(user_id=user_id, title="Task 1", description="Pending task 1", _session=session)
    add_task(user_id=user_id, title="Task 2", description="Pending task 2", _session=session)
    add_task(user_id=user_id, title="Task 3", description="Completed task", _session=session)

    # Mark Task 3 as completed
    statement = select(Task).where(Task.user_id == user_id, Task.title == "Task 3")
    task3 = session.exec(statement).first()
    task3.completed = True
    session.add(task3)
    session.commit()

    # Act
    result = list_tasks(user_id=user_id, status="all", _session=session)

    # Assert
    assert result["status"] == "success"
    assert "tasks" in result["data"]
    assert len(result["data"]["tasks"]) == 3

    # Verify task structure
    for task in result["data"]["tasks"]:
        assert "task_id" in task
        assert "title" in task
        assert "description" in task
        assert "completed" in task
        assert "created_at" in task

    # Verify we have both pending and completed tasks
    completed_count = sum(1 for task in result["data"]["tasks"] if task["completed"])
    pending_count = sum(1 for task in result["data"]["tasks"] if not task["completed"])
    assert completed_count == 1
    assert pending_count == 2


def test_list_tasks_pending(session):
    """
    T025: Test that list_tasks filters pending tasks correctly

    Expected behavior:
    - Returns only tasks where completed=False
    - Excludes completed tasks
    - Returns correct task count
    """
    from tools.server import add_task, list_tasks

    # Arrange
    user_id = "test_user_list_pending"

    # Create tasks
    add_task(user_id=user_id, title="Pending 1", _session=session)
    add_task(user_id=user_id, title="Pending 2", _session=session)
    add_task(user_id=user_id, title="Completed 1", _session=session)

    # Mark one task as completed
    statement = select(Task).where(Task.user_id == user_id, Task.title == "Completed 1")
    task = session.exec(statement).first()
    task.completed = True
    session.add(task)
    session.commit()

    # Act
    result = list_tasks(user_id=user_id, status="pending", _session=session)

    # Assert
    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 2

    # All returned tasks should be pending
    for task in result["data"]["tasks"]:
        assert task["completed"] is False


def test_list_tasks_completed(session):
    """
    T026: Test that list_tasks filters completed tasks correctly

    Expected behavior:
    - Returns only tasks where completed=True
    - Excludes pending tasks
    - Returns correct task count
    """
    from tools.server import add_task, list_tasks

    # Arrange
    user_id = "test_user_list_completed"

    # Create tasks
    add_task(user_id=user_id, title="Pending 1", _session=session)
    add_task(user_id=user_id, title="Completed 1", _session=session)
    add_task(user_id=user_id, title="Completed 2", _session=session)

    # Mark two tasks as completed
    for title in ["Completed 1", "Completed 2"]:
        statement = select(Task).where(Task.user_id == user_id, Task.title == title)
        task = session.exec(statement).first()
        task.completed = True
        session.add(task)
    session.commit()

    # Act
    result = list_tasks(user_id=user_id, status="completed", _session=session)

    # Assert
    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 2

    # All returned tasks should be completed
    for task in result["data"]["tasks"]:
        assert task["completed"] is True


def test_list_tasks_filters_by_user(session):
    """
    T027: Test that list_tasks enforces user isolation

    Expected behavior:
    - Returns only tasks belonging to the specified user_id
    - Does not return tasks from other users
    - User isolation is strictly enforced
    """
    from tools.server import add_task, list_tasks

    # Arrange
    user1_id = "user_1_isolation_test"
    user2_id = "user_2_isolation_test"

    # Create tasks for user 1
    add_task(user_id=user1_id, title="User 1 Task 1", _session=session)
    add_task(user_id=user1_id, title="User 1 Task 2", _session=session)

    # Create tasks for user 2
    add_task(user_id=user2_id, title="User 2 Task 1", _session=session)
    add_task(user_id=user2_id, title="User 2 Task 2", _session=session)
    add_task(user_id=user2_id, title="User 2 Task 3", _session=session)

    # Act
    result_user1 = list_tasks(user_id=user1_id, status="all", _session=session)
    result_user2 = list_tasks(user_id=user2_id, status="all", _session=session)

    # Assert
    assert result_user1["status"] == "success"
    assert result_user2["status"] == "success"

    # User 1 should only see their 2 tasks
    assert len(result_user1["data"]["tasks"]) == 2
    for task in result_user1["data"]["tasks"]:
        assert "User 1" in task["title"]

    # User 2 should only see their 3 tasks
    assert len(result_user2["data"]["tasks"]) == 3
    for task in result_user2["data"]["tasks"]:
        assert "User 2" in task["title"]


# ========================================
# Phase 6: User Story 3 - complete_task Tests
# ========================================

def test_complete_task_marks_complete(session):
    """
    T046: Test that complete_task marks a task as completed

    Expected behavior:
    - Task completed status changes from False to True
    - Returns success status with updated task data
    - Task remains in database with completed=True
    - Returns task_id, title, completed, updated_at
    """
    from tools.server import add_task, complete_task

    # Arrange
    user_id = "test_user_complete"

    # Create a task
    result = add_task(user_id=user_id, title="Task to complete", _session=session)
    task_id = result["data"]["task_id"]

    # Act
    result = complete_task(user_id=user_id, task_id=task_id, _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["task_id"] == task_id
    assert result["data"]["completed"] is True
    assert "updated_at" in result["data"]

    # Verify task is marked complete in database
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.completed is True


def test_complete_task_idempotent(session):
    """
    T047: Test that complete_task is idempotent

    Expected behavior:
    - Completing an already completed task succeeds
    - No error is returned
    - Task remains completed
    """
    from tools.server import add_task, complete_task

    # Arrange
    user_id = "test_user_idempotent"

    # Create and complete a task
    result = add_task(user_id=user_id, title="Already done", _session=session)
    task_id = result["data"]["task_id"]
    complete_task(user_id=user_id, task_id=task_id, _session=session)

    # Act - complete it again
    result = complete_task(user_id=user_id, task_id=task_id, _session=session)

    # Assert - should still succeed
    assert result["status"] == "success"
    assert result["data"]["completed"] is True


def test_complete_task_unauthorized(session):
    """
    T048: Test that complete_task enforces ownership

    Expected behavior:
    - Cannot complete task belonging to another user
    - Returns error status
    - Task remains in original state
    """
    from tools.server import add_task, complete_task

    # Arrange
    user1_id = "user1_complete"
    user2_id = "user2_complete"

    # User 1 creates a task
    result = add_task(user_id=user1_id, title="User 1 task", _session=session)
    task_id = result["data"]["task_id"]

    # Act - User 2 tries to complete User 1's task
    result = complete_task(user_id=user2_id, task_id=task_id, _session=session)

    # Assert
    assert result["status"] == "error"
    assert "unauthorized" in result["error"].lower() or "does not belong" in result["error"].lower()

    # Verify task is still pending
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.completed is False


# ========================================
# Phase 7: User Story 4 - update_task Tests
# ========================================

def test_update_task_title(session):
    """
    T052: Test that update_task can update title

    Expected behavior:
    - Task title is updated
    - Description remains unchanged
    - Returns success with updated task data
    """
    from tools.server import add_task, update_task

    # Arrange
    user_id = "test_user_update_title"

    # Create a task
    result = add_task(user_id=user_id, title="Original title", description="Original desc", _session=session)
    task_id = result["data"]["task_id"]

    # Act
    result = update_task(user_id=user_id, task_id=task_id, title="Updated title", _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["title"] == "Updated title"
    assert result["data"]["description"] == "Original desc"  # Unchanged

    # Verify in database
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.title == "Updated title"
    assert task.description == "Original desc"


def test_update_task_description(session):
    """
    T053: Test that update_task can update description

    Expected behavior:
    - Task description is updated
    - Title remains unchanged
    - Returns success with updated task data
    """
    from tools.server import add_task, update_task

    # Arrange
    user_id = "test_user_update_desc"

    # Create a task
    result = add_task(user_id=user_id, title="Original title", description="Original desc", _session=session)
    task_id = result["data"]["task_id"]

    # Act
    result = update_task(user_id=user_id, task_id=task_id, description="Updated description", _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["title"] == "Original title"  # Unchanged
    assert result["data"]["description"] == "Updated description"

    # Verify in database
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.title == "Original title"
    assert task.description == "Updated description"


def test_update_task_both(session):
    """
    T054: Test that update_task can update both title and description

    Expected behavior:
    - Both title and description are updated
    - Returns success with updated task data
    """
    from tools.server import add_task, update_task

    # Arrange
    user_id = "test_user_update_both"

    # Create a task
    result = add_task(user_id=user_id, title="Old title", description="Old desc", _session=session)
    task_id = result["data"]["task_id"]

    # Act
    result = update_task(user_id=user_id, task_id=task_id, title="New title", description="New desc", _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["title"] == "New title"
    assert result["data"]["description"] == "New desc"

    # Verify in database
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.title == "New title"
    assert task.description == "New desc"


def test_update_task_unauthorized(session):
    """
    T055: Test that update_task enforces ownership

    Expected behavior:
    - Cannot update task belonging to another user
    - Returns error status
    - Task remains unchanged
    """
    from tools.server import add_task, update_task

    # Arrange
    user1_id = "user1_update"
    user2_id = "user2_update"

    # User 1 creates a task
    result = add_task(user_id=user1_id, title="User 1 task", description="User 1 desc", _session=session)
    task_id = result["data"]["task_id"]

    # Act - User 2 tries to update User 1's task
    result = update_task(user_id=user2_id, task_id=task_id, title="Hacked title", _session=session)

    # Assert
    assert result["status"] == "error"
    assert "unauthorized" in result["error"].lower() or "does not belong" in result["error"].lower()

    # Verify task is unchanged
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task.title == "User 1 task"
    assert task.description == "User 1 desc"


# ========================================
# Phase 8: User Story 5 - delete_task Tests
# ========================================

def test_delete_task_removes(session):
    """
    T059: Test that delete_task removes a task

    Expected behavior:
    - Task is removed from database
    - Returns success status with deleted task info
    - Subsequent queries don't find the task
    """
    from tools.server import add_task, delete_task

    # Arrange
    user_id = "test_user_delete"

    # Create a task
    result = add_task(user_id=user_id, title="Task to delete", _session=session)
    task_id = result["data"]["task_id"]

    # Verify task exists
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task is not None

    # Act
    result = delete_task(user_id=user_id, task_id=task_id, _session=session)

    # Assert
    assert result["status"] == "success"
    assert result["data"]["task_id"] == task_id
    assert result["data"]["deleted"] is True

    # Verify task is gone from database
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task is None


def test_delete_task_unauthorized(session):
    """
    T060: Test that delete_task enforces ownership

    Expected behavior:
    - Cannot delete task belonging to another user
    - Returns error status
    - Task remains in database
    """
    from tools.server import add_task, delete_task

    # Arrange
    user1_id = "user1_delete"
    user2_id = "user2_delete"

    # User 1 creates a task
    result = add_task(user_id=user1_id, title="User 1 task", _session=session)
    task_id = result["data"]["task_id"]

    # Act - User 2 tries to delete User 1's task
    result = delete_task(user_id=user2_id, task_id=task_id, _session=session)

    # Assert
    assert result["status"] == "error"
    assert "unauthorized" in result["error"].lower() or "does not belong" in result["error"].lower()

    # Verify task still exists
    statement = select(Task).where(Task.id == UUID(task_id))
    task = session.exec(statement).first()
    assert task is not None
    assert task.title == "User 1 task"


def test_delete_task_not_found(session):
    """
    T061: Test that delete_task handles non-existent task

    Expected behavior:
    - Returns error when task doesn't exist
    - Returns "Task not found" error message
    """
    from tools.server import delete_task

    # Arrange
    user_id = "test_user_not_found"
    fake_task_id = str(uuid4())  # Valid UUID but doesn't exist

    # Act
    result = delete_task(user_id=user_id, task_id=fake_task_id, _session=session)

    # Assert
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
