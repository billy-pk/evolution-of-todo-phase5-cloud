---
id: 0003
title: AI chatbot implementation planning
stage: plan
date: 2025-12-12
surface: agent
model: claude-sonnet-4-5
feature: 001-ai-chatbot
branch: 001-ai-chatbot
user: bilali
command: /sp.plan
labels: ["planning", "ai-chatbot", "mcp-tools", "openai-agents", "phase3"]
links:
  spec: specs/001-ai-chatbot/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-ai-chatbot/plan.md
  - specs/001-ai-chatbot/research.md
  - specs/001-ai-chatbot/data-model.md
  - specs/001-ai-chatbot/contracts/chat-endpoint.md
  - specs/001-ai-chatbot/contracts/mcp-tools.md
  - specs/001-ai-chatbot/quickstart.md
  - CLAUDE.md
tests:
  - None (planning stage - no tests executed)
---

## Prompt

prepare implementation plan according to: # Phase 3 Implementation Plan – AI-Powered Chatbot

## 1. Purpose

This document defines the  plan/implementation strategy for Phase 3 of the Evolution of Todo project.
Phase 3 adds an AI chat interface using ChatKit, OpenAI Agents SDK, LLM GPT-4o, MCP tools using official MCP SDK and persistent conversation storage.
The plan preserves all Phase 2 functionality and builds on the existing full-stack application.

---

# 2. Technology Stack for Phase 3

## 2.1 Frontend
- Next.js (App Router)
- OpenAI ChatKit UI components
- TailwindCSS
- JWT authentication via Better Auth
- API calls using fetch with Authorization header

## 2.2 Backend
- FastAPI
- SQLModel ORM
- Neon PostgreSQL
- UV for Python environment and dependency management
- OpenAI Agents SDK
- GPT-4o as the primary model
- Official MCP SDK for python
- MCP server for task operations
- Pydantic for request/response models

## 2.3 Dev Tools
- UV for:
  - Virtual environment
  - Dependency installation
  - Running FastAPI backend

## 2.4 MCP Tools Specification

The MCP server exposes tools to allow the AI agent to manipulate tasks in the existing database.

---

## Tool: add_task
Purpose:
Create a new task.

Parameters:
- user_id (string, required)
- title (string, required)
- description (string, optional)

Output:
- task_id
- status ("created")
- title

---

## Tool: list_tasks
Purpose:
List tasks for a user.

Parameters:
- user_id (string, required)
- status ("all", "pending", "completed")

Output:
List of task objects.

---

## Tool: update_task
Purpose:
Modify title or description.

Parameters:
- user_id (string, required)
- task_id (int, required)
- title (string, optional)
- description (string, optional)

Output:
- task_id
- status ("updated")
- title

---

## Tool: complete_task
Purpose:
Mark task as completed.

Parameters:
- user_id (string, required)
- task_id (int, required)

Output:
- task_id
- status ("completed")
- title

---

## Tool: delete_task
Purpose:
Delete a task.

Parameters:
- user_id (string, required)
- task_id (int, required)

Output:
- task_id
- status ("deleted")
- title

---

## Security Rules
- All tools verify user ownership
- Tools must not leak data across users

## Response snapshot

Planning workflow executed successfully with the following key outputs:

**Phase 0 (Research)**: Generated research.md (588 lines) covering:
- OpenAI Agents SDK integration with GPT-4o
- MCP SDK for standardized tool definitions
- Database schema design (Conversation and Message tables)
- OpenAI ChatKit frontend integration
- Stateless REST endpoint architecture
- Rate limiting strategy
- Comprehensive testing strategy (Unit + Integration + E2E)
- Environment configuration approach

**Phase 1 (Design & Contracts)**: Generated:
- data-model.md (382 lines): Complete database schema for Conversation and Message entities, ERD, SQLModel definitions, migration scripts
- contracts/chat-endpoint.md (474 lines): Full REST API contract with request/response formats, error handling, security, performance characteristics
- contracts/mcp-tools.md (658 lines): Detailed specifications for 5 MCP tools (add_task, list_tasks, update_task, complete_task, delete_task) with Pydantic schemas, test cases, security patterns
- quickstart.md (445 lines): Development setup guide covering prerequisites, dependencies, database migration, TDD workflow, debugging tips, testing checklist

**Constitution Check**: All 6 constitutional principles validated (pre-design and post-design):
- ✅ Backwards Compatibility (NON-NEGOTIABLE)
- ✅ Stateless Server Design (NON-NEGOTIABLE)
- ✅ Security First
- ✅ Single Source of Truth
- ✅ Test-Driven Development (improved from ⚠️ to ✅)
- ✅ Extensibility and Modularity

**Agent Context**: Updated CLAUDE.md with Phase 3 technologies (Python 3.13, Neon PostgreSQL)

**Total Planning Documentation**: 2,782 lines across 6 artifacts

## Outcome

- ✅ Impact: Complete implementation plan with research, design, contracts, and quickstart guide. All constitutional gates passed. Ready for task generation via /sp.tasks.
- 🧪 Tests: No tests executed (planning stage). Test strategy fully defined in research.md and contracts.
- 📁 Files: Created 6 planning artifacts (plan.md, research.md, data-model.md, chat-endpoint.md, mcp-tools.md, quickstart.md). Updated CLAUDE.md.
- 🔁 Next prompts: Run /sp.tasks to generate task breakdown (tasks.md) with Red-Green-Refactor cycles.
- 🧠 Reflection: Planning workflow followed structured approach (Phase 0 research → Phase 1 design → Constitution re-evaluation). All unknowns resolved. No architectural blockers detected.

## Evaluation notes (flywheel)

- Failure modes observed: None. Planning workflow executed smoothly.
- Graders run and results (PASS/FAIL): PASS - All constitutional gates passed, no violations.
- Prompt variant (if applicable): Standard /sp.plan command with technology stack specification
- Next experiment (smallest change to try): Proceed with /sp.tasks to generate task breakdown and validate TDD workflow design.
