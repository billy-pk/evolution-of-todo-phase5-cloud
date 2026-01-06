# Quickstart Guide: Phase V Event-Driven Microservices

**Feature**: Phase V Event-Driven Microservices Architecture
**Branch**: `005-event-driven-microservices`
**Date**: 2026-01-06

## Overview

This guide walks you through setting up and testing the Phase V event-driven microservices architecture locally on Minikube. Follow these steps to run all 6 microservices with Redpanda event streaming.

**Time to Complete**: 30-45 minutes (first time)

---

## Prerequisites

### Required Software

1. **Docker** (v20+)
```bash
docker --version
```

2. **Minikube** (v1.28+)
```bash
minikube version
```

3. **Kubectl** (v1.28+)
```bash
kubectl version --client
```

4. **Helm** (v3.x)
```bash
helm version
```

5. **Dapr CLI** (v1.14+)
```bash
dapr version
```

6. **Python** (v3.13)
```bash
python --version
```

7. **Node.js** (v18+)
```bash
node --version
```

### Install Missing Tools

**Minikube**:
```bash
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

**Dapr CLI**:
```bash
# macOS/Linux
wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash
```

**Helm**:
```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

---

## Step 1: Start Minikube

Start a local Kubernetes cluster with sufficient resources:

```bash
# Start Minikube with 4 CPUs and 8GB RAM
minikube start --cpus=4 --memory=8192

# Verify Minikube is running
minikube status
```

Expected output:
```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

---

## Step 2: Initialize Dapr in Kubernetes

Install Dapr control plane to Minikube:

```bash
# Initialize Dapr in Kubernetes mode
dapr init -k

# Wait for Dapr pods to be ready (takes 1-2 minutes)
kubectl wait --for=condition=ready pod --all -n dapr-system --timeout=120s

# Verify Dapr installation
dapr status -k
```

Expected output:
```
  NAME                   NAMESPACE    HEALTHY  STATUS   REPLICAS  VERSION  AGE  CREATED
  dapr-dashboard         dapr-system  True     Running  1         1.14.0   30s  2026-01-06 10:00:00
  dapr-sidecar-injector  dapr-system  True     Running  1         1.14.0   30s  2026-01-06 10:00:00
  dapr-sentry            dapr-system  True     Running  1         1.14.0   30s  2026-01-06 10:00:00
  dapr-operator          dapr-system  True     Running  1         1.14.0   30s  2026-01-06 10:00:00
  dapr-placement         dapr-system  True     Running  1         1.14.0   30s  2026-01-06 10:00:00
```

---

## Step 3: Start Redpanda Docker

Start Redpanda for local event streaming:

```bash
# Start Redpanda Docker container
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

# Verify Redpanda is running
docker ps | grep redpanda
```

**Troubleshooting**: If port 9092 is already in use:
```bash
# Stop existing Kafka/Redpanda
docker stop $(docker ps -q --filter "publish=9092")

# Then retry the Redpanda start command
```

---

## Step 4: Create Kubernetes Secrets

Create required secrets for services:

```bash
# 1. PostgreSQL credentials (Neon or local PostgreSQL)
kubectl create secret generic postgres-credentials \
  --from-literal=connectionString="postgresql://user:password@host:5432/evolution_todo"

# 2. OpenAI API key (existing from Phase 3/4)
kubectl create secret generic openai-credentials \
  --from-literal=apiKey="sk-your-openai-api-key"

# 3. Better Auth secret (existing from Phase 3/4)
kubectl create secret generic better-auth-secret \
  --from-literal=secret="your-shared-secret-min-32-chars"

# Verify secrets created
kubectl get secrets
```

Expected output:
```
NAME                    TYPE     DATA   AGE
postgres-credentials    Opaque   1      10s
openai-credentials      Opaque   1      10s
better-auth-secret      Opaque   1      10s
```

**Note**: Replace placeholders with actual credentials. For local development, you can use a local PostgreSQL database or Neon's free tier.

---

## Step 5: Run Database Migrations

Apply Phase V database schema changes:

```bash
# Navigate to backend directory
cd backend

# Install dependencies (if not already done)
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run migrations
alembic upgrade head

# Verify new tables exist
psql $DATABASE_URL -c "\dt"
```

Expected output (should include):
```
 public | tasks             | table | user
 public | recurrence_rules  | table | user
 public | reminders         | table | user
 public | audit_log         | table | user
 public | dapr_state        | table | user
 public | dapr_jobs         | table | user
```

---

## Step 6: Apply Dapr Components

Deploy Dapr component configurations:

```bash
# Apply local Dapr components
kubectl apply -f specs/005-event-driven-microservices/contracts/dapr-components/local/

# Verify components are loaded
dapr components -k
```

Expected output:
```
NAMESPACE  NAME         TYPE                      VERSION  SCOPES  CREATED              AGE
default    pubsub       pubsub.kafka              v1               2026-01-06 10:00:00  10s
default    statestore   state.postgresql          v1               2026-01-06 10:00:00  10s
default    jobs         jobs.postgresql           v1               2026-01-06 10:00:00  10s
default    kubernetes   secretstores.kubernetes   v1               2026-01-06 10:00:00  10s
```

---

## Step 7: Deploy Services to Minikube

### Build Docker Images

```bash
# Enable Minikube Docker environment
eval $(minikube docker-env)

# Build backend image
cd backend
docker build -t evolution-todo-backend:latest .

# Build frontend image
cd ../frontend
docker build -t evolution-todo-frontend:latest .

# Build microservices images
cd ../services/notification-service
docker build -t notification-service:latest .

cd ../recurring-task-service
docker build -t recurring-task-service:latest .

cd ../audit-service
docker build -t audit-service:latest .

cd ../websocket-service
docker build -t websocket-service:latest .

# Return to repo root
cd ../..
```

### Deploy with Helm

```bash
# Deploy Backend API
helm install backend-api ./infrastructure/helm/backend-api/ \
  -f ./infrastructure/helm/backend-api/values-local.yaml

# Deploy Notification Service
helm install notification-service ./infrastructure/helm/notification-service/

# Deploy Recurring Task Service
helm install recurring-task-service ./infrastructure/helm/recurring-task-service/

# Deploy Audit Service
helm install audit-service ./infrastructure/helm/audit-service/

# Deploy WebSocket Service
helm install websocket-service ./infrastructure/helm/websocket-service/

# Deploy Frontend
helm install frontend ./infrastructure/helm/frontend/ \
  -f ./infrastructure/helm/frontend/values-local.yaml

# Verify all pods are running
kubectl get pods
```

Expected output (after 2-3 minutes):
```
NAME                                    READY   STATUS    RESTARTS   AGE
backend-api-...                         2/2     Running   0          2m
notification-service-...                2/2     Running   0          2m
recurring-task-service-...              2/2     Running   0          2m
audit-service-...                       2/2     Running   0          2m
websocket-service-...                   2/2     Running   0          2m
frontend-...                            1/1     Running   0          2m
```

**Note**: Pods with Dapr sidecars show `2/2` (app container + Dapr sidecar).

---

## Step 8: Access the Application

Get Minikube IP and access services via NodePort:

```bash
# Get Minikube IP
minikube ip
```

**Service URLs**:
- **Frontend**: `http://<minikube-ip>:30080`
- **Backend API**: `http://<minikube-ip>:30081`
- **WebSocket Service**: `ws://<minikube-ip>:30082`

**Example**:
```bash
# If Minikube IP is 192.168.49.2
Frontend: http://192.168.49.2:30080
Backend: http://192.168.49.2:30081
WebSocket: ws://192.168.49.2:30082
```

Open `http://<minikube-ip>:30080` in your browser to access the application.

---

## Test Scenarios

### Test Scenario 1: Create Recurring Task

**Objective**: Verify recurring task generation works end-to-end.

**Steps**:
1. Sign in to the application (`http://<minikube-ip>:30080`)
2. Navigate to Chat (`/chat`)
3. Send message: *"Create a task: Weekly team meeting, recurrence weekly, priority high, tags work and meetings"*
4. Wait for AI response confirming task creation
5. Mark the task as complete (via chat: *"Mark task 'Weekly team meeting' as complete"*)
6. Wait 10-30 seconds
7. List tasks: *"Show me all my tasks"*
8. **Expected Result**: New instance of "Weekly team meeting" appears with next week's due date

**Verification**:
```bash
# Check audit log for task.completed and task.created events
kubectl logs -l app=audit-service --tail=50
```

Expected log entries:
```
[INFO] Received event: task.completed - Task ID: xxx, User: user-123
[INFO] Audit log entry created: task.completed
[INFO] Received event: task.created - Task ID: yyy, User: user-123 (recurring instance)
[INFO] Audit log entry created: task.created
```

---

### Test Scenario 2: Due Date Reminders

**Objective**: Verify reminder scheduling and delivery.

**Steps**:
1. Send message: *"Create a task: Submit report, due tomorrow at 5pm, reminder 1 hour before"*
2. Wait for confirmation
3. Check reminder was scheduled:
```bash
# Query reminders table
kubectl exec -it <backend-pod> -- python -c "
from backend.models import Reminder
from backend.db import engine
from sqlmodel import Session, select
with Session(engine) as session:
    reminders = session.exec(select(Reminder)).all()
    for r in reminders:
        print(f'Reminder ID: {r.id}, Time: {r.reminder_time}, Status: {r.status}')
"
```
4. **Expected Result**: Reminder with status `pending` and correct `reminder_time`

**Fast-forward test** (optional):
```bash
# Manually trigger reminder (for testing without waiting)
# This would require accessing Dapr Jobs API directly
```

---

### Test Scenario 3: Search and Filter

**Objective**: Verify advanced search/filter works with priorities and tags.

**Steps**:
1. Create multiple tasks with different priorities and tags:
   - *"Create task: Fix bug, priority high, tag work"*
   - *"Create task: Grocery shopping, priority low, tag personal"*
   - *"Create task: Code review, priority normal, tag work"*
2. Filter by priority: *"Show me all high priority tasks"*
3. **Expected Result**: Only "Fix bug" appears
4. Filter by tag: *"Show me tasks with tag 'work'"*
5. **Expected Result**: "Fix bug" and "Code review" appear

---

### Test Scenario 4: Live Updates (WebSocket)

**Objective**: Verify WebSocket broadcasts real-time updates.

**Steps**:
1. Open application in two browser tabs (Tab A and Tab B)
2. Sign in with the same user in both tabs
3. In Tab A: Create a new task via chat
4. **Expected Result**: Task appears immediately in Tab B without refresh

**Verification**:
```bash
# Check WebSocket service logs
kubectl logs -l app=websocket-service --tail=20
```

Expected log entries:
```
[INFO] WebSocket connection established: user-123
[INFO] Received event from task-updates topic: task_created
[INFO] Broadcasting to user-123: task_created (1 connections)
```

---

### Test Scenario 5: Audit Trail

**Objective**: Verify all task operations are logged.

**Steps**:
1. Perform various task operations (create, update, complete, delete)
2. Query audit log:
```bash
kubectl exec -it <backend-pod> -- python -c "
from backend.models import AuditLog
from backend.db import engine
from sqlmodel import Session, select
with Session(engine) as session:
    logs = session.exec(
        select(AuditLog)
        .where(AuditLog.user_id == 'user-123')
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
    ).all()
    for log in logs:
        print(f'{log.timestamp} - {log.event_type} - Task ID: {log.task_id}')
"
```
3. **Expected Result**: All operations appear in chronological order

---

## End-to-End Validation Checklist

Run through this checklist to verify the system is working correctly:

- [ ] ✅ All 6 microservices running (`kubectl get pods` shows 6 pods with STATUS=Running)
- [ ] ✅ Dapr components healthy (`dapr components -k` shows 4 components)
- [ ] ✅ Redpanda running (`docker ps | grep redpanda` shows container)
- [ ] ✅ Database tables exist (tasks, recurrence_rules, reminders, audit_log)
- [ ] ✅ Frontend accessible via browser (`http://<minikube-ip>:30080`)
- [ ] ✅ Chat endpoint responds (send message and get AI response)
- [ ] ✅ Task creation works (create task via chat, verify in database)
- [ ] ✅ Recurring task generation works (complete recurring task → new instance created)
- [ ] ✅ Reminder scheduling works (create task with reminder → reminder in database)
- [ ] ✅ Search/filter works (filter by priority/tag → correct results)
- [ ] ✅ WebSocket updates work (create task in one tab → appears in other tab)
- [ ] ✅ Audit log works (all operations logged to audit_log table)
- [ ] ✅ Event flow works (publish event → consumers process within 2 seconds)

**All checks passed?** 🎉 Phase V is running successfully!

---

## Monitoring and Debugging

### View Logs

**Backend API**:
```bash
kubectl logs -l app=backend-api --tail=100 -f
```

**Notification Service**:
```bash
kubectl logs -l app=notification-service --tail=100 -f
```

**Recurring Task Service**:
```bash
kubectl logs -l app=recurring-task-service --tail=100 -f
```

**Audit Service**:
```bash
kubectl logs -l app=audit-service --tail=100 -f
```

**WebSocket Service**:
```bash
kubectl logs -l app=websocket-service --tail=100 -f
```

**Dapr Sidecar** (for specific pod):
```bash
kubectl logs <pod-name> -c daprd --tail=100 -f
```

### Check Event Flow

**Publish test event manually**:
```bash
# Port-forward Dapr sidecar
kubectl port-forward <backend-pod> 3500:3500

# Publish event via Dapr HTTP API
curl -X POST http://localhost:3500/v1.0/publish/pubsub/task-events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "task.created",
    "event_id": "test-123",
    "task_id": "test-456",
    "user_id": "test-user",
    "task_data": {"title": "Test task", "completed": false},
    "timestamp": "2026-01-06T10:00:00Z",
    "schema_version": "1.0.0"
  }'
```

**Verify consumers received event**:
```bash
# Check audit service logs
kubectl logs -l app=audit-service --tail=10 | grep "test-123"
```

### Access Dapr Dashboard

```bash
# Start Dapr dashboard
dapr dashboard -k

# Open browser to http://localhost:8080
```

The dashboard shows:
- All Dapr components
- Running applications
- Pub/Sub subscriptions
- Metrics and traces

---

## Troubleshooting

### Problem: Pods not starting

**Symptoms**: `kubectl get pods` shows STATUS=CrashLoopBackOff or ImagePullBackOff

**Solution**:
```bash
# Check pod events
kubectl describe pod <pod-name>

# Common issues:
# 1. Image not found → Rebuild image with `eval $(minikube docker-env)`
# 2. Secret not found → Verify secrets exist: `kubectl get secrets`
# 3. Database connection failed → Check DATABASE_URL in secret
```

### Problem: Events not flowing

**Symptoms**: Tasks created but audit log empty, recurring tasks not generating

**Solution**:
```bash
# 1. Check Redpanda is running
docker ps | grep redpanda

# 2. Check Dapr Pub/Sub component
dapr components -k | grep pubsub

# 3. Check consumer logs for errors
kubectl logs -l app=audit-service --tail=50

# 4. Verify topics exist in Redpanda
docker exec -it redpanda rpk topic list
```

Expected topics: `task-events`, `reminders`, `task-updates`

### Problem: Reminders not triggering

**Symptoms**: Reminder created but notification not delivered

**Solution**:
```bash
# 1. Check Dapr Jobs component
dapr components -k | grep jobs

# 2. Check scheduled jobs
kubectl exec -it <backend-pod> -- python -c "
from backend.db import engine
from sqlmodel import text, Session
with Session(engine) as session:
    result = session.exec(text('SELECT * FROM dapr_jobs ORDER BY due_time DESC LIMIT 10'))
    for row in result:
        print(row)
"

# 3. Check Notification Service logs
kubectl logs -l app=notification-service --tail=50 | grep "reminder"
```

### Problem: WebSocket not connecting

**Symptoms**: Browser console shows WebSocket connection failed

**Solution**:
```bash
# 1. Check WebSocket Service is running
kubectl get pods -l app=websocket-service

# 2. Verify NodePort is accessible
minikube service websocket-service --url

# 3. Check WebSocket Service logs
kubectl logs -l app=websocket-service --tail=50

# 4. Test WebSocket connection manually
wscat -c ws://<minikube-ip>:30082/ws/<user-id>?token=<jwt>
```

---

## Cleanup

To stop and remove all resources:

```bash
# Uninstall Helm releases
helm uninstall backend-api notification-service recurring-task-service audit-service websocket-service frontend

# Delete Dapr components
kubectl delete -f specs/005-event-driven-microservices/contracts/dapr-components/local/

# Delete secrets
kubectl delete secret postgres-credentials openai-credentials better-auth-secret

# Stop Redpanda
docker stop redpanda
docker rm redpanda

# Stop Minikube
minikube stop

# (Optional) Delete Minikube cluster
minikube delete
```

---

## Next Steps

1. ✅ **Local Setup Complete** - All 6 microservices running
2. ⏭️ **Run `/sp.tasks`** - Generate implementation task breakdown
3. ⏭️ **Implement Phase 0 Research** - Finalize architectural decisions
4. ⏭️ **Implement Phase 1 Design** - Code data models and event publishers
5. ⏭️ **Deploy to Cloud (OKE)** - Follow cloud deployment guide

---

## Resources

- **Dapr Documentation**: https://docs.dapr.io/
- **Redpanda Documentation**: https://docs.redpanda.com/
- **Minikube Documentation**: https://minikube.sigs.k8s.io/docs/
- **Helm Documentation**: https://helm.sh/docs/
- **Kubernetes Documentation**: https://kubernetes.io/docs/

---

**Status**: ✅ COMPLETE
**Last Updated**: 2026-01-06
**Estimated Setup Time**: 30-45 minutes
