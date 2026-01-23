# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Evolution of Todo - Phase 3: AI-Powered Chatbot. A full-stack todo application with conversational AI interface built using FastAPI (backend), Next.js (frontend), Better Auth (authentication), and OpenAI Agents SDK with MCP tools.

**Key Architecture**: Monorepo with separate backend and frontend directories. Backend uses FastAPI with SQLModel ORM connecting to Neon PostgreSQL. Frontend uses Next.js 16+ App Router with Better Auth for JWT-based authentication. AI chatbot layer uses OpenAI Agents SDK with MCP (Model Context Protocol) tools.

## Common Development Commands

### Backend (Python 3.13 + FastAPI)

```bash
cd backend

# Install dependencies (using uv)
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Run development server
uvicorn main:app --reload --port 8000

# Run MCP server (required for chat functionality)
cd tools
python server.py

# Run tests
pytest

# Run specific test file
pytest tests/test_filename.py

# Run with coverage
pytest --cov=. --cov-report=html

# Code quality
ruff check .           # Linting
black .                # Formatting
mypy .                 # Type checking
```

### Frontend (Next.js 16 + TypeScript)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev            # Runs on http://localhost:3000

# Build for production
npm run build

# Run production build
npm start

# Run tests
npm test

# Lint
npm run lint
```

### Environment Setup

Both backend and frontend require `.env` files with matching `BETTER_AUTH_SECRET`:

**Backend** (`backend/.env`):
```
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=<shared-secret>
BETTER_AUTH_ISSUER=http://localhost:3000
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
OPENAI_API_KEY=<your-key>
MCP_SERVER_URL=http://localhost:8001
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=<shared-secret>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://...
```

## Architecture Overview

### Backend Structure (`/backend`)

```
main.py              - FastAPI app entry point, CORS configuration
models.py            - SQLModel models (Task, Conversation, Message)
schemas.py           - Pydantic request/response schemas
db.py                - Database engine and session management
middleware.py        - JWT authentication middleware (JWKS validation)
config.py            - Settings and environment configuration
routes/
  chat.py            - Chat endpoint (POST /api/{user_id}/chat)
services/
  agent.py           - OpenAI Agent initialization and message processing
tools/
  server.py          - MCP server with task tools (FastMCP)
tests/               - Pytest test suite
```

**Key Backend Patterns**:
- All API routes are under `/api/` prefix
- User isolation enforced via JWT `user_id` in path parameters
- Chat endpoint is stateless - reconstructs context from database
- MCP tools connect to same PostgreSQL database as REST API

### Frontend Structure (`/frontend`)

```
app/
  (auth)/            - Auth routes (signin, signup)
  (dashboard)/       - Protected routes (tasks, chat)
  api/auth/          - Better Auth API routes
  layout.tsx         - Root layout
  page.tsx           - Landing page
components/          - React components (TaskForm, TaskList, Navbar)
lib/
  api.ts             - API client with automatic JWT attachment
  auth.ts            - Better Auth server configuration
  auth-client.ts     - Better Auth client configuration
  types.ts           - TypeScript type definitions
```

**Key Frontend Patterns**:
- Uses Next.js App Router with route groups `(auth)`, `(dashboard)`
- Better Auth handles authentication with JWT tokens
- All backend API calls go through `lib/api.ts` which auto-attaches JWT
- Chat page uses OpenAI ChatKit React component

### Authentication Flow

1. User signs up/in via Better Auth on frontend
2. Better Auth generates EdDSA-signed JWT with `user_id` claim
3. Frontend stores session and extracts JWT via `authClient.token()`
4. All API requests include `Authorization: Bearer <token>` header
5. Backend middleware validates JWT against JWKS endpoint
6. Extracted `user_id` must match path parameter for authorization

### AI Chat Architecture

1. User sends message via ChatKit UI at `/chat`
2. Frontend calls `POST /api/{user_id}/chat` with message and conversation_id
3. Backend chat endpoint:
   - Validates JWT and user ownership
   - Loads conversation history from database
   - Initializes OpenAI Agent with MCP tools
   - Processes message through agent
   - Saves messages to database
   - Returns assistant response
4. MCP Server provides tools:
   - `add_task` - Create new task
   - `list_tasks` - List user's tasks
   - `update_task` - Update existing task
   - `complete_task` - Toggle task completion
   - `delete_task` - Delete task

**Critical**: MCP server must be running on port 8001 for chat to work.

### Database Schema

**Core Tables** (SQLModel):
- `tasks` - User tasks (id, user_id, title, description, completed, created_at)
- `conversations` - Chat conversations (id, user_id, title, created_at)
- `messages` - Chat messages (id, conversation_id, role, content, created_at)

**Important**: All tables have `user_id` for multi-tenant isolation.

## Testing

### Backend Tests
- Located in `backend/tests/`
- Use pytest with async support (`pytest-asyncio`)
- Test database operations, API endpoints, JWT middleware, MCP tools
- Run: `pytest` or `pytest tests/test_file.py`

### Frontend Tests
- Located in `frontend/tests/`
- Use Jest + React Testing Library
- Test components in isolation
- Run: `npm test`

### Manual Testing

**Phase 5 Microservices Testing:**
Run automated health checks and event flow tests:
```bash
# Quick health check (17 tests)
./test-microservices-simple.sh

# Event flow verification
./test-event-flow.sh
```

See `TEST_RESULTS.md` for latest test execution results including:
- Pod health status and Dapr components
- Event-driven architecture verification
- Microservices communication testing
- Database and Redpanda connectivity

## Code Standards and Conventions

**Refer to** `.specify/memory/constitution.md` for comprehensive principles.

**Key Points**:
- Python: Follow PEP 8, use type hints, async/await for I/O operations
- TypeScript: Strict mode enabled, explicit return types preferred
- Security: Never hardcode secrets, always validate user_id matches JWT
- Error Handling: Use proper HTTP status codes, provide meaningful error messages
- Single Source of Truth: Tasks created via chat appear in UI and vice versa
- Backwards Compatibility: Phase 3 additions must not break Phase 2 REST API

## Current Development Context

**Active Feature**: Phase 3 AI Chatbot (branch: `001-ai-chatbot`)

**Recent Work**:
- Implemented chat endpoint with conversation persistence
- Set up MCP server with task management tools
- Integrated OpenAI Agents SDK
- Added ChatKit UI component
- Configured JWKS-based JWT validation

**Known Issues/TODOs**:
- Check `specs/001-ai-chatbot/tasks.md` for current task status
- See `gitStatus` for uncommitted changes

## Important Files and References

- `CONSTITUTION.md` - Phase 5 mission, goals, and architectural principles
- `TEST_RESULTS.md` - Latest microservices test execution results
- `DEPLOYMENT_TROUBLESHOOTING.md` - Kubernetes/Minikube troubleshooting guide
- `test-microservices-simple.sh` - Automated health check script
- `test-event-flow.sh` - Event propagation testing script
- `.specify/` - Spec-Driven Development templates and scripts
- `history/prompts/` - Prompt History Records (PHRs)
- `specs/005-event-driven-microservices/` - Phase 5 specifications

## Spec-Driven Development (SDD) Workflow

This project uses Spec-Kit Plus for specification-driven development. Custom slash commands are available in `.claude/commands/`:

- `/sp.specify` - Create/update feature specification
- `/sp.plan` - Generate implementation plan
- `/sp.tasks` - Generate actionable tasks
- `/sp.implement` - Execute implementation
- `/sp.analyze` - Cross-artifact consistency analysis
- `/sp.adr` - Create Architectural Decision Record
- `/sp.phr` - Record Prompt History Record

**Important**: Follow the PHR creation process after completing implementation work (see existing CLAUDE.md rules section for detailed PHR guidelines).

## Multi-Server Development

**Three servers must run simultaneously**:

1. **Frontend** (port 3000): `cd frontend && npm run dev`
2. **Backend** (port 8000): `cd backend && uvicorn main:app --reload`
3. **MCP Server** (port 8001): `cd backend/tools && python server.py`

When making changes that affect chat functionality, restart all three servers to ensure consistency.

## Technology-Specific Notes

### Better Auth
- EdDSA algorithm for JWT signing (not RS256)
- JWKS endpoint at `/api/auth/jwks`
- JWT includes `user_id` claim extracted in middleware
- Session duration: 15 minutes (configurable)

### OpenAI Agents SDK
- Agent initialized per request (stateless)
- MCP tools connected via `MCPServerStreamableHttp`
- Context includes last 50 messages from conversation
- System prompt guides assistant behavior for task management

### FastMCP (MCP Server)
- Uses `FastMCP` with `stateless_http=True`
- Tools decorated with `@mcp.tool()`
- Each tool validates inputs and returns structured responses
- Connects to PostgreSQL via SQLModel engine

### SQLModel
- Combines SQLAlchemy and Pydantic
- Use `Session(engine)` for database operations
- Models inherit from `SQLModel, table=True`
- Automatic Pydantic validation on model creation

## Active Technologies
- Python 3.13 (backend), TypeScript/Next.js 16 (frontend) + FastAPI, Next.js App Router, Better Auth, OpenAI Agents SDK, FastMCP (003-remove-legacy-endpoints)
- Neon PostgreSQL (no schema changes required) (003-remove-legacy-endpoints)

## Recent Changes
- 003-remove-legacy-endpoints: Added Python 3.13 (backend), TypeScript/Next.js 16 (frontend) + FastAPI, Next.js App Router, Better Auth, OpenAI Agents SDK, FastMCP
