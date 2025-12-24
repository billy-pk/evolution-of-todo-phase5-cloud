"""
Unit tests for ChatKit integration endpoints.

Tests cover:
- Session creation and validation
- Session token refresh
- Thread management (create, list, get)
- Message handling
- Error scenarios
- User isolation
"""

import pytest
import jwt
import json
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from sqlmodel import Session, select

from main import app
from config import settings
from models import Conversation, Message
from db import get_session
from routes.chatkit import ChatKitSessionManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_user_id():
    """Generate a test user ID"""
    return str(uuid4())


@pytest.fixture
def test_jwt_token(test_user_id):
    """Create a valid Better Auth JWT token"""
    now = datetime.now(UTC)
    payload = {
        "sub": test_user_id,
        "user_id": test_user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.BETTER_AUTH_SECRET,
        algorithm="HS256"
    )
    return token


@pytest.fixture
def invalid_jwt_token():
    """Create an invalid JWT token"""
    return "invalid.token.here"


@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create database session for tests"""
    from db import engine
    from sqlmodel import Session as SQLModelSession

    session = SQLModelSession(engine)
    yield session
    session.close()


# ============================================================================
# Session Endpoint Tests
# ============================================================================

class TestSessionEndpoint:
    """Test POST /api/chatkit/session"""

    def test_create_session_success(self, client, test_jwt_token, test_user_id):
        """Test successful session creation"""
        response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "client_secret" in data
        assert "user_id" in data
        assert data["user_id"] == test_user_id

        # Verify client_secret is a valid JWT
        payload = jwt.decode(
            data["client_secret"],
            settings.BETTER_AUTH_SECRET,
            algorithms=["HS256"]
        )
        assert payload["user_id"] == test_user_id
        assert payload["type"] == "chatkit_session"

    def test_create_session_missing_auth(self, client):
        """Test session creation without authorization header"""
        response = client.post("/api/chatkit/session")

        assert response.status_code == 401
        assert "Missing or invalid Authorization header" in response.json()["detail"]

    def test_create_session_invalid_token(self, client, invalid_jwt_token):
        """Test session creation with invalid JWT"""
        response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {invalid_jwt_token}"}
        )

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_session_token_has_30min_expiry(self, client, test_jwt_token):
        """Test that session token expires in 30 minutes"""
        response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )

        data = response.json()
        payload = jwt.decode(
            data["client_secret"],
            settings.BETTER_AUTH_SECRET,
            algorithms=["HS256"]
        )

        # Extract expiry
        now = datetime.now(UTC).timestamp()
        exp_time = payload["exp"]
        duration = exp_time - payload["iat"]

        # Should be approximately 30 minutes (1800 seconds)
        # Allow ±5 seconds for test execution
        assert 1795 <= duration <= 1805


# ============================================================================
# Refresh Endpoint Tests
# ============================================================================

class TestRefreshEndpoint:
    """Test POST /api/chatkit/refresh"""

    def test_refresh_token_success(self, client, test_jwt_token, test_user_id):
        """Test successful token refresh"""
        # Create initial session
        response1 = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        old_token = response1.json()["client_secret"]

        # Refresh the token
        response2 = client.post(
            "/api/chatkit/refresh",
            json={"token": old_token}
        )

        assert response2.status_code == 200
        data = response2.json()
        assert "client_secret" in data
        assert data["user_id"] == test_user_id

        # New token should be valid
        new_payload = jwt.decode(
            data["client_secret"],
            settings.BETTER_AUTH_SECRET,
            algorithms=["HS256"]
        )
        assert new_payload["user_id"] == test_user_id
        assert new_payload["type"] == "chatkit_session"

    def test_refresh_token_missing_token(self, client):
        """Test refresh without token in body"""
        response = client.post(
            "/api/chatkit/refresh",
            json={}
        )

        assert response.status_code == 400
        assert "Missing token" in response.json()["detail"]

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/chatkit/refresh",
            json={"token": "invalid.token.here"}
        )

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]


# ============================================================================
# Thread Management Tests
# ============================================================================

class TestThreadEndpoints:
    """Test thread (conversation) management endpoints"""

    def test_create_thread(self, client, test_jwt_token, db_session):
        """Test POST /api/chatkit/threads"""
        # Create session first
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        # Create thread
        response = client.post(
            "/api/chatkit/threads",
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "created_at" in data

        # Verify thread exists in database
        stmt = select(Conversation).where(Conversation.id == data["id"])
        conv = db_session.exec(stmt).first()
        assert conv is not None

    def test_list_threads(self, client, test_jwt_token, test_user_id, db_session):
        """Test GET /api/chatkit/threads"""
        # Create session
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        # Create a thread manually in database
        conv = Conversation(user_id=test_user_id)
        db_session.add(conv)
        db_session.commit()

        # List threads
        response = client.get(
            "/api/chatkit/threads",
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert len(data["threads"]) >= 1

    def test_get_thread(self, client, test_jwt_token, test_user_id, db_session):
        """Test GET /api/chatkit/threads/{id}"""
        # Create session
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        # Create thread in database
        conv = Conversation(user_id=test_user_id)
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        # Add a message
        msg = Message(
            conversation_id=conv.id,
            user_id=test_user_id,
            role="user",
            content="Test message"
        )
        db_session.add(msg)
        db_session.commit()

        # Get thread
        response = client.get(
            f"/api/chatkit/threads/{conv.id}",
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(conv.id)
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Test message"

    def test_get_nonexistent_thread(self, client, test_jwt_token):
        """Test GET /api/chatkit/threads/{id} with invalid thread"""
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        response = client.get(
            f"/api/chatkit/threads/{uuid4()}",
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 404


# ============================================================================
# Message Endpoint Tests
# ============================================================================

class TestMessageEndpoint:
    """Test POST /api/chatkit/messages"""

    def test_message_missing_thread_id(self, client, test_jwt_token):
        """Test message without thread_id"""
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        response = client.post(
            "/api/chatkit/messages",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 400
        assert "Missing thread_id or message" in response.json()["detail"]

    def test_message_missing_text(self, client, test_jwt_token):
        """Test message without message text"""
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        response = client.post(
            "/api/chatkit/messages",
            json={"thread_id": str(uuid4())},
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 400

    def test_message_nonexistent_thread(self, client, test_jwt_token):
        """Test message to non-existent thread"""
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret = session_response.json()["client_secret"]

        response = client.post(
            "/api/chatkit/messages",
            json={
                "thread_id": str(uuid4()),
                "message": "Test"
            },
            headers={"Authorization": f"Bearer {client_secret}"}
        )

        assert response.status_code == 404
        assert "Thread not found" in response.json()["detail"]


# ============================================================================
# User Isolation Tests
# ============================================================================

class TestUserIsolation:
    """Test that users can't access each other's data"""

    def test_user_cant_access_other_user_thread(
        self, client, test_user_id, test_jwt_token, db_session
    ):
        """Test that user A can't access user B's thread"""
        user_b_id = str(uuid4())

        # Create session for user A
        session_response = client.post(
            "/api/chatkit/session",
            headers={"Authorization": f"Bearer {test_jwt_token}"}
        )
        client_secret_a = session_response.json()["client_secret"]

        # Create thread for user B
        conv_b = Conversation(user_id=user_b_id)
        db_session.add(conv_b)
        db_session.commit()
        db_session.refresh(conv_b)

        # User A tries to access user B's thread
        response = client.get(
            f"/api/chatkit/threads/{conv_b.id}",
            headers={"Authorization": f"Bearer {client_secret_a}"}
        )

        assert response.status_code == 404


# ============================================================================
# Session Token Manager Tests
# ============================================================================

class TestSessionTokenManager:
    """Test ChatKitSessionManager utility"""

    def test_create_and_verify_token(self, test_user_id):
        """Test token creation and verification"""
        token, _ = ChatKitSessionManager.create_session_token(test_user_id)

        # Verify token
        extracted_user_id = ChatKitSessionManager.verify_session_token(token)

        assert extracted_user_id == test_user_id

    def test_verify_invalid_token(self):
        """Test verifying invalid token"""
        result = ChatKitSessionManager.verify_session_token("invalid.token.here")
        assert result is None

    def test_verify_expired_token(self, test_user_id):
        """Test verifying expired token"""
        # Create token with 0 duration (immediately expired)
        now = datetime.now(UTC)
        payload = {
            "user_id": test_user_id,
            "type": "chatkit_session",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()),  # Already expired
        }

        expired_token = jwt.encode(
            payload,
            settings.BETTER_AUTH_SECRET,
            algorithm="HS256"
        )

        # Verification should fail due to expiry
        result = ChatKitSessionManager.verify_session_token(expired_token)
        assert result is None

    def test_token_not_chatkit_type(self, test_user_id):
        """Test token that's not a ChatKit session token"""
        now = datetime.now(UTC)
        payload = {
            "user_id": test_user_id,
            "type": "some_other_type",  # Wrong type
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }

        token = jwt.encode(
            payload,
            settings.BETTER_AUTH_SECRET,
            algorithm="HS256"
        )

        result = ChatKitSessionManager.verify_session_token(token)
        assert result is None
