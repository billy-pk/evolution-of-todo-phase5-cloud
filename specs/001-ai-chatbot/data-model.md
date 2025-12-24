# Data Model: AI-Powered Chatbot

**Feature**: 001-ai-chatbot
**Date**: 2025-12-12
**Status**: Design Complete

## Overview

This document defines the data models for Phase 3, including new entities (Conversation, Message) and their relationships. Phase 2's Task model remains unchanged to maintain backwards compatibility.

---

## Entity Relationship Diagram

```
┌─────────────────┐
│      User       │ (Better Auth - external)
│   (user_id)     │
└────────┬────────┘
         │
         │ 1:N
         │
    ┌────┴─────────────────┬─────────────────┐
    │                      │                 │
    ▼                      ▼                 ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Conversation  │   │     Message     │   │      Task       │
│      (new)      │   │     (new)       │   │   (existing)    │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │                      ▲
         │ 1:N                  │
         └──────────────────────┘
```

**Relationships**:
- User → Conversation: 1:N (one user has many conversations)
- User → Message: 1:N (one user has many messages)
- Conversation → Message: 1:N (one conversation has many messages)
- User → Task: 1:N (inherited from Phase 2, unchanged)

---

## 1. Task (Existing - NO CHANGES)

**Table**: `tasks`
**Purpose**: Represents a todo item (inherited from Phase 2)
**Phase**: Phase 2 (unchanged in Phase 3)

### Schema

| Column       | Type            | Constraints                  | Description                       |
|--------------|-----------------|------------------------------|-----------------------------------|
| id           | UUID            | PRIMARY KEY                  | Unique task identifier            |
| user_id      | VARCHAR(255)    | NOT NULL, INDEX              | User ID from Better Auth          |
| title        | VARCHAR(200)    | NOT NULL, MIN_LENGTH(1)      | Task title (required)             |
| description  | VARCHAR(1000)   | NULLABLE                     | Task description (optional)       |
| completed    | BOOLEAN         | NOT NULL, DEFAULT FALSE      | Completion status                 |
| created_at   | TIMESTAMP       | NOT NULL, DEFAULT NOW()      | Creation timestamp (UTC)          |
| updated_at   | TIMESTAMP       | NOT NULL, DEFAULT NOW()      | Last update timestamp (UTC)       |

### Indexes
- `idx_tasks_user_id` on `user_id` (existing)

### SQLModel Definition
```python
class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True, max_length=255)
    title: str = Field(max_length=200, min_length=1)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Validation Rules
- title: 1-200 characters, required
- description: 0-1000 characters, optional
- user_id: Must match JWT token user_id
- All operations filtered by user_id for isolation

### State Transitions
```
[Created] --complete_task--> [Completed]
[Completed] --update_task--> [Completed] (can update title/description)
[Any State] --delete_task--> [Deleted] (hard delete)
```

---

## 2. Conversation (New in Phase 3)

**Table**: `conversations`
**Purpose**: Represents a chat thread between a user and the AI assistant
**Phase**: Phase 3 (new)

### Schema

| Column       | Type            | Constraints                  | Description                           |
|--------------|-----------------|------------------------------|---------------------------------------|
| id           | UUID            | PRIMARY KEY                  | Unique conversation identifier        |
| user_id      | VARCHAR(255)    | NOT NULL, INDEX              | User ID from Better Auth (FK ref)     |
| title        | VARCHAR(200)    | NULLABLE                     | Optional conversation title           |
| created_at   | TIMESTAMP       | NOT NULL, DEFAULT NOW()      | Creation timestamp (UTC)              |
| updated_at   | TIMESTAMP       | NOT NULL, DEFAULT NOW()      | Last message timestamp (UTC)          |

### Indexes
- `idx_conversations_user_id` on `user_id` (for user's conversation list)
- `idx_conversations_updated_at` on `updated_at` (for sorting by recent activity)

### SQLModel Definition
```python
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="Unique conversation identifier")
    user_id: str = Field(index=True, max_length=255, description="User ID from Better Auth")
    title: Optional[str] = Field(default=None, max_length=200, description="Optional conversation title (e.g., first user message)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last message timestamp (UTC)")
```

### Validation Rules
- user_id: Must match JWT token user_id
- title: Auto-generated from first user message if not provided, max 200 characters
- created_at: Immutable after creation
- updated_at: Updated on every new message

### Lifecycle
- **Creation**: Automatically created on first message if conversation_id not provided
- **Update**: updated_at refreshed on each new message
- **Deletion**: Manual deletion by user (soft delete possible in future via deleted_at column)
- **Retention**: Indefinite (as per requirement FR-047)

### Query Patterns
```python
# Get user's conversations (sorted by most recent)
SELECT * FROM conversations
WHERE user_id = ?
ORDER BY updated_at DESC
LIMIT 50;

# Check conversation ownership
SELECT id FROM conversations
WHERE id = ? AND user_id = ?;
```

---

## 3. Message (New in Phase 3)

**Table**: `messages`
**Purpose**: Represents a single message within a conversation (user or assistant)
**Phase**: Phase 3 (new)

### Schema

| Column           | Type            | Constraints                       | Description                               |
|------------------|-----------------|-----------------------------------|-------------------------------------------|
| id               | UUID            | PRIMARY KEY                       | Unique message identifier                 |
| conversation_id  | UUID            | NOT NULL, INDEX, FK conversations | Conversation this message belongs to      |
| user_id          | VARCHAR(255)    | NOT NULL, INDEX                   | User ID (for user isolation)              |
| role             | VARCHAR(20)     | NOT NULL, CHECK('user','assistant') | Message role: "user" or "assistant"       |
| content          | TEXT            | NOT NULL                          | Message text content                      |
| tool_calls       | TEXT            | NULLABLE                          | JSON array of tool calls (if role=assistant) |
| created_at       | TIMESTAMP       | NOT NULL, DEFAULT NOW()           | Message timestamp (UTC)                   |

### Indexes
- `idx_messages_conversation_id` on `conversation_id` (for loading conversation history)
- `idx_messages_user_id` on `user_id` (for user isolation queries)
- `idx_messages_created_at` on `created_at` (for chronological ordering)

### SQLModel Definition
```python
class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="Unique message identifier")
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True, description="Conversation FK")
    user_id: str = Field(index=True, max_length=255, description="User ID for isolation")
    role: str = Field(max_length=20, description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message text content")
    tool_calls: Optional[str] = Field(default=None, description="JSON array of tool calls (for assistant messages)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Message timestamp (UTC)")

    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError('role must be "user" or "assistant"')
        return v
```

### Validation Rules
- role: Must be "user" or "assistant" (enforced via CHECK constraint and validator)
- content: Required, no length limit (TEXT type)
- tool_calls: Optional, only for assistant messages, must be valid JSON array
- conversation_id: Must exist in conversations table and belong to user_id
- user_id: Must match conversation's user_id (foreign key referential integrity)

### Message Roles
- **user**: Messages sent by the user (input)
- **assistant**: Messages sent by the AI agent (responses)

### Tool Calls Format
When role = "assistant" and the agent called tools, store as JSON array:
```json
[
  {
    "tool": "add_task",
    "parameters": {
      "user_id": "user-123",
      "title": "Buy groceries"
    },
    "result": {
      "task_id": "uuid-...",
      "status": "created",
      "title": "Buy groceries"
    }
  }
]
```

### Query Patterns
```python
# Load conversation history (ordered chronologically)
SELECT * FROM messages
WHERE conversation_id = ? AND user_id = ?
ORDER BY created_at ASC;

# Load last N messages (for context window)
SELECT * FROM messages
WHERE conversation_id = ? AND user_id = ?
ORDER BY created_at DESC
LIMIT 100;

# Count messages in conversation
SELECT COUNT(*) FROM messages
WHERE conversation_id = ?;
```

### Lifecycle
- **Creation**: Created when user sends message or agent responds
- **Update**: Immutable after creation (no updates allowed)
- **Deletion**: Cascade delete when conversation is deleted
- **Retention**: Same as parent conversation (indefinite)

---

## Database Migration

### Migration Script: `backend/scripts/migrate_conversations.py`

```python
from sqlmodel import SQLModel, create_engine
from backend.models import Conversation, Message
from backend.config import settings

def run_migration():
    """Create conversations and messages tables"""
    engine = create_engine(settings.DATABASE_URL)

    # Create tables (only new ones; existing tables unchanged)
    SQLModel.metadata.create_all(engine, tables=[
        Conversation.__table__,
        Message.__table__
    ])

    print("✅ Migration complete: conversations and messages tables created")

if __name__ == "__main__":
    run_migration()
```

### Rollback Strategy
```sql
-- Rollback script (if needed)
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
```

---

## Data Integrity Rules

### 1. User Isolation (CRITICAL)
- Every query MUST filter by user_id
- Conversations: `WHERE user_id = ?`
- Messages: `WHERE user_id = ?` (even though they have conversation_id)
- Tasks: `WHERE user_id = ?` (inherited from Phase 2)

### 2. Foreign Key Constraints
- `messages.conversation_id` → `conversations.id` (CASCADE DELETE)
- No FK from conversations/messages to Better Auth users (external system)

### 3. Timestamps
- All timestamps in UTC (use `datetime.now(UTC)`)
- created_at: Immutable
- updated_at: Auto-update on modification

### 4. Transaction Boundaries
- Save user message + assistant response in single transaction (atomicity)
- Create conversation + first message in single transaction

---

## Indexing Strategy

### Performance Goals
- Load conversation history: <100ms for 100 messages
- List user's conversations: <50ms for 50 conversations
- Verify conversation ownership: <10ms

### Indexes Required
1. `conversations(user_id)` - List user's conversations
2. `conversations(updated_at)` - Sort by recent activity
3. `messages(conversation_id)` - Load conversation history
4. `messages(user_id)` - User isolation queries
5. `messages(created_at)` - Chronological ordering

### Index Maintenance
- Monitor index usage with PostgreSQL pg_stat_user_indexes
- Add composite index on (conversation_id, created_at) if queries slow down

---

## Storage Estimates

### Per-User Averages
- Conversations: ~10-50 conversations per user
- Messages: ~50-1000 messages per user (20-100 messages per conversation)
- Tasks: ~5-50 tasks per user (inherited from Phase 2)

### Storage Requirements (1000 users)
- Conversations: ~100 KB (10 KB per 1000 rows)
- Messages: ~10 MB (10 KB per 1000 rows * 1000 users)
- Total new storage: ~10 MB (negligible for Neon PostgreSQL free tier)

### Scalability Notes
- Neon PostgreSQL free tier: 0.5 GB storage, 100 hours compute/month
- No concerns for MVP (1000 users, 1M messages = ~1 GB)
- Consider archiving old conversations if storage becomes issue (Phase 5+)

---

## Summary

Phase 3 introduces **2 new entities**:
1. ✅ **Conversation**: Chat thread metadata (id, user_id, title, timestamps)
2. ✅ **Message**: Individual messages within conversations (role, content, tool_calls)

**Phase 2 Task entity**: Unchanged, fully compatible with Phase 3.

**Next Step**: Generate API contracts for the chat endpoint and MCP tools.
