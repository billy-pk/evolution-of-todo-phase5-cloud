"""
FastAPI Application Entry Point

T020: FastAPI app initialization with CORS configuration
T035: Apply JWT middleware to all /api routes
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from middleware import JWTBearer
import logging
from typing import Optional
from dapr.clients import DaprClient
from services.event_publisher import EventPublisher
import events

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Phase V: Global Dapr client and EventPublisher instances
# Initialized at startup, closed at shutdown
dapr_client: Optional[DaprClient] = None
event_publisher: Optional[EventPublisher] = None


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    T020: Initializes FastAPI with CORS configuration
    """
    app = FastAPI(
        title="Todo API",
        description="API for managing todo tasks with authentication",
        version="1.0.0"
    )

    # T020: Add CORS middleware
    # Note: Cannot use allow_origins=["*"] with allow_credentials=True
    # Must specify exact origins when using credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Local development
            "https://evolution-of-todo-ai-chatbot-phase3.vercel.app",  # Production frontend
            "https://evolution-of-todo-ai-chatbot-phase3-hdxtoezc4.vercel.app",  # Vercel deployment URL
            "https://evolution-of-todo-ai-chatbot-phase3-bftn81ny4.vercel.app",  # Another deployment URL
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Authorization"]
    )

    return app


# Create the main application instance
app = create_app()


# Phase V: Startup and shutdown events for Dapr client lifecycle
@app.on_event("startup")
async def startup_event():
    """
    T029: Initialize Dapr client and EventPublisher on application startup.

    The Dapr client connects to the Dapr sidecar (localhost:3500 by default).
    If Dapr is not available, the app will log a warning but continue running
    (allows backward compatibility with Phase 3/4 without Dapr).
    """
    global dapr_client, event_publisher

    try:
        dapr_client = DaprClient()
        event_publisher = EventPublisher(dapr_client)
        events.set_event_publisher(event_publisher)  # Make available globally
        logger.info("✓ Dapr client initialized successfully (Phase V event-driven mode enabled)")
    except Exception as e:
        logger.warning(f"⚠ Failed to initialize Dapr client: {e}")
        logger.warning("Running in Phase 3/4 compatibility mode (events disabled)")
        dapr_client = None
        event_publisher = None
        events.set_event_publisher(None)


@app.on_event("shutdown")
async def shutdown_event():
    """
    T029: Close Dapr client connection on application shutdown.
    """
    global dapr_client, event_publisher

    if event_publisher:
        event_publisher.close()
        logger.info("✓ EventPublisher closed")

    if dapr_client:
        dapr_client.close()
        logger.info("✓ Dapr client closed")


@app.head("/health")
@app.get("/health")
async def health_check():
    """
    T086: Health check endpoint with database connection verification.
    GET /api/health (also accessible at /health for convenience).
    Does not require JWT authentication but verifies database connectivity.
    """
    from db import engine
    from sqlmodel import text

    health_status = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "disconnected"
    }

    try:
        # Test database connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    return health_status


# Alias for /api/health (same handler)
@app.get("/api/health")
async def health_check_api():
    """
    T086: Health check endpoint at /api/health.
    Does not require JWT authentication - defined before middleware is applied.
    """
    return await health_check()


# T044: Include chat route (User Story 6 - Conversation History)
# Chat endpoint already has JWTBearer in its dependencies
try:
    from routes import chat
    app.include_router(chat.router)  # No need for prefix - already in router
    logging.getLogger(__name__).info("Chat route registered successfully")
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import chat route: {e}")
except Exception as e:
    logging.getLogger(__name__).error(f"Error registering chat route: {e}")

# ChatKit integration routes (no JWT middleware - handles auth internally)
# These endpoints bridge ChatKit UI with our custom conversation database
try:
    from routes import chatkit
    app.include_router(chatkit.router)
    app.include_router(chatkit.chatkit_router)
    logging.getLogger(__name__).info("ChatKit routes registered successfully")
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import chatkit route: {e}")
except Exception as e:
    logging.getLogger(__name__).error(f"Error registering chatkit route: {e}")
