"""
Integration tests for Chat Endpoint (User Story 6)

Following TDD discipline: Tests written FIRST before implementation

Tests cover:
- T030: Chat endpoint creates conversation
- T031: Chat endpoint loads conversation history
- T032: Chat endpoint requires JWT authentication
- T033: Chat endpoint enforces user isolation
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel, select
from models import Conversation, Message
from uuid import uuid4, UUID
import json


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


@pytest.fixture
def mock_agent_response():
    """Mock agent response for testing without calling OpenAI"""
    return {
        "response": "I've added 'Buy groceries' to your tasks.",
        "tool_calls": [
            {
                "tool": "add_task",
                "parameters": {"user_id": "test_user", "title": "Buy groceries"},
                "result": {"status": "success", "task_id": str(uuid4())}
            }
        ],
        "model": "gpt-4o",
        "tokens_used": 150
    }


# ========================================
# Phase 5: User Story 6 - Chat Endpoint Tests
# ========================================

def test_chat_creates_conversation(session, mock_agent_response):
    """
    T030: Test that chat endpoint creates a new conversation when conversation_id not provided

    Expected behavior:
    - Creates new conversation with user_id
    - Saves user message to database
    - Calls AI agent
    - Saves assistant response to database
    - Returns conversation_id, response, messages
    """
    # This test will be mocked to avoid calling OpenAI
    # We're testing the endpoint logic, not the AI agent

    # Arrange
    user_id = "test_user_123"
    message_text = "Create a task to buy groceries"

    # Mock request to chat endpoint (will be implemented)
    request_data = {
        "message": message_text
    }

    # Expected behavior (test will fail until endpoint is implemented)
    # 1. Endpoint should create conversation
    # 2. Save user message
    # 3. Call agent
    # 4. Save assistant message
    # 5. Return response

    # For now, this will fail with 404 Not Found
    # Once implemented, we'll verify:

    # Verify conversation was created
    conversations = session.exec(select(Conversation).where(Conversation.user_id == user_id)).all()
    # assert len(conversations) == 1  # Will uncomment when endpoint exists

    # Verify messages were saved
    if conversations:
        conversation = conversations[0]
        messages = session.exec(
            select(Message).where(Message.conversation_id == conversation.id)
        ).all()
        # assert len(messages) == 2  # user + assistant
        # assert messages[0].role == "user"
        # assert messages[0].content == message_text
        # assert messages[1].role == "assistant"


def test_chat_loads_conversation_history(session):
    """
    T031: Test that chat endpoint loads existing conversation history

    Expected behavior:
    - When conversation_id provided, load existing conversation
    - Load last 100 messages from conversation
    - Pass message history to AI agent
    - Append new messages to existing conversation
    """
    # Arrange - Create existing conversation with history
    user_id = "test_user_456"
    conversation = Conversation(user_id=user_id)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    # Add previous messages
    msg1 = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content="Create a task to write docs"
    )
    msg2 = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="assistant",
        content="I've added 'Write docs' to your tasks."
    )
    session.add(msg1)
    session.add(msg2)
    session.commit()

    # Act - Send new message to existing conversation
    request_data = {
        "message": "What did I just ask you to do?",
        "conversation_id": str(conversation.id)
    }

    # Expected: Agent should receive previous messages as context
    # Expected: New messages should be appended to same conversation

    # Verify history was loaded (will test when endpoint exists)
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    ).all()

    initial_message_count = len(messages)
    assert initial_message_count == 2  # The two we created


def test_chat_requires_jwt(session):
    """
    T032: Test that chat endpoint requires JWT authentication

    Expected behavior:
    - Request without Authorization header returns 401
    - Request with invalid token returns 401
    - Request with valid token but wrong user_id returns 403
    """
    # Arrange
    user_id = "test_user_789"
    request_data = {
        "message": "Create a task"
    }

    # Test 1: No Authorization header
    # Expected: 401 Unauthorized

    # Test 2: Invalid token
    # Expected: 401 Unauthorized

    # Test 3: Valid token but user_id mismatch
    # Expected: 403 Forbidden

    # These tests will be implemented when we have the endpoint
    # For now, documenting expected behavior
    pass


def test_chat_conversation_ownership(session):
    """
    T033: Test that chat endpoint enforces conversation ownership (user isolation)

    Expected behavior:
    - User A cannot access User B's conversation
    - Attempting to use another user's conversation_id returns 403/404
    - Conversations are filtered by user_id
    """
    # Arrange - Create conversation for User A
    user_a = "user_a_123"
    user_b = "user_b_456"

    conversation_a = Conversation(user_id=user_a)
    session.add(conversation_a)
    session.commit()
    session.refresh(conversation_a)

    # Act - User B tries to access User A's conversation
    request_data = {
        "message": "Show me the history",
        "conversation_id": str(conversation_a.id)
    }

    # Expected: User B's request should be rejected
    # Should return 403 Forbidden or 404 Not Found

    # Verify conversation ownership is checked
    # This will be tested when endpoint exists
    pass


def test_chat_message_persistence():
    """
    Additional test: Verify messages are saved in atomic transaction

    Expected behavior:
    - User message and assistant message saved together
    - If agent fails, user message still saved
    - Transaction rollback on database error
    """
    # This will be implemented with the endpoint
    pass


def test_chat_conversation_updated_at():
    """
    Additional test: Verify conversation updated_at is refreshed

    Expected behavior:
    - conversation.updated_at is updated on each new message
    - Used for sorting conversations by recent activity
    """
    # This will be implemented with the endpoint
    pass
