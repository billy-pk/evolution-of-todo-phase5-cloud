"""
ChatKit Server Implementation

This module implements a custom ChatKit server that integrates with our existing
PostgreSQL database and OpenAI Agents SDK.
"""

import json
import logging
from typing import Any, AsyncIterator, Optional, Literal
from datetime import datetime, UTC
from uuid import uuid4

from chatkit.server import (
    ChatKitServer,
    ThreadStreamEvent,
    ThreadMetadata,
    ThreadItem,
    Page,
    UserMessageItem,
    AssistantMessageItem,
    Store,
    StoreItemType,
)
from chatkit.agents import (
    stream_agent_response,
    simple_to_agent_input,
    AgentContext,
    Attachment,
)
from agents import Runner
from sqlmodel import Session, select

from db import engine
from models import Conversation, Message
from config import settings

logger = logging.getLogger(__name__)


class SimpleMemoryStore(Store[dict]):
    """
    Simple in-memory store implementation for ChatKit.

    This is a minimal implementation to get ChatKit working.
    We'll integrate with PostgreSQL properly later.
    """

    def __init__(self):
        self.threads: dict[str, ThreadMetadata] = {}
        self.items: dict[str, dict[str, ThreadItem]] = {}  # thread_id -> {item_id -> item}
        self.attachments: dict[str, Attachment] = {}

    def generate_thread_id(self, context: dict) -> str:
        """Generate a unique thread ID."""
        return str(uuid4())

    def generate_item_id(
        self,
        item_type: Literal["message", "tool_call", "task", "workflow", "attachment"],
        thread: ThreadMetadata,
        context: dict,
    ) -> str:
        """Generate a unique item ID."""
        return str(uuid4())

    async def load_thread(self, thread_id: str, context: dict) -> ThreadMetadata:
        """Load a thread by ID."""
        if thread_id not in self.threads:
            raise ValueError(f"Thread {thread_id} not found")
        return self.threads[thread_id]

    async def load_threads(
        self, limit: int, after: str | None, order: str, context: dict
    ) -> Page[ThreadMetadata]:
        """Load multiple threads."""
        thread_list = list(self.threads.values())
        return Page(data=thread_list[:limit], has_more=False)

    async def save_thread(self, thread: ThreadMetadata, context: dict) -> None:
        """Save a thread."""
        self.threads[thread.id] = thread
        if thread.id not in self.items:
            self.items[thread.id] = {}

    async def delete_thread(self, thread_id: str, context: dict) -> None:
        """Delete a thread."""
        if thread_id in self.threads:
            del self.threads[thread_id]
        if thread_id in self.items:
            del self.items[thread_id]

    async def load_thread_items(
        self, thread_id: str, after: str | None, limit: int, order: str, context: dict
    ) -> Page[ThreadItem]:
        """Load items for a thread."""
        if thread_id not in self.items:
            return Page(data=[], has_more=False)

        items = list(self.items[thread_id].values())
        return Page(data=items[:limit], has_more=False)

    async def load_item(self, thread_id: str, item_id: str, context: dict) -> ThreadItem:
        """Load a specific item."""
        if thread_id not in self.items or item_id not in self.items[thread_id]:
            raise ValueError(f"Item {item_id} not found in thread {thread_id}")
        return self.items[thread_id][item_id]

    async def save_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        """Save an item."""
        if thread_id not in self.items:
            self.items[thread_id] = {}
        self.items[thread_id][item.id] = item

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        """Add an item to a thread."""
        await self.save_item(thread_id, item, context)

    async def delete_thread_item(self, thread_id: str, item_id: str, context: dict) -> None:
        """Delete an item from a thread."""
        if thread_id in self.items and item_id in self.items[thread_id]:
            del self.items[thread_id][item_id]

    async def load_attachment(self, attachment_id: str, context: dict) -> Attachment:
        """Load attachment data."""
        if attachment_id not in self.attachments:
            raise ValueError(f"Attachment {attachment_id} not found")
        return self.attachments[attachment_id]

    async def save_attachment(self, attachment: Attachment, context: dict) -> None:
        """Save attachment data."""
        self.attachments[attachment.id] = attachment

    async def delete_attachment(self, attachment_id: str, context: dict) -> None:
        """Delete an attachment."""
        if attachment_id in self.attachments:
            del self.attachments[attachment_id]


class TaskManagerChatKitServer(ChatKitServer[dict]):
    """
    Custom ChatKit server for task management.

    Integrates with our existing database and MCP tools for real task management.
    """

    def __init__(self, data_store: Store):
        super().__init__(data_store)
        self.db_engine = engine

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Handle incoming messages and stream responses.

        This is called whenever a user sends a message.
        Uses the existing MCP-connected agent for real task management.
        """
        from chatkit.server import ThreadItemDoneEvent

        logger.info(f"TaskManagerChatKitServer.respond called for thread {thread.id}")

        if input is None:
            logger.warning("No input provided to respond")
            error_item = AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                content=[{"type": "output_text", "text": "No message provided. Please send a message."}],
                created_at=datetime.now(UTC),
            )
            yield ThreadItemDoneEvent(item=error_item)
            return

        # Get user_id from context
        user_id = context.get("user_id")
        if not user_id:
            logger.error("No user_id in context")
            error_item = AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                content=[{"type": "output_text", "text": "Authentication error. Please sign in again."}],
                created_at=datetime.now(UTC),
            )
            yield ThreadItemDoneEvent(item=error_item)
            return

        # Import the existing agent creation function
        from services.agent import create_task_agent

        # Create agent context for ChatKit
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        # Convert ChatKit input to Agent SDK format
        agent_input = await simple_to_agent_input(input)

        if not agent_input:
            logger.warning("Failed to convert input to agent format")
            error_item = AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                content=[{"type": "output_text", "text": "Could not process your message. Please try again."}],
                created_at=datetime.now(UTC),
            )
            yield ThreadItemDoneEvent(item=error_item)
            return

        logger.info(f"Running MCP agent for user {user_id} with input: {agent_input}")

        try:
            # Create agent with MCP tools (connects to real PostgreSQL via MCP server)
            logger.info("Creating task agent...")
            agent, mcp_server = await create_task_agent(user_id)
            logger.info(f"Agent created successfully. MCP server: {mcp_server}")

            logger.info("Entering MCP server context...")
            async with mcp_server:
                logger.info("MCP server context entered successfully")

                # Run the agent with streaming
                logger.info("Starting Runner.run_streamed...")
                result = Runner.run_streamed(
                    agent,
                    input=agent_input,
                )
                logger.info(f"Runner.run_streamed returned: {type(result)}")

                # Stream the agent response as ChatKit events
                logger.info("Starting to stream agent response...")
                event_count = 0
                async for event in stream_agent_response(agent_context, result):
                    event_count += 1
                    logger.info(f"Yielding event #{event_count}: {type(event)}")
                    yield event

                logger.info(f"Finished streaming {event_count} events")

        except Exception as e:
            logger.error(f"Error in respond: {str(e)}", exc_info=True)
            # Yield an error message to the user
            error_item = AssistantMessageItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                content=[{"type": "output_text", "text": f"Sorry, I encountered an error: {str(e)}"}],
                created_at=datetime.now(UTC),
            )
            yield ThreadItemDoneEvent(item=error_item)
