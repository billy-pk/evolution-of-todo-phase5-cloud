---
id: "0002"
stage: "green"
feature: "005-event-driven-microservices"
title: "Microservices Helm Charts Implementation (T111-T114)"
date: "2026-01-07"
model: "claude-sonnet-4.5"
status: "completed"
tags: ["helm", "kubernetes", "microservices", "dapr", "deployment", "infrastructure"]
---

# Prompt History Record: Microservices Helm Charts Implementation

## Prompt

Implement tasks T111 to T114 for Phase V Event-Driven Microservices:

**Tasks (All Parallel [P]):**
- T111: Create notification-service Helm chart in infrastructure/helm/notification-service/
- T112: Create recurring-task-service Helm chart in infrastructure/helm/recurring-task-service/
- T113: Create audit-service Helm chart in infrastructure/helm/audit-service/
- T114: Create websocket-service Helm chart in infrastructure/helm/websocket-service/

**Context:**
- Phase V microservices architecture with event-driven communication via Dapr
- Four specialized microservices for task management operations:
  - **Notification Service**: Delivers reminders via webhook (subscribes to `reminders` topic)
  - **Recurring Task Service**: Generates next task instances (subscribes to `task-events` topic)
  - **Audit Service**: Logs all operations (subscribes to `task-events` topic)
  - **WebSocket Service**: Broadcasts real-time updates (subscribes to `task-updates` topic)
- All services require Dapr sidecar for Pub/Sub integration
- Shared PostgreSQL database (Neon) for state storage
- Deployment targets: Minikube (local) and Oracle Kubernetes Engine (cloud)

## Response

Successfully implemented all 4 microservice Helm charts (T111-T114) in parallel, creating production-ready Kubernetes deployment configurations.

### Files Created

**Per Service (4 services × 8 files = 32 files):**

**notification-service/** (Port 8003):
1. `Chart.yaml` - Chart metadata (v1.0.0)
2. `values.yaml` - Default configuration (ClusterIP service, 256Mi memory limit)
3. `.helmignore` - Helm ignore patterns
4. `templates/_helpers.tpl` - Template helpers
5. `templates/deployment.yaml` - Deployment with Dapr sidecar (subscribes to `reminders`)
6. `templates/service.yaml` - ClusterIP service
7. `templates/configmap.yaml` - Application configuration
8. `templates/secrets.yaml` - Database URL secret

**recurring-task-service/** (Port 8002):
1-8. Same structure as notification-service (subscribes to `task-events`)

**audit-service/** (Port 8004):
1-8. Same structure as notification-service (subscribes to `task-events`)

**websocket-service/** (Port 8005, NodePort 30082):
1-8. Same structure but with NodePort service type for WebSocket connections

**Total Files Created**: 32 files across 4 microservices

### Service Configurations

| Service | Port | Service Type | Dapr App ID | Pub/Sub Topics | NodePort |
|---------|------|--------------|-------------|----------------|----------|
| notification-service | 8003 | ClusterIP | notification-service | reminders | - |
| recurring-task-service | 8002 | ClusterIP | recurring-task-service | task-events | - |
| audit-service | 8004 | ClusterIP | audit-service | task-events | - |
| websocket-service | 8005 | NodePort | websocket-service | task-updates | 30082 |

### Key Features Implemented

**Dapr Integration:**
- Pod annotations for Dapr sidecar injection on all services
- Service-specific Dapr app IDs for service mesh
- HTTP protocol on application port
- Metrics enabled (port 9090)

**Resource Management:**
- Conservative limits for microservices (300m CPU, 256Mi memory)
- Lower requests for efficient resource usage (100m CPU, 128Mi memory)
- Autoscaling disabled by default (can be enabled per service)

**Health Checks:**
- Liveness probe: `GET /health` (30s initial delay, 10s period)
- Readiness probe: `GET /health` (10s initial delay, 5s period)

**Security:**
- Hardened security context (runAsNonRoot: true, drop ALL capabilities)
- Database URL stored in Kubernetes Secret
- No hardcoded credentials

**Service Discovery:**
- All services use Helm template helpers for consistent naming
- Kubernetes DNS for inter-service communication
- Dapr service invocation for synchronous calls

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Backend API     │  │  Notification    │                │
│  │  (Port 8000)     │  │  Service         │                │
│  │  + Dapr Sidecar  │  │  (Port 8003)     │                │
│  │  NodePort 30081  │  │  + Dapr Sidecar  │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Recurring Task  │  │  Audit Service   │                │
│  │  Service         │  │  (Port 8004)     │                │
│  │  (Port 8002)     │  │  + Dapr Sidecar  │                │
│  │  + Dapr Sidecar  │  └──────────────────┘                │
│  └──────────────────┘                                       │
│                                                              │
│  ┌──────────────────┐                                       │
│  │  WebSocket       │                                       │
│  │  Service         │                                       │
│  │  (Port 8005)     │                                       │
│  │  + Dapr Sidecar  │                                       │
│  │  NodePort 30082  │                                       │
│  └──────────────────┘                                       │
│                                                              │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────┐                                       │
│  │  Dapr Control    │                                       │
│  │  Plane           │                                       │
│  │  (Pub/Sub,       │                                       │
│  │   State Store)   │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────┐        ┌──────────────┐
  │  Redpanda   │        │  PostgreSQL  │
  │  (Events)   │        │  (State)     │
  └─────────────┘        └──────────────┘
```

### Validation

All four Helm charts pass validation:

```bash
# notification-service
1 chart(s) linted, 0 chart(s) failed

# recurring-task-service
1 chart(s) linted, 0 chart(s) failed

# audit-service
1 chart(s) linted, 0 chart(s) failed

# websocket-service
1 chart(s) linted, 0 chart(s) failed
```

### Installation Examples

**Deploy all microservices:**

```bash
# Notification Service
helm install notification-service ./infrastructure/helm/notification-service \
  --set-string env.DATABASE_URL="postgresql://..."

# Recurring Task Service
helm install recurring-task-service ./infrastructure/helm/recurring-task-service \
  --set-string env.DATABASE_URL="postgresql://..."

# Audit Service
helm install audit-service ./infrastructure/helm/audit-service \
  --set-string env.DATABASE_URL="postgresql://..."

# WebSocket Service
helm install websocket-service ./infrastructure/helm/websocket-service \
  --set-string env.DATABASE_URL="postgresql://..."
```

**Access WebSocket Service (NodePort):**
```bash
# Local Minikube
ws://localhost:30082/ws/{user_id}
```

### Constitution Compliance

✅ **Principle II (Stateless Server Design)**: All microservices are stateless, share database
✅ **Principle III (Security First)**: Kubernetes Secrets for DATABASE_URL, hardened security context
✅ **Principle VI (Extensibility and Modularity)**: Each microservice has dedicated Helm chart
✅ **Principle VII (Infrastructure as Code)**: All deployment configs version-controlled
✅ **Principle X (Event-Driven Architecture)**: Dapr Pub/Sub integration via annotations
✅ **Principle XI (Cloud Portability)**: Application code unchanged, Dapr components handle environment

### Design Patterns

**Single Responsibility:**
- Notification Service: Only handles reminder delivery
- Recurring Task Service: Only generates next task instances
- Audit Service: Only logs events
- WebSocket Service: Only broadcasts real-time updates

**Idempotency:**
- All services handle duplicate events gracefully
- Database reconciliation before action
- Event ID tracking for deduplication

**Observability:**
- Health probes on all services
- Dapr metrics enabled (port 9090)
- Structured logging via LOG_LEVEL environment variable

### Next Steps

The microservices Helm charts are complete. Next tasks in Phase 10:
- **T115-T119**: Create Helm chart for frontend (Next.js, no Dapr sidecar)
- **T120-T123**: Create deployment scripts (deploy-local.sh, deploy-cloud.sh)

### Performance Characteristics

**Resource Footprint** (per service):
- CPU Request: 100m (0.1 cores)
- CPU Limit: 300m (0.3 cores)
- Memory Request: 128Mi
- Memory Limit: 256Mi

**Total Cluster Resources** (4 microservices):
- CPU: 400m request, 1.2 cores limit
- Memory: 512Mi request, 1Gi limit

Plus Dapr sidecars (typically ~50m CPU, 128Mi memory per sidecar = 200m CPU, 512Mi memory total)

## Artifacts

- **Helm Charts**: 4 microservices (32 files total)
- **Validation**: All charts pass `helm lint` with 0 errors
- **Tasks Updated**: tasks.md marks T111-T114 as completed
- **Total Infrastructure Files**: 37 YAML/TPL files across 5 Helm charts (backend-api + 4 microservices)

## Status

✅ **COMPLETED** - All 4 microservice Helm charts implemented and validated in parallel
