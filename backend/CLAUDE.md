# Backend Guidelines – FastAPI App (hackathon-todo)

## Stack
- FastAPI
- SQLModel
- Neon PostgreSQL
- JWT auth (Better Auth tokens)
- Uvicorn for dev server

## Target Structure
- `main.py`          – FastAPI app, router mounting
- `models.py`        – SQLModel models (Task, Conversation, Message)
- `schemas.py`       – Pydantic request/response models
- `db.py`            – DB engine + session management
- `routes/chat.py`   – Chat endpoint for conversational task management
- `middleware.py`    – JWT validation middleware (JWKS)
- `services/agent.py` – OpenAI Agent with MCP tools
- `tools/server.py`  – MCP server with task management tools

## API Conventions
- All endpoints under `/api/`.
- Conversational task management via `/api/{user_id}/chat` endpoint
- All responses are JSON.
- Use Pydantic models for request/response bodies.
- Use `HTTPException` with proper status codes for errors.

## Database
- Use SQLModel models matching:
  - @specs/database/schema.md
- DB connection URL comes from env var `DATABASE_URL` (Neon PostgreSQL).
- Use alembic or simple migration strategy as needed (later phases can refine).

## Auth & Authorization
- Every request must include a JWT in `Authorization: Bearer <token>`.
- Use shared secret `BETTER_AUTH_SECRET` to verify tokens.
- Extract `user_id` from JWT and ensure:
  - Path user_id == token user_id
  - Queries are always filtered by `user_id`.

## Running Dev Server (expected)
- `uvicorn main:app --reload --port 8000`
