"""
AI Agent Service

This module provides the AI agent service that connects to the MCP server
and processes user messages. It uses the OpenAI Agents SDK with MCP integration.

Architecture:
- Connects to MCP server via MCPServerStreamableHttp (separate mode)
- Uses direct function tools (mounted mode)
- Uses OpenAI GPT-4o model for natural language understanding
- Stateless design: loads conversation history from database
- Returns structured responses with tool calls
"""

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings
from config import settings
from typing import List, Dict, Any
import logging
import os

# Set OpenAI API key in environment for agents SDK (if provided)
if settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Global MCP server instance (singleton pattern for connection reuse)
_mcp_server = None
_mcp_server_lock = None


async def get_mcp_server():
    """
    Get or create the global MCP server instance.
    Uses singleton pattern to reuse connection across requests.

    Returns:
        MCPServerStreamableHttp: Shared MCP server instance
    """
    global _mcp_server, _mcp_server_lock

    # Initialize lock on first call
    if _mcp_server_lock is None:
        import asyncio
        _mcp_server_lock = asyncio.Lock()

    async with _mcp_server_lock:
        if _mcp_server is None:
            mcp_url = settings.mcp_server_url
            logger.info(f"🔌 Initializing MCP server connection (first time) to: {mcp_url}")
            _mcp_server = MCPServerStreamableHttp(
                name="Task MCP Server",
                params={
                    "url": mcp_url,
                    "timeout": settings.OPENAI_API_TIMEOUT,
                },
                cache_tools_list=True,
                max_retry_attempts=3,
            )
            logger.info("🔌 MCP server instance created")
        return _mcp_server


async def create_task_agent(user_id: str):
    """
    Create an AI agent connected to the Task MCP Server.

    Args:
        user_id: User ID for contextualizing agent responses

    Returns:
        Tuple of (agent, server) for use in async context manager
    """
    # Get shared MCP server connection (singleton)
    server = await get_mcp_server()

    # Create agent with MCP tools (new agent per request for user_id isolation)
    agent = Agent(
        name="TaskAssistant",
        instructions=f"""You are a helpful assistant that manages todo tasks for users.

You have access to tools to create, list, update, complete, and delete tasks.

Current user ID: {user_id}

IMPORTANT - Task ID Handling:
- Task IDs are UUIDs (e.g., "123e4567-e89b-12d3-a456-426614174000")
- Users will refer to tasks by TITLE (e.g., "Buy groceries"), NOT by ID
- When updating, completing, or deleting a task:
  1. FIRST call list_tasks_tool to get all tasks
  2. Find the task that matches the user's description (by title)
  3. Extract the task_id (UUID) from that task
  4. THEN call update_task_tool/complete_task_tool/delete_task_tool with that task_id

Guidelines:
- Always use the provided user_id when calling tools
- Be concise and friendly in your responses
- When creating tasks, extract the task title from user input
- When listing tasks, format them in a clear, readable way
- Confirm actions after completing them (e.g., "I've marked 'Buy groceries' as complete")
- If multiple tasks match the user's description, ask which one they mean
- If no tasks match, tell the user the task wasn't found
""",
        mcp_servers=[server],
        model=settings.OPENAI_MODEL,  # gpt-4o
    )

    return agent, server


async def process_message(
    user_id: str,
    message: str,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Process a user message using the AI agent.

    Args:
        user_id: User ID from JWT token
        message: User's message text
        conversation_history: Previous messages in conversation (optional)

    Returns:
        Dict with:
            - response: AI assistant's text response
            - tool_calls: List of tool calls made (for logging)
            - model: Model used
            - tokens_used: Approximate token count
    """
    try:
        import time

        # Create agent with MCP connection
        start_total = time.time()
        start_agent = time.time()
        agent, server = await create_task_agent(user_id)
        agent_creation_time = time.time() - start_agent
        logger.info(f"⏱️  Agent creation took {agent_creation_time:.2f}s")

        async with server:
            # Prepare messages for agent
            start_prep = time.time()
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})
            prep_time = time.time() - start_prep
            logger.info(f"⏱️  Message preparation took {prep_time:.3f}s")

            # Run agent
            logger.info(f"🤖 Processing message for user {user_id}: {message[:100]}...")
            start_run = time.time()
            result = await Runner.run(agent, messages)
            run_time = time.time() - start_run
            logger.info(f"⏱️  Agent run took {run_time:.2f}s")

            # Extract tool calls from result
            start_extract = time.time()
            tool_calls = []
            if hasattr(result, 'tool_calls') and result.tool_calls:
                for tool_call in result.tool_calls:
                    tool_calls.append({
                        "tool": tool_call.name,
                        "parameters": tool_call.arguments,
                        "result": tool_call.result if hasattr(tool_call, 'result') else None
                    })
                logger.info(f"🔧 Tools called: {[tc['tool'] for tc in tool_calls]}")
            extract_time = time.time() - start_extract

            total_time = time.time() - start_total
            logger.info(f"⏱️  TOTAL process_message took {total_time:.2f}s (agent: {agent_creation_time:.2f}s, run: {run_time:.2f}s, extract: {extract_time:.3f}s)")

            # Return structured response
            return {
                "response": result.final_output if hasattr(result, 'final_output') else str(result),
                "tool_calls": tool_calls,
                "model": settings.OPENAI_MODEL,
                "tokens_used": 0,  # TODO: Extract from result if available
            }

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return {
            "response": "I'm sorry, I encountered an error processing your request. Please try again.",
            "tool_calls": [],
            "model": settings.OPENAI_MODEL,
            "tokens_used": 0,
            "error": str(e)
        }


async def process_message_streaming(
    user_id: str,
    message: str,
    conversation_history: List[Dict[str, str]] = None
):
    """
    Process a user message with streaming support (for future use).

    Args:
        user_id: User ID from JWT token
        message: User's message text
        conversation_history: Previous messages in conversation (optional)

    Yields:
        Stream events from the agent
    """
    try:
        agent, server = await create_task_agent(user_id)

        async with server:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Run agent with streaming
            result = Runner.run_streamed(agent, messages)
            async for event in result.stream_events():
                yield event

    except Exception as e:
        logger.error(f"Error in streaming: {str(e)}", exc_info=True)
        yield {"type": "error", "error": str(e)}
