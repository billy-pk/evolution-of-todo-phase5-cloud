# Implementation Plan: AI-Powered Chatbot

**Branch**: `001-ai-chatbot` | **Date**: 2025-12-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-chatbot/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Phase 3 adds an AI-powered chatbot interface that enables users to manage tasks through natural language conversation. The chatbot uses OpenAI Agents SDK with GPT-4o model, exposes task operations via MCP (Model Context Protocol) tools, persists conversation history in the database, and integrates seamlessly with the existing Phase 2 task management UI. All chat interactions are authenticated via JWT, fully stateless, and maintain strict user isolation.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript/JavaScript (frontend with Next.js)
**Primary Dependencies**:
  - Backend: FastAPI, SQLModel, OpenAI Agents SDK, MCP SDK (official Python), PyJWT, httpx, uvicorn
  - Frontend: Next.js (App Router), React, OpenAI ChatKit, TailwindCSS, Better Auth (JWT client)
**Storage**: Neon PostgreSQL (via SQLModel ORM)
**Testing**: pytest (backend), Jest + React Testing Library (frontend)
**Target Platform**: Linux/WSL2 development, Docker-ready (for future Kubernetes deployment in Phase 4)
**Project Type**: Web application (frontend + backend)
**Performance Goals**:
  - Chat endpoint response time <3s (95th percentile) for typical task operations
  - Support 50 concurrent users without degradation
  - AI agent processes natural language requests with 90%+ success rate on first attempt
**Constraints**:
  - Must maintain full backwards compatibility with Phase 2 (all REST endpoints, database schema, and UI unchanged)
  - Fully stateless server design (no in-memory session storage)
  - All context reconstructed from database on each request
  - JWT authentication required for all chat endpoints
  - MCP tools must verify task ownership before operations
**Scale/Scope**:
  - 1-50 tasks per user (typical)
  - 2-100 messages per conversation (typical)
  - Rate limit: 100 requests/hour per user
  - Task descriptions capped at 1000 characters
  - Conversations retained indefinitely with manual delete option

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Backwards Compatibility (NON-NEGOTIABLE)
**Status**: ✅ PASS

- All REST API endpoints from Phase 2 remain unchanged (tasks CRUD at `/api/{user_id}/tasks`)
- Tasks table schema remains intact (no migrations to existing columns)
- Better Auth with JWT remains the authentication system
- Task CRUD UI not modified or removed
- New components (chat endpoint, conversations/messages tables, MCP tools) are additive only

### II. Stateless Server Design (NON-NEGOTIABLE)
**Status**: ✅ PASS

- Chat endpoint `/api/{user_id}/chat` is fully stateless
- No in-memory session storage
- Context reconstructed from database on every request using conversation_id
- Each request independently processable with JWT + conversation_id
- OpenAI Agents SDK configured to use external conversation storage (database)

### III. Security First
**Status**: ✅ PASS

- All chat requests require JWT: `Authorization: Bearer <token>`
- User isolation enforced for:
  - Tasks (inherited from Phase 2, already implemented)
  - Conversations (new table with user_id foreign key)
  - Messages (new table with user_id foreign key)
- MCP tools verify task ownership using user_id before any operation
- No hard-coded secrets; using environment variables (OPENAI_API_KEY, DATABASE_URL, BETTER_AUTH_SECRET)
- Path user_id must match token user_id (enforced by existing middleware)

### IV. Single Source of Truth
**Status**: ✅ PASS

- Both UI and Chat interfaces operate on the same `tasks` table
- Tasks created via Chat appear in Phase 2 UI immediately
- Tasks created via UI are accessible and modifiable via Chat
- No data duplication or synchronization logic
- MCP tools call the same database operations as Phase 2 REST endpoints

### V. Test-Driven Development
**Status**: ⚠️ REQUIRES ATTENTION

- Plan includes test strategy for MCP tools, chat endpoint, and integration tests
- Tests will be written before implementation (Red-Green-Refactor cycle)
- Implementation must follow TDD discipline
- **ACTION**: Ensure tasks.md includes explicit test-first tasks for each component

### VI. Extensibility and Modularity
**Status**: ✅ PASS

- Components are modular:
  - MCP tools as separate module (`backend/mcp/tools.py`)
  - Chat endpoint as separate route (`backend/routes/chat.py`)
  - Conversation models as additions to existing models (`backend/models.py`)
  - Frontend chat UI as new page (`frontend/src/app/chat/page.tsx`)
- Clean API boundaries maintained
- No architectural decisions block Phase 4 (Kubernetes) or Phase 5 (Microservices)
- Configuration externalized (OPENAI_API_KEY, MCP_SERVER_URL if needed)
- Docker-ready design (stateless, environment-driven)

### Summary
**Overall Status**: ✅ PASS (with 1 reminder for TDD discipline during implementation)

No violations requiring justification. All non-negotiable principles satisfied. Feature is constitutionally sound and ready for Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── main.py                    # FastAPI app (existing, no changes)
├── models.py                  # SQLModel models (ADD: Conversation, Message)
├── schemas.py                 # Pydantic schemas (ADD: ChatRequest, ChatResponse)
├── db.py                      # Database engine (existing, no changes)
├── config.py                  # Settings (ADD: OPENAI_API_KEY)
├── middleware.py              # JWT auth (existing, no changes)
├── routes/
│   ├── tasks.py               # Task CRUD (existing, no changes)
│   └── chat.py                # NEW: Chat endpoint
├── mcp/
│   ├── __init__.py            # NEW: MCP module init
│   ├── server.py              # NEW: MCP server setup
│   └── tools.py               # NEW: MCP tool implementations (add_task, list_tasks, etc.)
├── services/
│   └── agent.py               # NEW: OpenAI Agents SDK integration
└── tests/
    ├── conftest.py            # Test fixtures (existing)
    ├── test_mcp_tools.py      # NEW: Unit tests for MCP tools
    ├── test_chat_endpoint.py  # NEW: Integration tests for chat endpoint
    └── test_agent.py          # NEW: Unit tests for agent service

frontend/
├── src/
│   ├── app/
│   │   ├── chat/
│   │   │   └── page.tsx       # NEW: Chat page with ChatKit UI
│   │   ├── tasks/             # Existing task pages (no changes)
│   │   └── layout.tsx         # Existing layout (ADD: chat nav link)
│   ├── components/
│   │   └── chat/              # NEW: Chat-specific components (if needed)
│   └── lib/
│       └── api.ts             # API client (ADD: chat endpoint calls)
└── __tests__/
    └── chat/                  # NEW: Frontend tests for chat page
```

**Structure Decision**: Web application structure (Option 2). Existing backend/ and frontend/ directories from Phase 2 are preserved. All Phase 3 additions are modular and isolated in new directories (`backend/mcp/`, `backend/services/`, `frontend/src/app/chat/`) or as new files in existing directories. No modifications to Phase 2 files except for additive changes (new models, new config variables, new navigation link).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. This section is intentionally left empty.

---

## Post-Design Constitution Re-evaluation

*Re-checked after Phase 1 (Design & Contracts) completion*

### Design Artifacts Reviewed
- ✅ research.md (Phase 0)
- ✅ data-model.md (Phase 1)
- ✅ contracts/chat-endpoint.md (Phase 1)
- ✅ contracts/mcp-tools.md (Phase 1)
- ✅ quickstart.md (Phase 1)

### Constitution Compliance Status

#### I. Backwards Compatibility (NON-NEGOTIABLE)
**Status**: ✅ PASS (Re-confirmed)

**Evidence**:
- data-model.md confirms Task model unchanged (line 7-51)
- contracts/chat-endpoint.md shows new endpoint at `/api/{user_id}/chat` (no conflicts with Phase 2 `/api/{user_id}/tasks`)
- contracts/mcp-tools.md shows tools operate on existing tasks table (single source of truth)
- quickstart.md confirms Phase 2 remains fully functional during Phase 3 development

**Conclusion**: No backwards compatibility violations. All Phase 2 functionality preserved.

#### II. Stateless Server Design (NON-NEGOTIABLE)
**Status**: ✅ PASS (Re-confirmed)

**Evidence**:
- contracts/chat-endpoint.md documents stateless request flow (lines 256-264):
  - Context reconstructed from database on each request
  - No in-memory session storage
  - conversation_id used to load history from database
- research.md confirms stateless design pattern (section 5)
- data-model.md shows all state persisted in conversations/messages tables

**Conclusion**: Stateless design fully implemented. Ready for horizontal scaling.

#### III. Security First
**Status**: ✅ PASS (Re-confirmed)

**Evidence**:
- contracts/chat-endpoint.md enforces JWT authentication (lines 13-20, 296-313)
- contracts/mcp-tools.md shows all tools verify user_id and ownership (lines 16-24)
- data-model.md includes user_id in all new tables for isolation (Conversation line 69, Message line 89)
- quickstart.md documents environment variable security (no hard-coded secrets)

**Conclusion**: Security requirements fully satisfied. User isolation enforced at all boundaries.

#### IV. Single Source of Truth
**Status**: ✅ PASS (Re-confirmed)

**Evidence**:
- data-model.md confirms single tasks table (line 7: "NO CHANGES")
- contracts/mcp-tools.md shows tools operate directly on tasks table (no intermediate storage)
- contracts/chat-endpoint.md confirms tasks created via chat appear immediately in Phase 2 UI (FR-036)

**Conclusion**: Single source of truth maintained. No data duplication.

#### V. Test-Driven Development
**Status**: ✅ PASS (Improved from ⚠️)

**Evidence**:
- contracts/mcp-tools.md includes test cases for each tool (lines 89-95, 177-183, etc.)
- contracts/chat-endpoint.md includes unit/integration/load test specifications (lines 376-408)
- quickstart.md documents TDD workflow (Step 7, Red-Green-Refactor)
- research.md includes comprehensive testing strategy (section 7)

**Conclusion**: TDD strategy fully defined. Ready for test-first implementation. Reminder action item satisfied.

#### VI. Extensibility and Modularity
**Status**: ✅ PASS (Re-confirmed)

**Evidence**:
- data-model.md shows modular schema design (2 new tables, no coupling to existing tables beyond user_id)
- contracts/ directory organizes API contracts separately (chat-endpoint.md, mcp-tools.md)
- quickstart.md confirms modular project structure (lines 39-73)
- research.md documents future enhancement paths (streaming, Redis rate limiting, etc.)

**Conclusion**: Modular design maintained. No architectural blockers for Phase 4/5.

### Overall Post-Design Status

**Status**: ✅ ALL GATES PASS

**Summary**:
- All 6 constitutional principles satisfied
- No violations requiring justification
- TDD reminder from initial check has been addressed
- Design artifacts are consistent and complete
- Ready to proceed to `/sp.tasks` for task generation

**No further constitution violations or concerns detected.**

---

## Planning Artifacts Summary

Phase 1 (Design & Contracts) deliverables:

| Artifact              | Status | Location                                      | Lines | Purpose                          |
|-----------------------|--------|-----------------------------------------------|-------|----------------------------------|
| research.md           | ✅      | specs/001-ai-chatbot/research.md              | 588   | Phase 0 research & decisions     |
| data-model.md         | ✅      | specs/001-ai-chatbot/data-model.md            | 382   | Database schema design           |
| chat-endpoint.md      | ✅      | specs/001-ai-chatbot/contracts/chat-endpoint.md | 474   | REST API contract               |
| mcp-tools.md          | ✅      | specs/001-ai-chatbot/contracts/mcp-tools.md   | 658   | MCP tool specifications          |
| quickstart.md         | ✅      | specs/001-ai-chatbot/quickstart.md            | 445   | Development setup guide          |
| plan.md (this file)   | ✅      | specs/001-ai-chatbot/plan.md                  | 235   | Implementation plan & context    |

**Total**: 2,782 lines of planning documentation

**Next Command**: `/sp.tasks` to generate tasks.md (Red-Green-Refactor task breakdown)
