# Implementation Plan: Phase V Event-Driven Microservices Architecture

**Branch**: `005-event-driven-microservices` | **Date**: 2026-01-06 | **Spec**: `/specs/005-event-driven-microservices/spec.md`

## Summary

Phase V transforms the existing Phase 3/4 monolithic conversational AI todo application into an event-driven microservices architecture using Dapr, Redpanda, and Kubernetes. The implementation adds advanced task management features (recurring tasks, due dates, reminders, priorities, tags, search/filter) while maintaining the conversational interface as the primary interaction model. The system will be deployed on Oracle Kubernetes Engine (OKE) with Redpanda Cloud for production event streaming, while supporting identical local development on Minikube with Redpanda Docker.

**Core Technical Approach**:
- **Database-First Pattern**: Write all state changes to PostgreSQL first, then publish events (ensures consistency even if event delivery fails)
- **Dapr Abstraction**: Application code remains unchanged between local and cloud deployments; only Dapr component YAML files change
- **Six Microservices**: Backend API (with MCP), Notification Service, Recurring Task Service, Audit Service, WebSocket Service, Frontend
- **Event Topics**: `task-events` (CRUD operations), `reminders` (scheduled notifications), `task-updates` (real-time UI sync)
- **Shared Database**: All microservices query the same Neon PostgreSQL database (single source of truth)

## Technical Context

**Language/Version**: Python 3.13 (backend services), TypeScript/Node.js 18+ (frontend)
**Primary Dependencies**:
- Backend: FastAPI 0.125+, SQLModel 0.0.27, OpenAI Agents SDK 0.6.4+, MCP 1.25+, Dapr Python SDK 1.14+
- Frontend: Next.js 16+, React 19+, Better Auth (EdDSA JWT), OpenAI ChatKit 1.4.1+
- Infrastructure: Dapr 1.14+, Redpanda (Kafka-compatible), Kubernetes 1.28+, Helm 3.x

**Storage**: Neon PostgreSQL (serverless, managed) - extended schema with recurring tasks, reminders, audit logs
**Event Streaming**: Redpanda Docker (local), Redpanda Cloud (production) accessed via Dapr Pub/Sub
**Testing**: pytest (backend unit/integration), Jest (frontend), contract tests (event schemas), end-to-end (full workflow)
**Target Platform**:
- Local: Minikube (Kubernetes 1.28+) + Redpanda Docker (single-node, no auth)
- Cloud: Oracle Kubernetes Engine (OKE) + Redpanda Cloud (SASL/SSL secured)

**Project Type**: Web application (monorepo) with microservices architecture
**Performance Goals**:
- Event delivery latency: <2 seconds end-to-end (write to consumer processing)
- Reminder accuracy: ±30 seconds of scheduled time
- Search/filter response: <2 seconds for 1000 tasks
- Concurrent users: 100+ without degradation

**Constraints**:
- Zero hardcoded secrets in code or container images
- Stateless microservices (horizontal scaling without sticky sessions)
- Database-first consistency (events are notifications, not source of truth)
- Cloud-agnostic code (vendor-specific configs only in Dapr YAML)
- Backwards compatibility: existing chat functionality must remain intact

**Scale/Scope**:
- 6 microservices (Backend API, Notification, Recurring Task, Audit, WebSocket, Frontend)
- 3 event topics with versioned JSON schemas
- 4 new database tables (recurrence_rules, reminders, audit_log, + extended tasks table)
- Local + Cloud deployment configurations (environment parity)

## Constitution Check

*Constitution v4.0.0 compliance validation (GATE: Must pass before Phase 0 research)*

### Principle Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Conversational Interface Primary** | ✅ PASS | All task operations remain accessible via chat. Advanced features (recurring, reminders, priorities, tags) integrate as MCP tool parameters |
| **II. Stateless Server Design** | ✅ PASS | All 6 microservices are stateless. State stored in PostgreSQL + Dapr State Store. Pods are horizontally scalable. Event-driven async communication via Dapr Pub/Sub |
| **III. Security First** | ✅ PASS | JWT auth enforced on all API requests. User isolation in database + events (user_id in payload). Secrets via Dapr Secret Store (cloud) or K8s Secrets (local). No hardcoded credentials |
| **IV. Single Source of Truth** | ✅ PASS | All data in single Neon PostgreSQL database. Database-first write pattern ensures consistency. Events are notifications, not source of truth |
| **V. Test-Driven Development** | ✅ PASS | Tests required before implementation: unit tests, integration tests, contract tests (event schemas), end-to-end tests (recurring task flow, reminder delivery) |
| **VI. Extensibility and Modularity** | ✅ PASS | Microservices architecture with clear service boundaries. Event schemas versioned. Async communication via Dapr Pub/Sub. Each service has own Dockerfile + Helm chart |
| **VII. Infrastructure as Code** | ✅ PASS | All configs version-controlled: Dockerfiles, Helm charts, Dapr component YAMLs (local + cloud). Deployments via `helm install`. No manual `kubectl` for production |
| **VIII. AI-Assisted DevOps** | ⚠️ OPTIONAL | Recommended for Dockerfile optimization (Gordon), Kubernetes troubleshooting (kubectl-ai, kagent). Not mandatory for Phase V |
| **IX. Local-First Cloud Development** | ✅ PASS | Minikube + Redpanda Docker for local development. Identical feature parity with OKE + Redpanda Cloud. Application code unchanged between environments |
| **X. Event-Driven Architecture** | ✅ PASS | Core requirement. Database-first persistence → publish events. Idempotent consumers. Versioned JSON schemas. Topics: task-events, reminders, task-updates |
| **XI. Cloud Portability via Dapr** | ✅ PASS | Core requirement. Application code calls Dapr APIs only (no vendor SDKs). Environment switching via Dapr component YAML changes only |
| **XII. Observability** | ⚠️ RECOMMENDED | Structured JSON logging, Prometheus metrics, health probes (liveness/readiness) required. Distributed tracing optional but recommended |

### Architectural Decisions Alignment

**Event-Driven Communication**:
- All task state changes publish events to Redpanda via Dapr Pub/Sub
- Database writes occur first, then events published (reliability over latency)
- Consumers are idempotent and handle out-of-order events

**Microservices Decomposition**:
- Backend API: Existing FastAPI + MCP server + event publishing (extended with Dapr)
- Notification Service: Subscribes to `reminders` topic, delivers notifications
- Recurring Task Service: Subscribes to `task-events` topic (task.completed), generates next instance
- Audit Service: Subscribes to `task-events` topic, logs all operations to audit_log table
- WebSocket Service: Subscribes to `task-updates` topic, broadcasts to connected clients
- Frontend: Existing Next.js app (no changes, consumes backend API)

**Dapr Building Blocks**:
- **Pub/Sub**: Redpanda (local Docker or Cloud)
- **State Store**: PostgreSQL (Neon) for application state
- **Jobs API**: Scheduled reminders (Dapr Jobs preferred over cron)
- **Secrets**: Kubernetes Secrets (local) or cloud provider secrets (OKE)
- **Service Invocation**: Inter-service synchronous calls (optional, prefer async events)

### Gates Passed
- ✅ No new governance violations introduced
- ✅ Event-driven architecture aligns with Constitution v4.0.0 Principle X
- ✅ Dapr abstraction aligns with Principle XI (cloud portability)
- ✅ Microservices maintain stateless design (Principle II)
- ✅ Single PostgreSQL database maintained (Principle IV)
- ✅ Infrastructure as Code enforced (Principle VII)

## Project Structure

### Documentation (this feature)

```text
specs/005-event-driven-microservices/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0: Dapr, Redpanda, event schemas, idempotency, reminder scheduling
├── data-model.md        # Phase 1: Extended database schema (tasks, recurrence_rules, reminders, audit_log)
├── quickstart.md        # Phase 1: Local development setup, test scenarios, validation steps
├── contracts/           # Phase 1: Event schemas and Dapr configurations
│   ├── events/
│   │   ├── task-events.schema.json       # JSON Schema for task-events topic
│   │   ├── reminders.schema.json          # JSON Schema for reminders topic
│   │   └── task-updates.schema.json       # JSON Schema for task-updates topic
│   ├── dapr-components/
│   │   ├── local/
│   │   │   ├── pubsub-redpanda.yaml       # Redpanda Docker (no auth)
│   │   │   ├── statestore-postgresql.yaml # PostgreSQL State Store
│   │   │   ├── jobs.yaml                  # Dapr Jobs API
│   │   │   └── secrets.yaml               # Kubernetes Secrets
│   │   └── cloud/
│   │       ├── pubsub-redpanda-cloud.yaml # Redpanda Cloud (SASL/SSL)
│   │       ├── statestore-postgresql.yaml # Same PostgreSQL (cloud credentials)
│   │       ├── jobs.yaml                  # Dapr Jobs API
│   │       └── secrets.yaml               # Cloud provider secrets
│   └── README.md        # Contract versioning and compatibility guide
└── tasks.md             # Phase 2: Actionable task list (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
evolution-of-todo/phase5-cloud/
├── backend/                          # Backend API + MCP Server (existing, extended)
│   ├── main.py                       # FastAPI app (add Dapr Pub/Sub client)
│   ├── routes/
│   │   ├── chat.py                   # Chat endpoint (extended with event publishing)
│   │   └── chatkit.py                # ChatKit integration (no changes)
│   ├── services/
│   │   ├── agent.py                  # OpenAI Agent (no changes)
│   │   └── event_publisher.py        # NEW: Dapr Pub/Sub event publishing service
│   ├── tools/
│   │   └── server.py                 # MCP server (extended with new parameters: priority, tags, due_date, recurrence)
│   ├── models.py                     # SQLModel models (extend Task, add RecurrenceRule, Reminder, AuditLog)
│   ├── schemas.py                    # Pydantic schemas (add event payloads)
│   ├── db.py                         # Database engine (no changes)
│   ├── middleware.py                 # JWT auth (no changes)
│   ├── migrations/                   # NEW: Alembic migrations for schema changes
│   │   └── 001_add_advanced_features.py
│   ├── Dockerfile                    # NEW: Multi-stage build for Backend API
│   ├── requirements.txt              # Extended with dapr, dapr-ext-grpc
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/                 # NEW: Event schema validation tests
│
├── services/                         # NEW: Microservices directory
│   ├── notification-service/
│   │   ├── notification_service.py   # Subscribes to reminders topic
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── recurring-task-service/
│   │   ├── recurring_task_service.py # Subscribes to task-events topic (task.completed)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── audit-service/
│   │   ├── audit_service.py          # Subscribes to task-events topic (all events)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   └── websocket-service/
│       ├── websocket_service.py      # FastAPI WebSocket + subscribes to task-updates topic
│       ├── Dockerfile
│       ├── requirements.txt
│       └── tests/
│
├── frontend/                         # Next.js frontend (existing, minimal changes)
│   ├── app/
│   │   ├── (auth)/                   # Auth pages (no changes)
│   │   ├── (dashboard)/
│   │   │   ├── chat/                 # Chat interface (extend with WebSocket for live updates)
│   │   │   └── tasks/                # Task list view (optional, for testing)
│   │   └── api/auth/                 # Better Auth (no changes)
│   ├── components/
│   │   ├── Navbar.tsx                # No changes
│   │   └── LiveTaskUpdates.tsx       # NEW: WebSocket client component
│   ├── lib/
│   │   ├── api.ts                    # API client (no changes)
│   │   ├── auth.ts                   # Auth config (no changes)
│   │   └── websocket.ts              # NEW: WebSocket connection manager
│   ├── Dockerfile                    # NEW: Multi-stage build for Next.js
│   └── tests/
│
├── infrastructure/                   # NEW: Helm charts and Dapr components
│   ├── helm/
│   │   ├── backend-api/
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   ├── values-local.yaml     # Minikube overrides
│   │   │   ├── values-cloud.yaml     # OKE overrides
│   │   │   └── templates/
│   │   │       ├── deployment.yaml   # Backend API + Dapr sidecar
│   │   │       ├── service.yaml
│   │   │       └── configmap.yaml
│   │   ├── notification-service/
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   │       ├── deployment.yaml   # Notification + Dapr sidecar
│   │   │       └── configmap.yaml
│   │   ├── recurring-task-service/
│   │   │   └── [same structure]
│   │   ├── audit-service/
│   │   │   └── [same structure]
│   │   ├── websocket-service/
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   │       ├── deployment.yaml   # WebSocket + Dapr sidecar
│   │   │       └── service.yaml      # NodePort 30082
│   │   └── frontend/
│   │       ├── Chart.yaml
│   │       ├── values.yaml
│   │       └── templates/
│   │           ├── deployment.yaml   # Next.js (no Dapr sidecar)
│   │           └── service.yaml      # NodePort 30080
│   ├── dapr-components/              # Symlink to specs/005-event-driven-microservices/contracts/dapr-components/
│   │   ├── local/
│   │   └── cloud/
│   └── scripts/
│       ├── deploy-local.sh           # Deploy to Minikube
│       ├── deploy-cloud.sh           # Deploy to OKE
│       └── setup-redpanda-docker.sh  # Start Redpanda Docker for local development
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Build and test all services
│       ├── deploy-oke.yml            # Deploy to Oracle OKE
│       └── contract-tests.yml        # Validate event schemas
│
├── specs/                            # Feature specifications (existing)
├── history/prompts/                  # PHRs (existing)
├── CLAUDE.md                         # Updated with Phase 5 guidance
├── CONSTITUTION.md                   # v4.0.0 (existing)
└── README.md                         # Updated with Phase 5 architecture
```

**Structure Decision**:

The project uses **Option 2: Web application (frontend + backend)** from the plan template, extended with a new `services/` directory for microservices and `infrastructure/` directory for Helm charts and Dapr configurations.

**Rationale**:
1. **Monorepo Preservation**: Maintains existing backend/ and frontend/ directories for backwards compatibility
2. **Microservices Isolation**: New services/ directory contains 4 independent microservices (Notification, Recurring Task, Audit, WebSocket)
3. **Infrastructure as Code**: New infrastructure/ directory centralizes all Kubernetes/Helm/Dapr configurations
4. **Environment Parity**: Local and cloud configurations coexist in infrastructure/dapr-components/{local,cloud}
5. **Backwards Compatibility**: Existing Phase 3/4 code paths remain intact; Phase 5 adds new capabilities

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations detected. All Phase V architectural decisions align with Constitution v4.0.0 principles.*

---

## Phase 0: Research (Next Step)

**Objective**: Investigate 6 technical unknowns and document architectural decisions in `research.md`.

### Research Topics

1. **Dapr Pub/Sub Configuration** - Compare local (Redpanda Docker, no auth) vs cloud (Redpanda Cloud, SASL/SSL)
2. **Event Schema Design** - Define JSON Schema structure, versioning strategy, backward compatibility
3. **Idempotency Strategy** - Select approach (database state reconciliation preferred)
4. **Reminder Scheduling** - Choose between Dapr Jobs API (recommended) vs cron binding
5. **WebSocket Architecture** - Design live update broadcast with user isolation
6. **Database Migration Strategy** - Plan zero-downtime migration with Alembic

**Output**: `research.md` with decisions, rationale, and alternatives considered for each topic.

---

## Phase 1: Design Artifacts (Next Step)

**Objective**: Create technical designs before implementation.

### Artifacts to Generate

1. **data-model.md** - Extended database schema with migrations
2. **contracts/events/*.schema.json** - JSON Schema for all event topics
3. **contracts/dapr-components/** - Local and cloud Dapr component YAMLs
4. **quickstart.md** - Local development setup and test scenarios
5. **contracts/README.md** - Contract versioning and compatibility guide

**Output**: Complete contracts/ directory structure with all design artifacts.

---

## Critical Next Steps

1. ✅ **Plan Complete** - This file documents the implementation strategy
2. ⏭️ **Generate research.md** - Document architectural decisions (Phase 0)
3. ⏭️ **Generate data-model.md** - Design extended database schema (Phase 1)
4. ⏭️ **Generate contracts/** - Create event schemas and Dapr YAMLs (Phase 1)
5. ⏭️ **Generate quickstart.md** - Document local development setup (Phase 1)
6. ⏭️ **Run `/sp.tasks`** - Generate actionable task breakdown (Phase 2)

---

**Plan Status**: ✅ COMPLETE
**Next Command**: Generate Phase 0/1 artifacts or run `/sp.tasks` to create implementation tasks
