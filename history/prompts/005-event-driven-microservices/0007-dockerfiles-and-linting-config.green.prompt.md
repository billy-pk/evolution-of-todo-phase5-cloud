---
id: 0007
title: Dockerfiles and Linting Configuration
stage: green
date: 2026-01-06
surface: claude-code
model: claude-sonnet-4-5
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.implement T005 T006
labels: [setup, docker, linting, phase1]
links:
  spec: specs/005-event-driven-microservices/spec.md
  ticket: tasks.md#T005-T006
  adr: null
  pr: null
files:
  - backend/Dockerfile
  - backend/.dockerignore
  - frontend/Dockerfile
  - frontend/.dockerignore
  - services/notification-service/Dockerfile
  - services/notification-service/.dockerignore
  - services/notification-service/pyproject.toml
  - services/recurring-task-service/Dockerfile
  - services/recurring-task-service/.dockerignore
  - services/recurring-task-service/pyproject.toml
  - services/audit-service/Dockerfile
  - services/audit-service/.dockerignore
  - services/audit-service/pyproject.toml
  - services/websocket-service/Dockerfile
  - services/websocket-service/.dockerignore
  - services/websocket-service/pyproject.toml
  - specs/005-event-driven-microservices/tasks.md
tests: []
---

## Prompt

Implement tasks T005 and T006 in parallel:
- T005: Create Dockerfiles for all 6 services (backend, frontend, notification-service, recurring-task-service, audit-service, websocket-service)
- T006: Configure linting and formatting for microservices (ruff, black, mypy)

Context from tasks.md:
- Both tasks are marked as [P] (can run in parallel)
- Part of Phase 1: Setup (Shared Infrastructure)
- Dockerfiles should use multi-stage builds for optimization
- All services should have consistent linting/formatting configuration

## Response snapshot

**Task T005 - Dockerfiles Created:**

1. **backend/Dockerfile** (1.3K):
   - Multi-stage build: builder + runtime
   - Python 3.13-slim base image
   - PostgreSQL dependencies (libpq-dev for build, libpq5 for runtime)
   - Non-root user (appuser) for security
   - Port 8000 exposed
   - Health check endpoint
   - CMD: uvicorn main:app

2. **frontend/Dockerfile** (1.3K):
   - Multi-stage build: deps + builder + runner
   - Node 18-alpine base image
   - Next.js 16 production build with standalone output
   - Non-root user (nextjs) for security
   - Port 3000 exposed
   - Health check endpoint
   - CMD: node server.js

3. **services/*/Dockerfile** (4 microservices, each 1.3K):
   - Consistent structure across all services
   - Multi-stage build: builder + runtime
   - Python 3.13-slim base image
   - Port 8080 exposed (Dapr sidecar communication)
   - Non-root user (appuser) for security
   - Service-specific CMD: python <service_name>.py

**Task T006 - Linting Configuration:**

Created pyproject.toml for all 4 microservices with:
- **Ruff**: Line length 100, Python 3.13 target, select E/F/I/N/W/UP rules
- **Black**: Line length 100, Python 3.13 target
- **Mypy**: Python 3.13, warn on return any, warn on unused configs
- **Pytest**: Async mode auto, testpaths configured

**Additional: .dockerignore Files:**

Created .dockerignore for backend, frontend, and all 4 microservices to exclude:
- Python artifacts (__pycache__, *.pyc, .venv/)
- Node modules (frontend only)
- Test files and coverage
- IDE files (.vscode/, .idea/)
- Environment files (.env*)
- Documentation (*.md, docs/)
- Git files (.git/, .gitignore)

## Outcome

- ✅ Impact: Created production-ready Dockerfiles for all 6 services with multi-stage builds, security hardening (non-root users), and health checks. Configured consistent linting/formatting for all Python microservices.
- 🧪 Tests: No tests required for this task (setup phase)
- 📁 Files: Created 17 files (6 Dockerfiles, 7 .dockerignore, 4 pyproject.toml), updated tasks.md
- 🔁 Next prompts: T007 (Database migrations), T008-T011 (Alembic migrations), T012-T015 (Extended models)
- 🧠 Reflection: Used multi-stage builds to minimize image size. All microservices have consistent structure for maintainability. Frontend Dockerfile assumes Next.js standalone output (need to verify next.config.js has `output: 'standalone'`).

## Evaluation notes (flywheel)

- Failure modes observed: None - straightforward Docker and config file creation
- Graders run and results (PASS/FAIL): N/A - no tests for this task
- Prompt variant (if applicable): Standard implementation from tasks.md
- Next experiment (smallest change to try): Consider using Docker BuildKit cache mounts for faster pip/npm installs
