# Phase 3 Overview – AI-Powered Todo Chatbot

## Purpose
Phase 3 extends the existing/previous Phase 2 full-stack todo application by adding an AI-powered conversational interface that allows users to manage tasks using natural language.

The AI layer uses:
- OpenAI ChatKit (UI)
- OpenAI Agents SDK (backend)
- MCP Tools (task operations)
- FastAPI chat endpoint
- Conversation and message persistence in the database

The system must preserve all Phase 2 functionality.

## Inherited Features from Phase 2
- Next.js frontend with JWT authentication via Better Auth
- FastAPI backend with REST task endpoints
- Neon PostgreSQL database
- SQLModel ORM
- Complete task CRUD system
- User isolation enforced by JWT user_id

## Phase 3 Additions
- Chat UI at /chat using ChatKit
- Natural language task management
- Chat endpoint: POST /api/{user_id}/chat
- MCP server exposing task tools
- AI agent capable of calling MCP tools
- New tables:
  - conversations
  - messages
- Stateless server design

## Goals
- Allow users to create, update, delete, and list tasks via natural language
- Persist chat history linked to user_id
- Maintain seamless integration with Phase 2 task UI

## Non-Goals
- Changing existing task UI
- Changing authentication system
- Breaking Phase 2 REST API
- Adding voice, translation, or advanced AI features

## Deliverables
- Chat UI
- Chat endpoint
- MCP tools implementation
- AI agent configuration
- DB migrations for conversations/messages
