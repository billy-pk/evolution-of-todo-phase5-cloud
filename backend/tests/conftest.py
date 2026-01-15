import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlmodel import create_engine, Session, SQLModel
import os
from fastapi import Depends

from main import create_app
from db import get_session, engine
from models import Task, Reminder, RecurrenceRule, AuditLog
from middleware import JWTBearer


def create_test_app():
    """Create a test version of the app with JWT middleware"""
    app = create_app()
    return app


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory database for testing"""
    test_engine = create_engine("sqlite:///./test.db", echo=True)
    SQLModel.metadata.create_all(bind=test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    # Create test app and apply dependency override
    app = create_test_app()
    app.dependency_overrides[get_session] = override_get_session

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def db_session():
    """Provide a database session for direct database operations in tests."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def client(test_db):
    """Create a test client with mocked JWT validation"""
    app = create_test_app()

    # Override JWTBearer to bypass actual token validation
    async def override_jwt_bearer():
        return "test_user_123"  # Return a dummy user_id

    app.dependency_overrides[JWTBearer] = override_jwt_bearer

    with TestClient(app) as c:
        yield c