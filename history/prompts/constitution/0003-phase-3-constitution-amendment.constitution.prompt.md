---
id: 0003
title: Phase 3 Constitution Amendment
stage: constitution
date: 2025-12-15
surface: claude-code-cli
model: claude-sonnet-4.5
feature: none
branch: 002-chatkit-refactor
user: bilali
command: /sp.constitution
labels: [architecture, phase-3, breaking-change, mcp-tools]
links:
  spec: specs/001-ai-chatbot/spec.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  - path: .specify/memory/constitution.md
    created: false
    modified: true
    lines_added: 80
    lines_removed: 56
tests:
  - none
---

## Prompt

User requested constitution amendment to align with Phase 3 requirements:

**REMOVE**:
- Traditional REST API endpoints for tasks and users (e.g., /api/tasks, /api/users)
- React UI components and routes used in Phase 2 web interface
- Frontend logic that handles task CRUD outside of the conversational agent
- Any test or mock data used for the old UI

**ADD/UPDATE** Requirements for Phase 3:
- Implement conversational interface for all Basic Level features
- Use OpenAI Agents SDK for AI logic
- Build MCP server with Official MCP SDK that exposes task operations as tools
- Stateless chat endpoint that persists conversation state to database
- AI agents use MCP tools to manage tasks
- MCP tools will also be stateless and will store state in the database

## Response snapshot

Updated constitution from v1.0.1 to v2.0.0 with MAJOR breaking changes:

**Key Changes**:
1. **REMOVED Principle I**: "Backwards Compatibility" - Phase 3 is now standalone, not extending Phase 2
2. **ADDED Principle I**: "Conversational Interface Primary" - All task operations via natural language chat
3. **UPDATED Principle II**: "Stateless Server Design" - Expanded to explicitly cover MCP tools statefulness
4. **UPDATED Principle IV**: "Single Source of Truth" - Removed UI references, focused on database-centric design
5. **EXPANDED Architecture Strategy**: Detailed MCP Tools Architecture section with:
   - Stateless MCP Server built with Official MCP SDK
   - Chat Endpoint stateless design
   - System boundaries clarified for Frontend → Backend → Agent → MCP Tools → Database flow

**Removed Content**:
- All references to "Phase 2 REST API endpoints"
- All references to "React UI components" and "task CRUD UI"
- All references to "extending Phase 2" or "backwards compatibility"
- Frontend logic for task CRUD outside conversational agent

**Added Content**:
- Conversational interface as primary interaction model
- OpenAI Agents SDK as AI logic framework
- Official MCP SDK for building MCP server
- Stateless MCP tools with database state storage
- Detailed MCP Tools Architecture section
- Updated system boundaries showing complete request flow

## Outcome

- ✅ Impact: MAJOR version bump (1.0.1 → 2.0.0) - Breaking changes to core principles
- 🧪 Tests: N/A - Constitution is documentation
- 📁 Files: 1 file modified (.specify/memory/constitution.md)
- 🔁 Next prompts: Update any existing specs/plans that reference removed principles
- 🧠 Reflection: Successfully redefined Phase 3 from "extension layer" to "standalone conversational AI system"

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A - Constitution amendment
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Verify specs/001-ai-chatbot/spec.md aligns with new constitution
