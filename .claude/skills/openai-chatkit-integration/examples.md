---
name: openai-chatkit-integration-examples
description: Complete working examples for ChatKit custom backend integration, including Store implementation, ChatKitServer, endpoints, frontend setup, and testing.
---

# OpenAI ChatKit Integration - Complete Examples

## Example 1: Complete SimpleMemoryStore Implementation

Full in-memory store implementation for development.

```python
"""
backend/services/chatkit_server.py

SimpleMemoryStore - In-memory ChatKit storage for development.
Replace with PostgresStore for production.
"""

from typing import Literal
from uuid import uuid4
from chatkit.server import (
    Store,
    ThreadMetadata,
    ThreadItem,
    Page,
    Attachment,
)


class SimpleMemoryStore(Store[dict]):
    """
    In-memory store for ChatKit threads, items, and attachments.

    WARNING: Data is lost on server restart. Use only for development.
    For production, use PostgresStore from chatkit.stores.
    """

    def __init__(self):
        # Storage dictionaries
        self.threads: dict[str, ThreadMetadata] = {}
        self.items: dict[str, dict[str, ThreadItem]] = {}  # thread_id -> {item_id -> item}
        self.attachments: dict[str, Attachment] = {}

    # ==================== ID Generation ====================

    def generate_thread_id(self, context: dict) -> str:
        """Generate unique thread ID."""
        return str(uuid4())

    def generate_item_id(
        self,
        item_type: Literal["message", "tool_call", "task", "workflow", "attachment"],
        thread: ThreadMetadata,
        context: dict,
    ) -> str:
        """Generate unique item ID."""
        return str(uuid4())

    # ==================== Thread Operations ====================

    async def load_thread(self, thread_id: str, context: dict) -> ThreadMetadata:
        """Load thread metadata by ID."""
        if thread_id not in self.threads:
            raise ValueError(f"Thread {thread_id} not found")
        return self.threads[thread_id]

    async def save_thread(self, thread: ThreadMetadata, context: dict) -> None:
        """Save or update thread metadata."""
        self.threads[thread.id] = thread
        if thread.id not in self.items:
            self.items[thread.id] = {}

    async def delete_thread(self, thread_id: str, context: dict) -> None:
        """Delete thread and all its items."""
        if thread_id in self.threads:
            del self.threads[thread_id]
        if thread_id in self.items:
            del self.items[thread_id]

    async def load_threads(
        self, limit: int, after: str | None, order: str, context: dict
    ) -> Page[ThreadMetadata]:
        """List threads with pagination."""
        thread_list = list(self.threads.values())
        # Simple pagination (production should use proper cursor-based pagination)
        return Page(data=thread_list[:limit], has_more=len(thread_list) > limit)

    # ==================== Item Operations ====================

    async def load_thread_items(
        self, thread_id: str, after: str | None, limit: int, order: str, context: dict
    ) -> Page[ThreadItem]:
        """List items in a thread with pagination."""
        if thread_id not in self.items:
            return Page(data=[], has_more=False)

        items = list(self.items[thread_id].values())
        return Page(data=items[:limit], has_more=len(items) > limit)

    async def load_item(self, thread_id: str, item_id: str, context: dict) -> ThreadItem:
        """Load a specific thread item."""
        if thread_id not in self.items or item_id not in self.items[thread_id]:
            raise ValueError(f"Item {item_id} not found in thread {thread_id}")
        return self.items[thread_id][item_id]

    async def save_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        """Save or update a thread item."""
        if thread_id not in self.items:
            self.items[thread_id] = {}
        self.items[thread_id][item.id] = item

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        """Add new item to thread."""
        await self.save_item(thread_id, item, context)

    async def delete_thread_item(self, thread_id: str, item_id: str, context: dict) -> None:
        """Delete a specific thread item."""
        if thread_id in self.items and item_id in self.items[thread_id]:
            del self.items[thread_id][item_id]

    # ==================== Attachment Operations ====================

    async def load_attachment(self, attachment_id: str, context: dict) -> Attachment:
        """Load attachment metadata."""
        if attachment_id not in self.attachments:
            raise ValueError(f"Attachment {attachment_id} not found")
        return self.attachments[attachment_id]

    async def save_attachment(self, attachment: Attachment, context: dict) -> None:
        """Save attachment metadata."""
        self.attachments[attachment.id] = attachment

    async def delete_attachment(self, attachment_id: str, context: dict) -> None:
        """Delete attachment."""
        if attachment_id in self.attachments:
            del self.attachments[attachment_id]
```

## Example 2: Complete ChatKitServer Implementation

Full ChatKit server with MCP tools integration.

```python
"""
backend/services/chatkit_server.py (continued)

TaskManagerChatKitServer - Custom ChatKit server with MCP tool integration.
"""

from typing import AsyncIterator
import logging
from chatkit.server import (
    ChatKitServer,
    ThreadMetadata,
    UserMessageItem,
    AssistantMessageItem,
    ThreadStreamEvent,
    ThreadItemDoneEvent,
)
from chatkit.agents import (
    stream_agent_response,
    simple_to_agent_input,
    AgentContext,
)
from agents import Runner

logger = logging.getLogger(__name__)


class TaskManagerChatKitServer(ChatKitServer[dict]):
    """
    Custom ChatKit server integrating with MCP tools and PostgreSQL.

    This server:
    1. Receives user messages from ChatKit UI
    2. Creates an AI agent with MCP tools for database operations
    3. Streams agent responses back to ChatKit UI
    4. Handles errors gracefully
    """

    def __init__(self, data_store: Store):
        super().__init__(data_store)

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """
        Process user messages and stream AI responses.

        Args:
            thread: Current conversation thread
            input: User's message (None for new threads)
            context: Request context with user_id

        Yields:
            ThreadStreamEvent: Events for ChatKit UI to render
        """
        if input is None:
            return

        # Get user_id from context (passed from endpoint)
        user_id = context.get("user_id")
        if not user_id:
            logger.error("No user_id in context")
            yield self._error_event(thread, context, "Authentication required")
            return

        logger.info(f"Processing message for user {user_id} in thread {thread.id}")

        # Import your existing agent creation function
        from services.agent import create_task_agent

        # Create ChatKit agent context
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        # Convert ChatKit input to Agent SDK format
        agent_input = await simple_to_agent_input(input)
        if not agent_input:
            logger.warning("Failed to convert ChatKit input to agent format")
            return

        try:
            # Create agent with MCP tools (connects to PostgreSQL)
            agent, mcp_server = await create_task_agent(user_id)

            async with mcp_server:
                # Run agent with streaming
                result = Runner.run_streamed(agent, input=agent_input)

                # Stream agent response as ChatKit events
                async for event in stream_agent_response(agent_context, result):
                    yield event

                logger.info(f"Successfully processed message for user {user_id}")

        except PermissionError as e:
            logger.error(f"Permission error for user {user_id}: {e}")
            yield self._error_event(thread, context, "You don't have permission to perform this action.")

        except Exception as e:
            logger.error(f"Error in respond for user {user_id}: {str(e)}", exc_info=True)
            yield self._error_event(thread, context, f"Sorry, I encountered an error: {str(e)}")

    def _error_event(self, thread: ThreadMetadata, context: dict, message: str) -> ThreadItemDoneEvent:
        """Create error event to display to user."""
        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{"type": "text", "text": message}],
        )
        return ThreadItemDoneEvent(item=error_item)
```

## Example 3: Complete ChatKit Endpoint

Full FastAPI endpoint implementation with authentication.

```python
"""
backend/routes/chatkit.py

ChatKit protocol endpoint with JWT authentication.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
import logging
from chatkit.server import StreamingResult, NonStreamingResult
from services.chatkit_server import TaskManagerChatKitServer, SimpleMemoryStore
from middleware import verify_token  # Your JWT validation function

logger = logging.getLogger(__name__)

# Create router
chatkit_router = APIRouter(tags=["chatkit"])

# Initialize ChatKit server (singleton)
data_store = SimpleMemoryStore()
chatkit_server = TaskManagerChatKitServer(data_store)


@chatkit_router.post("/chatkit")
async def chatkit_endpoint(request: Request):
    """
    Main ChatKit protocol endpoint.

    Receives all ChatKit requests (thread creation, messages, etc.)
    and routes them through the ChatKitServer.

    Authentication:
    - Expects JWT in Authorization header
    - Validates JWT and extracts user_id
    - Passes user_id as context to ChatKitServer
    """
    try:
        # Validate JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing Authorization header")
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate using JWKS/JWT (your existing auth system)
        user_id = verify_token(token)

        if not user_id:
            logger.warning("Invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")

        logger.info(f"ChatKit request from user {user_id}")

        # Create context with user_id for authorization
        context = {"user_id": user_id}

        # Get request body
        body = await request.body()

        # Process through ChatKit server
        result = await chatkit_server.process(body, context)

        # Return streaming or JSON response
        if isinstance(result, StreamingResult):
            return StreamingResponse(
                result,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )
        elif isinstance(result, NonStreamingResult):
            return Response(content=result.json, media_type="application/json")
        else:
            # Fallback for other result types
            return Response(content=str(result), media_type="application/json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ChatKit endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## Example 4: Complete Frontend Implementation

Full Next.js page with ChatKit integration.

```tsx
/**
 * app/(dashboard)/chat/page.tsx
 *
 * Chat Page - AI-Powered Conversational Interface with OpenAI ChatKit
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/auth-client';
import { ChatKit, useChatKit } from '@openai/chatkit-react';
import { authClient } from '@/lib/auth-client';

export default function ChatPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Redirect to signin if not authenticated
  useEffect(() => {
    if (!isPending && !session?.user) {
      router.push('/signin');
    }
  }, [session, isPending, router]);

  // ChatKit configuration for custom backend
  const { control } = useChatKit({
    api: {
      // Custom backend URL - ChatKit will POST requests here
      url: `${apiUrl}/chatkit`,

      // Domain key - required for production, skipped on localhost
      domainKey: process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY || 'localhost-dev',

      // Custom fetch to inject our auth headers
      async fetch(input: RequestInfo | URL, init?: RequestInit) {
        console.log('🔵 ChatKit: Custom fetch called', { url: input });

        // Get Better Auth JWT for authenticating with our backend
        const { data, error: authError } = await authClient.token();
        if (authError || !data?.token) {
          console.error('ChatKit: Auth error', authError);
          throw new Error('Not authenticated - please sign in');
        }

        // Inject auth header
        const headers = {
          ...init?.headers,
          'Authorization': `Bearer ${data.token}`,
        };

        console.log('ChatKit: Fetching with auth header');
        return fetch(input, {
          ...init,
          headers,
        });
      },
    },
    initialThread: null,  // Start with new thread view
    theme: {
      colorScheme: 'light',
      color: {
        accent: {
          primary: '#2563eb', // blue-600
          level: 2,
        },
      },
      radius: 'round',
      density: 'normal',
      typography: { fontFamily: 'system-ui, -apple-system, sans-serif' },
    },
    composer: {
      placeholder: 'Ask me to create tasks, list tasks, or help you manage your todo list...',
    },
    startScreen: {
      greeting: 'Welcome to AI Assistant',
      prompts: [
        {
          label: 'Create a task',
          prompt: 'Create a new task for me',
          icon: 'notebook-pencil',
        },
        {
          label: 'List tasks',
          prompt: 'Show me all my tasks',
          icon: 'search',
        },
        {
          label: 'Get help',
          prompt: 'Help me organize my tasks',
          icon: 'lightbulb',
        },
      ],
    },
    onError: ({ error: err }) => {
      console.error('ChatKit error:', err);
      setError(err?.message || 'An error occurred');
    },
    onThreadChange: ({ threadId }) => {
      console.log('ChatKit: Thread changed', { threadId });
    },
  });

  // Show loading state while checking authentication
  if (isPending) {
    return (
      <div className="flex flex-col h-screen bg-white items-center justify-center">
        <div className="text-center">
          <div className="inline-block">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
          <p className="text-gray-600 mt-4">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render ChatKit if not authenticated (will redirect)
  if (!session?.user) {
    return null;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Error Display */}
      {error && (
        <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex-shrink-0">
          <p className="text-red-800 text-sm">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 text-xs mt-2 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ChatKit Component - Full height, ChatKit provides its own greeting */}
      <ChatKit
        control={control}
        className="flex-1 w-full"
        style={{ minHeight: '400px' }}
      />
    </div>
  );
}
```

## Example 5: Testing Examples

### Backend Unit Tests

```python
"""
backend/tests/test_chatkit.py

Unit tests for ChatKit server integration.
"""

import pytest
from services.chatkit_server import TaskManagerChatKitServer, SimpleMemoryStore
from chatkit.server import ThreadMetadata, UserMessageItem


@pytest.mark.asyncio
async def test_simple_memory_store():
    """Test SimpleMemoryStore basic operations."""
    store = SimpleMemoryStore()

    # Create thread
    thread_id = store.generate_thread_id({})
    thread = ThreadMetadata(id=thread_id, title="Test Thread")

    # Save thread
    await store.save_thread(thread, {})

    # Load thread
    loaded = await store.load_thread(thread_id, {})
    assert loaded.id == thread_id
    assert loaded.title == "Test Thread"

    # Delete thread
    await store.delete_thread(thread_id, {})

    # Verify deletion
    with pytest.raises(ValueError):
        await store.load_thread(thread_id, {})


@pytest.mark.asyncio
async def test_chatkit_server_respond():
    """Test ChatKitServer respond method."""
    store = SimpleMemoryStore()
    server = TaskManagerChatKitServer(store)

    # Create thread
    thread = ThreadMetadata(id="test-thread", title="Test")
    await store.save_thread(thread, {})

    # Create user message
    input_item = UserMessageItem(
        id="msg-1",
        thread_id="test-thread",
        content=[{"type": "text", "text": "Add a task to buy groceries"}],
    )

    context = {"user_id": "test-user"}

    # Collect events
    events = []
    async for event in server.respond(thread, input_item, context):
        events.append(event)

    # Verify we got response events
    assert len(events) > 0
    assert any("task" in str(event).lower() for event in events)
```

### Frontend Integration Tests

```tsx
/**
 * frontend/tests/chat.test.tsx
 *
 * Integration tests for ChatKit component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPage from '@/app/(dashboard)/chat/page';

// Mock ChatKit
jest.mock('@openai/chatkit-react', () => ({
  ChatKit: ({ control }: any) => (
    <div data-testid="chatkit-component">ChatKit Mock</div>
  ),
  useChatKit: () => ({ control: {} }),
}));

// Mock auth
jest.mock('@/lib/auth-client', () => ({
  useSession: () => ({
    data: { user: { id: 'test-user', email: 'test@example.com' } },
    isPending: false,
  }),
  authClient: {
    token: async () => ({ data: { token: 'mock-jwt-token' }, error: null }),
  },
}));

describe('ChatPage', () => {
  it('renders ChatKit component when authenticated', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('chatkit-component')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    // Override mock to show loading
    jest.spyOn(require('@/lib/auth-client'), 'useSession').mockReturnValue({
      data: null,
      isPending: true,
    });

    render(<ChatPage />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays error message when ChatKit errors', async () => {
    const { rerender } = render(<ChatPage />);

    // Simulate error
    const errorEvent = new CustomEvent('chatkit-error', {
      detail: { message: 'Test error' },
    });
    window.dispatchEvent(errorEvent);

    await waitFor(() => {
      expect(screen.getByText(/Test error/i)).toBeInTheDocument();
    });
  });
});
```

## Example 6: Production Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myuser"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://myuser:${DB_PASSWORD}@postgres:5432/myapp
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      MCP_SERVER_URL: http://mcp-server:8001/mcp
      BETTER_AUTH_SECRET: ${BETTER_AUTH_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      mcp-server:
        condition: service_started
    restart: unless-stopped

  mcp-server:
    build:
      context: ./backend
      dockerfile: Dockerfile.mcp
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql://myuser:${DB_PASSWORD}@postgres:5432/myapp
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
      NEXT_PUBLIC_CHATKIT_DOMAIN_KEY: ${CHATKIT_DOMAIN_KEY}
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

### Environment Variables

```bash
# .env.production

# Database
DB_PASSWORD=secure_password_here

# OpenAI
OPENAI_API_KEY=sk-proj-xxx

# Auth
BETTER_AUTH_SECRET=your_secret_here

# ChatKit
CHATKIT_DOMAIN_KEY=dk_xxx  # Get from OpenAI dashboard
```

### Running in Production

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```
