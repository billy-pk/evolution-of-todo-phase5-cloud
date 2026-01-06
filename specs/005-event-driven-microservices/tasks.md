# Tasks: Phase V Event-Driven Microservices Architecture

**Input**: Design documents from `/specs/005-event-driven-microservices/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are REQUIRED per Constitution Principle V (Test-Driven Development). Contract tests for event schemas and integration tests for end-to-end workflows are mandatory.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This project uses a monorepo structure:
- **Backend**: `backend/` (FastAPI + MCP Server)
- **Frontend**: `frontend/` (Next.js)
- **Microservices**: `services/` (Notification, Recurring Task, Audit, WebSocket)
- **Infrastructure**: `infrastructure/` (Helm charts, Dapr components)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and infrastructure setup for event-driven microservices architecture

- [X] T001 Create services/ directory structure for microservices (notification-service, recurring-task-service, audit-service, websocket-service)
- [X] T002 Create infrastructure/ directory structure (helm/, dapr-components/, scripts/)
- [X] T003 [P] Create Alembic migrations directory in backend/migrations/
- [X] T004 [P] Initialize Python virtual environments for all microservices (services/*/requirements.txt with Dapr SDK, FastAPI, SQLModel)
- [X] T005 [P] Create Dockerfiles for all 6 services (backend, frontend, notification-service, recurring-task-service, audit-service, websocket-service)
- [X] T006 [P] Configure linting and formatting for microservices (ruff, black, mypy)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Schema

- [X] T007 Create Alembic migration 001_add_advanced_features.py to add columns to tasks table (priority, tags, due_date, recurrence_id)
- [X] T008 Create Alembic migration 002_create_recurrence_rules.py to create recurrence_rules table
- [X] T009 Create Alembic migration 003_create_reminders.py to create reminders table
- [X] T010 Create Alembic migration 004_create_audit_log.py to create audit_log table
- [X] T011 Run database migrations and verify schema changes applied

### Extended Models

- [X] T012 [P] Extend Task model in backend/models.py (add priority, tags, due_date, recurrence_id fields, configure updated_at with onupdate trigger)
- [X] T013 [P] Create RecurrenceRule model in backend/models.py
- [X] T014 [P] Create Reminder model in backend/models.py
- [X] T015 [P] Create AuditLog model in backend/models.py

### Event Schemas and Dapr Components

- [X] T016 [P] Create task-events.schema.json in specs/005-event-driven-microservices/contracts/events/
- [X] T017 [P] Create reminders.schema.json in specs/005-event-driven-microservices/contracts/events/
- [X] T018 [P] Create task-updates.schema.json in specs/005-event-driven-microservices/contracts/events/
- [X] T019 [P] Create local Dapr pubsub-redpanda.yaml in specs/005-event-driven-microservices/contracts/dapr-components/local/
- [X] T020 [P] Create local Dapr statestore-postgresql.yaml in specs/005-event-driven-microservices/contracts/dapr-components/local/
- [X] T021 [P] Create local Dapr jobs.yaml in specs/005-event-driven-microservices/contracts/dapr-components/local/
- [X] T022 [P] Create local Dapr secrets.yaml in specs/005-event-driven-microservices/contracts/dapr-components/local/
- [X] T023 [P] Create cloud Dapr pubsub-redpanda-cloud.yaml in specs/005-event-driven-microservices/contracts/dapr-components/cloud/
- [X] T024 [P] Create cloud Dapr statestore-postgresql.yaml in specs/005-event-driven-microservices/contracts/dapr-components/cloud/
- [X] T025 [P] Create cloud Dapr jobs.yaml in specs/005-event-driven-microservices/contracts/dapr-components/cloud/
- [X] T026 [P] Create cloud Dapr secrets.yaml in specs/005-event-driven-microservices/contracts/dapr-components/cloud/

### Event Publishing Infrastructure

- [X] T027 Create EventPublisher service in backend/services/event_publisher.py (Dapr Pub/Sub client wrapper)
- [X] T028 Create event payload schemas in backend/schemas.py (TaskEventPayload, ReminderEventPayload, TaskUpdatePayload)
- [X] T029 Integrate Dapr client in backend/main.py (initialize DaprClient singleton)
- [X] T030 Add event publishing to existing task endpoints in backend/routes/chat.py (publish task.created, task.updated, task.completed, task.deleted events) **[Depends on T027-T029]**

### Contract Tests

- [X] T031 [P] Create contract test for task-events schema in backend/tests/contract/test_task_events_schema.py
- [X] T032 [P] Create contract test for reminders schema in backend/tests/contract/test_reminders_schema.py
- [X] T033 [P] Create contract test for task-updates schema in backend/tests/contract/test_task_updates_schema.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Recurring Task Management (Priority: P1) 🎯 MVP

**Goal**: Enable users to create tasks that repeat automatically (daily, weekly, monthly) so they don't have to manually recreate routine tasks

**Independent Test**: Create a task with recurrence "daily", mark it complete, and verify a new instance is automatically created with the same attributes for the next occurrence

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T034 [P] [US1] Integration test for recurring task creation in backend/tests/integration/test_recurring_task_creation.py
- [X] T035 [P] [US1] Integration test for recurring task generation in backend/tests/integration/test_recurring_task_generation.py
- [X] T036 [P] [US1] Unit test for recurrence pattern calculation in backend/tests/unit/test_recurrence_logic.py

### Implementation for User Story 1

- [X] T037 [US1] Extend MCP tool add_task in backend/tools/server.py to accept recurrence parameters (pattern, interval, due_date, priority, tags)
- [X] T038 [US1] Extend MCP tool update_task in backend/tools/server.py to support updating recurrence rules (pattern, interval, due_date, priority, tags)
- [X] T039 [US1] Create RecurrenceService in backend/services/recurrence_service.py (calculate next occurrence, validate patterns)
- [X] T040 [US1] Update task creation logic in backend/tools/server.py to create RecurrenceRule when recurrence specified
- [X] T041 [US1] Create Recurring Task Service main file in services/recurring-task-service/recurring_task_service.py (FastAPI app with Dapr Pub/Sub)
- [X] T042 [US1] Implement Dapr Pub/Sub subscription to task-events topic in services/recurring-task-service/recurring_task_service.py (/dapr/subscribe endpoint)
- [X] T043 [US1] Implement task.completed event handler in services/recurring-task-service/recurring_task_service.py (process_recurring_task function with RecurrenceService)
- [X] T044 [US1] Implement idempotent next instance creation logic in services/recurring-task-service/recurring_task_service.py (database query to check existing next instance)
- [X] T045 [US1] Add validation for recurrence patterns in backend/services/recurrence_service.py (daily: 1-365, weekly: 1-52, monthly: 1-12)
- [X] T046 [US1] Add logging for recurring task operations in services/recurring-task-service/recurring_task_service.py (structured logging with correlation IDs)

**Checkpoint**: At this point, User Story 1 should be fully functional - tasks can be created with recurrence and automatically generate next instances

---

## Phase 4: User Story 2 - Due Dates and Reminders (Priority: P2)

**Goal**: Enable users to set due dates on tasks and receive automatic reminders so they never miss important deadlines

**Independent Test**: Create a task with a due date and reminder time, then verify the reminder triggers automatically at the scheduled time via notification service

### Tests for User Story 2

- [ ] T047 [P] [US2] Integration test for due date validation in backend/tests/integration/test_due_date_validation.py
- [ ] T048 [P] [US2] Integration test for reminder scheduling in backend/tests/integration/test_reminder_scheduling.py
- [ ] T049 [P] [US2] Integration test for reminder delivery in backend/tests/integration/test_reminder_delivery.py

### Implementation for User Story 2

- [ ] T050 [P] [US2] Extend MCP tool add_task in backend/tools/server.py to accept due_date parameter (ISO8601)
- [ ] T051 [P] [US2] Extend MCP tool add_task in backend/tools/server.py to accept reminder_offset parameter (e.g., "1 hour before")
- [ ] T052 [US2] Create ReminderService in backend/services/reminder_service.py (schedule reminders via Dapr Jobs API)
- [ ] T053 [US2] Implement due date validation in backend/services/reminder_service.py (reject past dates unless explicitly allowed)
- [ ] T053b [US2] Integrate dateparser library for natural language date parsing in backend/services/reminder_service.py (e.g., "tomorrow at 5pm" → ISO8601)
- [ ] T054 [US2] Update task creation logic in backend/tools/server.py to create Reminder and schedule via Dapr Jobs API
- [ ] T055 [US2] Create Notification Service main file in services/notification-service/notification_service.py
- [ ] T056 [US2] Implement Dapr Pub/Sub subscription to reminders topic in services/notification-service/notification_service.py
- [ ] T057 [US2] Implement Dapr Jobs API job handler endpoint in services/notification-service/notification_service.py (/api/jobs/reminder)
- [ ] T058 [US2] Implement notification delivery logic in services/notification-service/notification_service.py (webhook delivery, update reminder status)
- [ ] T059 [US2] Implement retry logic with exponential backoff in services/notification-service/notification_service.py (max 3 retries)
- [ ] T060 [US2] Add idempotency check in services/notification-service/notification_service.py (skip if task completed or deleted)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - tasks can have due dates and reminders

---

## Phase 5: User Story 3 - Advanced Task Filtering and Search (Priority: P3)

**Goal**: Enable users to search, filter, and sort tasks by multiple criteria (tags, priority, due date, status) to quickly find relevant tasks

**Independent Test**: Create multiple tasks with different tags, priorities, and statuses, then verify search and filter operations return correct results

### Tests for User Story 3

- [ ] T061 [P] [US3] Integration test for task search in backend/tests/integration/test_task_search.py
- [ ] T062 [P] [US3] Integration test for task filtering in backend/tests/integration/test_task_filtering.py
- [ ] T063 [P] [US3] Unit test for search query parsing in backend/tests/unit/test_search_parser.py

### Implementation for User Story 3

- [ ] T064 [P] [US3] Create MCP tool search_tasks in backend/tools/server.py (search by title, description, tags)
- [ ] T065 [P] [US3] Create MCP tool filter_tasks in backend/tools/server.py (filter by priority, status, due date, tags)
- [ ] T066 [US3] Implement SearchService in backend/services/search_service.py (build SQLModel queries with filters)
- [ ] T067 [US3] Add support for multiple filter criteria in backend/services/search_service.py (AND/OR logic)
- [ ] T068 [US3] Implement sorting logic in backend/services/search_service.py (by due_date, priority, created_at)
- [ ] T069 [US3] Add pagination support in backend/services/search_service.py (limit, offset)
- [ ] T070 [US3] Optimize queries with database indexes in backend/services/search_service.py (leverage ix_tasks_tags GIN index)

**Checkpoint**: All three user stories should now be independently functional - search and filter enhance task discovery

---

## Phase 6: User Story 4 - Priority-Based Task Organization (Priority: P4)

**Goal**: Enable users to assign priorities (low, normal, high, critical) to tasks to focus on the most important work first

**Independent Test**: Create tasks with different priorities, then verify they can be filtered and sorted by priority level

### Tests for User Story 4

- [ ] T071 [P] [US4] Integration test for priority assignment in backend/tests/integration/test_priority_assignment.py
- [ ] T072 [P] [US4] Integration test for priority sorting in backend/tests/integration/test_priority_sorting.py

### Implementation for User Story 4

- [ ] T073 [P] [US4] Extend MCP tool add_task in backend/tools/server.py to accept priority parameter (low, normal, high, critical)
- [ ] T074 [P] [US4] Extend MCP tool update_task in backend/tools/server.py to support updating priority
- [ ] T075 [US4] Add priority validation in backend/schemas.py (enum: low, normal, high, critical)
- [ ] T076 [US4] Add priority to recurrence metadata in backend/services/recurrence_service.py (preserve priority on next instance)
- [ ] T077 [US4] Update filter_tasks MCP tool in backend/tools/server.py to support priority filtering
- [ ] T078 [US4] Update search results to default sort by priority in backend/services/search_service.py (critical > high > normal > low)

**Checkpoint**: User Story 4 complete - tasks can be organized by priority

---

## Phase 7: User Story 5 - Tag-Based Task Categorization (Priority: P5)

**Goal**: Enable users to add multiple tags (e.g., "work", "personal", "urgent") to tasks for flexible categorization

**Independent Test**: Create tasks with multiple tags, then verify tags are preserved through recurrence, search, and filter operations

### Tests for User Story 5

- [ ] T079 [P] [US5] Integration test for tag assignment in backend/tests/integration/test_tag_assignment.py
- [ ] T080 [P] [US5] Integration test for tag filtering in backend/tests/integration/test_tag_filtering.py

### Implementation for User Story 5

- [ ] T081 [P] [US5] Extend MCP tool add_task in backend/tools/server.py to accept tags parameter (array of strings)
- [ ] T082 [P] [US5] Extend MCP tool update_task in backend/tools/server.py to support updating tags
- [ ] T083 [US5] Add tag validation in backend/schemas.py (max 10 tags, max 50 chars each, case-insensitive)
- [ ] T084 [US5] Add tags to recurrence metadata in backend/services/recurrence_service.py (preserve tags on next instance)
- [ ] T085 [US5] Update filter_tasks MCP tool in backend/tools/server.py to support tag filtering (ANY or ALL logic)
- [ ] T086 [US5] Update search_tasks MCP tool in backend/tools/server.py to search within tags
- [ ] T087 [US5] Normalize tags to lowercase in backend/tools/server.py (consistent search/filter)

**Checkpoint**: All five user stories complete - full feature set implemented

---

## Phase 8: Audit Service Implementation

**Purpose**: Log all task operations to audit_log table for compliance and debugging

- [ ] T088 Create Audit Service main file in services/audit-service/audit_service.py
- [ ] T089 Implement Dapr Pub/Sub subscription to task-events topic in services/audit-service/audit_service.py
- [ ] T090 Implement event handler for all event types in services/audit-service/audit_service.py (task.created, task.updated, task.completed, task.deleted, include recurrence_id in deletion events for recurring task tracking)
- [ ] T091 Write audit log entries to audit_log table in services/audit-service/audit_service.py
- [ ] T092 Add error handling for audit failures in services/audit-service/audit_service.py (log but don't block main flow)
- [ ] T093 Create integration test for audit logging in backend/tests/integration/test_audit_logging.py

---

## Phase 9: WebSocket Service Implementation

**Purpose**: Enable real-time task updates across multiple browser tabs/devices

- [ ] T094 Create WebSocket Service main file in services/websocket-service/websocket_service.py
- [ ] T095 Implement WebSocket connection manager in services/websocket-service/websocket_service.py (user_id → connections mapping)
- [ ] T096 Implement WebSocket endpoint /ws/{user_id} in services/websocket-service/websocket_service.py
- [ ] T097 Add JWT authentication for WebSocket connections in services/websocket-service/websocket_service.py
- [ ] T098 Implement Dapr Pub/Sub subscription to task-updates topic in services/websocket-service/websocket_service.py
- [ ] T099 Implement broadcast logic in services/websocket-service/websocket_service.py (user-isolated broadcasting)
- [ ] T100 Add connection lifecycle management in services/websocket-service/websocket_service.py (connect, disconnect, reconnect)
- [ ] T101 [P] Create WebSocket client component in frontend/components/LiveTaskUpdates.tsx
- [ ] T102 [P] Create WebSocket connection manager in frontend/lib/websocket.ts (auto-reconnect with exponential backoff)
- [ ] T103 Integrate WebSocket updates in frontend/app/(dashboard)/chat/page.tsx
- [ ] T104 Create integration test for WebSocket broadcasting in backend/tests/integration/test_websocket_updates.py

---

## Phase 10: Helm Charts and Deployment

**Purpose**: Create Kubernetes deployment configurations for all services

### Backend API Helm Chart

- [ ] T105 Create backend-api Helm chart structure in infrastructure/helm/backend-api/ (Chart.yaml, values.yaml, templates/)
- [ ] T106 Create backend-api deployment template in infrastructure/helm/backend-api/templates/deployment.yaml (with Dapr sidecar annotations)
- [ ] T107 Create backend-api service template in infrastructure/helm/backend-api/templates/service.yaml (NodePort 30081)
- [ ] T108 Create backend-api configmap template in infrastructure/helm/backend-api/templates/configmap.yaml
- [ ] T109 [P] Create values-local.yaml overrides in infrastructure/helm/backend-api/values-local.yaml
- [ ] T110 [P] Create values-cloud.yaml overrides in infrastructure/helm/backend-api/values-cloud.yaml

### Microservices Helm Charts

- [ ] T111 [P] Create notification-service Helm chart in infrastructure/helm/notification-service/ (Chart.yaml, values.yaml, templates/)
- [ ] T112 [P] Create recurring-task-service Helm chart in infrastructure/helm/recurring-task-service/ (Chart.yaml, values.yaml, templates/)
- [ ] T113 [P] Create audit-service Helm chart in infrastructure/helm/audit-service/ (Chart.yaml, values.yaml, templates/)
- [ ] T114 [P] Create websocket-service Helm chart in infrastructure/helm/websocket-service/ (Chart.yaml, values.yaml, templates/)

### Frontend Helm Chart

- [ ] T115 Create frontend Helm chart structure in infrastructure/helm/frontend/ (Chart.yaml, values.yaml, templates/)
- [ ] T116 Create frontend deployment template in infrastructure/helm/frontend/templates/deployment.yaml (no Dapr sidecar)
- [ ] T117 Create frontend service template in infrastructure/helm/frontend/templates/service.yaml (NodePort 30080)
- [ ] T118 [P] Create values-local.yaml overrides in infrastructure/helm/frontend/values-local.yaml
- [ ] T119 [P] Create values-cloud.yaml overrides in infrastructure/helm/frontend/values-cloud.yaml

### Deployment Scripts

- [ ] T120 Create deploy-local.sh script in infrastructure/scripts/deploy-local.sh (deploy to Minikube with Redpanda Docker)
- [ ] T121 Create deploy-cloud.sh script in infrastructure/scripts/deploy-cloud.sh (deploy to OKE with Redpanda Cloud)
- [ ] T122 Create setup-redpanda-docker.sh script in infrastructure/scripts/setup-redpanda-docker.sh (start local Redpanda container)
- [ ] T123 Create teardown.sh script in infrastructure/scripts/teardown.sh (cleanup all resources)

---

## Phase 11: CI/CD Pipeline

**Purpose**: Automate build, test, and deployment workflows

- [ ] T124 [P] Create ci.yml workflow in .github/workflows/ci.yml (build and test all services on PR)
- [ ] T125 [P] Create deploy-oke.yml workflow in .github/workflows/deploy-oke.yml (deploy to Oracle OKE on main branch merge)
- [ ] T126 [P] Create contract-tests.yml workflow in .github/workflows/contract-tests.yml (validate event schemas)
- [ ] T127 Add Docker image build steps to ci.yml (build all 6 service images)
- [ ] T128 Add test execution steps to ci.yml (run pytest, contract tests, integration tests)
- [ ] T129 Add Oracle OKE deployment steps to deploy-oke.yml (helm upgrade with cloud values)
- [ ] T130 Configure GitHub Secrets for OKE deployment (KUBECONFIG, DATABASE_URL, OPENAI_API_KEY, BETTER_AUTH_SECRET)

---

## Phase 12: End-to-End Testing

**Purpose**: Validate complete user workflows across all microservices

- [ ] T131 Create end-to-end test for recurring task workflow in backend/tests/e2e/test_recurring_task_e2e.py (create → complete → verify next instance)
- [ ] T132 Create end-to-end test for reminder workflow in backend/tests/e2e/test_reminder_e2e.py (create → schedule → deliver → verify status)
- [ ] T133 Create end-to-end test for search and filter workflow in backend/tests/e2e/test_search_filter_e2e.py (create multiple → search → filter → verify results)
- [ ] T134 Create end-to-end test for WebSocket updates in backend/tests/e2e/test_websocket_e2e.py (create task → verify broadcast → verify UI update)
- [ ] T135 Create end-to-end test for audit trail in backend/tests/e2e/test_audit_e2e.py (perform operations → verify all logged)
- [ ] T135b Create end-to-end test for Redpanda outage recovery in backend/tests/e2e/test_redpanda_resilience_e2e.py (create task during outage → verify event published when streaming restored)

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [ ] T136 [P] Update CLAUDE.md with Phase V architecture, development commands, and multi-server setup
- [ ] T137 [P] Update README.md with Phase V overview, architecture diagram, and deployment instructions
- [ ] T138 [P] Update CONSTITUTION.md compliance section with Phase V validation
- [ ] T139 Add health probes (liveness, readiness) to all service deployments in infrastructure/helm/*/templates/deployment.yaml
- [ ] T140 Add Prometheus metrics endpoints to all services (backend, notification, recurring-task, audit, websocket)
- [ ] T141 Add structured JSON logging to all services (with correlation IDs for distributed tracing)
- [ ] T142 Implement rate limiting for WebSocket connections in services/websocket-service/websocket_service.py (max 3 per user)
- [ ] T143 Add event schema versioning documentation in specs/005-event-driven-microservices/contracts/README.md
- [ ] T144 Optimize database queries with query analysis in backend/services/search_service.py (EXPLAIN ANALYZE)
- [ ] T145 Add security hardening (validate all user_id matches JWT, sanitize tags input, prevent SQL injection)
- [ ] T146 Run quickstart.md validation (follow all steps, verify end-to-end validation checklist passes)
- [ ] T147 Perform load testing (100 concurrent users, verify <2s event latency, verify reminder ±30s accuracy)
- [ ] T148 Create architecture decision record (ADR) for database-first event pattern in specs/005-event-driven-microservices/adr/001-database-first-events.md
- [ ] T149 Create architecture decision record (ADR) for Dapr Jobs over cron in specs/005-event-driven-microservices/adr/002-dapr-jobs-api.md
- [ ] T150 Create Prompt History Record (PHR) for Phase V implementation in history/prompts/005-event-driven-microservices/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User Story 1 (Recurring Tasks): Can start after Foundational - No dependencies on other stories
  - User Story 2 (Due Dates/Reminders): Can start after Foundational - No dependencies on other stories
  - User Story 3 (Search/Filter): Can start after Foundational - No dependencies on other stories
  - User Story 4 (Priorities): Can start after Foundational - No dependencies on other stories
  - User Story 5 (Tags): Can start after Foundational - No dependencies on other stories
- **Audit Service (Phase 8)**: Depends on Foundational phase (event publishing infrastructure)
- **WebSocket Service (Phase 9)**: Depends on Foundational phase (event publishing infrastructure)
- **Helm Charts (Phase 10)**: Depends on User Story 1 minimum (MVP deployment)
- **CI/CD (Phase 11)**: Depends on Helm Charts completion
- **E2E Testing (Phase 12)**: Depends on all user stories being implemented
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

All user stories are INDEPENDENT after Foundational phase completion:
- **User Story 1 (P1)**: No dependencies on other stories
- **User Story 2 (P2)**: No dependencies on other stories (can work with or without US1)
- **User Story 3 (P3)**: No dependencies on other stories (searches all tasks regardless of recurrence/reminders)
- **User Story 4 (P4)**: No dependencies on other stories (priority is independent attribute)
- **User Story 5 (P5)**: No dependencies on other stories (tags are independent attributes)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before MCP tools
- MCP tools before microservice consumers
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase**:
- T003, T004, T005, T006 can run in parallel (different directories/files)

**Foundational Phase**:
- T012, T013, T014, T015 (models) can run in parallel
- T016, T017, T018 (event schemas) can run in parallel
- T019-T022 (local Dapr components) can run in parallel
- T023-T026 (cloud Dapr components) can run in parallel
- T031, T032, T033 (contract tests) can run in parallel

**User Story 1**:
- T034, T035, T036 (tests) can run in parallel
- T037, T038 (MCP tool extensions) can run in parallel

**User Story 2**:
- T047, T048, T049 (tests) can run in parallel
- T050, T051 (MCP tool extensions) can run in parallel

**User Story 3**:
- T061, T062, T063 (tests) can run in parallel
- T064, T065 (MCP tools) can run in parallel

**User Story 4**:
- T071, T072 (tests) can run in parallel
- T073, T074 (MCP tool extensions) can run in parallel

**User Story 5**:
- T079, T080 (tests) can run in parallel
- T081, T082 (MCP tool extensions) can run in parallel

**WebSocket Phase**:
- T101, T102 (frontend components) can run in parallel

**Helm Charts**:
- T109, T110 (backend values) can run in parallel
- T111, T112, T113, T114 (microservices charts) can run in parallel
- T118, T119 (frontend values) can run in parallel

**CI/CD**:
- T124, T125, T126 (workflows) can run in parallel

**Polish**:
- T136, T137, T138 (documentation) can run in parallel

**Entire User Stories**:
- Once Foundational phase completes, ALL user stories (Phase 3-7) can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Integration test for recurring task creation in backend/tests/integration/test_recurring_task_creation.py"
Task: "Integration test for recurring task generation in backend/tests/integration/test_recurring_task_generation.py"
Task: "Unit test for recurrence pattern calculation in backend/tests/unit/test_recurrence_logic.py"

# After tests written, extend MCP tools in parallel:
Task: "Extend MCP tool add_task in backend/tools/server.py to accept recurrence parameters (pattern, interval)"
Task: "Extend MCP tool update_task in backend/tools/server.py to support updating recurrence rules"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T033) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T034-T046)
4. Complete Phase 8: Audit Service (T088-T093) - for logging recurring task events
5. Complete Phase 10: Minimal Helm Charts (T105-T113) - deploy backend + recurring-task-service
6. **STOP and VALIDATE**: Test User Story 1 independently using quickstart.md test scenario 1
7. Deploy/demo if ready

**Estimated Tasks for MVP**: 60 tasks (Setup + Foundational + US1 + Audit + Minimal Helm)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T033)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!) (T034-T046, T088-T093, T105-T113)
3. Add User Story 2 → Test independently → Deploy (T047-T060, T120-T123 for reminder service)
4. Add User Story 3 → Test independently → Deploy (T061-T070)
5. Add User Story 4 → Test independently → Deploy (T071-T078)
6. Add User Story 5 → Test independently → Deploy (T079-T087)
7. Add WebSocket Service → Test independently → Deploy (T094-T104)
8. Complete CI/CD + E2E Testing → Production ready (T124-T135)
9. Polish and documentation → Release (T136-T150)

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T033)
2. Once Foundational is done:
   - Developer A: User Story 1 (Recurring Tasks) - T034-T046
   - Developer B: User Story 2 (Due Dates/Reminders) - T047-T060
   - Developer C: User Story 3 (Search/Filter) - T061-T070
   - Developer D: Audit Service + WebSocket Service - T088-T104
   - Developer E: Helm Charts + Deployment - T105-T123
3. Stories complete and integrate independently
4. Team completes E2E Testing together (T131-T135)
5. Team completes Polish together (T136-T150)

---

## Task Count Summary

- **Phase 1 (Setup)**: 6 tasks
- **Phase 2 (Foundational)**: 27 tasks ⚠️ BLOCKING
- **Phase 3 (User Story 1 - Recurring Tasks)**: 13 tasks
- **Phase 4 (User Story 2 - Due Dates/Reminders)**: 15 tasks (includes T053b for NLP date parsing)
- **Phase 5 (User Story 3 - Search/Filter)**: 10 tasks
- **Phase 6 (User Story 4 - Priorities)**: 8 tasks
- **Phase 7 (User Story 5 - Tags)**: 9 tasks
- **Phase 8 (Audit Service)**: 6 tasks
- **Phase 9 (WebSocket Service)**: 11 tasks
- **Phase 10 (Helm Charts)**: 19 tasks
- **Phase 11 (CI/CD)**: 7 tasks
- **Phase 12 (E2E Testing)**: 6 tasks (includes T135b for Redpanda resilience)
- **Phase 13 (Polish)**: 15 tasks

**Total Tasks**: 152

**Parallel Opportunities**: 40+ tasks can run in parallel (marked with [P])

**Independent Test Criteria**:
- User Story 1: Create recurring task → complete → verify next instance created
- User Story 2: Create task with reminder → verify scheduled → verify delivered
- User Story 3: Create 10 tasks → search "urgent" → verify correct subset returned
- User Story 4: Create tasks with mixed priorities → sort by priority → verify order
- User Story 5: Create tasks with tags → filter by tag → verify correct subset returned

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) + Phase 8 (Audit) + Minimal Phase 10 (Helm) = ~60 tasks

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution Principle V requires TDD - write tests first
- Constitution Principle X requires event-driven architecture - all state changes publish events
- Constitution Principle XI requires Dapr abstraction - application code unchanged between local/cloud
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

**Status**: ✅ COMPLETE (Updated with all remediation fixes)
**Generated**: 2026-01-06
**Last Updated**: 2026-01-06 (Added T053b for NLP dates, T135b for resilience testing, updated T012 for updated_at logic, added T030 dependency note)
**Total Tasks**: 152
**MVP Tasks**: 61 (Setup + Foundational + US1 including T053b + Audit + Minimal Deployment)
**Fixes Applied**: All CRITICAL and HIGH issues resolved, all MEDIUM issues resolved, bonus LOW issues addressed
