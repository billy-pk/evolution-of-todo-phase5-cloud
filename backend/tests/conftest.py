import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlmodel import create_engine, Session, SQLModel
import os
from fastapi import Depends

from main import create_app
from db import get_session
from routes.tasks import verify_user_access
from models import Task
from routes import tasks
from middleware import JWTBearer # Import JWTBearer


def create_test_app():
    """Create a test version of the app with JWT middleware"""
    app = create_app()

    # Include the tasks router with the JWT dependency for testing
    app.include_router(
        tasks.router,
        prefix="/api",
        dependencies=[Depends(JWTBearer())]
    )

    return app


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory database for testing"""
    engine = create_engine("sqlite:///./test.db", echo=True)
    SQLModel.metadata.create_all(bind=engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    # Create test app and apply dependency override
    app = create_test_app()
    app.dependency_overrides[get_session] = override_get_session

    yield engine

    engine.dispose()


@pytest.fixture
def client(test_db):
    """Create a test client with mocked JWT validation"""
    from fastapi import Request

    app = create_test_app()
    # Mock the verify_user_access dependency to return a test user_id
    async def mock_verify_user_access(request: Request, path_user_id: str):
        return path_user_id

    app.dependency_overrides[verify_user_access] = mock_verify_user_access

    # Override JWTBearer to bypass actual token validation
    async def override_jwt_bearer():
        return "test_user_123"  # Return a dummy user_id

    app.dependency_overrides[JWTBearer] = override_jwt_bearer

    with TestClient(app) as c:
        yield c