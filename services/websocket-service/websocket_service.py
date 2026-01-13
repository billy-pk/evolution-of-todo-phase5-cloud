"""
WebSocket Service - Phase V Event-Driven Microservices
Provides real-time task updates via WebSocket connections
Subscribes to task-updates topic and broadcasts to connected clients
"""

import os
import logging
import json
from typing import Dict, Set
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="WebSocket Service", version="1.0.0")

# Connection manager - stores active WebSocket connections by user_id
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"✓ WebSocket connected: user_id={user_id} (total connections: {self.get_connection_count(user_id)})")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"✓ WebSocket disconnected: user_id={user_id} (remaining connections: {self.get_connection_count(user_id)})")

    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast message to all connections for a specific user"""
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return

        connections = self.active_connections[user_id].copy()
        logger.info(f"Broadcasting to user {user_id}: {len(connections)} connections")

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {str(e)}")
                self.disconnect(connection, user_id)


# Global connection manager
manager = ConnectionManager()

# Dapr configuration
DAPR_PUBSUB_NAME = os.getenv("DAPR_PUBSUB_NAME", "pubsub")
TASK_UPDATES_TOPIC = "task-updates"


# Event models
class TaskUpdatePayload(BaseModel):
    """Task update payload from task-updates topic"""
    event_type: str
    task_id: str
    user_id: str
    task_data: dict
    timestamp: str


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "status": "healthy",
        "service": "websocket-service",
        "active_users": len(manager.active_connections),
        "total_connections": total_connections
    }


# Dapr Pub/Sub subscription endpoint
@app.get("/dapr/subscribe")
async def subscribe():
    """
    Dapr calls this endpoint to discover pub/sub subscriptions
    Returns list of topics this service subscribes to
    """
    subscriptions = [
        {
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": TASK_UPDATES_TOPIC,
            "route": "/events/task-updates"
        }
    ]
    logger.info(f"Dapr subscribe endpoint called, returning {len(subscriptions)} subscriptions")
    return subscriptions


# Task updates handler
@app.post("/events/task-updates")
async def handle_task_update(request: Request):
    """
    Handle task update events from task-updates topic
    Broadcasts updates to all connected WebSocket clients for the affected user
    """
    try:
        # Parse event
        body = await request.json()
        logger.info(f"Received event from {TASK_UPDATES_TOPIC} topic")

        # Extract event data
        if "data" in body:
            event_data = body["data"]
        else:
            event_data = body

        event_type = event_data.get("event_type")
        user_id = event_data.get("user_id")
        task_id = event_data.get("task_id")
        task_data = event_data.get("task_data", {})

        logger.info(f"Processing update: {event_type} - Task ID: {task_id}, User: {user_id}")

        # Broadcast to user's WebSocket connections
        message = {
            "type": event_type,
            "task_id": task_id,
            "task_data": task_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        await manager.broadcast_to_user(user_id, message)

        logger.info(f"✓ Broadcast complete for user {user_id}")

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"✗ Error processing task update: {str(e)}", exc_info=True)
        return Response(status_code=200)  # Acknowledge to Dapr even on error


# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time task updates
    Clients connect to /ws/{user_id} to receive live updates
    """
    await manager.connect(websocket, user_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection.established",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to WebSocket service - you will receive real-time task updates"
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., heartbeat/ping)
                data = await websocket.receive_text()

                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

            except WebSocketDisconnect:
                logger.info(f"Client disconnected normally: user_id={user_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {str(e)}")
                break

    finally:
        manager.disconnect(websocket, user_id)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log service startup"""
    logger.info("=" * 50)
    logger.info("WebSocket Service Starting")
    logger.info("=" * 50)
    logger.info(f"Dapr Pub/Sub: {DAPR_PUBSUB_NAME}")
    logger.info(f"Subscribing to topic: {TASK_UPDATES_TOPIC}")
    logger.info("WebSocket endpoint: /ws/{user_id}")
    logger.info("=" * 50)


# Main entry point
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8005"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
