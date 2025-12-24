---
id: 0005
title: architectural-correction-openai-agents-sdk
stage: plan
date: 2025-12-12
surface: agent
model: claude-sonnet-4-5
feature: 001-ai-chatbot
branch: 001-ai-chatbot
user: bilali
command: /sp.phr
labels: ["architecture", "openai-agents-sdk", "documentation-correction", "planning", "official-documentation", "context7"]
links:
  spec: specs/001-ai-chatbot/spec.md
  ticket: null
  adr: history/adr/0001-mcp-tool-integration-for-ai-agent-task-operations.md
  pr: null
files:
  - specs/001-ai-chatbot/tasks.md
  - specs/001-ai-chatbot/research.md
  - specs/001-ai-chatbot/contracts/mcp-tools.md
tests:
  - None (documentation correction - no tests executed)
---

## Prompt

option 1

## Response snapshot

Executed Option 1 to correct planning documents using official SDK patterns:

1. **Verified official documentation** via Context7 MCP server for:
   - OpenAI Agents Python SDK (`/openai/openai-agents-python`)
   - OpenAI ChatKit JS (`/websites/openai_github_io_chatkit-js`)
   - MCP Python SDK (`/modelcontextprotocol/python-sdk`)

2. **Identified critical architectural issue**: Planning documents (research.md, contracts/mcp-tools.md) used non-existent MCP SDK API patterns (`from mcp import Tool, MCPServer`) that don't exist in official MCP Python SDK.

3. **Corrected architecture** to use OpenAI Agents SDK native `@function_tool` decorator pattern:
   - Removed dependency on separate MCP server (unnecessary complexity)
   - Updated all tool definitions to use `@function_tool` decorator
   - Changed file structure from `backend/mcp/` to `backend/services/agent_tools.py`
   - Reduced task count from 115 to 100 by eliminating redundant "schema + handler + tool definition + server registration" pattern

4. **Updated planning artifacts**:
   - **tasks.md**: Consolidated tool implementation tasks, renumbered T001-T100, updated terminology from "MCP tools" to "agent function tools"
   - **research.md**: Rewrote section 2 with correct OpenAI Agents SDK @function_tool pattern
   - **contracts/mcp-tools.md**: Updated title, overview, and all code examples to reflect @function_tool architecture

5. **Preserved correctness**: ChatKit integration (T003, T072-T080) already correct per official documentation.

## Outcome

- ✅ Impact: Corrected architectural mismatch between planning documents and official SDK APIs. Prevented implementation failure from attempting to use non-existent `from mcp import Tool, MCPServer` imports. Simplified architecture by removing unnecessary MCP server layer. Reduced task count by 15 tasks (115→100).
- 🧪 Tests: None (planning document correction - no code implementation or test execution)
- 📁 Files: Updated 3 planning documents (tasks.md, research.md, contracts/mcp-tools.md)
- 🔁 Next prompts: Begin implementation with corrected architecture starting from Phase 1 (Setup). Use `/sp.implement` or manual execution of tasks.md following TDD discipline.
- 🧠 Reflection: Verifying official documentation before implementation prevents costly refactoring. The initial planning assumed an MCP SDK API that mirrors OpenAI's tool calling format, but the official MCP SDK is for building standalone protocol servers, not for integrating tools directly with OpenAI Agents. The @function_tool decorator is the correct, simpler approach for this architecture.

## Evaluation notes (flywheel)

- Failure modes observed: Initial planning phase did not verify official SDK APIs before designing architecture. Planning documents used assumed API patterns (`from mcp import Tool`) without consulting official documentation.
- Graders run and results (PASS/FAIL): PASS - All 3 planning documents corrected to match official OpenAI Agents SDK patterns. Task count validated (100 tasks, proper renumbering).
- Prompt variant (if applicable): Standard documentation verification workflow using Context7 MCP server to fetch official library documentation.
- Next experiment (smallest change to try): Add "verify official documentation" as explicit checkpoint in `/sp.plan` workflow before generating tasks.md to catch API mismatches during planning rather than during implementation.
