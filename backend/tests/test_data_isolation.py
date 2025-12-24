from main import app
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from models import Task
from db import get_session
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from fastapi import Request


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory database for testing"""
    engine = create_engine("sqlite:///./test_isolation.db", echo=True)

    # Drop all tables first to ensure clean state
    SQLModel.metadata.drop_all(bind=engine)

    # Create tables
    SQLModel.metadata.create_all(bind=engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    # We'll apply this override in each specific test
    yield engine

    # Clean up after test
    SQLModel.metadata.drop_all(bind=engine)
    engine.dispose()


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_user_a_cannot_list_user_b_tasks(mock_get_signing_key, mock_decode, test_db):
    """Test T090: User A cannot list User B's tasks"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create tasks for User A
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.post(
            f"/api/user_a_123/tasks",
            headers={"Authorization": "Bearer fake-token-a"},
            json={"title": "User A Task 1", "description": "Task for User A"}
        )
        assert response.status_code in [200, 201]
        
        response = client.post(
            f"/api/user_a_123/tasks",
            headers={"Authorization": "Bearer fake-token-a"},
            json={"title": "User A Task 2", "description": "Task for User A"}
        )
        assert response.status_code in [200, 201]

        # Create tasks for User B
        mock_decode.return_value = {"user_id": "user_b_456"}
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "User B Task 1", "description": "Task for User B"}
        )
        assert response.status_code in [200, 201]
        
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "User B Task 2", "description": "Task for User B"}
        )
        assert response.status_code in [200, 201]

        # Now test that User A cannot access User B's tasks
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.get(f"/api/user_b_456/tasks", headers={"Authorization": "Bearer fake-token-a"})
        
        # Should return 403 Forbidden due to user_id mismatch
        assert response.status_code == 403


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_user_a_cannot_access_user_b_individual_task(mock_get_signing_key, mock_decode, test_db):
    """Test T090: User A cannot view User B's individual task"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create a task for User B
        mock_decode.return_value = {"user_id": "user_b_456"}
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "Private Task", "description": "User B's private task"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]

        # Now test that User A cannot access User B's task
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.get(f"/api/user_b_456/tasks/{task_id}", headers={"Authorization": "Bearer fake-token-a"})
        
        # Should return 403 Forbidden
        assert response.status_code == 403


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_user_a_cannot_update_user_b_task(mock_get_signing_key, mock_decode, test_db):
    """Test T090: User A cannot update User B's task"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create a task for User B
        mock_decode.return_value = {"user_id": "user_b_456"}
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "Update Protected Task", "description": "Task that should not be updated by others"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]

        # Now test that User A cannot update User B's task
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.put(
            f"/api/user_b_456/tasks/{task_id}",
            headers={"Authorization": "Bearer fake-token-a"},
            json={"title": "Hacked Title", "description": "Hacked Description"}
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_user_a_cannot_delete_user_b_task(mock_get_signing_key, mock_decode, test_db):
    """Test T090: User A cannot delete User B's task"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create a task for User B
        mock_decode.return_value = {"user_id": "user_b_456"}
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "Delete Protected Task", "description": "Task that should not be deleted by others"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]

        # Now test that User A cannot delete User B's task
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.delete(f"/api/user_b_456/tasks/{task_id}", headers={"Authorization": "Bearer fake-token-a"})
        
        # Should return 403 Forbidden
        assert response.status_code == 403


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_user_a_only_sees_own_tasks(mock_get_signing_key, mock_decode, test_db):
    """Test T090: User A should only see their own tasks"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create tasks for User A
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.post(
            f"/api/user_a_123/tasks",
            headers={"Authorization": "Bearer fake-token-a"},
            json={"title": "User A Task 1", "description": "Task for User A"}
        )
        assert response.status_code in [200, 201]
        
        response = client.post(
            f"/api/user_a_123/tasks",
            headers={"Authorization": "Bearer fake-token-a"},
            json={"title": "User A Task 2", "description": "Another task for User A"}
        )
        assert response.status_code in [200, 201]

        # Create tasks for User B
        mock_decode.return_value = {"user_id": "user_b_456"}
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "User B Task 1", "description": "Task for User B"}
        )
        assert response.status_code in [200, 201]
        
        response = client.post(
            f"/api/user_b_456/tasks",
            headers={"Authorization": "Bearer fake-token-b"},
            json={"title": "User B Task 2", "description": "Another task for User B"}
        )
        assert response.status_code in [200, 201]

        # User A should only see their own tasks
        mock_decode.return_value = {"user_id": "user_a_123"}
        response = client.get(f"/api/user_a_123/tasks", headers={"Authorization": "Bearer fake-token-a"})
        assert response.status_code == 200
        data = response.json()
        user_a_tasks = data["tasks"]  # Response is {"tasks": [...], "total": ...}

        # Verify User A only sees their tasks
        user_a_titles = [task["title"] for task in user_a_tasks]
        assert "User A Task 1" in user_a_titles
        assert "User A Task 2" in user_a_titles
        assert len(user_a_tasks) == 2


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_database_query_filtering(mock_get_signing_key, mock_decode, test_db):
    """Test T090: Database queries properly filter by user_id"""
    from main import app

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()

    with TestClient(app) as client:
        # Create mixed tasks for both users
        # User A creates 3 tasks
        mock_decode.return_value = {"user_id": "user_a_123"}
        for i in range(3):
            response = client.post(
                f"/api/user_a_123/tasks",
                headers={"Authorization": "Bearer fake-token-a"},
                json={"title": f"User A Task {i}", "description": f"Task {i} for User A"}
            )
            assert response.status_code in [200, 201]

        # User B creates 3 tasks
        mock_decode.return_value = {"user_id": "user_b_456"}
        for i in range(3):
            response = client.post(
                f"/api/user_b_456/tasks",
                headers={"Authorization": "Bearer fake-token-b"},
                json={"title": f"User B Task {i}", "description": f"Task {i} for User B"}
            )
            assert response.status_code in [200, 201]

        # Each user should only see 3 tasks (their own)
        mock_decode.return_value = {"user_id": "user_a_123"}
        response_a = client.get(f"/api/user_a_123/tasks", headers={"Authorization": "Bearer fake-token-a"})
        assert response_a.status_code == 200
        data_a = response_a.json()
        user_a_tasks = data_a["tasks"]  # Response is {"tasks": [...], "total": ...}
        assert len(user_a_tasks) == 3

        mock_decode.return_value = {"user_id": "user_b_456"}
        response_b = client.get(f"/api/user_b_456/tasks", headers={"Authorization": "Bearer fake-token-b"})
        assert response_b.status_code == 200
        data_b = response_b.json()
        user_b_tasks = data_b["tasks"]  # Response is {"tasks": [...], "total": ...}
        assert len(user_b_tasks) == 3