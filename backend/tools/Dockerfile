# MCP Server Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (needed for imports)
COPY ../ /app/

# Set working directory to tools
WORKDIR /app/tools

# Expose MCP server port
EXPOSE 8001

# Run MCP server with uvicorn
CMD ["python", "-c", "import uvicorn; from server import mcp; uvicorn.run(mcp.streamable_http_app(), host='0.0.0.0', port=8001, log_level='info')"]
