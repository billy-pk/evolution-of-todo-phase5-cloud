---
id: 0003
title: phase5-complete-plan-and-design-artifacts
stage: plan
date: 2026-01-06
surface: claude-code-cli
model: claude-sonnet-4.5
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.plan
labels: [plan, phase5, microservices, dapr, redpanda, event-driven, design, contracts, research, data-model, quickstart]
links:
  spec: specs/005-event-driven-microservices/spec.md
  plan: specs/005-event-driven-microservices/plan.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  - path: specs/005-event-driven-microservices/plan.md
    role: implementation plan with architecture strategy
    lines: 316
  - path: specs/005-event-driven-microservices/research.md
    role: architectural decisions for 6 research topics
    lines: 650+
  - path: specs/005-event-driven-microservices/data-model.md
    role: extended database schema with migrations
    lines: 750+
  - path: specs/005-event-driven-microservices/quickstart.md
    role: local development setup guide
    lines: 550+
  - path: specs/005-event-driven-microservices/contracts/README.md
    role: contract versioning and deployment guide
    lines: 400+
  - path: specs/005-event-driven-microservices/contracts/events/task-events.schema.json
    role: JSON Schema for task CRUD events v1.0.0
    lines: 140+
  - path: specs/005-event-driven-microservices/contracts/events/reminders.schema.json
    role: JSON Schema for reminder lifecycle events v1.0.0
    lines: 140+
  - path: specs/005-event-driven-microservices/contracts/events/task-updates.schema.json
    role: JSON Schema for WebSocket UI updates v1.0.0
    lines: 120+
  - path: specs/005-event-driven-microservices/contracts/dapr-components/local/pubsub-redpanda.yaml
    role: Dapr Pub/Sub component for local Redpanda Docker
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/local/statestore-postgresql.yaml
    role: Dapr State Store component for PostgreSQL
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/local/jobs.yaml
    role: Dapr Jobs API component for reminders
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/local/secrets.yaml
    role: Kubernetes Secrets component for local
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/cloud/pubsub-redpanda-cloud.yaml
    role: Dapr Pub/Sub component for Redpanda Cloud (SASL/SSL)
    lines: 30
  - path: specs/005-event-driven-microservices/contracts/dapr-components/cloud/statestore-postgresql.yaml
    role: Dapr State Store component for cloud PostgreSQL
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/cloud/jobs.yaml
    role: Dapr Jobs API component for cloud
    lines: 20
  - path: specs/005-event-driven-microservices/contracts/dapr-components/cloud/secrets.yaml
    role: Kubernetes Secrets component for cloud (OKE)
    lines: 40
tests:
  - N/A (design phase, contract tests defined in data-model.md)
---

## Prompt

**User Command**: `/sp.plan` followed by user request to "generate phase 0" and "generate phase 1 artifacts"

**Context**: Generate comprehensive implementation plan and design artifacts for Phase V Event-Driven Microservices Architecture.

**Initial Request**: User ran `/sp.plan` command to generate the implementation plan. Plan agent was invoked but the generated plan was not saved to plan.md (only 104 lines of template remained). User then requested to locate the existing plan, discovered it was not properly saved, and requested regeneration.

**Subsequent Requests**:
1. "generate phase 0" - Generate research.md with architectural decisions
2. "generate phase 1 artifacts" - Generate data-model.md, contracts/ (event schemas + Dapr components), quickstart.md

**Feature Requirements** (from spec.md):
- 5 user stories (P1: Recurring tasks, P2: Due dates/reminders, P3: Search/filter, P4: Priorities, P5: Tags)
- 40 functional requirements covering event-driven architecture, microservices, Dapr, Redpanda
- 6 microservices: Backend API, Notification Service, Recurring Task Service, Audit Service, WebSocket Service, Frontend
- Database-first pattern (write to PostgreSQL, then publish events)
- Event topics: task-events, reminders, task-updates
- Local (Minikube + Redpanda Docker) and cloud (OKE + Redpanda Cloud) deployment

## Response snapshot

**Phase 0: Research (research.md)**

Generated comprehensive architectural decisions for 6 research topics:

1. **Dapr Pub/Sub Configuration**
   - Decision: Separate YAML files for local (Redpanda Docker, no auth) vs cloud (Redpanda Cloud, SASL/SSL)
   - Rationale: Application code 100% identical between environments; only YAML changes
   - Alternative rejected: Single YAML with environment variables (adds complexity)

2. **Event Schema Design**
   - Decision: JSON Schema with semantic versioning (MAJOR.MINOR.PATCH)
   - Envelope format: event_type, event_id, task_id, user_id, task_data, timestamp, schema_version
   - Compatibility: Consumers handle MINOR versions, reject unknown MAJOR versions
   - Alternative rejected: Protocol Buffers (adds complexity, harder to debug)

3. **Idempotency Strategy**
   - Decision: Database state reconciliation (no separate idempotency table)
   - Pattern: Check database state before taking action (e.g., next recurring task already exists → skip)
   - Rationale: Aligns with Constitution Principle IV (Single Source of Truth)
   - Alternative rejected: Idempotency table with event_id (extra table to manage)

4. **Reminder Scheduling**
   - Decision: Dapr Jobs API with PostgreSQL backend
   - Rationale: Persistent across restarts, dynamic scheduling, ±5s accuracy
   - Alternative rejected: Cron binding (static schedules only, can't create reminders at runtime)

5. **WebSocket Architecture**
   - Decision: Dedicated WebSocket Service subscribing to task-updates topic
   - Components: Connection manager (user_id → [WebSocket connections]), broadcast by user isolation
   - Security: JWT validation, user-based filtering, rate limiting
   - Alternative rejected: Backend API manages WebSockets (violates stateless design)

6. **Database Migration Strategy**
   - Decision: Alembic with nullable columns for zero-downtime deployment
   - Migrations: Add columns to tasks table (priority, tags, due_date, recurrence_id), create new tables (recurrence_rules, reminders, audit_log)
   - Backward compatibility: All new columns nullable or have defaults
   - Alternative rejected: Manual SQL scripts (no version tracking, error-prone)

**Phase 1: Design Artifacts**

1. **data-model.md** (750+ lines):
   - Extended tasks table with 4 new columns
   - 3 new tables: recurrence_rules, reminders, audit_log
   - SQLModel definitions with complete examples
   - Migration strategy with Alembic DDL
   - 15 indexes for query optimization
   - Query patterns and performance considerations
   - Test data seed script

2. **contracts/events/** (3 JSON Schema files):
   - **task-events.schema.json**: Task CRUD events (v1.0.0) with event types: task.created, task.updated, task.completed, task.deleted
   - **reminders.schema.json**: Reminder lifecycle events (v1.0.0) with event types: reminder.scheduled, reminder.triggered, reminder.delivered, reminder.failed
   - **task-updates.schema.json**: WebSocket UI updates (v1.0.0) with update types: task_created, task_updated, task_completed, task_deleted, task_recurring_generated
   - All schemas include semantic versioning, examples, and validation rules

3. **contracts/dapr-components/** (8 YAML files):
   - **Local components** (4 files): pubsub-redpanda.yaml, statestore-postgresql.yaml, jobs.yaml, secrets.yaml
   - **Cloud components** (4 files): pubsub-redpanda-cloud.yaml (SASL/SSL secured), statestore-postgresql.yaml, jobs.yaml, secrets.yaml
   - Environment parity: Application code unchanged, only YAML differs
   - Complete with comments explaining configuration differences

4. **contracts/README.md** (400+ lines):
   - Schema versioning strategy and compatibility rules
   - Event topic descriptions and producers/consumers
   - Dapr component deployment instructions (local vs cloud)
   - Contract testing examples with pytest + jsonschema
   - Monitoring and observability metrics
   - Troubleshooting guide for common issues

5. **quickstart.md** (550+ lines):
   - 8-step local development setup (Minikube, Dapr, Redpanda Docker, secrets, migrations)
   - 5 comprehensive test scenarios:
     * Test 1: Create recurring task → mark complete → verify next instance generated
     * Test 2: Due date reminders → verify scheduled and delivered
     * Test 3: Search and filter by priority/tags
     * Test 4: Live WebSocket updates across browser tabs
     * Test 5: Audit trail verification
   - 12-point end-to-end validation checklist
   - Monitoring and debugging commands (kubectl logs, dapr dashboard)
   - Troubleshooting guide (pods not starting, events not flowing, reminders not triggering, WebSocket not connecting)
   - Cleanup instructions
   - Estimated setup time: 30-45 minutes

**Implementation Plan (plan.md)**

Regenerated complete 316-line implementation plan with:

- **Summary**: Phase V transformation from monolith to event-driven microservices
- **Technical Context**: Python 3.13, FastAPI, Dapr 1.14+, Redpanda, Kubernetes, Helm, Next.js 16
- **Constitution Check**: All 12 principles validated (9 existing + 3 new: Event-Driven Architecture, Cloud Portability, Observability)
- **Project Structure**: Monorepo with backend/, services/ (4 new microservices), infrastructure/, contracts/
- **Phase 0**: 6 research topics (Dapr Pub/Sub, event schemas, idempotency, reminders, WebSocket, migrations)
- **Phase 1**: Design artifacts (data-model.md, contracts/, quickstart.md)
- **Critical Next Steps**: Generate research.md → Generate Phase 1 artifacts → Run /sp.tasks

## Outcome

- ✅ **Impact**: Complete architectural blueprint for Phase V event-driven microservices transformation. Generated 16 files (3,000+ lines) covering implementation plan, research decisions, data model, event schemas, Dapr configurations, and local development setup. All artifacts align with Constitution v4.0.0 (Event-Driven Architecture, Cloud Portability, Observability principles).

- 🧪 **Tests**: Contract tests defined in data-model.md and contracts/README.md. Test scenarios documented in quickstart.md (5 end-to-end scenarios covering recurring tasks, reminders, search/filter, WebSocket, audit trail). Contract test examples use pytest + jsonschema validation.

- 📁 **Files**: 16 files generated across 4 categories:
  1. Core documentation (4 files): plan.md, research.md, data-model.md, quickstart.md
  2. Event schemas (3 JSON Schema files): task-events, reminders, task-updates
  3. Dapr components (8 YAML files): local (4) + cloud (4) configurations for Pub/Sub, State Store, Jobs, Secrets
  4. Contracts documentation (1 file): contracts/README.md with versioning strategy and deployment guide

- 🔁 **Next prompts**:
  1. Run `/sp.tasks` to generate actionable task breakdown (Phase 2)
  2. Implement Phase 0 research decisions (prototype Dapr Pub/Sub locally, validate Redpanda Docker setup)
  3. Implement Phase 1 design artifacts (extend database schema, create MCP tool parameters, implement event publisher service)
  4. Update CLAUDE.md with Phase 5 event-driven patterns and architecture guidance

- 🧠 **Reflection**: Successfully generated comprehensive planning and design artifacts after plan.md regeneration was needed. The plan agent's output from the initial run was not persisted to file, requiring manual regeneration. Phase 0 research documented all architectural decisions with rationale and alternatives considered. Phase 1 artifacts provide complete technical specifications for implementation. The database-first event pattern (write to PostgreSQL, then publish events) preserves single source of truth while enabling event-driven capabilities. Dapr abstraction ensures cloud portability (local Minikube ↔ OKE with only YAML changes). Event schemas use JSON Schema with semantic versioning for backward compatibility. Local development setup is well-documented with 8 steps and 5 test scenarios, estimated at 30-45 minutes for first-time setup.

## Evaluation notes (flywheel)

- **Failure modes observed**: Plan agent output not persisted to plan.md in initial run (only 104 lines of template remained). Root cause: plan.md was overwritten with template instead of preserving Plan agent's generated content. Workaround: Manually regenerated plan.md by writing the comprehensive plan based on Plan agent's design recommendations. Phase 0 and Phase 1 artifacts generated successfully using Write tool.

- **Graders run and results (PASS/FAIL)**:
  - Constitution Check: PASS (12/12 principles compliant - 9 existing + 3 new Phase 5 principles)
  - Spec Coverage: PASS (all 5 user stories covered, 40 functional requirements addressed)
  - Design Completeness: PASS (data model, event schemas, Dapr components, quickstart guide all complete)
  - Environment Parity: PASS (local and cloud configurations with identical application code)
  - Backward Compatibility: PASS (nullable columns, existing Phase 3/4 tasks continue working)

- **Prompt variant (if applicable)**: Used Task tool with Plan subagent for initial planning attempt. After plan.md persistence failure, switched to direct file generation with Write tool for plan.md, research.md, data-model.md, quickstart.md, and all contract files.

- **Next experiment (smallest change to try)**:
  1. Test Plan agent's file persistence mechanism to understand why plan.md was not saved correctly in initial run
  2. Generate tasks.md using `/sp.tasks` command to create dependency-ordered implementation breakdown
  3. Prototype Dapr Pub/Sub locally with Redpanda Docker to validate event flow
  4. Implement database migrations using Alembic to extend tasks table and create new tables
  5. Create contract tests for event schemas using pytest + jsonschema validation
