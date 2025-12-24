#!/usr/bin/env python3
"""
Standalone MCP Server for Separate Deployment

This script runs the MCP server as a standalone service for 2-service deployment.
Use this when MOUNT_MCP_SERVER=false and MCP runs on a separate host.

Usage:
    python mcp_standalone.py

Environment Variables:
    PORT - Port to run on (default: 8001)
    DATABASE_URL - PostgreSQL connection string
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import MCP server
from tools.server import mcp

def main():
    """Run the standalone MCP server."""
    import uvicorn
    import contextlib
    from typing import AsyncIterator

    port = int(os.environ.get("PORT", 8001))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting standalone MCP server on {host}:{port}")
    logger.info(f"   MCP endpoint will be at: http://{host}:{port}/")
    logger.info(f"   Database: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")

    # Create lifespan context manager to initialize MCP session manager
    @contextlib.asynccontextmanager
    async def lifespan_wrapper(app) -> AsyncIterator[None]:
        """Initialize MCP session manager on startup."""
        logger.info("🔌 Initializing MCP session manager...")
        async with mcp.session_manager.run():
            logger.info("✅ MCP session manager initialized")
            yield
        logger.info("🔌 MCP session manager shutdown")

    # Get the streamable HTTP ASGI app from FastMCP (serves at root)
    mcp_app = mcp.streamable_http_app()

    # --- ADD HEALTH CHECK HERE ---
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    # Define a simple function for the health check
    async def health_check(request):
        return JSONResponse({"status": "healthy", "service": "mcp-standalone"})

    # Manually add the route to the Starlette app's router
    # This handles both GET and HEAD automatically
    mcp_app.routes.append(Route("/health", endpoint=health_check, methods=["GET", "HEAD"]))

    # Wrap with lifespan
    mcp_app.router.lifespan_context = lifespan_wrapper

    # Run with uvicorn - MCP serves at root path
    # Transport security is configured in tools/server.py with allowed_hosts
    uvicorn.run(mcp_app, host=host, port=port)

if __name__ == "__main__":
    main()
