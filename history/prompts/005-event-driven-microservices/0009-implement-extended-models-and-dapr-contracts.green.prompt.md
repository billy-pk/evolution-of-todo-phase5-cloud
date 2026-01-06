---
id: "0009"
title: "Implement Extended Models and Dapr Contracts"
stage: "green"
date: "2026-01-06"
surface: "Claude Code CLI"
model: "claude-sonnet-4-5"
feature: "005-event-driven-microservices"
branch: "005-event-driven-microservices"
user: "bilali"
command: "/sp.implement"
labels: ["models", "dapr", "event-schemas", "contracts", "phase-v"]
links:
  spec: "specs/005-event-driven-microservices/spec.md"
  ticket: "N/A"
  adr: "N/A"
  pr: "N/A"
files:
  - path: "backend/models.py"
    status: "modified"
    lines_added: 240
    description: "Extended Task model with 4 new fields (priority, tags, due_date, recurrence_id), added RecurrenceRule, Reminder, and AuditLog models"
  - path: "specs/005-event-driven-microservices/contracts/events/task-events.schema.json"
    status: "verified"
    description: "JSON Schema for task lifecycle events (task.created, task.updated, task.completed, task.deleted)"
  - path: "specs/005-event-driven-microservices/contracts/events/reminders.schema.json"
    status: "verified"
    description: "JSON Schema for reminder lifecycle events (reminder.scheduled, reminder.triggered, reminder.delivered, reminder.failed)"
  - path: "specs/005-event-driven-microservices/contracts/events/task-updates.schema.json"
    status: "verified"
    description: "JSON Schema for real-time UI updates via WebSocket"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/local/pubsub-redpanda.yaml"
    status: "verified"
    description: "Dapr Pub/Sub component for local Redpanda Docker (no auth)"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/local/statestore-postgresql.yaml"
    status: "verified"
    description: "Dapr State Store component for PostgreSQL"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/local/jobs.yaml"
    status: "verified"
    description: "Dapr Jobs API component for reminder scheduling"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/local/secrets.yaml"
    status: "verified"
    description: "Dapr Secret Store component using Kubernetes Secrets"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/cloud/pubsub-redpanda-cloud.yaml"
    status: "verified"
    description: "Dapr Pub/Sub component for Redpanda Cloud (SASL/SSL)"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/cloud/statestore-postgresql.yaml"
    status: "verified"
    description: "Dapr State Store component for cloud PostgreSQL"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/cloud/jobs.yaml"
    status: "verified"
    description: "Dapr Jobs API component for cloud"
  - path: "specs/005-event-driven-microservices/contracts/dapr-components/cloud/secrets.yaml"
    status: "verified"
    description: "Dapr Secret Store component for cloud (Kubernetes Secrets or OCI Vault)"
  - path: "specs/005-event-driven-microservices/tasks.md"
    status: "modified"
    description: "Marked tasks T012-T026 as completed"
tests:
  - name: "Python syntax check"
    status: "passed"
    description: "Verified models.py has valid Python syntax"
  - name: "JSON schema validation"
    status: "passed"
    description: "Verified all event schemas are valid JSON"
---

## Prompt

implement tasks t012 to t015

User input: implement tasks t016 to t026

## Response snapshot

Successfully implemented tasks T012-T026 from the Phase V Event-Driven Microservices Architecture implementation plan:

**Tasks T012-T015 (Extended Models)**:
1. Extended Task model with 4 new fields: priority (indexed), tags (PostgreSQL array), due_date (indexed), recurrence_id (FK to recurrence_rules)
2. Added updated_at trigger with SQLAlchemy onupdate for automatic timestamp updates
3. Created RecurrenceRule model with pattern (daily/weekly/monthly), interval, and JSON metadata for preserving task attributes
4. Created Reminder model with reminder_time, status (pending/sent/failed), delivery_method, retry_count
5. Created AuditLog model with event_type, user_id, task_id, JSON details for immutable audit trail

All models follow SQLModel best practices with proper indexing, foreign keys, and type annotations.

**Tasks T016-T018 (Event Schemas)**:
Verified existing JSON Schemas for event-driven architecture:
- task-events.schema.json: Defines task.created, task.updated, task.completed, task.deleted events with full task data snapshots
- reminders.schema.json: Defines reminder.scheduled, reminder.triggered, reminder.delivered, reminder.failed lifecycle events
- task-updates.schema.json: Defines real-time UI updates for WebSocket broadcasting (task_created, task_updated, task_completed, task_deleted, task_recurring_generated)

**Tasks T019-T022 (Local Dapr Components)**:
Verified Dapr component configurations for local development (Minikube + Redpanda Docker):
- pubsub-redpanda.yaml: Kafka-compatible Pub/Sub using Redpanda Docker (no auth, localhost:9092)
- statestore-postgresql.yaml: PostgreSQL state store using Kubernetes Secret Store
- jobs.yaml: Dapr Jobs API using PostgreSQL for persistent reminder scheduling
- secrets.yaml: Kubernetes Secret Store for local environment

**Tasks T023-T026 (Cloud Dapr Components)**:
Verified Dapr component configurations for cloud deployment (OKE + Redpanda Cloud):
- pubsub-redpanda-cloud.yaml: Kafka-compatible Pub/Sub using Redpanda Cloud with SASL/SCRAM-SHA-256 and TLS
- statestore-postgresql.yaml: Same PostgreSQL state store (Neon is cloud-native)
- jobs.yaml: Same Jobs API configuration for cloud
- secrets.yaml: Kubernetes Secret Store with optional OCI Vault migration path

All configurations follow the database-first pattern and Dapr abstraction principle (application code unchanged between environments).

## Outcome

- ✅ Impact: Completed Foundational Phase (Phase 2) extended models and contracts. Database schema supports all 5 user stories. Event schemas and Dapr components ready for event-driven microservices implementation.
- 🧪 Tests: Python syntax validation passed. JSON schema validation passed. Ready for contract tests (T031-T033).
- 📁 Files: Modified 1 file (backend/models.py), verified 12 contract files (3 event schemas + 8 Dapr components + tasks.md)
- 🔁 Next prompts: Implement Event Publishing Infrastructure (T027-T030), then Contract Tests (T031-T033)
- 🧠 Reflection: All contract files already existed from previous planning session. Implementation focused on extending models.py with Phase V fields and verifying contract specifications. SQLAlchemy integration (ARRAY, JSON, onupdate trigger) required careful column configuration. The database-first pattern ensures backward compatibility - all new fields are optional/have defaults.

## Evaluation notes (flywheel)

- Failure modes observed: None. All tasks completed successfully.
- Graders run and results (PASS/FAIL): Manual verification PASS (syntax checks, JSON validation)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Implement EventPublisher service (T027) to test Dapr Pub/Sub integration with event schemas
