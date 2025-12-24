# CONSTITUTION.md
Evolution of Todo – Phase 3: AI-Powered Chatbot

## 1. Purpose of This Document

This Constitution defines the mission, boundaries, requirements, and architectural principles for Phase 3 of the Evolution of Todo project.

Phase 3 builds on the completed implementation from previous phase namely Phase 2, preserving all working functionality while adding an AI-powered natural-language interface using:

- OpenAI ChatKit
- OpenAI Agents SDK
- MCP Tools
- FastAPI chat endpoint
- Conversation/message persistence

This document guides Spec-Kit Plus and Claude Code in generating and implementing Phase 3 specifications.

---

## 2. Inherited System (From Phase 2)

Phase 3 inherits the entire working codebase from Phase 2, which includes:

### 2.1 System Capabilities

- Multi-user authenticated todo system
- Full-stack application:
  - Frontend: Next.js App Router, TailwindCSS
  - Backend: FastAPI, Python
  - Database: SQLModel + Neon PostgreSQL
- Better Auth integration using JWT-based authentication
- REST API providing:
  - Create task
  - List tasks
  - Update task
  - Delete task
  - Toggle completion
- User isolation enforced at the database and API level
- Responsive task management UI

### 2.2 Non-Negotiable Constraints

Phase 3 must not break any Phase 2 functionality:

- All REST endpoints must keep working
- The tasks table schema must remain intact
- Better Auth with JWT must remain the authentication system
- Task CRUD UI must not be modified or removed
- All Phase 2 code must continue running without regression

---

## 3. Phase 3 Mission

Phase 3 introduces an AI-powered conversational interface that enhances the todo system without replacing or altering the existing Phase 2 interfaces.

### 3.1 Goals

- Add a /chat page where users can interact with an AI assistant
- Enable natural-language task management:
  - Add tasks
  - List tasks
  - Update tasks
  - Complete tasks
  - Delete tasks
- Implement a stateless chat endpoint:
  POST /api/{user_id}/chat
- Store and manage conversations and messages in the database
- Implement MCP tools so the agent can operate on tasks using the same database
- Ensure the assistant uses the same data that the main UI uses

### 3.2 New Components Introduced

- Chat UI using OpenAI ChatKit 
- Chat API endpoint (FastAPI)
- OpenAI Agent configuration
- MCP server with tools:
  - add_task
  - list_tasks
  - update_task
  - delete_task
  - complete_task
- SQLModel tables:
  - conversations
  - messages
- Updated frontend API client that attaches JWT to all chat requests

---

## 4. Architectural Principles

### 4.1 Backwards Compatibility

- Existing REST API must remain unchanged
- Task UI must remain functional
- No breaking database migrations are allowed

### 4.2 Stateless Server Design

- Chat endpoint must be fully stateless
- No in-memory session storage allowed
- Context must be reconstructed from the database every time

### 4.3 Security

- All chat requests must include JWT Authorization: Bearer <token>
- User isolation must be enforced for:
  - Tasks
  - Conversations
  - Messages
- MCP tools must verify task ownership using user_id

### 4.4 Single Source of Truth

- Tasks created via Chat must appear in Phase 2 UI
- Tasks created via UI must appear in Chat
- Both systems must operate on the same tasks table

### 4.5 Extensibility

- Architecture must smoothly support next Phase 4 (Kubernetes) and Phase 5 (Cloud-native scaling)
- No hard-coded secrets or hostnames

---

## 5. Deliverables for Phase 3

### 5.1 Specifications

Spec-Kit Plus must generate:

- specs/overview.md
- specs/features/chatbot.md
- specs/api/chat-endpoint.md
- specs/api/mcp-tools.md
- specs/ui/chat-page.md
- specs/database/conversations.md

### 5.2 Implementations

Claude Code must implement:

- /chat frontend page
- ChatKit integration
- JWT-secured chat API
- MCP tools and server
- SQLModel models for conversations and messages
- Database migrations
- Agent initialization logic

---

## 6. Non-Goals for Phase 3

Phase 3 must not:

- Modify or redesign the existing task UI
- Modify task CRUD endpoints
- Replace Better Auth or JWT
- Introduce new authentication methods
- Implement multi-conversation UI
- Add voice functionality (optional future enhancement)

---

## 7. Completion Criteria

### Functional Completion

- /chat UI loads and displays conversation history
- Users can manage tasks using natural language
- MCP tools operate correctly
- Chat endpoint returns assistant messages correctly
- Conversations and messages persist across reloads

### Technical Completion

- JWT authentication enforced on all chat calls
- No Phase 2 functionality is broken
- All specifications validated using /sp.analyze
- Task data remains consistent between UI and Chat

---

## 8. Evolution Path

Phase 3 prepares the system for:

- Phase 4: Kubernetes deployment
- Phase 5: Scalable microservices architecture

Therefore Phase 3 must ensure:

- Components are modular
- Frontend and backend boundaries remain clean
- No architectural decisions block future phases

---

## 9. Summary

Phase 3 is an AI extension layer built on top of the fully functional Phase 2 system.

It enhances the application by adding:

- Conversational intelligence
- Agent-driven task management
- MCP-backed tool execution
- Persisted chat history

All while maintaining:

- Security
- Backwards compatibility
- Extensibility

This Constitution governs all Phase 3 specification and implementation through Spec-Kit Plus and Claude Code.
