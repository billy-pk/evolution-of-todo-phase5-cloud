# Quickstart: AI-Powered Chatbot Development

**Feature**: 001-ai-chatbot
**Date**: 2025-12-12
**Status**: Ready for Implementation

---

## Prerequisites

Before starting Phase 3 implementation, ensure Phase 2 is fully functional:

✅ **Backend**:
- FastAPI server running on `localhost:8000`
- PostgreSQL database connected (Neon)
- JWT authentication working (Better Auth)
- Task CRUD endpoints operational (`/api/{user_id}/tasks`)

✅ **Frontend**:
- Next.js dev server running on `localhost:3000`
- Better Auth configured with JWT
- Task UI accessible and functional

✅ **Tools**:
- Python 3.13 installed
- UV package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 18+ and npm/pnpm installed
- PostgreSQL client (optional, for manual database inspection)

---

## Step 1: Environment Setup

### Backend Environment Variables

Add the following to `backend/.env`:

```bash
# Existing Phase 2 variables (DO NOT MODIFY)
DATABASE_URL=postgresql://user:pass@host/db
BETTER_AUTH_SECRET=your-secret-key
BETTER_AUTH_URL=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# NEW Phase 3 variables
OPENAI_API_KEY=sk-...                  # Get from OpenAI dashboard
OPENAI_MODEL=gpt-4o                    # Primary model
OPENAI_API_TIMEOUT=30                  # Timeout in seconds
RATE_LIMIT_REQUESTS_PER_HOUR=100      # Rate limit per user
```

**Get OpenAI API Key**:
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and paste into `.env`

### Frontend Environment Variables

Add to `frontend/.env.local` (if not already present):

```bash
# Existing Phase 2 variables
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=your-secret-key
BETTER_AUTH_URL=http://localhost:3000
```

---

## Step 2: Install Dependencies

### Backend Dependencies

```bash
cd backend

# Install OpenAI SDK
uv pip install openai

# Install MCP SDK (official Python)
uv pip install mcp

# Verify installations
uv pip list | grep -E "openai|mcp"
```

**Expected Output**:
```
mcp                    1.0.0
openai                 1.58.1
```

### Frontend Dependencies

```bash
cd frontend

# Install OpenAI ChatKit
npm install @openai/chatkit

# Verify installation
npm list @openai/chatkit
```

---

## Step 3: Database Migration

### Create Conversations and Messages Tables

```bash
cd backend

# Run migration script (to be created in implementation)
uv run python scripts/migrate_conversations.py
```

**Expected Output**:
```
✅ Creating conversations table...
✅ Creating messages table...
✅ Creating indexes...
✅ Migration complete
```

### Verify Tables Created

```bash
# Connect to database and verify
uv run python -c "
from sqlmodel import create_engine, text
from config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public'\"))
    print('Tables:', [row[0] for row in result])
"
```

**Expected Output**:
```
Tables: ['tasks', 'conversations', 'messages', 'user', 'session', 'account', 'verification']
```

---

## Step 4: Project Structure

After implementation, the project structure will be:

```
backend/
├── main.py                    # Existing (no changes)
├── models.py                  # ADD: Conversation, Message models
├── schemas.py                 # ADD: ChatRequest, ChatResponse schemas
├── config.py                  # ADD: OPENAI_API_KEY setting
├── routes/
│   ├── tasks.py               # Existing (no changes)
│   └── chat.py                # NEW: Chat endpoint
├── mcp/
│   ├── __init__.py            # NEW
│   ├── server.py              # NEW: MCP server setup
│   └── tools.py               # NEW: 5 MCP tools
├── services/
│   └── agent.py               # NEW: OpenAI Agents SDK integration
└── tests/
    ├── test_mcp_tools.py      # NEW: MCP tool unit tests
    ├── test_chat_endpoint.py  # NEW: Chat endpoint integration tests
    └── test_agent.py          # NEW: Agent service unit tests

frontend/
├── src/
│   ├── app/
│   │   ├── chat/
│   │   │   └── page.tsx       # NEW: Chat page
│   │   └── layout.tsx         # UPDATE: Add chat nav link
│   └── lib/
│       └── api.ts             # UPDATE: Add chat API calls
└── __tests__/
    └── chat/                  # NEW: Chat page tests
```

---

## Step 5: Development Workflow

### Start Backend (Terminal 1)

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Expected Output**:
```
▲ Next.js 15.x.x
- Local:        http://localhost:3000
- Ready in 2.3s
```

### Run Tests (Terminal 3)

```bash
# Backend tests
cd backend
uv run pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## Step 6: Test Chat Endpoint Manually

### Using curl

```bash
# Get JWT token from Better Auth (login via frontend first)
export JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Test chat endpoint (new conversation)
curl -X POST http://localhost:8000/api/your-user-id/chat \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a task to test the chatbot"}'
```

**Expected Response**:
```json
{
  "conversation_id": "uuid-...",
  "response": "I've created a task 'test the chatbot' for you...",
  "tool_calls": [...],
  "messages": [...]
}
```

### Using Frontend

1. Navigate to http://localhost:3000/chat
2. Type: "Create a task to buy groceries"
3. Send message
4. Verify:
   - Task created in database
   - Response displayed in chat UI
   - Task appears in task list (http://localhost:3000/tasks)

---

## Step 7: TDD Workflow (Red-Green-Refactor)

### 1. Write Test (RED)

```bash
cd backend
# Create test file
cat > tests/test_mcp_tools.py << 'EOF'
def test_add_task_creates_task():
    from backend.mcp.tools import add_task_handler
    result = add_task_handler(user_id="test-user", title="Test task")
    assert result["status"] == "success"
    assert "task_id" in result["data"]
EOF

# Run test (should FAIL)
uv run pytest tests/test_mcp_tools.py::test_add_task_creates_task -v
```

**Expected**: `FAILED` (function doesn't exist yet)

### 2. Implement Feature (GREEN)

```bash
# Implement add_task_handler in backend/mcp/tools.py
# (See data-model.md and mcp-tools.md for implementation details)

# Run test again (should PASS)
uv run pytest tests/test_mcp_tools.py::test_add_task_creates_task -v
```

**Expected**: `PASSED`

### 3. Refactor (REFACTOR)

- Clean up code
- Extract duplicated logic
- Improve naming
- Add comments
- Run tests again (should still PASS)

---

## Step 8: Debugging Tips

### Backend Debugging

```bash
# Enable debug logging
cd backend
uv run uvicorn main:app --reload --log-level debug

# Check database queries
uv run python -c "
from sqlmodel import create_engine, Session, select
from backend.models import Conversation, Message
from backend.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)  # echo=True shows SQL
with Session(engine) as session:
    conversations = session.exec(select(Conversation)).all()
    print(f'Total conversations: {len(conversations)}')
"
```

### Frontend Debugging

```bash
# Check API calls in browser DevTools
# Network tab → Filter by "chat" → Inspect request/response

# React DevTools
# Install extension: https://react.dev/learn/react-developer-tools
```

### OpenAI API Debugging

```python
# Test OpenAI API directly
import openai
from backend.config import settings

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

---

## Step 9: Common Issues & Solutions

### Issue: OpenAI API Key Invalid

**Error**: `AuthenticationError: Incorrect API key provided`

**Solution**:
1. Verify OPENAI_API_KEY in `backend/.env`
2. Check key hasn't been revoked at https://platform.openai.com/api-keys
3. Restart backend server after updating `.env`

### Issue: Database Connection Failed

**Error**: `OperationalError: could not connect to server`

**Solution**:
1. Verify DATABASE_URL in `backend/.env`
2. Check Neon dashboard for database status
3. Test connection: `uv run python -c "from backend.db import engine; engine.connect()"`

### Issue: JWT Token Expired

**Error**: `401 Unauthorized`

**Solution**:
1. Log in again via frontend (Better Auth)
2. Token expires after 24 hours by default
3. Check BETTER_AUTH_SECRET matches between frontend and backend

### Issue: MCP Tools Not Found

**Error**: `Tool 'add_task' not registered`

**Solution**:
1. Verify MCP server initialization in `backend/mcp/server.py`
2. Check tools are registered before agent creation
3. Restart backend server

### Issue: Chat UI Not Loading

**Error**: `Module not found: @openai/chatkit`

**Solution**:
1. Run `npm install @openai/chatkit` in frontend/
2. Clear Next.js cache: `rm -rf frontend/.next`
3. Restart frontend dev server

---

## Step 10: Performance Optimization

### Backend Optimization

```python
# Enable connection pooling (already configured in Phase 2)
# backend/db.py
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10
)

# Limit conversation history loaded
# backend/routes/chat.py
messages = session.exec(
    select(Message)
    .where(Message.conversation_id == conversation_id)
    .order_by(Message.created_at.desc())
    .limit(100)  # Only load last 100 messages
).all()
```

### Frontend Optimization

```typescript
// Implement request debouncing to prevent spam
// frontend/src/app/chat/page.tsx
import { useMemo, useCallback } from 'react';
import debounce from 'lodash/debounce';

const debouncedSendMessage = useMemo(
  () => debounce((message: string) => {
    // Send message to API
  }, 500),
  []
);
```

---

## Step 11: Testing Checklist

Before marking Phase 3 complete, verify:

### Backend Tests
- [ ] All MCP tool unit tests pass (add_task, list_tasks, update_task, complete_task, delete_task)
- [ ] Chat endpoint integration tests pass (create conversation, load history, tool execution)
- [ ] Agent service unit tests pass (message processing, tool calling)
- [ ] User isolation tests pass (cannot access other users' tasks/conversations)
- [ ] Rate limiting tests pass (429 after 100 requests/hour)

### Frontend Tests
- [ ] Chat page renders correctly
- [ ] Message input and send button work
- [ ] Loading indicator displays while AI processes
- [ ] Error messages display for failed requests
- [ ] Conversation history persists across page refreshes

### Integration Tests
- [ ] Create task via chat → Task appears in task list UI
- [ ] Complete task via UI → Chat can list it as completed
- [ ] Multiple conversations → Each maintains separate history
- [ ] JWT expiration → Redirects to login

### Manual QA
- [ ] Natural language commands work (create, list, update, complete, delete tasks)
- [ ] AI asks clarifying questions for ambiguous requests
- [ ] Tool calls displayed in chat UI (optional but recommended)
- [ ] Responsive design works on mobile (optional for MVP)

---

## Step 12: Next Steps After Quickstart

After completing the quickstart setup:

1. **Run `/sp.tasks`** to generate the detailed task list (`specs/001-ai-chatbot/tasks.md`)
2. **Implement tasks** following TDD (Red-Green-Refactor) cycle
3. **Run `/sp.analyze`** to verify cross-artifact consistency
4. **Create ADR** if significant architectural decisions are made (use `/sp.adr`)
5. **Commit work** using `/sp.git.commit_pr` when ready for PR

---

## Summary

Phase 3 quickstart covers:
1. ✅ Environment setup (API keys, dependencies)
2. ✅ Database migration (conversations, messages tables)
3. ✅ Project structure (new files and directories)
4. ✅ Development workflow (TDD, testing, debugging)
5. ✅ Common issues and solutions
6. ✅ Performance optimization tips
7. ✅ Testing checklist

**Ready to implement!** Proceed to `/sp.tasks` to generate the task breakdown.
