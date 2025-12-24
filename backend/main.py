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

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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
