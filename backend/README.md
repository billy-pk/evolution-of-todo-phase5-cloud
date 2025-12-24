# Backend Setup - Phase 3 AI Chatbot Todo Application

This is the backend for the conversational AI todo application with chat endpoint, MCP tools, and persistent storage.

## Tech Stack
- Python 3.13+
- FastAPI (chat API)
- SQLModel (ORM)
- Neon PostgreSQL
- Better Auth (JWT with JWKS)
- OpenAI Agents SDK
- FastMCP (MCP server)

## Architecture

**Phase 3 Conversational Backend**:
- Single chat endpoint: `POST /api/{user_id}/chat`
- MCP server with 5 task management tools
- OpenAI Agent for natural language processing
- No traditional REST CRUD endpoints

## Setup Instructions

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment with UV
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Environment Configuration
Create a `.env` file with:
```env
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=<shared-secret>
BETTER_AUTH_ISSUER=http://localhost:3000
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
OPENAI_API_KEY=<your-openai-key>
MCP_SERVER_URL=http://localhost:8001
```

**Important**: `BETTER_AUTH_SECRET` must match the frontend configuration.

### 5. Run Database Migrations
```bash
# Create tables in Neon database
python scripts/migrate.py
```

### 6. Start Backend Server
```bash
uvicorn main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000

### 7. Start MCP Server (Required)
In a separate terminal:
```bash
cd backend
source .venv/bin/activate
uv run tools/start_server_8001.py
```

MCP server will be available at: http://localhost:8001

**API Documentation** (auto-generated):
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure
```
main.py              - FastAPI app initialization, chat route
models.py            - SQLModel models (Task, Conversation, Message)
db.py                - Database engine and session management
middleware.py        - JWT authentication middleware (JWKS validation)
config.py            - Configuration (env vars, secrets)
schemas.py           - Pydantic request/response models
routes/
  chat.py            - Chat endpoint for conversational task management
services/
  agent.py           - OpenAI Agent initialization and message processing
tools/
  server.py          - MCP server with task management tools
  start_server_8001.py - MCP server startup script
scripts/
  migrate.py         - Database migration script
tests/               - Pytest test suite
```

## Common Commands
```bash
# Run backend API server
uvicorn main:app --reload --port 8000

# Run MCP server
uv run tools/start_server_8001.py

# Run tests
pytest

# Format code
black .

# Lint code
ruff check .

# Type check
mypy .
```

## API Endpoints

### Chat Endpoint
**POST** `/api/{user_id}/chat`
- **Authentication**: JWT Bearer token required
- **Request Body**:
  ```json
  {
    "message": "Add a task to buy groceries",
    "conversation_id": "optional-uuid"
  }
  ```
- **Response**:
  ```json
  {
    "response": "I've added the task 'buy groceries' to your list.",
    "conversation_id": "uuid"
  }
  ```

### Health Check
**GET** `/health` or `/api/health`
- **Authentication**: Not required
- **Response**: Database connection status

## MCP Tools

The MCP server provides 5 tools for the AI agent:

1. **add_task**: Create a new task
2. **list_tasks**: List user's tasks (all/pending/completed)
3. **update_task**: Update task details
4. **complete_task**: Toggle task completion status
5. **delete_task**: Delete a task

All tools enforce user isolation via `user_id` parameter.

## Database Models

### Task
```python
id: UUID
user_id: str
title: str
description: str | None
completed: bool
created_at: datetime
```

### Conversation
```python
id: UUID
user_id: str
title: str | None
created_at: datetime
```

### Message
```python
id: UUID
conversation_id: UUID
role: str (user/assistant)
content: str
created_at: datetime
```

## Authentication Flow

1. Frontend obtains JWT from Better Auth
2. Frontend sends JWT in `Authorization: Bearer <token>` header
3. Backend validates JWT against JWKS endpoint
4. Extracts `user_id` from JWT claims
5. Enforces user isolation in all database queries

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_chat.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run MCP tool tests
pytest tests/test_tools.py
```

## Development Workflow

1. Start PostgreSQL (Neon) database
2. Start backend API server (port 8000)
3. Start MCP server (port 8001)
4. Start frontend (port 3000)
5. Test chat interface at http://localhost:3000/chat

## Troubleshooting

**MCP Server Connection Issues**:
- Ensure MCP server is running on port 8001
- Check `MCP_SERVER_URL` in `.env`
- Verify no port conflicts

**Authentication Errors**:
- Verify `BETTER_AUTH_SECRET` matches frontend
- Check `BETTER_AUTH_JWKS_URL` is accessible
- Ensure JWT token is included in requests

**Database Connection Issues**:
- Verify `DATABASE_URL` is correct
- Check Neon database is active
- Run migrations if tables don't exist
