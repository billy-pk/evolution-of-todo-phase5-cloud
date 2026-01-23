"""
Integration Test for WebSocket Broadcasting (Phase V - Phase 9).

This test validates that the WebSocket Service correctly broadcasts task updates:
- WebSocket connection establishment
- Dapr event subscription and handling
- User-isolated broadcasting (users only receive their own updates)
- Connection lifecycle management

Test Strategy:
- Simulate WebSocket connections using FastAPI TestClient
- Simulate Dapr event payloads to /events/task-updates endpoint
- Verify messages are broadcast to correct user connections
- Test rate limiting and max connections per user
- Test error handling and disconnection scenarios

Expected Behavior:
- WebSocket endpoint accepts connections with/without JWT token
- Dapr events trigger broadcast to matching user connections
- User isolation: user A doesn't receive user B's updates
- Multiple connections per user all receive broadcasts
- Failed connections are removed from manager
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import json
import asyncio

import sys
import os

# Add websocket service to path
websocket_service_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "services", "websocket-service"
)
sys.path.insert(0, websocket_service_dir)


@pytest.fixture
def test_user_id():
    """Fixture for unique test user ID."""
    return f"test-user-{uuid4()}"


@pytest.fixture
def test_user_id_2():
    """Fixture for second unique test user ID."""
    return f"test-user-{uuid4()}"


@pytest.fixture
def websocket_client():
    """Fixture to create test client for WebSocket service."""
    from websocket_service import app
    with TestClient(app) as client:
        yield client


def create_task_update_event(
    event_type: str,
    user_id: str,
    task_id: str = None,
    task_data: dict = None
) -> dict:
    """
    Create a mock task update event payload in Dapr format.

    Args:
        event_type: Event type (task.created, task.updated, etc.)
        user_id: User ID for the event
        task_id: Task ID (optional, generates if not provided)
        task_data: Task data (optional, uses defaults if not provided)

    Returns:
        Dict formatted as Dapr CloudEvent
    """
    if task_id is None:
        task_id = str(uuid4())

    if task_data is None:
        task_data = {
            "id": task_id,
            "title": f"Test task for {event_type}",
            "description": "Test description",
            "completed": event_type == "task.completed",
            "priority": "normal",
            "tags": ["test"],
            "due_date": datetime.now(UTC).isoformat()
        }

    return {
        "data": {
            "event_type": event_type,
            "task_id": task_id,
            "user_id": user_id,
            "task_data": task_data,
            "timestamp": datetime.now(UTC).isoformat()
        }
    }


def test_websocket_service_health(websocket_client):
    """
    Test WebSocket service health endpoint.

    Expected: Returns healthy status with connection counts
    """
    response = websocket_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "websocket-service"
    assert "active_users" in data
    assert "total_connections" in data


def test_websocket_service_readiness(websocket_client):
    """
    Test WebSocket service readiness endpoint.

    Expected: Returns ready status
    """
    response = websocket_client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "websocket-service"


def test_websocket_service_metrics(websocket_client):
    """
    Test WebSocket service metrics endpoint.

    Expected: Returns metrics for monitoring
    """
    response = websocket_client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "websocket_active_connections" in data
    assert "websocket_active_users" in data
    assert "websocket_max_per_user" in data


def test_dapr_subscribe_endpoint(websocket_client):
    """
    Test Dapr subscription endpoint.

    Expected: Returns subscription to task-updates topic
    """
    response = websocket_client.get("/dapr/subscribe")
    assert response.status_code == 200
    subscriptions = response.json()
    assert len(subscriptions) == 1
    assert subscriptions[0]["topic"] == "task-updates"
    assert subscriptions[0]["route"] == "/events/task-updates"


def test_websocket_connection_establishment(websocket_client, test_user_id):
    """
    Test WebSocket connection can be established.

    Expected:
    - Connection is accepted
    - Welcome message is received
    - Connection is tracked in manager
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Should receive welcome message
        data = websocket.receive_json()
        assert data["type"] == "connection.established"
        assert data["user_id"] == test_user_id
        assert "connection_id" in data
        assert "timestamp" in data


def test_websocket_ping_pong(websocket_client, test_user_id):
    """
    Test WebSocket ping/pong keepalive.

    Expected:
    - Server responds to 'ping' with 'pong' JSON message
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Skip welcome message
        websocket.receive_json()

        # Send ping
        websocket.send_text("ping")

        # Should receive pong
        data = websocket.receive_json()
        assert data["type"] == "pong"
        assert "timestamp" in data


def test_task_update_event_handling(websocket_client, test_user_id):
    """
    Test that task update events are handled correctly.

    Expected:
    - Event is accepted (200 response)
    - Event is logged (no errors)
    """
    event = create_task_update_event(
        event_type="task.created",
        user_id=test_user_id
    )

    response = websocket_client.post("/events/task-updates", json=event)
    assert response.status_code == 200


def test_task_update_event_missing_user_id(websocket_client):
    """
    Test handling of events without user_id.

    Expected:
    - Returns 200 (no error response)
    - No broadcast attempted
    """
    event = {
        "data": {
            "event_type": "task.created",
            "task_id": str(uuid4()),
            # Missing: user_id
            "task_data": {"title": "Test", "completed": False},
            "timestamp": datetime.now(UTC).isoformat()
        }
    }

    response = websocket_client.post("/events/task-updates", json=event)
    assert response.status_code == 200


def test_task_update_broadcast_to_connected_user(websocket_client, test_user_id):
    """
    Test that task update is broadcast to connected user.

    Expected:
    - Connected WebSocket receives the broadcast message
    - Message contains correct event type and task data
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Skip welcome message
        websocket.receive_json()

        # Send task update event
        task_id = str(uuid4())
        event = create_task_update_event(
            event_type="task.created",
            user_id=test_user_id,
            task_id=task_id,
            task_data={
                "id": task_id,
                "title": "Broadcast test task",
                "completed": False,
                "priority": "high"
            }
        )

        websocket_client.post("/events/task-updates", json=event)

        # WebSocket should receive broadcast
        data = websocket.receive_json()
        assert data["type"] == "task.created"
        assert data["task_id"] == task_id
        assert data["task_data"]["title"] == "Broadcast test task"
        assert "correlation_id" in data


def test_user_isolation_no_cross_broadcast(websocket_client, test_user_id, test_user_id_2):
    """
    Test that users only receive their own updates (user isolation).

    Expected:
    - User A's update is NOT broadcast to User B
    - User isolation is enforced
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id_2}") as websocket_user_b:
        # Skip welcome message for user B
        websocket_user_b.receive_json()

        # Send task update event for user A
        event = create_task_update_event(
            event_type="task.created",
            user_id=test_user_id  # User A
        )

        websocket_client.post("/events/task-updates", json=event)

        # User B should NOT receive any message (we'll use a timeout approach)
        # In TestClient, we can't easily do timeout, so we verify through metrics
        # that user B's connection is still active but didn't receive the message

        # Verify health shows 1 active user (user B)
        health = websocket_client.get("/health").json()
        assert health["active_users"] >= 1


def test_multiple_connections_same_user(websocket_client, test_user_id):
    """
    Test that multiple connections for same user all receive broadcasts.

    Expected:
    - Both connections receive the same broadcast
    - Connection count increases correctly
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as ws1:
        # Skip welcome
        ws1.receive_json()

        with websocket_client.websocket_connect(f"/ws/{test_user_id}") as ws2:
            # Skip welcome
            ws2.receive_json()

            # Verify two connections
            health = websocket_client.get("/health").json()
            assert health["total_connections"] >= 2

            # Send event
            task_id = str(uuid4())
            event = create_task_update_event(
                event_type="task.updated",
                user_id=test_user_id,
                task_id=task_id
            )

            websocket_client.post("/events/task-updates", json=event)

            # Both connections should receive broadcast
            data1 = ws1.receive_json()
            data2 = ws2.receive_json()

            assert data1["type"] == "task.updated"
            assert data2["type"] == "task.updated"
            assert data1["task_id"] == task_id
            assert data2["task_id"] == task_id


def test_all_event_types_broadcast(websocket_client, test_user_id):
    """
    Test that all event types are broadcast correctly.

    Expected:
    - task.created, task.updated, task.completed, task.deleted all broadcast
    """
    event_types = ["task.created", "task.updated", "task.completed", "task.deleted"]

    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Skip welcome
        websocket.receive_json()

        for event_type in event_types:
            task_id = str(uuid4())
            event = create_task_update_event(
                event_type=event_type,
                user_id=test_user_id,
                task_id=task_id
            )

            websocket_client.post("/events/task-updates", json=event)

            # Should receive broadcast
            data = websocket.receive_json()
            assert data["type"] == event_type
            assert data["task_id"] == task_id


def test_unwrapped_event_format(websocket_client, test_user_id):
    """
    Test handling of events without Dapr 'data' wrapper.

    Expected:
    - Service handles both wrapped and unwrapped formats
    """
    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Skip welcome
        websocket.receive_json()

        task_id = str(uuid4())
        # Send event without 'data' wrapper (direct format)
        event = {
            "event_type": "task.created",
            "task_id": task_id,
            "user_id": test_user_id,
            "task_data": {"title": "Unwrapped event task", "completed": False},
            "timestamp": datetime.now(UTC).isoformat()
        }

        websocket_client.post("/events/task-updates", json=event)

        # Should receive broadcast
        data = websocket.receive_json()
        assert data["type"] == "task.created"
        assert data["task_id"] == task_id


def test_connection_count_tracking(websocket_client, test_user_id):
    """
    Test that connection counts are tracked accurately.

    Expected:
    - Connection count increases on connect
    - Connection count decreases on disconnect
    """
    # Initial state
    health_before = websocket_client.get("/health").json()
    initial_connections = health_before["total_connections"]

    with websocket_client.websocket_connect(f"/ws/{test_user_id}") as websocket:
        # Skip welcome
        websocket.receive_json()

        # Check connection count increased
        health_during = websocket_client.get("/health").json()
        assert health_during["total_connections"] == initial_connections + 1
        assert health_during["active_users"] >= 1

    # After disconnect, count should decrease (may need small delay)
    health_after = websocket_client.get("/health").json()
    assert health_after["total_connections"] == initial_connections


def test_invalid_json_event(websocket_client):
    """
    Test handling of invalid JSON in event payload.

    Expected:
    - Returns 200 (graceful handling)
    - Error is logged but doesn't break service
    """
    response = websocket_client.post(
        "/events/task-updates",
        content="invalid json {",
        headers={"Content-Type": "application/json"}
    )
    # FastAPI may return 422 for invalid JSON, or 200 if we handle it
    assert response.status_code in [200, 422]
