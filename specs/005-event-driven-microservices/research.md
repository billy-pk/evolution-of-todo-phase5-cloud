# Phase 0 Research: Phase V Event-Driven Microservices Architecture

**Feature**: Phase V Event-Driven Microservices Architecture
**Branch**: `005-event-driven-microservices`
**Date**: 2026-01-06
**Status**: Research Complete

## Overview

This document captures architectural decisions made during Phase 0 research for Phase V. Each research topic includes the decision made, rationale, alternatives considered, and implementation guidance.

---

## Research Topic 1: Dapr Pub/Sub Configuration

### Decision

Use **separate Dapr component YAML files** for local (Redpanda Docker) and cloud (Redpanda Cloud) environments with identical application code calling Dapr Pub/Sub APIs.

### Configuration Details

**Local Environment (Minikube + Redpanda Docker)**:
- Broker: `redpanda:9092` (Docker service name)
- Authentication: None (no auth required for local Docker)
- Consumer Group: `todo-app`
- TLS: Disabled

**Cloud Environment (OKE + Redpanda Cloud)**:
- Broker: Redpanda Cloud endpoint (e.g., `<cluster-id>.redpanda.cloud:9092`)
- Authentication: SASL/SCRAM-SHA-256 with username/password from Kubernetes Secret
- Consumer Group: `todo-app` (same as local for consistency)
- TLS: Enabled (required for Redpanda Cloud)

### Rationale

1. **Environment Parity**: Application code remains 100% identical between local and cloud
2. **Security**: Local development doesn't require credentials; production enforces SASL/TLS
3. **Simplicity**: Developers can start Redpanda Docker with a single command, no authentication setup
4. **Cloud Portability**: Switching providers (Kafka, AWS Kinesis, Azure Event Hubs) requires only YAML changes
5. **Dapr Abstraction**: Application calls `dapr.publish()` - no direct Kafka/Redpanda SDK usage

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Single YAML with environment variables | Requires application restart when switching environments; harder to validate configurations |
| Direct Kafka client in application code | Violates Constitution Principle XI (Cloud Portability); vendor lock-in |
| Helm chart templates with conditionals | Adds complexity; separate files are more explicit and easier to validate |

### Implementation Guidance

**Directory Structure**:
```
specs/005-event-driven-microservices/contracts/dapr-components/
├── local/
│   └── pubsub-redpanda.yaml
└── cloud/
    └── pubsub-redpanda-cloud.yaml
```

**Application Code Pattern** (Python):
```python
from dapr.clients import DaprClient

# Publish event (same code for local and cloud)
with DaprClient() as client:
    client.publish_event(
        pubsub_name="pubsub",  # Component name from YAML
        topic_name="task-events",
        data=json.dumps(event_payload)
    )
```

**Deployment**:
- Local: `kubectl apply -f contracts/dapr-components/local/`
- Cloud: `kubectl apply -f contracts/dapr-components/cloud/`

### References
- [Dapr Pub/Sub Documentation](https://docs.dapr.io/developing-applications/building-blocks/pubsub/)
- [Redpanda Kafka Compatibility](https://docs.redpanda.com/current/get-started/intro-to-rpk/)

---

## Research Topic 2: Event Schema Design

### Decision

Use **JSON Schema** for event validation with a standardized envelope format and semantic versioning for schema evolution.

### Event Envelope Format

**Standard Envelope** (all events):
```json
{
  "event_type": "string (e.g., task.created, task.updated, task.completed, task.deleted)",
  "event_id": "uuid (unique identifier for deduplication)",
  "task_id": "uuid (nullable for system events)",
  "user_id": "string (for user isolation)",
  "task_data": {
    "title": "string",
    "description": "string (nullable)",
    "completed": "boolean",
    "priority": "string (enum: low, normal, high, critical)",
    "tags": ["array of strings"],
    "due_date": "ISO8601 datetime string (nullable)",
    "recurrence_id": "uuid (nullable)"
  },
  "timestamp": "ISO8601 datetime string",
  "schema_version": "string (semver: 1.0.0)"
}
```

### Schema Versioning Strategy

**Versioning Rules**:
- **MAJOR**: Breaking changes (remove required field, change field type)
- **MINOR**: Backward-compatible additions (new optional field)
- **PATCH**: Documentation or validation rule changes (no structure changes)

**Compatibility Contract**:
- Producers MUST include `schema_version` in every event
- Consumers MUST handle all MINOR versions within the same MAJOR version
- Consumers MUST reject events with unknown MAJOR versions
- Consumers MUST ignore unknown fields (forward compatibility)

**Example Evolution**:
- `1.0.0`: Initial schema (task.created, task.updated, task.completed, task.deleted)
- `1.1.0`: Add optional `recurrence_id` field (backward compatible)
- `2.0.0`: Change `priority` from string to integer (breaking change - rejected)

### Rationale

1. **Validation**: JSON Schema enables contract testing before deployment
2. **Documentation**: Schema serves as machine-readable API documentation
3. **Backward Compatibility**: Consumers can handle new optional fields without changes
4. **Idempotency**: `event_id` enables deduplication
5. **User Isolation**: `user_id` in every event enables filtering by consumer

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Protocol Buffers (protobuf) | Adds complexity; JSON is sufficient for event throughput; harder to debug |
| Avro with Schema Registry | Requires separate Schema Registry service; overkill for 3 event topics |
| No schema validation | Leads to runtime errors; hard to catch breaking changes before deployment |
| Event versioning via topic names | Creates topic sprawl (task-events-v1, task-events-v2); harder to manage |

### Implementation Guidance

**Schema Location**:
```
specs/005-event-driven-microservices/contracts/events/
├── task-events.schema.json     # v1.0.0
├── reminders.schema.json        # v1.0.0
└── task-updates.schema.json     # v1.0.0
```

**Contract Tests**:
```python
import jsonschema

def test_task_created_event_validates():
    schema = load_schema("task-events.schema.json")
    event = {
        "event_type": "task.created",
        "event_id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "user_id": "user-123",
        "task_data": {
            "title": "Test task",
            "completed": False,
            "priority": "normal",
            "tags": ["work"]
        },
        "timestamp": "2026-01-06T10:00:00Z",
        "schema_version": "1.0.0"
    }
    jsonschema.validate(event, schema)  # Should not raise
```

### References
- [JSON Schema Specification](https://json-schema.org/specification)
- [Semantic Versioning](https://semver.org/)

---

## Research Topic 3: Idempotency Strategy

### Decision

Use **database state reconciliation** pattern where consumers check current database state before taking action, rather than maintaining separate idempotency tables.

### Implementation Pattern

**Principle**: Events trigger actions only if the current database state allows the action.

**Example - Recurring Task Generation**:
```python
# Recurring Task Service receives task.completed event
@app.subscribe(pubsub_name="pubsub", topic="task-events")
def handle_task_completed(event):
    task_id = event["task_id"]
    user_id = event["user_id"]

    # Check current database state
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id,
        Task.completed == True  # Verify task is actually complete
    ).first()

    if not task or not task.recurrence_id:
        return  # Task not found, already processed, or not recurring

    # Check if next instance already exists
    recurrence_rule = db.query(RecurrenceRule).get(task.recurrence_id)
    next_due_date = calculate_next_occurrence(recurrence_rule)

    existing_next = db.query(Task).filter(
        Task.recurrence_id == task.recurrence_id,
        Task.due_date == next_due_date,
        Task.completed == False
    ).first()

    if existing_next:
        return  # Next instance already generated (idempotent)

    # Safe to create next instance
    next_task = create_next_instance(task, recurrence_rule)
    db.add(next_task)
    db.commit()
```

### Rationale

1. **Simplicity**: No separate idempotency table to manage
2. **Database is Source of Truth**: Aligns with Constitution Principle IV
3. **Natural Deduplication**: Database constraints (unique indexes) prevent duplicates
4. **Stateless Consumers**: No need to remember which events were processed
5. **Out-of-Order Events**: Works correctly even if events arrive out of sequence

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Idempotency table with event_id | Extra table to maintain; requires TTL or cleanup; adds write overhead |
| Distributed locks (Redis, etcd) | Adds external dependency; increases complexity; lock contention issues |
| Event deduplication in Dapr/Redpanda | Consumer-side idempotency is still required; infrastructure-level dedup is insufficient |
| Message IDs with at-most-once delivery | Risks data loss if consumer crashes; violates reliability requirements |

### Edge Cases Handled

**Duplicate Events**:
- Multiple `task.completed` events for same task → Only first creates next instance (database state check prevents duplicate)

**Out-of-Order Events**:
- `task.completed` arrives before `task.created` → Consumer checks if task exists; skips if not found
- `task.deleted` arrives after `task.completed` → Next instance already created; manual cleanup if needed (acceptable)

**Partial Failures**:
- Consumer crashes after creating next instance but before acknowledging event → Event replays; database state check sees next instance exists; skips (idempotent)

### Implementation Guidance

**Best Practices**:
1. Always query database state before acting on event
2. Use database transactions for atomic operations
3. Use unique constraints to prevent duplicates (e.g., `UNIQUE(recurrence_id, due_date)`)
4. Log events that are skipped due to state mismatch (audit trail)
5. Design actions to be idempotent by nature (e.g., "set status to X" vs "increment counter")

**Anti-Patterns to Avoid**:
- ❌ Assuming event arrival order
- ❌ Maintaining in-memory state about processed events
- ❌ Using event data as single source of truth (always verify with database)

### References
- [Idempotent Receiver Pattern](https://www.enterpriseintegrationpatterns.com/patterns/messaging/IdempotentReceiver.html)
- [Database State Reconciliation in Event-Driven Systems](https://microservices.io/patterns/data/saga.html)

---

## Research Topic 4: Reminder Scheduling

### Decision

Use **Dapr Jobs API** for reminder scheduling instead of cron binding.

### Configuration

**Dapr Jobs Component** (`jobs.yaml`):
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: jobs
spec:
  type: jobs.postgresql  # Uses PostgreSQL for persistent job storage
  version: v1
  metadata:
  - name: connectionString
    secretKeyRef:
      name: postgres-credentials
      key: connectionString
```

**Scheduling Pattern**:
```python
from dapr.clients import DaprClient
from datetime import datetime, timedelta

# When task is created with reminder
def schedule_reminder(task_id, user_id, reminder_time):
    job_name = f"reminder-{task_id}-{uuid.uuid4()}"

    with DaprClient() as client:
        client.schedule_job(
            job_name=job_name,
            schedule=reminder_time.isoformat(),  # ISO8601: 2026-01-06T17:00:00Z
            data={
                "task_id": str(task_id),
                "user_id": user_id,
                "reminder_type": "due_date"
            },
            dueTime=reminder_time.isoformat()
        )
```

**Receiving Scheduled Job**:
```python
# Notification Service endpoint
@app.post("/api/jobs/reminder")
async def handle_reminder_job(job_data: dict):
    task_id = job_data["task_id"]
    user_id = job_data["user_id"]

    # Fetch task from database
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()

    if not task or task.completed:
        return {"status": "skipped"}  # Task completed or deleted

    # Send notification
    await send_notification(user_id, f"Reminder: {task.title} is due soon")

    # Update reminder status
    db.query(Reminder).filter(
        Reminder.task_id == task_id
    ).update({"status": "sent", "sent_at": datetime.utcnow()})
    db.commit()

    return {"status": "delivered"}
```

### Rationale

1. **Persistence**: Jobs survive pod restarts (stored in PostgreSQL)
2. **Scalability**: Horizontal scaling without duplicate execution
3. **Dynamic Scheduling**: Reminders created at runtime (not predefined cron schedules)
4. **Accuracy**: Better than ±30s requirement (typically <5s jitter)
5. **Dapr Integration**: Native Dapr building block (no external cron service)

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Cron binding | Static schedules only; can't create reminders dynamically for user-defined due dates |
| Celery Beat | Adds dependency (Redis/RabbitMQ); extra service to manage; not cloud-agnostic |
| Kubernetes CronJob | Can't create jobs dynamically at runtime; requires pre-defined YAML manifests |
| Polling database for due reminders | Inefficient; higher latency; scales poorly; misses reminders if service is down |
| APScheduler (in-process) | State lost on pod restart; duplicate execution with multiple replicas |

### Edge Cases Handled

**Task Deleted Before Reminder**:
- Job executes → Handler queries database → Task not found → Skip notification (idempotent)

**Task Completed Before Reminder**:
- Job executes → Handler checks `task.completed == True` → Skip notification

**Reminder Time in Past**:
- Validation at creation time rejects due dates in past
- If system clock skew: Job executes immediately → Handler checks if still relevant

**Multiple Reminders for Same Task**:
- Each reminder gets unique `job_name` → Dapr executes all independently
- Example: "1 hour before" + "1 day before" → Two separate jobs

### Performance Considerations

**Expected Load**:
- ~100 concurrent users
- ~10 tasks per user with reminders
- ~1000 scheduled jobs at any time
- Dapr Jobs API with PostgreSQL backend handles this easily

**Scaling**:
- Horizontal scaling: Multiple Notification Service replicas
- Dapr ensures only one replica executes each job
- PostgreSQL backend handles distributed locking

### Implementation Guidance

**Testing Reminders**:
```python
# Integration test
def test_reminder_delivery():
    # Schedule reminder 5 seconds in future
    reminder_time = datetime.utcnow() + timedelta(seconds=5)
    schedule_reminder(task_id, user_id, reminder_time)

    # Wait for job execution
    time.sleep(6)

    # Verify reminder was sent
    reminder = db.query(Reminder).filter(
        Reminder.task_id == task_id
    ).first()
    assert reminder.status == "sent"
    assert reminder.sent_at is not None
```

**Monitoring**:
- Log all scheduled jobs with job_name and execution time
- Track reminder delivery success rate
- Alert on failures (e.g., reminder not delivered within 1 minute of schedule)

### References
- [Dapr Jobs API Documentation](https://docs.dapr.io/developing-applications/building-blocks/jobs/)
- [Dapr Jobs with PostgreSQL](https://docs.dapr.io/reference/components-reference/supported-jobs/postgresql/)

---

## Research Topic 5: WebSocket Architecture

### Decision

Implement a dedicated **WebSocket Service** that subscribes to `task-updates` topic and broadcasts to connected clients with user-based connection isolation.

### Architecture

**Component Flow**:
1. Backend API publishes event to `task-updates` topic (after database write)
2. WebSocket Service subscribes to `task-updates` topic via Dapr Pub/Sub
3. WebSocket Service maintains mapping: `user_id → [WebSocket connections]`
4. On event received: Extract `user_id` → Broadcast to all connections for that user
5. Frontend clients connect via WebSocket, receive real-time updates

**WebSocket Service Structure**:
```python
# websocket_service.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dapr.ext.fastapi import DaprApp
import json

app = FastAPI()
dapr_app = DaprApp(app)

# Connection manager: user_id -> list of WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # TODO: Verify JWT token from query params or headers
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive (receive ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

# Dapr Pub/Sub subscription
@dapr_app.subscribe(pubsub_name="pubsub", topic="task-updates")
async def handle_task_update(event):
    user_id = event["user_id"]
    update_type = event["update_type"]
    task_data = event["task_data"]

    # Broadcast to all WebSocket connections for this user
    message = {
        "type": update_type,
        "task": task_data,
        "timestamp": event["timestamp"]
    }
    await manager.broadcast_to_user(user_id, message)
```

**Frontend WebSocket Client**:
```typescript
// lib/websocket.ts
import { useAuth } from '@/lib/auth-client'

export function useTaskUpdates(onUpdate: (update: any) => void) {
  const { session } = useAuth()

  useEffect(() => {
    if (!session?.user?.id) return

    const ws = new WebSocket(
      `ws://localhost:30082/ws/${session.user.id}?token=${session.token}`
    )

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data)
      onUpdate(update)
    }

    ws.onerror = (error) => console.error('WebSocket error:', error)
    ws.onclose = () => console.log('WebSocket disconnected')

    // Send ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }, [session?.user?.id])
}
```

### Rationale

1. **Real-Time Updates**: Users see task changes immediately (recurring tasks generated, reminders triggered)
2. **User Isolation**: Connection manager ensures users only receive their own updates
3. **Scalability**: Stateless service (connections in-memory per pod); horizontal scaling supported
4. **Decoupling**: WebSocket Service is independent consumer; backend API doesn't manage WebSocket connections
5. **Event-Driven**: Subscribes to `task-updates` topic like any other consumer

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Server-Sent Events (SSE) | Unidirectional (server→client only); WebSocket supports bidirectional (future: client actions) |
| Polling (HTTP requests every N seconds) | Inefficient; higher latency; increased load on backend API |
| Backend API manages WebSockets | Violates stateless design; doesn't scale horizontally; tight coupling |
| Firebase/Pusher (third-party) | External dependency; vendor lock-in; additional cost; violates cloud-agnostic requirement |

### Security Considerations

**Authentication**:
- WebSocket connection URL includes JWT token: `/ws/{user_id}?token=<jwt>`
- WebSocket Service validates JWT before accepting connection
- Rejects connection if token invalid or user_id mismatch

**User Isolation**:
- Connection manager stores connections by `user_id`
- Event handler extracts `user_id` from event payload
- Broadcast only to connections matching event `user_id`

**Rate Limiting**:
- Limit WebSocket connections per user (e.g., max 3 concurrent connections)
- Prevent connection spam (e.g., max 10 connections per minute)

### Edge Cases Handled

**Connection Lost**:
- Frontend automatically reconnects with exponential backoff
- User sees "Disconnected" indicator in UI
- No data loss (task state in database; missed updates fetched on reconnect)

**Multiple Tabs/Devices**:
- Each tab/device opens separate WebSocket connection
- All connections for same user_id receive broadcasts
- Example: User opens chat in 2 tabs → Both tabs receive live updates

**Service Restart**:
- All WebSocket connections dropped
- Clients detect disconnect and reconnect automatically
- Connection manager rebuilds user_id → connections mapping

**No Active Connections**:
- Event published to `task-updates` topic
- WebSocket Service receives event
- `manager.broadcast_to_user()` finds no connections → No-op (acceptable)

### Performance Considerations

**Expected Load**:
- 100 concurrent users
- ~2 WebSocket connections per user (average)
- ~200 active WebSocket connections total
- Event rate: <10 events/second

**Scaling**:
- WebSocket Service can scale horizontally
- Each pod maintains its own connection manager
- Load balancer distributes connections across pods
- Events delivered to all pods (each broadcasts to its connections)

### Implementation Guidance

**Deployment**:
```yaml
# Kubernetes Service (NodePort for local, LoadBalancer for cloud)
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
spec:
  type: NodePort
  ports:
  - port: 8002
    targetPort: 8002
    nodePort: 30082
  selector:
    app: websocket-service
```

**Testing**:
```python
# Test WebSocket connection and broadcast
def test_websocket_broadcast():
    # Connect WebSocket client
    with websocket_connect("ws://localhost:8002/ws/user-123?token=<jwt>") as ws:
        # Publish event to task-updates topic
        publish_event("task-updates", {
            "user_id": "user-123",
            "update_type": "task_created",
            "task_data": {"id": "task-456", "title": "New task"}
        })

        # Receive message on WebSocket
        message = ws.receive_json()
        assert message["type"] == "task_created"
        assert message["task"]["id"] == "task-456"
```

### References
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)

---

## Research Topic 6: Database Migration Strategy

### Decision

Use **Alembic** for versioned database migrations with **nullable columns** for all new fields to ensure zero-downtime deployment.

### Migration Plan

**Phase 1: Add New Columns to tasks Table** (backward compatible):
```python
# migrations/001_add_advanced_features.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add new columns (all nullable for backward compatibility)
    op.add_column('tasks', sa.Column('priority', sa.String(20), nullable=True, server_default='normal'))
    op.add_column('tasks', sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('tasks', sa.Column('due_date', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column('recurrence_id', sa.UUID(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_tasks_recurrence_id',
        'tasks', 'recurrence_rules',
        ['recurrence_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for performance
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])
    op.create_index('ix_tasks_priority', 'tasks', ['priority'])
    op.create_index('ix_tasks_tags', 'tasks', ['tags'], postgresql_using='gin')

def downgrade():
    op.drop_constraint('fk_tasks_recurrence_id', 'tasks')
    op.drop_column('tasks', 'recurrence_id')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'priority')
```

**Phase 2: Create New Tables**:
```python
def upgrade():
    # Create recurrence_rules table
    op.create_table(
        'recurrence_rules',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('pattern', sa.String(50), nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_recurrence_rules_user_id', 'recurrence_rules', ['user_id'])
    op.create_index('ix_recurrence_rules_task_id', 'recurrence_rules', ['task_id'])

    # Create reminders table
    op.create_table(
        'reminders',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('reminder_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('delivery_method', sa.String(50), server_default='webhook'),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_reminder_time', 'reminders', ['reminder_time'])
    op.create_index('ix_reminders_status', 'reminders', ['status'])

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('ix_audit_log_task_id', 'audit_log', ['task_id'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('ix_audit_log_event_type', 'audit_log', ['event_type'])
```

### Rationale

1. **Zero-Downtime**: All new columns nullable → existing code continues working
2. **Versioned**: Alembic tracks migration history in database
3. **Reversible**: Each migration has `upgrade()` and `downgrade()` functions
4. **Testable**: Migrations tested in staging before production
5. **Gradual Rollout**: New features opt-in (old tasks without priority/tags work fine)

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Manual SQL scripts | No version tracking; error-prone; hard to rollback |
| Django ORM migrations | Requires Django; project uses FastAPI with SQLModel |
| Flyway or Liquibase | Java-based; adds complexity; Alembic is Python-native |
| Schema-per-microservice | Violates Constitution Principle IV (Single Source of Truth); adds complexity |

### Backward Compatibility

**Existing Tasks**:
- All existing tasks have `priority = 'normal'` (server default)
- `tags`, `due_date`, `recurrence_id` are `NULL` (acceptable for existing tasks)
- No code changes needed for existing task CRUD operations

**Gradual Feature Adoption**:
- Old clients (Phase 3/4): Ignore new columns → Continue working
- New clients (Phase 5): Use new columns → Enhanced features

### Migration Execution

**Local Development**:
```bash
# Generate migration
alembic revision --autogenerate -m "Add advanced features"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Production Deployment**:
1. Deploy migration to staging environment
2. Validate: Run automated tests against staging database
3. Create database backup before production migration
4. Apply migration to production: `alembic upgrade head`
5. Monitor for errors; rollback if issues detected
6. Deploy new application code (Phase 5 features)

### Performance Considerations

**Index Strategy**:
- `due_date`: B-tree index for range queries ("tasks due this week")
- `priority`: B-tree index for filtering ("high priority tasks")
- `tags`: GIN index for array containment queries ("tasks with tag 'work'")
- `user_id`: Existing B-tree index (no change)

**Query Patterns**:
```sql
-- Filter by priority (uses ix_tasks_priority)
SELECT * FROM tasks WHERE user_id = 'user-123' AND priority = 'high';

-- Filter by tags (uses ix_tasks_tags with GIN)
SELECT * FROM tasks WHERE user_id = 'user-123' AND 'work' = ANY(tags);

-- Tasks due soon (uses ix_tasks_due_date)
SELECT * FROM tasks WHERE user_id = 'user-123'
  AND due_date > NOW() AND due_date < NOW() + INTERVAL '7 days'
  ORDER BY due_date ASC;
```

### Testing Migrations

**Unit Tests**:
```python
def test_migration_001_adds_columns():
    # Run migration
    alembic.upgrade("001")

    # Verify columns exist
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tasks')}
    assert 'priority' in columns
    assert 'tags' in columns
    assert 'due_date' in columns
    assert 'recurrence_id' in columns

def test_migration_001_is_reversible():
    # Run migration
    alembic.upgrade("001")

    # Rollback
    alembic.downgrade("base")

    # Verify columns removed
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tasks')}
    assert 'priority' not in columns
```

**Data Integrity Tests**:
```python
def test_existing_tasks_unaffected():
    # Create task before migration
    task = Task(user_id="user-123", title="Old task", completed=False)
    db.add(task)
    db.commit()

    # Run migration
    alembic.upgrade("head")

    # Verify task still exists and functional
    task = db.query(Task).filter(Task.user_id == "user-123").first()
    assert task.title == "Old task"
    assert task.priority == "normal"  # Server default applied
    assert task.tags is None
```

### Implementation Guidance

**Alembic Setup**:
```python
# alembic/env.py
from backend.models import Base  # SQLModel models
from backend.db import engine

target_metadata = Base.metadata

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()
```

**CI/CD Integration**:
```yaml
# .github/workflows/deploy-oke.yml
- name: Run database migrations
  run: |
    # Connect to production database (via bastion or VPN)
    export DATABASE_URL=${{ secrets.DATABASE_URL }}
    alembic upgrade head

- name: Deploy services
  run: |
    helm upgrade backend-api ./infrastructure/helm/backend-api/
```

### References
- [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- [Zero-Downtime Database Migrations](https://www.braintreepayments.com/blog/safe-operations-for-high-volume-postgresql/)

---

## Summary

All 6 research topics have been investigated and decisions documented. Key takeaways:

1. **Dapr Pub/Sub**: Separate YAML files for local/cloud; application code unchanged
2. **Event Schemas**: JSON Schema with semantic versioning; envelope format with `event_id` for deduplication
3. **Idempotency**: Database state reconciliation; no separate idempotency table
4. **Reminder Scheduling**: Dapr Jobs API with PostgreSQL backend; dynamic scheduling
5. **WebSocket Architecture**: Dedicated WebSocket Service subscribing to `task-updates`; user-isolated connection manager
6. **Database Migrations**: Alembic with nullable columns; zero-downtime deployment

**Next Steps**: Proceed to Phase 1 to generate design artifacts (data-model.md, contracts/, quickstart.md).

---

**Research Status**: ✅ COMPLETE
**Date Completed**: 2026-01-06
**Ready for Phase 1**: Yes
