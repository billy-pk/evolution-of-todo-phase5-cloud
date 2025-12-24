import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import threading
import time
from datetime import datetime
from uuid import uuid4

from main import app
from models import Task
from db import get_session
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory database for testing"""
    engine = create_engine("sqlite:///./test_concurrent.db", echo=True)

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
def test_concurrent_task_creation(mock_get_signing_key, mock_decode, test_db):
    """Test T089: Concurrent Task Creation"""
    from fastapi.testclient import TestClient
    from fastapi import Request

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()
    mock_decode.return_value = {"user_id": "test_user_123"}

    with TestClient(app) as client:
        # Simulate multiple concurrent requests to create tasks
        def create_task(title):
            response = client.post(
                f"/api/test_user_123/tasks",
                headers={"Authorization": "Bearer fake-token"},
                json={"title": title, "description": f"Description for {title}"}
            )
            return response
    
        # Create 3 tasks concurrently
        titles = ["Task A", "Task B", "Task C"]
        results = []
    
        def worker(title):
            result = create_task(title)
            results.append(result)
    
        threads = []
        for title in titles:
            thread = threading.Thread(target=worker, args=(title,))
            threads.append(thread)
            thread.start()
    
        for thread in threads:
            thread.join()
    
        # Verify all requests were successful
        for result in results:
            assert result.status_code in [200, 201], f"Failed to create task: {result.json()}"
    
        # Verify all 3 tasks exist in the list
        response = client.get(f"/api/test_user_123/tasks", headers={"Authorization": "Bearer fake-token"})
        assert response.status_code == 200
        data = response.json()
        tasks = data["tasks"]  # Response is {"tasks": [...], "total": ...}
        created_titles = [task["title"] for task in tasks]
        assert "Task A" in created_titles
        assert "Task B" in created_titles
        assert "Task C" in created_titles


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_concurrent_task_updates(mock_get_signing_key, mock_decode, test_db):
    """Test T089: Concurrent Task Updates"""
    from fastapi.testclient import TestClient
    from fastapi import Request

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()
    mock_decode.return_value = {"user_id": "test_user_123"}

    with TestClient(app) as client:
        # First, create a task to update
        response = client.post(
            f"/api/test_user_123/tasks",
            headers={"Authorization": "Bearer fake-token"},
            json={"title": "Original Task", "description": "Original description"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]
        
        # Define update functions for concurrent updates
        def update_task(update_data):
            response = client.put(
                f"/api/test_user_123/tasks/{task_id}",
                headers={"Authorization": "Bearer fake-token"},
                json=update_data
            )
            return response
    
        # Update values for concurrent attempts
        update_data_1 = {"title": "Updated by Thread 1", "description": "Updated description 1"}
        update_data_2 = {"title": "Updated by Thread 2", "description": "Updated description 2"}
        
        result_1, result_2 = None, None
        
        def update_worker_1():
            nonlocal result_1
            result_1 = update_task(update_data_1)
        
        def update_worker_2():
            nonlocal result_2
            result_2 = update_task(update_data_2)
        
        # Run updates concurrently
        thread_1 = threading.Thread(target=update_worker_1)
        thread_2 = threading.Thread(target=update_worker_2)
        
        thread_1.start()
        thread_2.start()
        
        thread_1.join()
        thread_2.join()
        
        # Both updates could potentially succeed (last write wins)
        # At least one should succeed
        assert result_1.status_code in [200, 201] or result_2.status_code in [200, 201]
        
        # Get the final state of the task to check which update was applied
        final_response = client.get(f"/api/test_user_123/tasks/{task_id}", headers={"Authorization": "Bearer fake-token"})
        assert final_response.status_code == 200
        final_task = final_response.json()
        assert final_task["id"] == task_id


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_concurrent_task_deletion(mock_get_signing_key, mock_decode, test_db):
    """Test T089: Concurrent Delete Operations"""
    from fastapi.testclient import TestClient
    from fastapi import Request

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()
    mock_decode.return_value = {"user_id": "test_user_123"}

    with TestClient(app) as client:
        # First, create a task to delete
        response = client.post(
            f"/api/test_user_123/tasks",
            headers={"Authorization": "Bearer fake-token"},
            json={"title": "Task to Delete", "description": "Description to delete"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]
        
        # Define delete function for concurrent deletion
        def delete_task():
            response = client.delete(f"/api/test_user_123/tasks/{task_id}", headers={"Authorization": "Bearer fake-token"})
            return response
        
        results = []
        
        def delete_worker():
            result = delete_task()
            results.append(result)
        
        # Run two deletion attempts concurrently
        thread_1 = threading.Thread(target=delete_worker)
        thread_2 = threading.Thread(target=delete_worker)
        
        thread_1.start()
        thread_2.start()
        
        thread_1.join()
        thread_2.join()
        
        # One should succeed (200/204), the other should get 404
        status_codes = [r.status_code for r in results]
        assert 200 in status_codes or 204 in status_codes, "At least one deletion should succeed"
        assert 404 in status_codes, "One deletion attempt should fail with 404"


@patch('middleware.jwt.decode')
@patch('middleware.jwks_client.get_signing_key_from_jwt')
def test_concurrent_completion_toggle(mock_get_signing_key, mock_decode, test_db):
    """Test T089: Toggle Completion Concurrently"""
    from fastapi.testclient import TestClient
    from fastapi import Request

    # Create app instance with test database
    engine = test_db

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    
    mock_get_signing_key.return_value = MagicMock()
    mock_decode.return_value = {"user_id": "test_user_123"}

    with TestClient(app) as client:
        # First, create a task to toggle
        response = client.post(
            f"/api/test_user_123/tasks",
            headers={"Authorization": "Bearer fake-token"},
            json={"title": "Toggle Completion Task", "description": "Task to toggle"}
        )
        assert response.status_code in [200, 201]
        task_id = response.json()["id"]
        
        # Initially, task should be incomplete
        get_response = client.get(f"/api/test_user_123/tasks/{task_id}", headers={"Authorization": "Bearer fake-token"})
        assert get_response.status_code == 200
        original_task = get_response.json()
        assert original_task["completed"] is False
        
        # Define toggle function for concurrent toggles
        def toggle_completion():
            response = client.patch(f"/api/test_user_123/tasks/{task_id}/complete", headers={"Authorization": "Bearer fake-token"})
            return response
        
        results = []
        
        def toggle_worker():
            result = toggle_completion()
            results.append(result)
        
        # Run two toggle attempts concurrently
        thread_1 = threading.Thread(target=toggle_worker)
        thread_2 = threading.Thread(target=toggle_worker)
        
        thread_1.start()
        thread_2.start()
        
        thread_1.join()
        thread_2.join()
        
        # Both requests should succeed
        for result in results:
            assert result.status_code == 200, f"Toggle failed: {result.json()}"
        
        # Get the final state to check completion status
        final_response = client.get(f"/api/test_user_123/tasks/{task_id}", headers={"Authorization": "Bearer fake-token"})
        assert final_response.status_code == 200
        final_task = final_response.json()
        
        # The final state should be consistent (either true or false)
        assert isinstance(final_task["completed"], bool)