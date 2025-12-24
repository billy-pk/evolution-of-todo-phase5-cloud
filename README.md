# Phase 3: AI-Powered Conversational Todo Application

A full-stack todo application with **pure conversational interface** - all task management via natural language chat powered by OpenAI Agents SDK and MCP tools.

## 🌟 Overview

This is **Phase 3** of the Evolution of Todo project - a complete architectural transformation from traditional REST API + UI to a **conversational-first application**:

- ✅ **No traditional forms** - All CRUD via natural language
- ✅ **No REST endpoints** - Single chat API
- ✅ **Conversational UI** - OpenAI ChatKit interface
- ✅ **MCP Tools** - Structured task operations for AI agent
- ✅ **Stateless Design** - All state in PostgreSQL

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User                                  │
└────────────────────┬────────────────────────────────────┘
                     │ Natural Language
                     ↓
┌─────────────────────────────────────────────────────────┐
│   Next.js Frontend (Port 3000)                          │
│   - OpenAI ChatKit UI                                   │
│   - Better Auth (JWT)                                   │
│   - Single route: /chat                                 │
└────────────────────┬────────────────────────────────────┘
                     │ POST /api/{user_id}/chat + JWT
                     ↓
┌─────────────────────────────────────────────────────────┐
│   FastAPI Backend (Port 8000)                           │
│   - Chat endpoint                                       │
│   - JWT middleware (JWKS validation)                    │
│   - OpenAI Agent orchestration                          │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ↓                       ↓
┌─────────────────┐    ┌──────────────────────┐
│  MCP Server     │    │  Neon PostgreSQL     │
│  (Port 8001)    │    │                      │
│  - 5 Task Tools │    │  - Tasks             │
│  - Stateless    │←───┤  - Conversations     │
│  - FastMCP      │    │  - Messages          │
└─────────────────┘    └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+** (frontend)
- **Python 3.13+** (backend)
- **PostgreSQL** (Neon or local)
- **OpenAI API Key**

### 1. Clone Repository
```bash
git clone <repository-url>
cd phase3-ai-chatbot
```

### 2. Setup Backend
```bash
cd backend
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Configure .env
cp .env.example .env
# Edit .env with your credentials

# Run migrations
python scripts/migrate.py

# Start backend API (Terminal 1)
uvicorn main:app --reload --port 8000

# Start MCP server (Terminal 2)
uv run tools/start_server_8001.py
```

### 3. Setup Frontend
```bash
cd frontend
npm install

# Configure .env.local
cp .env.local.example .env.local
# Edit .env.local with your credentials

# Start frontend (Terminal 3)
npm run dev
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Chat Interface**: http://localhost:3000/chat
- **Backend API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
phase3-ai-chatbot/
├── backend/                    # FastAPI backend
│   ├── main.py                # App entry point
│   ├── routes/
│   │   └── chat.py           # Chat endpoint
│   ├── services/
│   │   └── agent.py          # OpenAI Agent
│   ├── tools/
│   │   ├── server.py         # MCP server
│   │   └── start_server_8001.py
│   ├── models.py             # SQLModel models
│   ├── middleware.py         # JWT auth
│   └── README.md
├── frontend/                  # Next.js frontend
│   ├── app/
│   │   ├── (auth)/           # Auth pages
│   │   ├── (dashboard)/
│   │   │   └── chat/         # Chat interface
│   │   └── api/auth/         # Better Auth
│   ├── components/
│   │   └── Navbar.tsx
│   ├── lib/
│   │   ├── api.ts            # API client
│   │   └── auth.ts           # Auth config
│   └── README.md
├── specs/                     # Feature specifications
│   └── 003-remove-legacy-endpoints/
├── history/prompts/           # Development history (PHRs)
├── CLAUDE.md                  # AI development guide
└── README.md                  # This file
```

## 💬 Using the Chat Interface

### Example Conversations

**Create tasks**:
```
You: Add a task to buy groceries
AI: I've created a task "buy groceries" for you.

You: Create a task: finish the report by Friday with high priority
AI: Task created: "finish the report by Friday" marked as high priority.
```

**List tasks**:
```
You: Show my tasks
AI: You have 3 tasks:
    1. Buy groceries (pending)
    2. Finish the report by Friday (pending, high priority)
    3. Call dentist (completed)

You: List only pending tasks
AI: Here are your pending tasks:
    1. Buy groceries
    2. Finish the report by Friday
```

**Update tasks**:
```
You: Update the groceries task to include milk and bread
AI: Updated task "buy groceries" with description "milk and bread".

You: Change the deadline for the report to Monday
AI: Updated task deadline to Monday.
```

**Complete tasks**:
```
You: Mark the groceries task as done
AI: Task "buy groceries" marked as complete!

You: Complete the report task
AI: Great! Task "finish the report by Friday" is now complete.
```

**Delete tasks**:
```
You: Delete the dentist task
AI: Task "call dentist" has been deleted.
```

## 🔧 Technology Stack

### Frontend
- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **TailwindCSS**
- **Better Auth** (JWT authentication)
- **OpenAI ChatKit** (conversational UI)

### Backend
- **Python 3.13**
- **FastAPI** (async web framework)
- **SQLModel** (ORM)
- **OpenAI Agents SDK** (agent orchestration)
- **FastMCP** (MCP server implementation)
- **Better Auth JWKS** (JWT validation)

### Database
- **Neon PostgreSQL** (serverless)
- **SQLModel Models**: Task, Conversation, Message

### Infrastructure
- **3-server architecture**: Frontend (3000), Backend API (8000), MCP Server (8001)
- **Stateless design**: All state in database
- **User isolation**: JWT-based multi-tenancy

## 📊 MCP Tools

The MCP server exposes 5 tools to the AI agent:

| Tool | Description | Parameters |
|------|-------------|------------|
| `add_task` | Create new task | `user_id`, `title`, `description` |
| `list_tasks` | List user's tasks | `user_id`, `status` (all/pending/completed) |
| `update_task` | Update task | `user_id`, `task_id`, `title`, `description` |
| `complete_task` | Toggle completion | `user_id`, `task_id` |
| `delete_task` | Delete task | `user_id`, `task_id` |

All tools enforce user isolation and return structured JSON responses.

## 🔒 Security

- **JWT Authentication**: All requests require valid Bearer token
- **JWKS Validation**: Backend validates tokens against Better Auth JWKS endpoint
- **User Isolation**: All database queries filtered by authenticated `user_id`
- **No Token in URL**: User ID in path, not in query parameters
- **Path-Token Matching**: Middleware verifies path `user_id` matches JWT claim

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest                    # All tests
pytest tests/test_chat.py # Chat endpoint tests
pytest tests/test_tools.py # MCP tool tests
pytest --cov=.            # With coverage
```

### Frontend Tests
```bash
cd frontend
npm test                  # All tests
npm test -- chat          # Chat component tests
```

### Manual Testing
1. Sign in at http://localhost:3000/signin
2. Navigate to http://localhost:3000/chat
3. Test all CRUD operations conversationally
4. Verify multi-user isolation (sign in as different users)

## 📚 Documentation

- **Frontend Setup**: [frontend/README.md](frontend/README.md)
- **Backend Setup**: [backend/README.md](backend/README.md)
- **AI Development Guide**: [CLAUDE.md](CLAUDE.md)
- **Feature Specs**: [specs/003-remove-legacy-endpoints/](specs/003-remove-legacy-endpoints/)
- **Development History**: [history/prompts/](history/prompts/)

## 🎯 Phase 3 Principles

Per [Constitution v2.0.0](.specify/memory/constitution.md):

1. **Conversational Interface Primary**: All task management via natural language
2. **Stateless Server Design**: Chat endpoint and MCP tools fully stateless
3. **Single Source of Truth**: PostgreSQL database for all state
4. **User Isolation**: JWT-based multi-tenancy at every layer
5. **Zero Legacy Code**: No REST CRUD endpoints, no traditional UI forms

## 🔄 Migration from Phase 2

Phase 3 removes all Phase 2 legacy code:

**Removed**:
- ❌ REST API endpoints (`GET/POST/PUT/PATCH/DELETE /api/{user_id}/tasks`)
- ❌ Traditional UI (TaskForm, TaskList, TaskItem components)
- ❌ Task page at `/tasks`
- ❌ API client methods for task CRUD

**Added**:
- ✅ Single chat endpoint (`POST /api/{user_id}/chat`)
- ✅ MCP server with 5 task tools
- ✅ OpenAI Agent with natural language processing
- ✅ ChatKit conversational UI

**Net Impact**: -993 lines of code (~40% reduction)

## 🛠️ Development

### Running All Servers
```bash
# Terminal 1: Backend API
cd backend && source .venv/bin/activate && uvicorn main:app --reload

# Terminal 2: MCP Server
cd backend && source .venv/bin/activate && uv run tools/start_server_8001.py

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Code Quality
```bash
# Backend
cd backend
black .           # Format
ruff check .      # Lint
mypy .            # Type check

# Frontend
cd frontend
npm run lint      # ESLint
npm run format    # Prettier
```

## 🚧 Troubleshooting

**Chat not responding?**
- Ensure MCP server is running on port 8001
- Check `OPENAI_API_KEY` is set in backend `.env`
- Verify `MCP_SERVER_URL=http://localhost:8001` in backend `.env`

**Authentication errors?**
- Verify `BETTER_AUTH_SECRET` matches in both `.env` files
- Check `BETTER_AUTH_JWKS_URL` is accessible from backend
- Ensure JWT token is being sent in `Authorization` header

**Database errors?**
- Verify `DATABASE_URL` is correct in both `.env` files
- Check Neon database is active
- Run migrations: `python backend/scripts/migrate.py`

## 📝 License

MIT

## 🤝 Contributing

This is an educational project demonstrating Phase 3 conversational architecture. Contributions welcome!

## 🎓 Learning Resources

- **OpenAI Agents SDK**: https://github.com/openai/openai-python
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Model Context Protocol**: https://modelcontextprotocol.io
- **Better Auth**: https://www.better-auth.com
- **Next.js App Router**: https://nextjs.org/docs
