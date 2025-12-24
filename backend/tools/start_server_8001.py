#!/usr/bin/env python
"""
Start MCP Server on Port 8001

This script starts the MCP server on port 8001 using uvicorn directly.
"""

import uvicorn
from server import mcp

if __name__ == "__main__":
    # Get the streamable HTTP app from FastMCP
    app = mcp.streamable_http_app()

    # Run with uvicorn on port 8001
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )
