# Database Specification: Conversations and Messages

## Purpose
Provide persistent chat history storage.

## Tables

### conversations
Columns:
- id: integer primary key
- user_id: string (foreign key to users.id)
- created_at: timestamp
- updated_at: timestamp

Indexes:
- (user_id)

Rules:
- A user may have multiple conversations
- Users cannot access others' conversations

---

### messages
Columns:
- id: integer primary key
- conversation_id: integer (foreign key to conversations.id)
- user_id: string
- role: "user" or "assistant"
- content: text
- created_at: timestamp

Indexes:
- (conversation_id)
- (user_id)

Rules:
- Messages belong to a conversation
- user_id must match conversation.user_id
