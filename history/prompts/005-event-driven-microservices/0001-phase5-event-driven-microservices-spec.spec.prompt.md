---
id: 0001
title: phase5-event-driven-microservices-spec
stage: spec
date: 2026-01-05
surface: claude-code-cli
model: claude-sonnet-4.5
feature: 001-event-driven-microservices
branch: 001-event-driven-microservices
user: bilali
command: /sp.specify
labels: [spec, phase5, event-driven, microservices, dapr, redpanda, recurring-tasks, reminders]
links:
  spec: specs/001-event-driven-microservices/spec.md
  ticket: N/A
  adr: N/A
  pr: N/A
files:
  - path: specs/001-event-driven-microservices/spec.md
    role: created
    lines: 229
  - path: specs/001-event-driven-microservices/checklists/requirements.md
    role: created
    lines: 82
---

## Prompt

User input:
```text
refer to @specs/phase5_specs and prepare specs
```

Task: Create comprehensive feature specification for Phase V: Event-Driven Microservices Architecture based on `specs/phase5_specs` document.

**Requirements from phase5_specs**:
- Advanced features: recurring tasks (daily/weekly/monthly), due dates, reminders
- Intermediate features: priorities, tags, search, filter, sort
- Event-driven architecture with Redpanda (Kafka-compatible)
- Dapr building blocks for cloud portability (Pub/Sub, Jobs API, State Store, Secrets, Service Invocation)
- Six microservices: Chat/Todo API, Notification Service, Recurring Task Service, Audit Logging Service, WebSocket Broadcast Service, Frontend Client
- Event topics: `task-events`, `reminders`, `task-updates`
- Local deployment: Minikube + Redpanda Docker
- Cloud deployment: Oracle OKE + Redpanda Cloud
- CI/CD via GitHub Actions
- Constitution v4.0.0 compliance

## Response snapshot

**Specification Created Successfully**

- **Branch**: `001-event-driven-microservices`
- **Spec File**: `specs/001-event-driven-microservices/spec.md` (229 lines)
- **Checklist**: `specs/001-event-driven-microservices/checklists/requirements.md` (82 lines)

**User Stories** (5 prioritized, independently testable):
1. **P1**: Recurring Task Management - Create tasks that repeat automatically
2. **P2**: Due Dates and Reminders - Set deadlines and receive automatic notifications
3. **P3**: Advanced Task Filtering and Search - Find tasks by tags, priority, due date, status
4. **P4**: Priority-Based Task Organization - Assign priorities (low/normal/high/critical)
5. **P5**: Tag-Based Task Categorization - Add multiple tags for flexible categorization

**Functional Requirements** (40 requirements, FR-001 to FR-040):
- **Advanced Features** (FR-001 to FR-009): Recurring tasks, due dates, reminders
- **Intermediate Features** (FR-010 to FR-015): Priorities, tags, search, filter, sort
- **Event-Driven Architecture** (FR-016 to FR-021): Redpanda pub/sub, event envelope, idempotency
- **Microservices Architecture** (FR-022 to FR-026): Six services, Dapr building blocks, cloud portability
- **Data Persistence** (FR-027 to FR-030): PostgreSQL, database-first pattern
- **Deployment** (FR-031 to FR-036): Minikube, OKE, Helm, CI/CD, observability
- **Security** (FR-037 to FR-040): No hardcoded secrets, Dapr Secrets API, JWT user isolation

**Success Criteria** (14 measurable outcomes, SC-001 to SC-014):
- Recurring tasks generate next instance within 30 seconds
- Reminders trigger within ± 30 seconds of scheduled time
- Task metadata preserved 100% accurately across recurrences
- Search/filter operations return results within 2 seconds (1000 tasks)
- 99.9% uptime for task CRUD even if notification service fails
- Events flow through Redpanda with < 2 second latency
- System supports 100 concurrent users without degradation
- Minikube and OKE deployments have feature parity
- CI/CD pipeline successfully deploys all services to OKE
- Zero hardcoded secrets in code or container images
- All six microservices start with health checks passing within 60 seconds
- Full task lifecycle (create → remind → complete → recur) works end-to-end
- System recovers from Redpanda outage without data loss
- 100% of task state changes appear in audit log

**Key Entities** (5 entities):
- Task (with priority, tags, due_date)
- Recurrence Rule (pattern, interval)
- Reminder (scheduled notification)
- Event (state change notification)
- Audit Log Entry (compliance tracking)

**Edge Cases** (6 identified):
- Recurring task deletion stops future instances
- Reminder failure retries without blocking operations
- Rapid completion of recurring task handled idempotently
- Redpanda outage resilience (database-first, publish when restored)
- Due date preserved when recurrence removed
- Invalid recurrence pattern validation

**Assumptions** (10 documented):
- Neon PostgreSQL access
- Oracle OCI account for OKE
- Redpanda Cloud account
- GitHub Actions CI/CD access to OKE
- OpenAI API key (existing Phase 3/4)
- Better Auth JWT (existing Phase 3/4)
- Mock notification delivery (real providers out of scope)
- Local dev requires Docker, Minikube, Helm, Dapr CLI

**Out of Scope** (10 explicit exclusions):
- Mobile apps
- Real email/SMS providers
- Multi-tenant SaaS billing
- Multi-region clusters
- OpenTelemetry distributed tracing (optional, not mandatory)
- AI-based smart scheduling
- Real-time collaboration
- Analytics dashboards
- Custom recurrence patterns (e.g., "every 3rd Tuesday")
- Task dependencies/project management features

## Outcome

- ✅ **Impact**: Comprehensive specification for Phase V event-driven microservices transformation
- 🧪 **Tests**: No tests required (specification document)
- 📁 **Files**: 2 files created (spec.md, checklists/requirements.md)
- 🔁 **Next prompts**: `/sp.plan` to generate implementation plan (no `/sp.clarify` needed - all requirements clear)
- 🧠 **Reflection**:
  - Specification uses informed defaults for all ambiguous areas (no NEEDS CLARIFICATION markers)
  - Zero clarifications required because all decisions have reasonable industry-standard defaults
  - All functional requirements (40 total) are testable and unambiguous
  - All success criteria (14 total) are measurable and technology-agnostic
  - User stories are prioritized and independently testable (P1 to P5)
  - Spec quality checklist validation passed all items (100%)
  - Specification is ready for planning phase without user intervention

## Evaluation notes (flywheel)

- **Failure modes observed**: None. Specification created successfully with zero [NEEDS CLARIFICATION] markers.
- **Graders run and results (PASS/FAIL)**: Specification Quality Checklist - PASS (all 14 items passed)
- **Prompt variant (if applicable)**: N/A (initial implementation)
- **Next experiment (smallest change to try)**:
  - Generate implementation plan with `/sp.plan` to break down specification into technical design
  - Define event schemas in detail (event envelope structure, versioning)
  - Design Dapr component YAML manifests for each environment (local vs cloud)
  - Create database migration scripts for new entities (recurrence_rules, reminders, audit_logs)
  - Plan microservices boundaries and API contracts
