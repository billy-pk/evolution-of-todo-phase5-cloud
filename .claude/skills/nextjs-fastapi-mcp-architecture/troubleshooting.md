# Deployment Troubleshooting Guide

This guide documents real production issues encountered during Kubernetes/Minikube deployment and their solutions.

---

## Table of Contents

1. [Node.js Happy Eyeballs ETIMEDOUT in Kubernetes](#1-nodejs-happy-eyeballs-etimedout-in-kubernetes)
2. [JWKS Decryption Error After Secret Change](#2-jwks-decryption-error-after-secret-change)
3. [Duplicate Task Creation from OpenAI Agents SDK](#3-duplicate-task-creation-from-openai-agents-sdk)
4. [Port-Forward Connection Issues](#4-port-forward-connection-issues)
5. [Dapr Operator Pod CreateContainerError](#5-dapr-operator-pod-createcontainererror)
6. [Idempotency Patterns for Event-Driven Systems](#6-idempotency-patterns-for-event-driven-systems)
7. [JSONB Query Patterns in PostgreSQL](#7-jsonb-query-patterns-in-postgresql)
8. [General Debugging Commands](#8-general-debugging-commands)

---

## 1. Node.js Happy Eyeballs ETIMEDOUT in Kubernetes

### Symptoms
```
Error: AggregateError
  code: 'ETIMEDOUT'
```
- Frontend (Node.js) pod cannot connect to external databases (e.g., Neon PostgreSQL)
- Backend (Python) pod CAN connect to same database successfully
- `nc` and `wget` from frontend pod work, but Node.js fails
- Error occurs with both direct and pooler database URLs

### Root Cause
Node.js's Happy Eyeballs implementation (`autoSelectFamily`) tries to connect to IPv4 and IPv6 addresses concurrently. In containerized Kubernetes environments with restricted networking, these concurrent connection attempts cause timeouts even though sequential connections work fine.

### Solution
Add this to any early-loading file in your Next.js app (e.g., `lib/auth.ts`):

```typescript
import dns from "dns";
import net from "net";

// Fix for Node.js Happy Eyeballs issue in containerized environments
// Disable concurrent IPv4/IPv6 connection attempts
net.setDefaultAutoSelectFamily(false);

// Also prioritize IPv4 for DNS resolution
dns.setDefaultResultOrder("ipv4first");
```

### Verification
Test from frontend pod:
```bash
kubectl exec <frontend-pod> -- node -e '
const net = require("net");
net.setDefaultAutoSelectFamily(false);
const socket = net.connect(443, "your-database-host.com", () => {
  console.log("Connected!");
  socket.end();
});
'
```

### After Fix
```bash
# Rebuild image with fix
eval $(minikube docker-env)
docker build -t frontend:latest ./frontend

# Restart deployment
kubectl rollout restart deployment frontend
```

---

## 2. JWKS Decryption Error After Secret Change

### Symptoms
```
BetterAuthError: Failed to decrypt private key. Make sure the secret currently
in use is the same as the one used to encrypt the private key.
```
- Sign-in redirects back to sign-in page
- User appears to authenticate but session doesn't persist
- Frontend logs show decryption failures

### Root Cause
Better Auth stores JWKS (JSON Web Key Set) keys in the database, encrypted with `BETTER_AUTH_SECRET`. If the secret changes, stored keys cannot be decrypted, breaking JWT signing/validation.

### Solution
Clean the JWKS table in the database:

```bash
# Option 1: Using backend pod with psycopg2
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('DELETE FROM jwks')
conn.commit()
print('JWKS table cleaned')
conn.close()
"

# Option 2: Using psql directly
psql $DATABASE_URL -c "DELETE FROM jwks;"
```

Then restart frontend to regenerate keys:
```bash
kubectl rollout restart deployment frontend
```

### Prevention
- **NEVER** change `BETTER_AUTH_SECRET` in production without cleaning JWKS first
- Keep secret consistent across all deployments (frontend and backend)
- Store secret securely and don't regenerate unnecessarily
- Document the secret location and rotation procedure

---

## 3. Duplicate Task Creation from OpenAI Agents SDK

### Symptoms
- Single chat request creates TWO identical tasks in database
- OpenAI dashboard shows only ONE tool call
- MCP server logs show two `CallToolRequest` events
- Each duplicate has different task_id and event_id

### Root Cause
The **OpenAI Agents SDK** makes duplicate internal calls to MCP tools during streaming responses. This is undocumented behavior - even though:
- ChatKit sends ONE HTTP request
- OpenAI API receives ONE request
- Dashboard shows ONE tool call
- The SDK calls MCP tools **TWICE** internally (visible in logs as different source ports)

### Evidence from Logs
```
MCP Server Logs:
Processing request of type CallToolRequest
Published task.created event: <event-id-1> for task <task-id-1>
INFO: 10.244.0.154:35598 - "POST / HTTP/1.1" 200 OK

Processing request of type CallToolRequest  <-- DUPLICATE CALL
Published task.created event: <event-id-2> for task <task-id-2>
INFO: 10.244.0.154:35606 - "POST / HTTP/1.1" 200 OK  <-- Different port
```

### Solution: Two-Layer Idempotency Protection

#### Layer 1: MCP Server Tool-Level Cache (PRIMARY FIX)

Add task creation cache to `backend/tools/server.py`:

```python
from datetime import datetime, UTC

# At module level (after FastMCP initialization)
_task_creation_cache = {}  # {(user_id, title_lower): (task_data, timestamp)}
TASK_CACHE_TTL_SECONDS = 60  # 1 minute cache window

def _clean_task_cache():
    """Remove expired entries from task creation cache."""
    now = datetime.now(UTC)
    expired_keys = [
        key for key, (_, timestamp) in _task_creation_cache.items()
        if (now - timestamp).total_seconds() > TASK_CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        del _task_creation_cache[key]

# In add_task function, after input validation:
_clean_task_cache()
cache_key = (user_id, title.strip().lower())

if cache_key in _task_creation_cache:
    cached_task_data, cached_timestamp = _task_creation_cache[cache_key]
    cache_age = (datetime.now(UTC) - cached_timestamp).total_seconds()

    if cache_age < TASK_CACHE_TTL_SECONDS:
        logger.warning(
            f"⚠️  DUPLICATE TASK CREATION DETECTED - Returning cached task | "
            f"user: {user_id[:20]}... | title: '{title}' | cache_age: {cache_age:.1f}s"
        )
        return {
            "status": "success",
            "data": cached_task_data,
            "idempotent": True
        }

# After successful task creation:
_task_creation_cache[cache_key] = (task_data, datetime.now(UTC))
logger.info(f"✓ Cached task creation | user: {user_id[:20]}... | title: '{title}'")
```

#### Layer 2: Audit Service Event-ID Deduplication

For event-driven systems using Dapr pub/sub, add event deduplication in `services/audit-service/audit_service.py`:

```python
from sqlalchemy import text

# In write_audit_log function, before creating audit log:
event_id = details.get("event_id")
if event_id:
    existing = session.exec(
        select(AuditLog).where(
            text("details->>'event_id' = :event_id")
        ).params(event_id=event_id)
    ).first()

    if existing:
        logger.info(
            f"⚠️ DUPLICATE EVENT DETECTED - Idempotent skip | "
            f"event_id: {event_id} | event_type: {event_type}"
        )
        return True  # Success - idempotent behavior
```

### Deployment

```bash
# Build MCP server with idempotency
cd backend
docker build -f tools/Dockerfile -t mcp-server:v2-idempotency .
minikube image load mcp-server:v2-idempotency
kubectl set image deployment/mcp-server mcp-server=mcp-server:v2-idempotency
kubectl rollout status deployment/mcp-server

# Build audit service with event deduplication
cd ../services/audit-service
docker build -t audit-service:v3-idempotency .
minikube image load audit-service:v3-idempotency
kubectl set image deployment/audit-service audit-service=audit-service:v3-idempotency
kubectl rollout status deployment/audit-service
```

### Verification

1. Create a task via chat interface
2. Check MCP logs for duplicate detection:
   ```bash
   kubectl logs -l app.kubernetes.io/name=mcp-server -c mcp-server --tail=50 | grep DUPLICATE
   ```
   Expected: `⚠️  DUPLICATE TASK CREATION DETECTED - Returning cached task`

3. Verify only one task in database:
   ```bash
   kubectl exec deployment/backend-api -- python3 -c "
   from sqlmodel import Session, create_engine, select
   from models import Task
   import os
   engine = create_engine(os.getenv('DATABASE_URL'))
   with Session(engine) as session:
       tasks = session.exec(select(Task).order_by(Task.created_at.desc()).limit(3)).all()
       for t in tasks: print(f'{t.title} | {t.created_at}')
   "
   ```

4. Verify only one audit log:
   ```bash
   kubectl exec deployment/backend-api -- python3 -c "
   from sqlmodel import Session, create_engine, select
   from models import AuditLog
   import os
   engine = create_engine(os.getenv('DATABASE_URL'))
   with Session(engine) as session:
       logs = session.exec(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(3)).all()
       for l in logs: print(f'{l.event_type} | {l.task_id}')
   "
   ```

### Key Insights
- **Idempotency must be implemented at every layer** in distributed event-driven systems
- HTTP endpoints may receive retries (though ChatKit doesn't retry in practice)
- MCP tools may be called multiple times by the SDK (OpenAI Agents SDK does this)
- Event handlers receive at-least-once delivery (Dapr pub/sub guarantees)

---

## 4. Port-Forward Connection Issues

### Symptoms
- Browser console shows `ERR_CONNECTION_REFUSED`
- Cannot access services at `http://localhost:3000` or `http://localhost:8000`
- Services running in cluster but not accessible locally

### Root Cause
Port-forward processes not running or terminated.

### Solution

```bash
# Check if port-forwards are running
ps aux | grep "port-forward"

# Kill any stale port-forwards
pkill -f "kubectl port-forward" 2>/dev/null

# Start fresh port-forwards
kubectl port-forward --address 0.0.0.0 svc/frontend 3000:3000 > /tmp/frontend-pf.log 2>&1 &
kubectl port-forward --address 0.0.0.0 svc/backend-api 8000:8000 > /tmp/backend-pf.log 2>&1 &

# Verify they're running
ps aux | grep "port-forward"

# Test connectivity
curl http://localhost:8000/health
curl http://localhost:3000
```

### Check Service Endpoints

```bash
kubectl get svc
kubectl get endpoints
kubectl describe svc frontend
kubectl describe svc backend-api
```

---

## 5. Dapr Operator Pod CreateContainerError

### Symptoms
- Dapr operator pod stuck in `CreateContainerError` state
- Backend-api pod stuck in `Init:0/1` (waiting for Dapr sidecar)
- Dapr sidecar injector cannot initialize containers

### Root Cause
Docker container name conflict or corrupted Dapr operator pod.

### Solution

```bash
# Delete stuck Dapr operator pod
kubectl delete pod -n dapr-system -l app=dapr-operator

# Wait for new pod to start
kubectl wait --for=condition=ready pod -l app=dapr-operator -n dapr-system --timeout=120s

# Verify Dapr system is healthy
kubectl get pods -n dapr-system

# Restart backend-api to reinitialize Dapr sidecar
kubectl rollout restart deployment backend-api
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=backend-api --timeout=120s

# Verify backend-api has 2/2 containers (app + daprd)
kubectl get pods -l app.kubernetes.io/name=backend-api
```

### Check Dapr Sidecar Logs

```bash
kubectl logs <pod-name> -c daprd
```

---

## 6. Idempotency Patterns for Event-Driven Systems

### Why Multiple Layers?

Distributed event-driven systems have multiple points where operations can be retried:
- **HTTP layer**: Client retries (network failures, timeouts)
- **SDK layer**: Internal duplicate calls (OpenAI Agents SDK)
- **Event layer**: At-least-once delivery (Dapr pub/sub, Kafka, SQS)

Each layer needs protection because failures can occur at any level.

### Implementation Pattern

#### 1. Request-Level Cache (HTTP Endpoints)

Use for external API endpoints that clients may retry:

```python
from datetime import datetime, UTC
import hashlib

_request_cache = {}  # {idempotency_key: (response, timestamp)}
CACHE_TTL_SECONDS = 300  # 5 minutes

def _generate_key(user_id: str, body: bytes) -> str:
    content = f"{user_id}:{body.decode('utf-8', errors='ignore')}"
    return hashlib.sha256(content.encode()).hexdigest()

def _clean_cache():
    now = datetime.now(UTC)
    expired = [
        k for k, (_, ts) in _request_cache.items()
        if (now - ts).total_seconds() > CACHE_TTL_SECONDS
    ]
    for k in expired:
        del _request_cache[k]

# In endpoint:
_clean_cache()
key = _generate_key(user_id, request_body)

if key in _request_cache:
    cached_response, timestamp = _request_cache[key]
    age = (datetime.now(UTC) - timestamp).total_seconds()
    logger.warning(f"Duplicate request detected (age: {age:.1f}s)")
    return cached_response

# Process request...
_request_cache[key] = (response, datetime.now(UTC))
```

#### 2. Operation-Level Cache (MCP Tools, Database Operations)

Use for operations that may be called multiple times by SDK or application logic:

```python
_operation_cache = {}  # {(user_id, operation_key): (result, timestamp)}
OPERATION_CACHE_TTL = 60  # 1 minute

# In tool function:
cache_key = (user_id, title.strip().lower())
if cache_key in _operation_cache:
    result, timestamp = _operation_cache[cache_key]
    age = (datetime.now(UTC) - timestamp).total_seconds()
    if age < OPERATION_CACHE_TTL:
        return result

# Perform operation...
_operation_cache[cache_key] = (result, datetime.now(UTC))
```

#### 3. Event-Level Deduplication (Event Handlers)

Use for event handlers that process pub/sub messages:

```python
# Store event_id in database with unique constraint
# Or check before processing:

from sqlalchemy import text

event_id = event_data.get("event_id")
if event_id:
    existing = session.exec(
        select(EventLog).where(
            text("details->>'event_id' = :event_id")
        ).params(event_id=event_id)
    ).first()

    if existing:
        logger.info(f"Duplicate event {event_id} - skipping")
        return  # Already processed
```

### Best Practices

1. **Generate unique event IDs** at the source:
   ```python
   import uuid
   event_id = str(uuid.uuid4())
   ```

2. **Use short TTLs** for caches (1-5 minutes) to avoid memory bloat

3. **Log duplicate detections** to monitor retry patterns:
   ```python
   logger.warning(f"DUPLICATE DETECTED | key: {key} | age: {age:.1f}s")
   ```

4. **Return success** for duplicates (idempotent behavior):
   ```python
   if is_duplicate:
       return {"status": "success", "data": cached_result, "idempotent": True}
   ```

5. **Clean expired entries** periodically to prevent memory leaks

---

## 7. JSONB Query Patterns in PostgreSQL

### Problem: Querying JSONB Columns in SQLModel/SQLAlchemy

PostgreSQL JSONB columns require special query syntax. Standard Python dictionary access doesn't work in SQLAlchemy queries.

### Common Mistakes

```python
# ❌ WRONG - Python dict syntax doesn't work in SQL queries
existing = session.exec(
    select(AuditLog).where(AuditLog.details["event_id"] == event_id)
).first()

# ❌ WRONG - Cast syntax is verbose and error-prone
from sqlalchemy import cast, String
existing = session.exec(
    select(AuditLog).where(
        cast(AuditLog.details["event_id"], String) == event_id
    )
).first()
```

### Correct Pattern: Text Operator with Parameters

```python
from sqlalchemy import text

# ✅ CORRECT - Use ->> text extraction operator with parameterized query
existing = session.exec(
    select(AuditLog).where(
        text("details->>'event_id' = :event_id")
    ).params(event_id=event_id)
).first()
```

### JSONB Operators Reference

| Operator | Returns | Example | Description |
|----------|---------|---------|-------------|
| `->` | JSONB | `data->'key'` | Get JSON object field |
| `->>` | Text | `data->>'key'` | Get JSON object field as text |
| `#>` | JSONB | `data#>'{a,b}'` | Get JSON object at path |
| `#>>` | Text | `data#>>'{a,b}'` | Get JSON object at path as text |
| `@>` | Boolean | `data @> '{"a":1}'` | Does JSONB contain value? |
| `?` | Boolean | `data ? 'key'` | Does JSONB contain key? |

### Practical Examples

#### Query Nested JSONB Field
```python
# Query: WHERE details->>'event_type' = 'task.created'
results = session.exec(
    select(AuditLog).where(
        text("details->>'event_type' = :event_type")
    ).params(event_type="task.created")
).all()
```

#### Query with Multiple JSONB Conditions
```python
# Query: WHERE details->>'user_id' = ? AND details->>'action' = ?
results = session.exec(
    select(AuditLog).where(
        text("details->>'user_id' = :user_id AND details->>'action' = :action")
    ).params(user_id=user_id, action="create")
).all()
```

#### Check JSONB Contains Key
```python
# Query: WHERE details ? 'event_id'
results = session.exec(
    select(AuditLog).where(
        text("details ? :key")
    ).params(key="event_id")
).all()
```

### Verification with Direct SQL

Test JSONB queries directly in PostgreSQL:
```sql
-- Connect to database
psql $DATABASE_URL

-- Test text extraction
SELECT id, details->>'event_id' as event_id
FROM audit_log
WHERE details->>'event_id' = '12345';

-- Test key existence
SELECT id, details
FROM audit_log
WHERE details ? 'event_id';
```

---

## 8. General Debugging Commands

### Pod Status and Logs

```bash
# Check all pods
kubectl get pods -o wide

# Check specific pod details
kubectl describe pod <pod-name>

# View logs
kubectl logs <pod-name>
kubectl logs <pod-name> -c <container-name>  # Multi-container pod
kubectl logs -l app.kubernetes.io/name=backend-api --tail=50
kubectl logs -l app.kubernetes.io/name=backend-api -f  # Follow

# Previous pod logs (after restart)
kubectl logs <pod-name> --previous
```

### Service and Endpoint Checks

```bash
# List services
kubectl get svc

# List endpoints
kubectl get endpoints

# Describe service
kubectl describe svc <service-name>

# Test service connectivity from another pod
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside pod:
wget -O- http://backend-api:8000/health
```

### Database Connectivity Tests

```bash
# Test from backend pod (Python)
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print('Database connected!')
conn.close()
"

# Test from frontend pod (Node.js) - AFTER Happy Eyeballs fix
kubectl exec <frontend-pod> -- node -e "
const net = require('net');
net.setDefaultAutoSelectFamily(false);
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.query('SELECT 1').then(() => console.log('DB OK')).catch(e => console.log('Error:', e.message));
"
```

### Secrets Verification

```bash
# List secrets
kubectl get secrets

# View secret (base64 decoded)
kubectl get secret <secret-name> -o jsonpath='{.data.key-name}' | base64 -d

# Compare secrets across services
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
kubectl get secret backend-api-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
# These must match!
```

### Deployment Management

```bash
# Rollout status
kubectl rollout status deployment <name>

# Restart deployment
kubectl rollout restart deployment <name>

# Rollback deployment
kubectl rollout undo deployment <name>

# View deployment history
kubectl rollout history deployment <name>

# Scale deployment
kubectl scale deployment <name> --replicas=2
```

### Docker Image Management (Minikube)

```bash
# Use Minikube's Docker daemon
eval $(minikube docker-env)

# List images in Minikube
docker images

# Build and load image
docker build -t service-name:tag .
minikube image load service-name:tag

# Verify image loaded
minikube image ls | grep service-name
```

### Dapr Debugging

```bash
# Check Dapr system pods
kubectl get pods -n dapr-system

# View Dapr sidecar logs
kubectl logs <pod-name> -c daprd

# Check Dapr components
kubectl get components

# Test Dapr pub/sub
kubectl exec <pod-with-dapr> -- curl -X POST \
  http://localhost:3500/v1.0/publish/pubsub-name/topic-name \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Resource Usage

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods

# Describe node
kubectl describe node <node-name>
```

---

## Success Indicators

When everything is working correctly:

**Pods:**
- All pods in `Running` state
- No `CrashLoopBackOff` or `Error` states
- Correct number of containers (e.g., `2/2` for Dapr-enabled pods)
- Health checks passing

**Frontend:**
- Sign-in page loads without errors
- Browser console shows no connection errors
- JWT tokens generated successfully
- Redirects to dashboard after login

**Backend:**
- Health endpoint returns `{"status": "healthy"}`
- Database connection confirmed
- No error messages in logs
- MCP server responds to tool calls

**End-to-End:**
- Users can sign up and log in
- Chat interface loads and responds
- Tasks created via chat appear in database (single entry)
- Audit logs created correctly (single entry per event)
- No duplicate detection warnings in normal operation

---

## Additional Resources

- [Kubernetes Debugging](https://kubernetes.io/docs/tasks/debug/)
- [Dapr Troubleshooting](https://docs.dapr.io/operations/troubleshooting/)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/functions-json.html)
- [Better Auth Docs](https://www.better-auth.com/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
