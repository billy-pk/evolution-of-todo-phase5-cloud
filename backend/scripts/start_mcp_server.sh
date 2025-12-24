#!/bin/bash
# Start MCP Server for Task Operations
#
# This script starts the MCP server that exposes task management tools
# to the AI agent via the Model Context Protocol.
#
# The server runs at http://localhost:8000/mcp by default.
#
# Usage:
#   ./scripts/start_mcp_server.sh

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting MCP Server..."
echo "📁 Backend directory: $BACKEND_DIR"
echo ""

# Change to backend directory
cd "$BACKEND_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please create a .env file with required configuration"
    echo "   See .env.example for reference"
    exit 1
fi

# Run the MCP server using uv
echo "Starting MCP server at http://localhost:8000/mcp"
echo "Press Ctrl+C to stop the server"
echo ""

uv run python tools/server.py
