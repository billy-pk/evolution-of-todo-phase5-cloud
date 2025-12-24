---
id: 0001
title: Remove Legacy Endpoints Spec
stage: spec
date: 2025-12-15
surface: claude-code-cli
model: claude-sonnet-4.5
feature: 003-remove-legacy-endpoints
branch: 003-remove-legacy-endpoints
user: bilali
command: /sp.specify
labels: [refactoring, cleanup, phase3, architecture-simplification]
links:
  spec: specs/003-remove-legacy-endpoints/spec.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  - path: specs/003-remove-legacy-endpoints/spec.md
    created: true
    modified: false
    lines_added: 175
    lines_removed: 0
  - path: specs/003-remove-legacy-endpoints/checklists/requirements.md
    created: true
    modified: false
    lines_added: 85
    lines_removed: 0
tests:
  - none
---

## Prompt

User requested specification amendment aligned with new Phase 3 constitution:

```
pl ammend the specifications according to @specs/remove_legacy_endpoints.md
```

**Context**: After updating the constitution to v2.0.0 (Phase 3 as standalone conversational AI system), the user needs to create a formal specification for removing legacy Phase 2 REST API endpoints and UI components per the requirements document at specs/remove_legacy_endpoints.md.

**Source Requirements** (from remove_legacy_endpoints.md):
- Remove traditional REST API endpoints for tasks (/api/tasks, /api/users)
- Remove React UI components and routes used in Phase 2 web interface
- Remove frontend logic that handles task CRUD outside conversational agent
- Remove any test or mock data used for old UI
- Implement conversational interface for all Basic Level features
- Use OpenAI Agents SDK for AI logic
- Build MCP server with Official MCP SDK exposing task operations as tools
- Stateless chat endpoint that persists conversation state to database
- AI agents use MCP tools to manage tasks (stateless, database-backed)

## Response snapshot

Successfully created feature specification for 003-remove-legacy-endpoints:

**Branch Created**: `003-remove-legacy-endpoints`

**Specification Structure**:
1. **3 User Stories** (P1: Backend cleanup, P2: Frontend cleanup, P3: API client cleanup)
   - Each independently testable
   - Clear acceptance scenarios using Given/When/Then format
   - Prioritized by dependency order

2. **6 Functional Requirements** (FR-001 through FR-006)
   - FR-001: Remove backend REST endpoints (tasks.py, main.py import)
   - FR-002: Remove frontend UI (page.tsx, 3 components)
   - FR-003: Remove API client methods (createTask, listTasks, etc.)
   - FR-004: Preserve essential infrastructure (chat, auth, MCP, db models)
   - FR-005: Maintain data integrity (no schema changes, no data loss)
   - FR-006: Removed endpoints return 404

3. **7 Quantitative Success Criteria + 5 Qualitative**
   - SC-001 through SC-007: Measurable outcomes (0 endpoints, 0 components, 100% parity, 500 LOC reduction)
   - Qualitative: Simplified architecture, reduced debt, streamlined UX

4. **Edge Cases**: Bookmarks to /tasks, existing data, build failures

5. **Non-Functional Requirements**: Performance, Security, Maintainability

6. **Assumptions & Dependencies**: MCP tools operational, chat functional, no external dependencies on legacy API

**Validation Results**: All checklist items PASS ✅
- No [NEEDS CLARIFICATION] markers
- No implementation details
- All requirements testable and unambiguous
- Success criteria technology-agnostic and measurable
- Ready for planning phase

## Outcome

- ✅ Impact: Feature specification created and validated for legacy code removal
- 🧪 Tests: N/A (specification phase)
- 📁 Files: 2 files created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: `/sp.plan` to generate implementation plan
- 🧠 Reflection: Specification successfully captures removal requirements without any clarification needs. All requirements are explicit and testable.

## Evaluation notes (flywheel)

- Failure modes observed: None - specification created successfully on first attempt
- Graders run and results (PASS/FAIL): Checklist validation PASS (all 14 items)
- Prompt variant (if applicable): Standard /sp.specify workflow
- Next experiment (smallest change to try): Proceed directly to /sp.plan (no clarifications needed)
