# MCP Server - Task Management Tools

This directory contains the MCP (Model Context Protocol) server that exposes task management tools to the AI agent.

## Architecture

```
┌─────────────────┐
│  OpenAI Agent   │  (backend/services/agent.py)
│    (GPT-4o)     │
└────────┬────────┘
         │
         │ MCPServerStreamableHttp
         │ (http://localhost:8000/mcp)
         │
┌────────▼────────┐
│   MCP Server    │  (backend/tools/server.py)
│    (FastMCP)    │
└────────┬────────┘
         │
         │ Direct DB Access
         │
┌────────▼────────┐
│   PostgreSQL    │  (Neon)
│   Database      │
└─────────────────┘
```

## Available Tools

1. **add_task** - Create a new task
   - Parameters: `user_id`, `title`, `description` (optional)
   - Returns: Task ID, title, completion status

2. **list_tasks** - List user's tasks (coming soon)
3. **complete_task** - Mark task as complete (coming soon)
4. **update_task** - Update task title/description (coming soon)
5. **delete_task** - Delete a task (coming soon)

## Running the MCP Server

### Option 1: Using the startup script

```bash
cd backend
./scripts/start_mcp_server.sh
```

### Option 2: Direct execution

```bash
cd backend
uv run python tools/server.py
```

The server will start at **http://localhost:8000/mcp**

## Development

### Running Tests

```bash
cd backend
uv run pytest tests/test_mcp_tools.py -v
```

### Adding New Tools

1. Define the tool function in `server.py`
2. Decorate with `@mcp.tool()`
3. Write tests in `tests/test_mcp_tools.py` (TDD: write tests first!)
4. Implement the tool logic
5. The tool will automatically be discovered by the AI agent

Example:

```python
@mcp.tool()
def my_new_tool(user_id: str, param: str) -> dict:
    """Tool description for the AI agent.

    Args:
        user_id: User ID from JWT token
        param: Parameter description

    Returns:
        Dict with status and data
    """
    # Implementation
    return {
        "status": "success",
        "data": {...}
    }
```

## Environment Variables

Required in `.env`:

```
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
MCP_SERVER_URL=http://localhost:8000/mcp
```

## Troubleshooting

### Server won't start
- Check that port 8000 is available
- Verify DATABASE_URL is set in .env
- Ensure all dependencies are installed: `uv sync`

### Tools not visible to agent
- Verify MCP server is running
- Check MCP_SERVER_URL matches in both server and agent config
- Look for connection errors in agent logs
