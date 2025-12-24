# UI Specification: Chat Page (/chat)

## Purpose
Provide a natural-language interface for managing tasks through the AI assistant.

## Requirements

### Layout
- Page located at /chat
- ChatKit-based UI
- Scrollable message list
- Input box at bottom
- Loading indicator during agent processing

### Features
- Show message history
- If conversation_id not provided, create a new conversation automatically
- Render:
  - user messages (right aligned)
  - assistant messages (left aligned)
- Allow user to click "New Conversation"

### Error States
- Show message when JWT is invalid
- Show error banner if backend returns 500

### Non-Goals
- Voice input
- Theme switching
- Multi-conversation sidebar (optional future)
