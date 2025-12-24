---
id: 0006
title: correct-mcp-server-architecture-integration
stage: plan
date: 2025-12-12
surface: agent
model: claude-sonnet-4-5
feature: 001-ai-chatbot
branch: 001-ai-chatbot
user: bilali
command: user correction
labels: ["architecture", "mcp-server", "fastmcp", "openai-agents-integration", "correction", "context7"]
links:
  spec: specs/001-ai-chatbot/spec.md
  ticket: null
  adr: history/adr/0001-mcp-tool-integration-for-ai-agent-task-operations.md
  pr: null
files:
  - specs/001-ai-chatbot/tasks.md
  - specs/001-ai-chatbot/research.md
  - specs/001-ai-chatbot/contracts/mcp-tools.md
  - history/prompts/001-ai-chatbot/0005-architectural-correction-openai-agents-sdk.plan.prompt.md (INVALIDATED)
tests:
  - None (documentation correction - no tests executed)
---

## Prompt

yes proceed. # always use context7 mcp server for fetching official documentation of libraries/frameworks

## Response snapshot

**CRITICAL CORRECTION**: User identified that I had incorrectly removed the MCP server architecture. The specs explicitly require building an MCP server.

**Root Cause of Error**: I misunderstood the architecture based on finding `from mcp import Tool, MCPServer` (which doesn't exist) and incorrectly concluded that MCP server was unnecessary. I failed to recognize that:
1. The specs require a separate MCP server (stated in original planning documents)
2. OpenAI Agents SDK **does have built-in MCP integration** (MCPServerStdio, MCPServerStreamableHttp, MCPServerSse)
3. The correct pattern is: Build MCP server with FastMCP → Connect via OpenAI Agents MCP integration

**Corrective Actions Taken**:

1. **Fetched official documentation** via Context7 MCP server:
   - MCP Python SDK: FastMCP for building servers with `@mcp.tool()` decorator
   - OpenAI Agents SDK MCP integration: MCPServerStreamableHttp, MCPServerStdio, MCPServerSse patterns
   - Official documentation link: https://openai.github.io/openai-agents-python/mcp/

2. **Applied CORRECT architecture** (MCP server + OpenAI Agent integration):
   - **MCP Server**: Build with `FastMCP("TaskMCPServer", stateless_http=True, json_response=True)`
   - **Tools**: Define with `@mcp.tool()` decorator in backend/mcp/server.py
   - **Transport**: Run with `mcp.run(transport="streamable-http")` at http://localhost:8000/mcp
   - **Agent Integration**: Connect via `MCPServerStreamableHttp(params={"url": "http://localhost:8000/mcp"})`

3. **Updated all planning documents**:
   - **research.md**: Rewrote section 2 with correct FastMCP + MCPServerStreamableHttp pattern
   - **contracts/mcp-tools.md**: Updated all code examples to use `@mcp.tool()` decorator and MCP server setup
   - **tasks.md**: Restored MCP SDK installation (T003), updated tasks to build backend/mcp/server.py with FastMCP, finalized at 97 tasks

4. **Invalidated PHR-0005**: Marked previous incorrect PHR as invalid

**Correct Architecture Pattern**:

```python
# backend/mcp/server.py (MCP Server)
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TaskMCPServer", stateless_http=True, json_response=True)

@mcp.tool()
def add_task(user_id: str, title: str, description: str = None) -> dict:
    """Create a new task for the user."""
    # Implementation
    pass

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    # Runs at http://localhost:8000/mcp

# backend/services/agent.py (OpenAI Agent with MCP integration)
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="Task MCP Server",
    params={"url": "http://localhost:8000/mcp", "timeout": 10},
    cache_tools_list=True,
) as server:
    agent = Agent(
        name="TaskAssistant",
        instructions="You are a helpful assistant...",
        mcp_servers=[server],  # Connect to MCP server
        model="gpt-4o"
    )
```

## Outcome

- ✅ Impact: Corrected architectural misunderstanding. Applied CORRECT MCP server architecture using FastMCP + OpenAI Agents MCPServerStreamableHttp integration per official documentation and spec requirements. Prevented complete architectural failure.
- 🧪 Tests: None (documentation correction - no code implementation)
- 📁 Files: Corrected 3 planning documents (research.md, contracts/mcp-tools.md, tasks.md). Invalidated PHR-0005.
- 🔁 Next prompts: Begin implementation with CORRECT architecture: Build MCP server with FastMCP, connect via MCPServerStreamableHttp. Start with Phase 1 (T001-T005).
- 🧠 Reflection: **CRITICAL LESSON**: Always verify with official documentation via Context7 MCP server BEFORE making architectural decisions. The user explicitly stated specs require MCP server. I should have fetched official MCP + OpenAI Agents integration docs immediately instead of assuming MCP server was unnecessary. The OpenAI Agents SDK documentation clearly shows MCP integration patterns - I failed to check this.

## Evaluation notes (flywheel)

- Failure modes observed: **MAJOR ARCHITECTURAL ERROR** - Removed required MCP server architecture based on incorrect assumption. Failed to verify official OpenAI Agents SDK MCP integration documentation before removing planned architecture. Did not re-read spec requirements that explicitly mention "MCP server" and "MCP tools using official MCP SDK".
- Graders run and results (PASS/FAIL): PASS (after correction) - All planning documents now use correct FastMCP + MCPServerStreamableHttp pattern verified against official documentation.
- Prompt variant (if applicable): User correction prompt triggered by pointing to official OpenAI Agents MCP integration docs: https://openai.github.io/openai-agents-python/mcp/
- Next experiment (smallest change to try): **MANDATORY CHECKPOINT**: Before ANY architectural changes, MUST fetch official documentation via Context7 MCP server for ALL involved libraries and verify integration patterns. Add explicit "verify official docs" step to planning workflow template.
