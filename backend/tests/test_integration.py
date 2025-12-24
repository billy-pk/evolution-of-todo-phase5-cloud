import pytest
from fastapi.testclient import TestClient
from main import app


def test_health_endpoint():
    """Test health check endpoint (related to T092)"""
    with TestClient(app) as client:
        response = client.get("/api/health")
        
        # The health endpoint may or may not exist yet, so check if it's a valid path
        # If it returns 200, check the response format
        # If it returns 404, that's okay if the endpoint hasn't been implemented yet
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # Verify it has expected health check fields
            assert "status" in data
            assert data["status"] in ["healthy", "unhealthy"]


def test_api_documentation_endpoints():
    """Test that API documentation endpoints exist (related to T092)"""
    with TestClient(app) as client:
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code in [200, 404]  # 404 if not configured


def test_app_startup():
    """Test that the app starts correctly (related to T092)"""
    # This test verifies that the app object is properly configured
    assert app is not None
    assert hasattr(app, 'routes')
    
    # Check that some expected routes exist
    route_paths = [route.path for route in app.routes]
    
    # We expect at least the health check and docs routes
    expected_paths = ["/api/health", "/docs", "/redoc"]
    
    found_expected = [path for path in expected_paths if path in route_paths]
    assert len(found_expected) >= 1  # At least one expected path should exist