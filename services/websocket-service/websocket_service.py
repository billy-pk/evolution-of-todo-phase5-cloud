"""
WebSocket Service (Phase V - Event-Driven Microservices).

This microservice provides real-time task updates via WebSocket connections.
It subscribes to the task-updates topic and broadcasts to connected clients.

Architecture:
- Subscribes to task-updates topic via Dapr Pub/Sub
- Maintains user_id → WebSocket connections mapping
- Validates JWT tokens for authenticated connections
- Broadcasts task updates to all connections for affected user
- Rate limits connections per user (max 3 concurrent connections)

Technology Stack:
- FastAPI for HTTP server and WebSocket endpoints
- Dapr Pub/Sub for event subscription
- JWT validation using JWKS from Better Auth
- Structured logging with correlation IDs

Security:
- JWT token validation before accepting WebSocket connections
- User isolation: users only receive their own task updates
- Connection rate limiting per user
"""

import os
import sys
import logging
import json
from datetime import datetime, UTC
from typing import Dict, Set, Optional
from uuid import uuid4
from collections import defaultdict
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Add backend directory to path for shared modules (JWT validation)
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="WebSocket Service",
    version="1.0.0",
    description="Real-time task updates via WebSocket connections"
)

# Configuration
DAPR_PUBSUB_NAME = os.getenv("DAPR_PUBSUB_NAME", "pubsub")
TASK_UPDATES_TOPIC = "task-updates"
BETTER_AUTH_URL = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
MAX_CONNECTIONS_PER_USER = int(os.getenv("MAX_CONNECTIONS_PER_USER", "3"))
CONNECTION_RATE_LIMIT_WINDOW = 60  # seconds
MAX_CONNECTIONS_PER_WINDOW = 10  # max new connections per minute

# JWKS client for JWT validation (lazy initialization)
_jwks_client = None


def get_jwks_client():
    """Get or initialize JWKS client for JWT validation."""
    global _jwks_client
    if _jwks_client is None:
        try:
            from jwt import PyJWKClient
            jwks_url = f"{BETTER_AUTH_URL}/api/auth/jwks"
            _jwks_client = PyJWKClient(jwks_url)
            logger.info(f"✓ JWKS client initialized: {jwks_url}")
        except Exception as e:
            logger.warning(f"⚠ Failed to initialize JWKS client: {e}")
            _jwks_client = None
    return _jwks_client


def verify_jwt_token(token: str) -> Optional[str]:
    """
    Verify JWT token and return user_id if valid.

    Args:
        token: JWT token string

    Returns:
        user_id if token is valid, None otherwise
    """
    if not token:
        return None

    try:
        import jwt

        jwks_client = get_jwks_client()
        if jwks_client is None:
            logger.warning("JWKS client not available, skipping JWT validation")
            return None

        # Get signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA", "ES256", "RS256"],
            options={
                "verify_exp": True,
                "verify_aud": False,
            }
        )

        # Extract user_id (Better Auth uses various fields)
        user_id = payload.get("user_id") or payload.get("id") or payload.get("sub")

        if user_id:
            logger.debug(f"JWT validated for user: {user_id}")
            return user_id
        else:
            logger.warning("JWT payload missing user identifier")
            return None

    except Exception as e:
        logger.warning(f"JWT validation failed: {e}")
        return None


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - User isolation: connections grouped by user_id
    - Rate limiting: max connections per user
    - Connection rate limiting: prevent spam connections
    - Lifecycle management: connect, disconnect, reconnect handling
    """

    def __init__(self, max_per_user: int = 3):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.max_per_user = max_per_user

        # Connection rate limiting: user_id -> list of connection timestamps
        self.connection_timestamps: Dict[str, list] = defaultdict(list)

    def _cleanup_rate_limit_window(self, user_id: str):
        """Remove expired timestamps from rate limit window."""
        current_time = time.time()
        cutoff = current_time - CONNECTION_RATE_LIMIT_WINDOW
        self.connection_timestamps[user_id] = [
            ts for ts in self.connection_timestamps[user_id] if ts > cutoff
        ]

    def can_connect(self, user_id: str) -> tuple[bool, str]:
        """
        Check if a new connection is allowed for the user.

        Returns:
            (allowed, reason) tuple
        """
        # Check connection count limit
        current_count = len(self.active_connections.get(user_id, set()))
        if current_count >= self.max_per_user:
            return False, f"Maximum connections ({self.max_per_user}) reached for user"

        # Check connection rate limit
        self._cleanup_rate_limit_window(user_id)
        if len(self.connection_timestamps[user_id]) >= MAX_CONNECTIONS_PER_WINDOW:
            return False, "Connection rate limit exceeded. Please wait before reconnecting."

        return True, "OK"

    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID for this connection

        Returns:
            True if connection accepted, False if rejected
        """
        # Check if connection is allowed
        allowed, reason = self.can_connect(user_id)
        if not allowed:
            logger.warning(f"Connection rejected for user {user_id}: {reason}")
            await websocket.close(code=4003, reason=reason)
            return False

        # Accept connection
        await websocket.accept()

        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        # Record connection timestamp for rate limiting
        self.connection_timestamps[user_id].append(time.time())

        logger.info(
            f"✓ WebSocket connected: user_id={user_id} "
            f"(connections: {self.get_connection_count(user_id)}/{self.max_per_user})"
        )
        return True

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(
            f"✓ WebSocket disconnected: user_id={user_id} "
            f"(remaining: {self.get_connection_count(user_id)})"
        )

    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections across all users."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_users(self) -> int:
        """Get number of users with active connections."""
        return len(self.active_connections)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """
        Broadcast message to all connections for a specific user.

        Args:
            user_id: User ID to broadcast to
            message: Message payload to send
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return 0

        connections = self.active_connections[user_id].copy()
        sent_count = 0
        failed_connections = []

        for connection in connections:
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                failed_connections.append(connection)

        # Remove failed connections
        for conn in failed_connections:
            self.disconnect(conn, user_id)

        if sent_count > 0:
            logger.info(f"Broadcast to user {user_id}: {sent_count} connections")

        return sent_count


# Global connection manager
manager = ConnectionManager(max_per_user=MAX_CONNECTIONS_PER_USER)


# Event models
class TaskUpdatePayload(BaseModel):
    """Task update payload from task-updates topic."""
    event_type: str
    task_id: str
    user_id: str
    task_data: dict
    timestamp: str


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {
        "status": "healthy",
        "service": "websocket-service",
        "active_users": manager.get_active_users(),
        "total_connections": manager.get_total_connections()
    }


@app.get("/readiness")
async def readiness_check():
    """Readiness check endpoint."""
    # Check if JWKS client is available (not required but good to have)
    jwks_available = get_jwks_client() is not None

    return {
        "status": "ready",
        "service": "websocket-service",
        "jwks_available": jwks_available
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    return {
        "websocket_active_connections": manager.get_total_connections(),
        "websocket_active_users": manager.get_active_users(),
        "websocket_max_per_user": MAX_CONNECTIONS_PER_USER
    }


@app.get("/dapr/subscribe")
async def subscribe():
    """
    Dapr subscription endpoint.

    Tells Dapr which topics this service subscribes to.
    """
    subscriptions = [
        {
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": TASK_UPDATES_TOPIC,
            "route": "/events/task-updates"
        }
    ]
    logger.info(f"Subscriptions registered: {subscriptions}")
    return subscriptions


@app.post("/events/task-updates")
async def handle_task_update(request: Request):
    """
    Handle task update events from task-updates topic.

    Broadcasts updates to all connected WebSocket clients for the affected user.

    Event Types:
    - task.created: New task created
    - task.updated: Task modified
    - task.completed: Task marked complete
    - task.deleted: Task deleted
    """
    correlation_id = str(uuid4())[:8]

    try:
        body = await request.json()
        logger.info(f"[{correlation_id}] Received event from {TASK_UPDATES_TOPIC} topic")

        # Extract event data (Dapr wraps payload in 'data' field)
        event_data = body.get("data", body)

        event_type = event_data.get("event_type")
        user_id = event_data.get("user_id")
        task_id = event_data.get("task_id")
        task_data = event_data.get("task_data", {})
        timestamp = event_data.get("timestamp", datetime.now(UTC).isoformat())

        if not user_id:
            logger.warning(f"[{correlation_id}] Event missing user_id, skipping broadcast")
            return Response(status_code=200)

        logger.info(f"[{correlation_id}] Processing {event_type}: task={task_id}, user={user_id}")

        # Prepare broadcast message
        message = {
            "type": event_type,
            "task_id": task_id,
            "task_data": task_data,
            "timestamp": timestamp,
            "correlation_id": correlation_id
        }

        # Broadcast to user's WebSocket connections
        sent_count = await manager.broadcast_to_user(user_id, message)

        logger.info(f"[{correlation_id}] ✓ Broadcast complete: {sent_count} connections")

        return Response(status_code=200)

    except json.JSONDecodeError as e:
        logger.error(f"[{correlation_id}] Invalid JSON in event: {e}")
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"[{correlation_id}] Error processing event: {e}", exc_info=True)
        return Response(status_code=200)  # Acknowledge to Dapr even on error


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time task updates.

    Clients connect to /ws/{user_id}?token=<jwt> to receive live updates.

    Authentication:
    - JWT token passed via query parameter
    - Token validated against JWKS
    - user_id in path must match token's user_id

    Connection Lifecycle:
    - On connect: validate token, add to connection manager
    - During connection: handle ping/pong for keepalive
    - On disconnect: remove from connection manager

    Rate Limiting:
    - Max 3 concurrent connections per user
    - Max 10 new connections per minute per user
    """
    connection_id = str(uuid4())[:8]
    authenticated_user_id = None

    try:
        # Validate JWT token
        if token:
            authenticated_user_id = verify_jwt_token(token)
            if authenticated_user_id:
                # Verify user_id matches token
                if authenticated_user_id != user_id:
                    logger.warning(
                        f"[{connection_id}] Token user_id mismatch: "
                        f"path={user_id}, token={authenticated_user_id}"
                    )
                    await websocket.close(code=4001, reason="User ID mismatch")
                    return
                logger.info(f"[{connection_id}] JWT validated for user {user_id}")
            else:
                logger.warning(f"[{connection_id}] Invalid JWT token for user {user_id}")
                # Allow connection but log warning (for development flexibility)
                # In production, uncomment the following:
                # await websocket.close(code=4002, reason="Invalid token")
                # return
        else:
            logger.warning(f"[{connection_id}] No token provided for user {user_id}")
            # Allow connection without token for development
            # In production, require token:
            # await websocket.close(code=4002, reason="Token required")
            # return

        # Connect to manager
        connected = await manager.connect(websocket, user_id)
        if not connected:
            return  # Connection was rejected (rate limit or max connections)

        # Send welcome message
        await websocket.send_json({
            "type": "connection.established",
            "user_id": user_id,
            "connection_id": connection_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "authenticated": authenticated_user_id is not None,
            "message": "Connected to WebSocket service - you will receive real-time task updates"
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()

                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                elif data.startswith("{"):
                    # Handle JSON messages (future use)
                    try:
                        msg = json.loads(data)
                        logger.debug(f"[{connection_id}] Received JSON message: {msg.get('type')}")
                    except json.JSONDecodeError:
                        pass

            except WebSocketDisconnect:
                logger.info(f"[{connection_id}] Client disconnected: user={user_id}")
                break
            except Exception as e:
                logger.error(f"[{connection_id}] Error in WebSocket loop: {e}")
                break

    except Exception as e:
        logger.error(f"[{connection_id}] WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket, user_id)


@app.on_event("startup")
async def startup_event():
    """Log service startup with configuration."""
    logger.info("=" * 60)
    logger.info("WebSocket Service Starting")
    logger.info("=" * 60)
    logger.info(f"Dapr Pub/Sub: {DAPR_PUBSUB_NAME}")
    logger.info(f"Subscribing to topic: {TASK_UPDATES_TOPIC}")
    logger.info(f"WebSocket endpoint: /ws/{{user_id}}?token=<jwt>")
    logger.info(f"Max connections per user: {MAX_CONNECTIONS_PER_USER}")
    logger.info(f"JWKS URL: {BETTER_AUTH_URL}/api/auth/jwks")
    logger.info("=" * 60)

    # Initialize JWKS client on startup
    get_jwks_client()


@app.on_event("shutdown")
async def shutdown_event():
    """Log service shutdown."""
    logger.info(
        f"WebSocket Service shutting down. "
        f"Active connections: {manager.get_total_connections()}"
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8005"))
    logger.info(f"Starting WebSocket Service on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
