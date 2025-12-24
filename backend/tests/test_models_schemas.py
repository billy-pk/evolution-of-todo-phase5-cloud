import pytest
from datetime import datetime
from models import Task
from schemas import TaskCreate, TaskUpdate, TaskResponse


def test_task_model_creation():
    """Test creating a Task model instance"""
    task = Task(
        user_id="user_123",
        title="Test Task",
        description="Test Description"
    )
    
    assert task.user_id == "user_123"
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.completed is False  # Default value


def test_task_model_with_completed_status():
    """Test Task model with completed status"""
    task = Task(
        user_id="user_456",
        title="Completed Task",
        completed=True
    )
    
    assert task.completed is True


def test_task_create_schema():
    """Test TaskCreate schema validation"""
    task_create = TaskCreate(
        title="New Task",
        description="New Description"
    )
    
    assert task_create.title == "New Task"
    assert task_create.description == "New Description"


def test_task_create_schema_validation():
    """Test TaskCreate schema validation with empty title"""
    with pytest.raises(ValueError):
        TaskCreate(title="", description="Invalid task")


def test_task_update_schema():
    """Test TaskUpdate schema"""
    task_update = TaskUpdate(
        title="Updated Task",
        description="Updated Description"
    )
    
    assert task_update.title == "Updated Task"
    assert task_update.description == "Updated Description"


def test_task_update_schema_partial():
    """Test TaskUpdate schema with partial data"""
    task_update = TaskUpdate(title="Only Title Updated")
    
    assert task_update.title == "Only Title Updated"
    assert task_update.description is None


def test_task_response_schema():
    """Test TaskResponse schema conversion"""
    # Create a mock task-like object
    mock_task = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "user_123",
        "title": "Response Task",
        "description": "Response Description",
        "completed": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    task_response = TaskResponse(**mock_task)
    
    assert task_response.user_id == "user_123"
    assert task_response.title == "Response Task"
    assert task_response.completed is False