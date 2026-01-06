# Feature Specification: Phase V Event-Driven Microservices Architecture

**Feature Branch**: `005-event-driven-microservices`
**Created**: 2026-01-05
**Status**: Draft
**Input**: User description: "Phase V: Advanced Event-Driven, Cloud-Native & Dapr-Enabled Todo System with Redpanda, Microservices, and Oracle OKE Deployment"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recurring Task Management (Priority: P1)

As a user, I want to create tasks that repeat automatically so that I don't have to manually recreate routine tasks like "Weekly team meeting" or "Daily standup".

**Why this priority**: Recurring tasks are a fundamental productivity feature that directly impacts user value. Without this, users must manually duplicate tasks, leading to errors and inefficiency. This is the most visible and valuable Phase V feature.

**Independent Test**: Can be fully tested by creating a task with recurrence (e.g., "daily"), marking it complete, and verifying a new instance is automatically created with the same attributes (title, description, priority, tags) for the next occurrence.

**Acceptance Scenarios**:

1. **Given** a user is authenticated, **When** they create a task "Daily standup" with recurrence "daily", **Then** the system stores the recurrence rule and creates the first instance
2. **Given** a recurring task exists with recurrence "weekly", **When** the user marks it complete, **Then** the system automatically creates the next instance for the following week
3. **Given** a recurring task "Monthly report" with priority "high" and tag "work", **When** the system generates the next instance, **Then** the new task preserves all metadata (priority, tags, description)

---

### User Story 2 - Due Dates and Reminders (Priority: P2)

As a user, I want to set due dates on tasks and receive automatic reminders so that I never miss important deadlines.

**Why this priority**: Due dates and reminders transform a simple task list into a time-aware productivity system. This is critical for professional use cases where deadlines matter. Depends on P1 (recurring tasks may have due dates).

**Independent Test**: Can be fully tested by creating a task with a due date and reminder time, then verifying the reminder triggers automatically at the scheduled time via notification service.

**Acceptance Scenarios**:

1. **Given** a user creates a task "Submit report", **When** they set the due date to "next Monday 5pm", **Then** the system stores the due date as ISO8601 datetime
2. **Given** a task has due date "2026-01-10 17:00:00", **When** the user adds a reminder "1 hour before", **Then** the system schedules the reminder via Dapr Jobs API
3. **Given** a scheduled reminder triggers, **When** the reminder time is reached, **Then** the notification service sends a notification to the user
4. **Given** a user tries to set a due date in the past, **When** they submit the task, **Then** the system rejects the due date with a validation error

---

### User Story 3 - Advanced Task Filtering and Search (Priority: P3)

As a user, I want to search, filter, and sort my tasks by multiple criteria (tags, priority, due date, status) so that I can quickly find relevant tasks in a large task list.

**Why this priority**: Search and filtering become essential as the task list grows. This enhances usability but is not blocking for core functionality. Can be implemented after recurring tasks and due dates are working.

**Independent Test**: Can be fully tested by creating multiple tasks with different tags, priorities, and statuses, then verifying search and filter operations return correct results.

**Acceptance Scenarios**:

1. **Given** a user has 50 tasks with various tags, **When** they search for "urgent", **Then** the system returns all tasks with "urgent" in title, description, or tags
2. **Given** a user has tasks with priorities "low", "normal", "high", **When** they filter by "high priority", **Then** only high-priority tasks are displayed
3. **Given** a user has completed and pending tasks, **When** they filter by "pending", **Then** only incomplete tasks are shown
4. **Given** a user has tasks with various due dates, **When** they sort by "due soonest first", **Then** tasks with nearest due dates appear first

---

### User Story 4 - Priority-Based Task Organization (Priority: P4)

As a user, I want to assign priorities (low, normal, high, critical) to tasks so that I can focus on the most important work first.

**Why this priority**: Priorities help users organize work by importance. This is an enhancement that improves usability but is not essential for basic task management. Can be implemented independently alongside other features.

**Independent Test**: Can be fully tested by creating tasks with different priorities, then verifying they can be filtered and sorted by priority level.

**Acceptance Scenarios**:

1. **Given** a user creates a task, **When** they set priority to "high", **Then** the system stores and displays the priority
2. **Given** a recurring task has priority "critical", **When** the next instance is generated, **Then** the new instance also has priority "critical"
3. **Given** a user has tasks with mixed priorities, **When** they sort by priority, **Then** critical tasks appear before high, high before normal, normal before low

---

### User Story 5 - Tag-Based Task Categorization (Priority: P5)

As a user, I want to add multiple tags (e.g., "work", "personal", "urgent") to tasks so that I can categorize and organize tasks flexibly.

**Why this priority**: Tags provide flexible categorization beyond simple folders. This is a nice-to-have feature that enhances organization but is not blocking for core workflows. Can be implemented independently.

**Independent Test**: Can be fully tested by creating tasks with multiple tags, then verifying tags are preserved through recurrence, search, and filter operations.

**Acceptance Scenarios**:

1. **Given** a user creates a task "Client meeting", **When** they add tags "work" and "urgent", **Then** the system stores both tags
2. **Given** a task has tags "work" and "urgent", **When** it recurs, **Then** the new instance preserves both tags
3. **Given** a user has tasks tagged "work" and "personal", **When** they filter by tag "work", **Then** only tasks with "work" tag are shown
4. **Given** a user searches for "urgent", **When** matching tags exist, **Then** tasks with "urgent" tag appear in results

---

### Edge Cases

- **What happens when a recurring task is deleted?** The system should stop generating future instances but preserve the deletion in audit log
- **What happens when a reminder fails to send?** The system should retry notification delivery (configurable retry policy) and log failure in audit trail without blocking task operations
- **What happens when a user marks a recurring task complete multiple times rapidly?** The system should handle idempotent operations and avoid creating duplicate future instances
- **What happens when event streaming (Redpanda) is temporarily unavailable?** The database write should succeed, and events should be published when streaming is restored (resilience pattern)
- **What happens when a task has a due date but recurrence is removed?** The due date should remain on the current task instance only, not propagated to future (now non-existent) recurrences
- **What happens when a user tries to create a recurring task with invalid recurrence pattern?** The system should validate recurrence rules and return clear error messages

## Requirements *(mandatory)*

### Functional Requirements

#### Advanced Features (Mandatory)

- **FR-001**: System MUST support recurring tasks with patterns: daily (every N days, 1-365), weekly (every N weeks, 1-52), monthly (every N months, 1-12)
- **FR-002**: System MUST automatically generate the next task instance when a recurring task is marked complete
- **FR-003**: System MUST preserve all task metadata (title, description, priority, tags) when generating recurring instances
- **FR-004**: System MUST store due dates as ISO8601 datetime strings with timezone support
- **FR-005**: System MUST validate that due dates are not in the past unless explicitly allowed by user
- **FR-006**: System MUST support natural language due date input (e.g., "tomorrow at 5pm", "next Monday")
- **FR-007**: System MUST allow one or more reminders per task
- **FR-008**: System MUST schedule reminders using Dapr Jobs API for persistent, scalable job scheduling
- **FR-009**: System MUST deliver reminders through the notification service via webhook delivery (configurable endpoint for testing, future: email/SMS providers)

#### Intermediate Features (Mandatory)

- **FR-010**: System MUST support task priorities: low, normal, high, and optionally critical
- **FR-011**: System MUST allow multiple tags per task
- **FR-012**: System MUST enable search by: title, description, tags, priority, and status
- **FR-013**: System MUST support filtering by: completed/pending, overdue, due today/this week, priority, and tags
- **FR-014**: System MUST support sorting by: creation date, due date, priority, and last updated
- **FR-015**: System MUST use "due soonest first" as the default sort order

#### Event-Driven Architecture

- **FR-016**: System MUST publish events to Redpanda topics for all task state changes via Dapr Pub/Sub API (not direct Kafka/Redpanda SDK)
- **FR-017**: System MUST use event topics: `task-events` (CRUD), `reminders` (scheduling), `task-updates` (UI sync)
- **FR-018**: System MUST include event envelope with: event_type, task_id, user_id, task_data, timestamp
- **FR-020**: System MUST handle events idempotently to avoid duplicate processing
- **FR-021**: System MUST handle out-of-order events gracefully

#### Microservices Architecture

- **FR-022**: System MUST implement six logical microservices: Backend API (includes embedded MCP Server for chat/todo operations), Notification Service, Recurring Task Service, Audit Service, WebSocket Service, Frontend Client
- **FR-023**: System MUST deploy each microservice as a separate container with Dapr sidecar
- **FR-024**: System MUST use Dapr building blocks for: Pub/Sub (Redpanda), State Store (PostgreSQL), Jobs API (reminders), Secrets (credentials), Service Invocation (inter-service calls)
- **FR-025**: Application code MUST NOT change between local (Minikube) and cloud (OKE) environments
- **FR-026**: Only Dapr component YAML configurations MUST change between environments

#### Data Persistence

- **FR-027**: System MUST store all data in Neon PostgreSQL database
- **FR-028**: System MUST maintain database schema for: tasks, recurrence rules, reminders, audit history
- **FR-029**: System MUST write to database first, then emit events (database-first pattern)
- **FR-030**: System MUST NOT create eventual consistency issues for core task data

#### Deployment and Infrastructure

- **FR-031**: System MUST support local development on Minikube with Redpanda Docker (single-node, no auth)
- **FR-032**: System MUST support cloud deployment on Oracle Kubernetes Engine (OKE) with Redpanda Cloud (SASL/SSL secured)
- **FR-033**: System MUST use Kubernetes-native deployment with Helm charts
- **FR-034**: System MUST implement CI/CD pipeline via GitHub Actions
- **FR-035**: System MUST implement health probes (liveness and readiness) for all services
- **FR-036**: System MUST implement observability: structured logging, Prometheus metrics, distributed tracing (optional)

#### Security and Secrets

- **FR-037**: System MUST NEVER hardcode secrets in code or container images
- **FR-038**: System MUST use Kubernetes Secrets (local) or Dapr Secrets API (cloud) for credentials
- **FR-039**: System MUST enforce user isolation for all tasks, conversations, and events via JWT user_id
- **FR-040**: System MUST validate user ownership before all task operations

### Key Entities

- **Task**: Represents a todo item with attributes: id, user_id, title, description, completed, priority (low/normal/high/critical), tags (array), due_date (ISO8601), created_at, updated_at
- **Recurrence Rule**: Defines how a task repeats with attributes: task_id, pattern (daily/weekly/monthly/custom), interval, metadata preservation rules
- **Reminder**: Represents a scheduled notification with attributes: id, task_id, user_id, reminder_time (ISO8601), status (pending/sent/failed), delivery_method
- **Event**: Represents a state change notification with attributes: event_type, task_id, user_id, task_data (JSON), timestamp (ISO8601)
- **Audit Log Entry**: Tracks task operations with attributes: id, event_type, user_id, task_id, timestamp, details (JSON)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create recurring tasks and observe automatic generation of next instance within 30 seconds of marking complete
- **SC-002**: Reminders trigger within ± 30 seconds of scheduled time under normal conditions
- **SC-003**: Task metadata (title, description, priority, tags) is preserved 100% accurately when recurring instances are generated
- **SC-004**: Search and filter operations return results within 2 seconds for task lists up to 1000 tasks
- **SC-005**: System maintains 99.9% uptime for task CRUD operations even if notification service fails (measured over 30-day rolling window, max 43 minutes downtime per month)
- **SC-006**: Events flow through Redpanda with end-to-end latency under 2 seconds from write to consumer processing
- **SC-007**: System supports at least 100 concurrent users without performance degradation
- **SC-008**: Minikube local deployment works identically to OKE cloud deployment (feature parity)
- **SC-009**: CI/CD pipeline successfully builds, tests, and deploys all services to OKE cluster
- **SC-010**: Zero hardcoded secrets found in code review or container image inspection
- **SC-011**: All six microservices start successfully with health checks passing within 60 seconds of deployment
- **SC-012**: Users can complete full task lifecycle (create → add due date → set reminder → receive notification → mark complete → observe recurrence) end-to-end
- **SC-013**: System recovers from Redpanda outage without data loss (events published when streaming restored)
- **SC-014**: 100% of task state changes appear in audit log for compliance tracking

## Assumptions

- Users have access to Neon PostgreSQL database (serverless, managed)
- Users have access to Oracle Cloud Infrastructure (OCI) account for OKE deployment
- Users have access to Redpanda Cloud account for production event streaming
- GitHub Actions CI/CD pipeline can access OKE cluster and container registry
- OpenAI API key is available for chat-based task management (existing Phase 3/4 functionality)
- Better Auth JWT authentication is already implemented (existing Phase 3/4 functionality)
- Users have basic familiarity with Kubernetes and Helm for deployment operations
- Notification delivery uses mock/webhook implementation (real email/SMS providers are out of scope)
- Local development requires Docker, Minikube, Helm, and Dapr CLI installed
- Event streaming performance is acceptable with Redpanda (Kafka-compatible) vs native Kafka

## Out of Scope

The following are explicitly NOT included in Phase V:

- Mobile applications (iOS/Android native apps)
- Real email/SMS notification providers (Twilio, SendGrid) - mock delivery acceptable
- Billing or multi-tenant SaaS features (commercial deployment)
- Multi-region Kubernetes clusters or global sync
- OpenTelemetry distributed tracing implementation (observability is recommended but not mandatory)
- AI-based smart scheduling or task prioritization
- Real-time collaboration features (multiple users editing same task simultaneously)
- Analytics dashboards or reporting features
- Custom recurrence patterns beyond daily/weekly/monthly (e.g., "every 3rd Tuesday")
- Task dependencies or project management features (subtasks, milestones, Gantt charts)

## Dependencies

- **Phase 3/4**: Existing conversational AI chat interface, Better Auth JWT, OpenAI Agents SDK, MCP tools
- **External Services**: Neon PostgreSQL, Redpanda Cloud, Oracle OKE, OpenAI API
- **Infrastructure**: Kubernetes (Minikube locally, OKE in cloud), Dapr runtime, Helm 3
- **Event Streaming**: Redpanda Docker (local development), Redpanda Cloud (production)
- **Constitution v4.0.0**: All Phase V work must comply with updated constitution principles (event-driven architecture, Dapr portability, observability)
