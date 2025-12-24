"""
API Contract Tests
Testing the API endpoints to ensure they follow the OpenAPI specification
"""
import pytest
from fastapi.testclient import TestClient
from main import create_app
from routes import tasks


def test_openapi_spec():
    """Test that OpenAPI spec is available"""
    # Create app for testing
    app = create_app()
    # Include the tasks router without the JWT dependency for testing
    app.include_router(
        tasks.router,
        prefix="/api",
        # Don't add the JWT dependency for tests
    )
    
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        spec = response.json()
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec
        
        # Check that task-related paths exist
        assert "/api/{user_id}/tasks" in spec["paths"]
        assert "/api/{user_id}/tasks/{task_id}" in spec["paths"]
        assert "/api/{user_id}/tasks/{task_id}/complete" in spec["paths"]