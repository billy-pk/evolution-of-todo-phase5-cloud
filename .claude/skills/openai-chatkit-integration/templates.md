---
name: openai-chatkit-integration-templates
description: Ready-to-use code templates for ChatKit integration, including frontend configuration, backend server setup, Store implementation, and deployment configs.
---

# OpenAI ChatKit Integration - Code Templates

## Template 1: Frontend ChatKit Configuration

Basic ChatKit React configuration template.

```tsx
'use client';

import { ChatKit, useChatKit } from '@openai/chatkit-react';
import { [YOUR_AUTH_CLIENT] } from '@/lib/auth-client';

export default function ChatPage() {
  const { data: session } = useSession();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const { control } = useChatKit({
    api: {
      url: `${apiUrl}/chatkit`,
      domainKey: process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY || 'localhost-dev',

      async fetch(input: RequestInfo | URL, init?: RequestInit) {
        // Get your auth token
        const token = await [YOUR_GET_TOKEN_FUNCTION]();
        if (!token) {
          throw new Error('Not authenticated');
        }

        return fetch(input, {
          ...init,
          headers: {
            ...init?.headers,
            'Authorization': `Bearer ${token}`,
          },
        });
      },
    },
    theme: {
      colorScheme: 'light',
      color: { accent: { primary: '#2563eb', level: 2 } },
    },
    startScreen: {
      greeting: 'Welcome to [YOUR_APP]',
      prompts: [
        { label: 'Example 1', prompt: 'Example prompt 1', icon: 'notebook-pencil' },
        { label: 'Example 2', prompt: 'Example prompt 2', icon: 'search' },
      ],
    },
  });

  if (!session?.user) return null;

  return <ChatKit control={control} className="flex-1 w-full" />;
}
```

## Template 2: Backend Store Implementation

Template for creating a custom Store implementation.

```python
from chatkit.server import Store, ThreadMetadata, ThreadItem, Page, Attachment
from typing import Literal
from uuid import uuid4

class [YourStore](Store[dict]):
    """Custom ChatKit store implementation."""

    def __init__(self, db_engine):
        self.engine = db_engine

    # ==================== ID Generation ====================

    def generate_thread_id(self, context: dict) -> str:
        return str(uuid4())

    def generate_item_id(
        self,
        item_type: Literal["message", "tool_call", "task", "workflow", "attachment"],
        thread: ThreadMetadata,
        context: dict,
    ) -> str:
        return str(uuid4())

    # ==================== Thread Operations ====================

    async def load_thread(self, thread_id: str, context: dict) -> ThreadMetadata:
        # Load from your database
        with Session(self.engine) as session:
            # Your implementation
            pass

    async def save_thread(self, thread: ThreadMetadata, context: dict) -> None:
        # Save to your database
        with Session(self.engine) as session:
            # Your implementation
            pass

    async def delete_thread(self, thread_id: str, context: dict) -> None:
        # Delete from your database
        with Session(self.engine) as session:
            # Your implementation
            pass

    async def load_threads(
        self, limit: int, after: str | None, order: str, context: dict
    ) -> Page[ThreadMetadata]:
        # List threads with pagination
        with Session(self.engine) as session:
            # Your implementation
            return Page(data=[], has_more=False)

    # ==================== Item Operations ====================

    async def load_thread_items(
        self, thread_id: str, after: str | None, limit: int, order: str, context: dict
    ) -> Page[ThreadItem]:
        # Load thread items
        with Session(self.engine) as session:
            # Your implementation
            return Page(data=[], has_more=False)

    async def load_item(self, thread_id: str, item_id: str, context: dict) -> ThreadItem:
        # Load single item
        with Session(self.engine) as session:
            # Your implementation
            pass

    async def save_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        # Save item
        with Session(self.engine) as session:
            # Your implementation
            pass

    async def add_thread_item(self, thread_id: str, item: ThreadItem, context: dict) -> None:
        await self.save_item(thread_id, item, context)

    async def delete_thread_item(self, thread_id: str, item_id: str, context: dict) -> None:
        # Delete item
        with Session(self.engine) as session:
            # Your implementation
            pass

    # ==================== Attachment Operations ====================

    async def load_attachment(self, attachment_id: str, context: dict) -> Attachment:
        # Load attachment
        pass

    async def save_attachment(self, attachment: Attachment, context: dict) -> None:
        # Save attachment
        pass

    async def delete_attachment(self, attachment_id: str, context: dict) -> None:
        # Delete attachment
        pass
```

## Template 3: ChatKitServer Implementation

Template for creating a custom ChatKitServer.

```python
from chatkit.server import ChatKitServer, ThreadMetadata, UserMessageItem, ThreadStreamEvent
from chatkit.agents import stream_agent_response, simple_to_agent_input, AgentContext
from agents import Runner
from typing import AsyncIterator
import logging

logger = logging.getLogger(__name__)


class [YourChatKitServer](ChatKitServer[dict]):
    """Custom ChatKit server with [YOUR_FEATURE]."""

    async def respond(
        self,
        thread: ThreadMetadata,
        input: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if input is None:
            return

        # Extract user_id from context
        user_id = context.get("user_id")
        if not user_id:
            logger.error("No user_id in context")
            return

        # Import your agent creation function
        from [YOUR_MODULE] import create_agent

        # Create agent context
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        # Convert ChatKit input to Agent format
        agent_input = await simple_to_agent_input(input)
        if not agent_input:
            return

        try:
            # Create agent (with tools if needed)
            agent = await create_agent(user_id)

            # Run agent with streaming
            result = Runner.run_streamed(agent, input=agent_input)

            # Stream response back to ChatKit
            async for event in stream_agent_response(agent_context, result):
                yield event

        except Exception as e:
            logger.error(f"Error in respond: {e}", exc_info=True)
            # Yield error message
            yield self._create_error_event(thread, context, str(e))

    def _create_error_event(self, thread, context, error_message):
        """Create error event for user."""
        from chatkit.server import AssistantMessageItem, ThreadItemDoneEvent

        error_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            content=[{"type": "text", "text": f"Error: {error_message}"}],
        )
        return ThreadItemDoneEvent(item=error_item)
```

## Template 4: FastAPI Endpoint

Template for ChatKit FastAPI endpoint.

```python
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from chatkit.server import StreamingResult, NonStreamingResult
from [YOUR_MODULE] import [YourChatKitServer], [YourStore]
import logging

logger = logging.getLogger(__name__)

# Create router
chatkit_router = APIRouter(prefix="/api", tags=["chatkit"])

# Initialize ChatKit server
data_store = [YourStore]()  # Or PostgresStore for production
chatkit_server = [YourChatKitServer](data_store)


@chatkit_router.post("/chatkit")
async def chatkit_endpoint(request: Request):
    """
    Main ChatKit protocol endpoint.

    Handles all ChatKit requests with JWT authentication.
    """
    try:
        # Extract and validate token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing auth header")

        token = auth_header[7:]
        user_id = [YOUR_VERIFY_TOKEN_FUNCTION](token)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Create context
        context = {"user_id": user_id}
        body = await request.body()

        # Process request
        result = await chatkit_server.process(body, context)

        # Return response
        if isinstance(result, StreamingResult):
            return StreamingResponse(
                result,
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        elif isinstance(result, NonStreamingResult):
            return Response(content=result.json, media_type="application/json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ChatKit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## Template 5: Layout with ChatKit Script

Template for Next.js layout with ChatKit web component.

```tsx
import Script from "next/script";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "[YOUR_APP_NAME]",
  description: "[YOUR_DESCRIPTION]",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* ChatKit Web Component - REQUIRED */}
        <Script
          src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
          strategy="beforeInteractive"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

## Template 6: Environment Variables

### Frontend (.env.local)

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# ChatKit Configuration
NEXT_PUBLIC_CHATKIT_DOMAIN_KEY=localhost-dev  # For prod: dk_xxx from OpenAI

# Auth Configuration
NEXT_PUBLIC_AUTH_URL=http://localhost:3000
```

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# OpenAI
OPENAI_API_KEY=sk-proj-xxx

# MCP Server (if using)
MCP_SERVER_URL=http://localhost:8001/mcp

# Auth
BETTER_AUTH_SECRET=your_secret_here
BETTER_AUTH_ISSUER=http://localhost:3000
BETTER_AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks

# Server
PORT=8000
LOG_LEVEL=INFO
```

## Template 7: Docker Deployment

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]
```

## Template 8: Nginx Configuration

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name [YOUR_DOMAIN];

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name [YOUR_DOMAIN];

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/[YOUR_DOMAIN]/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/[YOUR_DOMAIN]/privkey.pem;

    # Frontend (Next.js)
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support for ChatKit streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # ChatKit endpoint (SSE streaming)
    location /chatkit {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE specific settings
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

## Template 9: systemd Service File

```ini
[Unit]
Description=[YOUR_APP] Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/app/backend
EnvironmentFile=/app/.env.production

# Run with uvicorn
ExecStart=/usr/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

# Restart configuration
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Template 10: Database Migration Script

```python
"""
migrations/001_create_chatkit_tables.py

Create tables for ChatKit data (if using custom store).
"""

from sqlmodel import SQLModel, Field, create_engine
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional


class Conversation(SQLModel, table=True):
    """ChatKit Thread/Conversation model."""
    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    title: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Message(SQLModel, table=True):
    """ChatKit Message/Item model."""
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    thread_id: UUID = Field(foreign_key="conversations.id", index=True)
    role: str = Field(max_length=50)  # "user" or "assistant"
    content: str = Field(sa_column_kwargs={"type_": "TEXT"})  # JSON string
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def migrate(database_url: str):
    """Run migration to create tables."""
    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    print("✅ ChatKit tables created successfully")


if __name__ == "__main__":
    import os
    database_url = os.getenv("DATABASE_URL")
    migrate(database_url)
```

## Quick Copy-Paste Snippets

### Valid ChatKit Icons

```tsx
// Valid icon names for startScreen prompts
'notebook-pencil'
'search'
'lightbulb'
'sparkle'
'square-code'
'chart'
```

### Error Handling

```python
# Create error event for ChatKit
from chatkit.server import AssistantMessageItem, ThreadItemDoneEvent

error_item = AssistantMessageItem(
    id=self.store.generate_item_id("message", thread, context),
    thread_id=thread.id,
    content=[{"type": "text", "text": "Error message here"}],
)
yield ThreadItemDoneEvent(item=error_item)
```

### CORS Configuration

```python
# FastAPI CORS for ChatKit
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### PostgresStore Setup

```python
# Use production PostgreSQL store
from chatkit.stores import PostgresStore

data_store = PostgresStore(
    connection_string=os.getenv("DATABASE_URL"),
    table_prefix="chatkit_",
)
```
