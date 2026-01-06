---
id: 0006
title: Initialize Microservice Dependencies
stage: green
date: 2026-01-06
surface: claude-code
model: claude-sonnet-4-5
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.implement T004
labels: [setup, dependencies, microservices, phase1]
links:
  spec: specs/005-event-driven-microservices/spec.md
  ticket: tasks.md#T004
  adr: null
  pr: null
files:
  - services/notification-service/requirements.txt
  - services/recurring-task-service/requirements.txt
  - services/audit-service/requirements.txt
  - services/websocket-service/requirements.txt
  - specs/005-event-driven-microservices/tasks.md
tests: []
---

## Prompt

Implement task T004: Initialize Python virtual environments for all microservices (services/*/requirements.txt with Dapr SDK, FastAPI, SQLModel)

Context from tasks.md:
- Task T004 is part of Phase 1: Setup (Shared Infrastructure)
- It's marked as [P] (can run in parallel)
- Dependencies needed: Dapr SDK, FastAPI, SQLModel
- Four microservices need requirements.txt files: notification-service, recurring-task-service, audit-service, websocket-service

## Response snapshot

Created requirements.txt files for all four microservices with appropriate dependencies:

1. **notification-service/requirements.txt**:
   - Core: FastAPI 0.125.0, uvicorn 0.38.0, pydantic 2.12.5
   - Database: SQLModel 0.0.27, psycopg2-binary 2.9.11
   - Dapr: dapr 1.14.0, dapr-ext-grpc 1.14.0
   - HTTP client: httpx 0.28.1 (for webhook delivery)
   - Auth: pyjwt 2.10.1, cryptography 46.0.3
   - Testing: pytest 9.0.2, pytest-asyncio 0.25.5
   - Validation: jsonschema 4.25.1

2. **recurring-task-service/requirements.txt**:
   - Same core dependencies as notification-service
   - Additional: python-dateutil 2.9.0 (for recurrence calculations)

3. **audit-service/requirements.txt**:
   - Same core dependencies as notification-service
   - No additional dependencies (simple event logging)

4. **websocket-service/requirements.txt**:
   - Same core dependencies as notification-service
   - Additional: websockets 15.0.1 (for WebSocket connections)

All services use:
- Python 3.13 compatible versions
- Matching FastAPI/SQLModel versions with backend for consistency
- Dapr SDK for event-driven communication
- JWT validation for authentication
- JSON Schema for contract testing

## Outcome

- ✅ Impact: Created requirements.txt for 4 microservices (notification, recurring-task, audit, websocket). Each service now has pinned dependencies ready for virtual environment setup and Docker builds.
- 🧪 Tests: No tests required for this task (setup phase)
- 📁 Files: Created 4 requirements.txt files, updated tasks.md (marked T004 as complete)
- 🔁 Next prompts: T005 (Create Dockerfiles), T006 (Configure linting), T007 (Database migrations)
- 🧠 Reflection: Dependency versions aligned with existing backend/requirements.txt for consistency. Service-specific deps added based on plan.md requirements (httpx for notifications, python-dateutil for recurrence, websockets for WebSocket service).

## Evaluation notes (flywheel)

- Failure modes observed: None - straightforward dependency file creation
- Graders run and results (PASS/FAIL): N/A - no tests for this task
- Prompt variant (if applicable): Standard implementation from tasks.md
- Next experiment (smallest change to try): Consider using uv for dependency management (match backend pattern)
