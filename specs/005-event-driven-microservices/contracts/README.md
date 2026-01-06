# Phase V Event Contracts and Dapr Components

**Feature**: Phase V Event-Driven Microservices Architecture
**Branch**: `005-event-driven-microservices`
**Date**: 2026-01-06

## Overview

This directory contains:
1. **Event Schemas** (`events/`) - JSON Schema definitions for all event topics
2. **Dapr Components** (`dapr-components/`) - Environment-specific Dapr component configurations

---

## Directory Structure

```
contracts/
├── events/
│   ├── task-events.schema.json       # Task CRUD events (v1.0.0)
│   ├── reminders.schema.json          # Reminder lifecycle events (v1.0.0)
│   └── task-updates.schema.json       # WebSocket UI updates (v1.0.0)
├── dapr-components/
│   ├── local/
│   │   ├── pubsub-redpanda.yaml       # Redpanda Docker (no auth)
│   │   ├── statestore-postgresql.yaml # PostgreSQL State Store
│   │   ├── jobs.yaml                  # Dapr Jobs API
│   │   └── secrets.yaml               # Kubernetes Secrets
│   └── cloud/
│       ├── pubsub-redpanda-cloud.yaml # Redpanda Cloud (SASL/SSL)
│       ├── statestore-postgresql.yaml # Same PostgreSQL (cloud credentials)
│       ├── jobs.yaml                  # Dapr Jobs API
│       └── secrets.yaml               # Kubernetes Secrets (OKE)
└── README.md                          # This file
```

---

## Event Schemas

### Schema Versioning

All event schemas follow **semantic versioning** (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (remove required field, change field type)
- **MINOR**: Backward-compatible additions (new optional field)
- **PATCH**: Documentation or validation rule changes

**Current Versions**:
- `task-events.schema.json`: **v1.0.0**
- `reminders.schema.json`: **v1.0.0**
- `task-updates.schema.json`: **v1.0.0**

### Event Topics

| Topic | Schema | Purpose | Producers | Consumers |
|-------|--------|---------|-----------|-----------|
| `task-events` | `task-events.schema.json` | Task CRUD operations | Backend API (via MCP tools) | Audit Service, Recurring Task Service |
| `reminders` | `reminders.schema.json` | Reminder scheduling and delivery | Backend API, Notification Service | Notification Service (consumes own events for tracking) |
| `task-updates` | `task-updates.schema.json` | Real-time UI updates | Backend API | WebSocket Service (broadcasts to frontend clients) |

### Schema Evolution Example

**Version 1.0.0** (current):
```json
{
  "event_type": "task.created",
  "task_data": {
    "title": "string",
    "completed": "boolean",
    "priority": "string"
  }
}
```

**Version 1.1.0** (backward-compatible addition):
```json
{
  "event_type": "task.created",
  "task_data": {
    "title": "string",
    "completed": "boolean",
    "priority": "string",
    "assignee": "string (optional, new field)"
  }
}
```

**Version 2.0.0** (breaking change - NOT ALLOWED without migration):
```json
{
  "event_type": "task.created",
  "task_data": {
    "title": "string",
    "completed": "boolean",
    "priority_level": "integer (renamed from 'priority' string)"
  }
}
```

### Compatibility Rules

**Producers (Backend API)**:
1. MUST include `schema_version` in every event
2. MUST validate events against JSON Schema before publishing
3. MUST NOT remove required fields (breaking change)
4. CAN add optional fields (MINOR version bump)

**Consumers (Services)**:
1. MUST handle all MINOR versions within the same MAJOR version
2. MUST reject events with unknown MAJOR versions
3. MUST ignore unknown fields (forward compatibility)
4. SHOULD log schema version mismatches for monitoring

---

## Dapr Components

### Environment Separation

**Local (Minikube + Redpanda Docker)**:
- Purpose: Development and testing
- Pub/Sub: Redpanda Docker (single-node, no authentication)
- PostgreSQL: Neon (same as cloud, but can be local PostgreSQL for offline development)
- Secrets: Kubernetes Secrets (local cluster)

**Cloud (OKE + Redpanda Cloud)**:
- Purpose: Production deployment
- Pub/Sub: Redpanda Cloud (multi-node, SASL/SSL secured)
- PostgreSQL: Neon (production database)
- Secrets: Kubernetes Secrets (OKE) or Oracle Cloud Vault (future)

### Application Code Portability

**✅ Application code remains 100% identical between local and cloud**:
```python
# backend/services/event_publisher.py
from dapr.clients import DaprClient
import json

def publish_task_event(event_payload):
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",  # Component name (same in local and cloud)
            topic_name="task-events",
            data=json.dumps(event_payload)
        )
```

**Only Dapr component YAML files change**:
```bash
# Deploy to local
kubectl apply -f contracts/dapr-components/local/

# Deploy to cloud
kubectl apply -f contracts/dapr-components/cloud/
```

### Deployment Instructions

#### Local Deployment (Minikube)

1. **Start Redpanda Docker**:
```bash
docker run -d --name redpanda \
  -p 9092:9092 \
  -p 9644:9644 \
  redpandadata/redpanda:latest \
  redpanda start \
  --overprovisioned \
  --smp 1 \
  --memory 1G \
  --reserve-memory 0M \
  --node-id 0 \
  --check=false
```

2. **Create Kubernetes Secrets**:
```bash
# PostgreSQL credentials
kubectl create secret generic postgres-credentials \
  --from-literal=connectionString="postgresql://user:password@host:5432/dbname"

# OpenAI API key (existing from Phase 3/4)
kubectl create secret generic openai-credentials \
  --from-literal=apiKey="sk-..."

# Better Auth secret (existing from Phase 3/4)
kubectl create secret generic better-auth-secret \
  --from-literal=secret="<shared-secret>"
```

3. **Apply Dapr Components**:
```bash
kubectl apply -f contracts/dapr-components/local/
```

4. **Verify Components**:
```bash
dapr components -k
```

Expected output:
```
NAMESPACE  NAME         TYPE                  VERSION  SCOPES  CREATED              AGE
default    pubsub       pubsub.kafka          v1               2026-01-06 10:00:00  2m
default    statestore   state.postgresql      v1               2026-01-06 10:00:00  2m
default    jobs         jobs.postgresql       v1               2026-01-06 10:00:00  2m
default    kubernetes   secretstores.kubernetes v1             2026-01-06 10:00:00  2m
```

#### Cloud Deployment (OKE)

1. **Get Redpanda Cloud Credentials**:
- Log in to Redpanda Cloud console
- Create cluster (if not exists)
- Copy broker URL (e.g., `abc123.redpanda.cloud:9092`)
- Generate SASL credentials (username/password)

2. **Update Dapr Component**:
```bash
# Edit cloud/pubsub-redpanda-cloud.yaml
# Replace <REDPANDA_CLOUD_BROKER_URL> with actual URL
```

3. **Create Kubernetes Secrets (OKE)**:
```bash
# PostgreSQL credentials (Neon production)
kubectl create secret generic postgres-credentials \
  --from-literal=connectionString="postgresql://user:password@...neon.tech/dbname?sslmode=require"

# Redpanda Cloud credentials
kubectl create secret generic redpanda-credentials \
  --from-literal=username="<username>" \
  --from-literal=password="<password>"

# OpenAI API key
kubectl create secret generic openai-credentials \
  --from-literal=apiKey="sk-..."

# Better Auth secret (production)
kubectl create secret generic better-auth-secret \
  --from-literal=secret="<production-shared-secret>"
```

4. **Apply Dapr Components**:
```bash
kubectl apply -f contracts/dapr-components/cloud/
```

5. **Verify Components**:
```bash
dapr components -k
```

---

## Contract Testing

### Validate Event Schemas

```python
# backend/tests/contract/test_event_schemas.py
import json
import jsonschema
import pytest

def load_schema(schema_file):
    with open(f"specs/005-event-driven-microservices/contracts/events/{schema_file}") as f:
        return json.load(f)

def test_task_created_event_validates():
    schema = load_schema("task-events.schema.json")
    event = {
        "event_type": "task.created",
        "event_id": "123e4567-e89b-12d3-a456-426614174000",
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user-123",
        "task_data": {
            "title": "Test task",
            "completed": False,
            "priority": "normal",
            "tags": ["work"],
            "due_date": "2026-01-13T10:00:00Z",
            "recurrence_id": None
        },
        "timestamp": "2026-01-06T10:00:00Z",
        "schema_version": "1.0.0"
    }
    jsonschema.validate(event, schema)  # Should not raise

def test_task_created_event_rejects_invalid():
    schema = load_schema("task-events.schema.json")
    event = {
        "event_type": "task.created",
        # Missing required fields
        "task_data": {"title": "Test"}
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(event, schema)
```

### Test Event Publishing

```python
# backend/tests/integration/test_event_publishing.py
from backend.services.event_publisher import publish_task_event
from dapr.clients import DaprClient
import time

def test_event_published_to_redpanda():
    event_payload = {
        "event_type": "task.created",
        "event_id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "user_id": "test-user",
        "task_data": {
            "title": "Integration test task",
            "completed": False,
            "priority": "normal"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "schema_version": "1.0.0"
    }

    # Publish event
    publish_task_event(event_payload)

    # Wait for consumer to process
    time.sleep(2)

    # Verify event was consumed (check audit_log table or consumer logs)
    audit = db.query(AuditLog).filter(
        AuditLog.user_id == "test-user",
        AuditLog.event_type == "task.created"
    ).first()
    assert audit is not None
```

---

## Monitoring and Observability

### Event Metrics

Track these metrics in production:

1. **Event Publishing**:
   - `events_published_total{topic, event_type}` - Total events published
   - `event_publish_duration_seconds{topic}` - Publish latency
   - `event_publish_errors_total{topic, error_type}` - Publish failures

2. **Event Consumption**:
   - `events_consumed_total{topic, consumer, event_type}` - Total events consumed
   - `event_processing_duration_seconds{consumer, event_type}` - Processing latency
   - `event_processing_errors_total{consumer, event_type}` - Processing failures

3. **Schema Validation**:
   - `schema_validation_errors_total{topic, schema_version}` - Invalid events
   - `schema_version_mismatches_total{topic, expected, actual}` - Version conflicts

### Alerting

Set up alerts for:

- ❌ Event publish failure rate >1% (5min window)
- ❌ Event processing lag >30 seconds
- ❌ Schema validation failures >0 (immediate)
- ❌ Dapr component unhealthy (immediate)
- ⚠️ Event processing latency >5 seconds (p95)

---

## Troubleshooting

### Event Not Published

1. Check Dapr component is healthy: `dapr components -k`
2. Check Redpanda is running: `docker ps | grep redpanda` (local) or check Redpanda Cloud console (cloud)
3. Check application logs for publish errors
4. Verify Kubernetes Secret exists: `kubectl get secret postgres-credentials`

### Event Not Consumed

1. Check consumer service is running: `kubectl get pods`
2. Check consumer logs: `kubectl logs <pod-name>`
3. Verify consumer is subscribed to topic (check Dapr subscription annotation)
4. Check Redpanda topic exists: `rpk topic list` (local) or Redpanda Cloud console (cloud)

### Schema Validation Failure

1. Check event payload matches JSON Schema
2. Verify `schema_version` is correct
3. Check for typos in field names
4. Review recent schema changes (CHANGELOG.md)

### Dapr Component Configuration Issues

1. Verify YAML syntax: `kubectl apply --dry-run=client -f <yaml-file>`
2. Check secret references exist: `kubectl get secrets`
3. Review Dapr logs: `kubectl logs -n dapr-system dapr-operator-<pod-id>`
4. Test component independently: `dapr run --app-id test --components-path ./contracts/dapr-components/local/`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-06 | Initial event schemas and Dapr components for Phase V |

---

## Next Steps

1. ✅ **Event Schemas** - Complete (3 schemas defined)
2. ✅ **Dapr Components** - Complete (local + cloud configurations)
3. ⏭️ **Contract Tests** - Implement in `backend/tests/contract/`
4. ⏭️ **Monitoring** - Set up Prometheus metrics for event publishing/consumption
5. ⏭️ **Documentation** - Update CLAUDE.md with Phase V event-driven patterns

---

**Status**: ✅ COMPLETE
**Maintainer**: Evolution of Todo Phase V Team
**Last Updated**: 2026-01-06
