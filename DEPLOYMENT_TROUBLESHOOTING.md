# Deployment Troubleshooting Guide

This guide helps you troubleshoot common issues when deploying the Evolution of Todo app to Kubernetes/Minikube.

---

## Kubernetes/Minikube Deployment Issues

### Issue 1: ETIMEDOUT Connecting to Neon from Node.js in Kubernetes

**Symptoms:**
```
Error: AggregateError
  code: 'ETIMEDOUT'
```
- Frontend pod cannot connect to Neon PostgreSQL
- Backend pod (Python) CAN connect to same database
- `nc` and `wget` from frontend pod work, but Node.js fails
- Error occurs with both direct and pooler Neon URLs

**Root Cause:**
Node.js's Happy Eyeballs implementation (`autoSelectFamily`) tries to connect to IPv4 and IPv6 addresses concurrently. In containerized Kubernetes environments, this concurrent connection attempt causes timeouts, even though sequential connections work fine.

**Solution:**
Add the following to `frontend/lib/auth.ts` (or any file that loads early):

```typescript
import dns from "dns";
import net from "net";

// Fix for Node.js Happy Eyeballs issue in containerized environments
// Disable concurrent IPv4/IPv6 connection attempts
net.setDefaultAutoSelectFamily(false);

// Also prioritize IPv4 for DNS resolution
dns.setDefaultResultOrder("ipv4first");
```

**Verification:**
```bash
# Test from frontend pod - should work after fix
kubectl exec <frontend-pod> -- node -e '
const net = require("net");
net.setDefaultAutoSelectFamily(false);
const socket = net.connect(443, "ep-divine-feather-a4qc11zk.us-east-1.aws.neon.tech", () => {
  console.log("Connected!");
  socket.end();
});
'
```

**After fix, rebuild and redeploy:**
```bash
eval $(minikube docker-env)
docker build -t frontend:latest ./frontend
kubectl rollout restart deployment frontend
```

---

### Issue 2: JWKS Decryption Error After Changing BETTER_AUTH_SECRET

**Symptoms:**
```
BetterAuthError: Failed to decrypt private key. Make sure the secret currently
in use is the same as the one used to encrypt the private key.
```
- Sign-in redirects back to sign-in page
- User appears to authenticate but session doesn't persist

**Root Cause:**
Better Auth stores JWKS (JSON Web Key Set) keys in the database, encrypted with the `BETTER_AUTH_SECRET`. If the secret changes, the stored keys cannot be decrypted.

**Solution:**
Clean the JWKS table in the database:

```bash
# Option 1: Using backend pod with psycopg2
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
conn = psycopg2.connect('YOUR_DATABASE_URL')
cur = conn.cursor()
cur.execute('DELETE FROM jwks')
conn.commit()
print('JWKS table cleaned')
conn.close()
"

# Option 2: Using psql directly
psql YOUR_DATABASE_URL -c "DELETE FROM jwks;"
```

Then restart the frontend to regenerate keys:
```bash
kubectl rollout restart deployment frontend
```

**Prevention:**
- Never change `BETTER_AUTH_SECRET` in production without cleaning JWKS
- Keep the secret consistent across all deployments (frontend and backend)
- Store the secret securely and don't regenerate unnecessarily

---

### Issue 3: Port-Forward Issues with Kubernetes Services

**Symptoms:**
- Cannot access services at localhost
- Connection refused or timeout when accessing localhost:3000 or localhost:8000

**Solution:**
Ensure port-forwards are running:
```bash
# Kill any stale port-forwards
pkill -f "kubectl port-forward" 2>/dev/null

# Start fresh port-forwards
kubectl port-forward svc/frontend 3000:3000 &
kubectl port-forward svc/backend-api 8000:8000 &

# Verify they're running
ps aux | grep "port-forward"
```

**Check service endpoints:**
```bash
kubectl get svc
kubectl get endpoints
```

---

### Issue 4: Secrets Mismatch Between Services

**Symptoms:**
- JWT validation fails
- "Invalid token signature" errors
- Sign-in works but API calls fail

**Solution:**
Verify secrets match across all services:
```bash
# Check frontend secret
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# Check backend secret
kubectl get secret backend-api-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# They must be EXACTLY the same
```

If they don't match, update the secrets:
```bash
SECRET="YourSecretHere"
kubectl patch secret frontend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"
kubectl patch secret backend-api-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"

# Restart deployments
kubectl rollout restart deployment frontend backend-api
```

---

### Issue 5: ChatKit Endpoint Crashing - Idempotency Type Handling Bug

**Symptoms:**
- ChatKit endpoint returns no response
- Chat UI shows errors when sending messages
- Backend logs show: `AttributeError: 'bytes' object has no attribute 'encode'`
- Error occurs on line attempting to cache ChatKit response

**Root Cause:**
The idempotency implementation incorrectly tried to encode bytes that were already bytes. ChatKit's `NonStreamingResult.json` property is already of type `bytes`, but the code attempted to call `.encode()` on it.

**Location:**
`backend/routes/chatkit.py:690`

**Buggy Code:**
```python
_cache_response(idempotency_key, user_id, result.json.encode(), "json")
```

**Fixed Code:**
```python
# result.json is already bytes, no need to encode
_cache_response(idempotency_key, user_id, result.json, "json")
```

**Solution:**
1. Apply the fix in `backend/routes/chatkit.py:690`
2. Rebuild Docker image:
   ```bash
   cd backend
   docker build -t backend-api:v3-idempotency-fixed .
   ```

3. Load to Minikube:
   ```bash
   minikube image load backend-api:v3-idempotency-fixed
   ```

4. Update deployment:
   ```bash
   kubectl set image deployment/backend-api backend-api=backend-api:v3-idempotency-fixed -n default
   kubectl rollout status deployment/backend-api -n default
   ```

5. Verify fix:
   ```bash
   kubectl logs -n default -l app.kubernetes.io/name=backend-api -c backend-api --tail=20
   ```

**Verification:**
- Send a chat message via frontend
- Should receive AI response without errors
- Tasks created via chat should appear in database (single entry)

**Known Related Issue:**
While this fix prevents duplicate task creation, **duplicate audit log entries** may still occur. This is because audit logs are published to Dapr pubsub, and the idempotency cache only protects the direct task creation, not the event publishing. The audit service may process duplicate events from ChatKit retries. This requires separate investigation and fixing at the event publishing or audit service level.

---

### Issue 6: Port-Forward Not Running for Backend API

**Symptoms:**
- Browser console shows: `ERR_CONNECTION_REFUSED` when accessing ChatKit
- Frontend can connect but backend API requests fail
- ChatKit shows: `POST http://localhost:8000/chatkit net::ERR_CONNECTION_REFUSED`

**Root Cause:**
Port-forward for backend-api service on port 8000 is not active.

**Solution:**
```bash
# Check if port-forward is running
ps aux | grep "port-forward" | grep backend

# If not running, start it
kubectl port-forward --address 0.0.0.0 svc/backend-api 8000:8000 > /tmp/backend-port-forward.log 2>&1 &

# Verify it's accessible
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"healthy","environment":"local","database":"connected"}
```

---

### Issue 7: Duplicate Task Creation from OpenAI Agents SDK

**Symptoms:**
- Single chat request creates TWO identical tasks in database
- Two audit log entries for same task creation
- OpenAI dashboard shows only ONE tool call, but database has duplicates
- MCP server logs show two `CallToolRequest` events for same operation

**Root Cause:**
The **OpenAI Agents SDK** makes duplicate calls to MCP tools during streaming responses. Even though:
- ChatKit sends ONE HTTP request to backend
- OpenAI API receives ONE request and shows ONE tool call in dashboard
- The Agents SDK's MCP integration calls the tool **TWICE** internally

This appears to be undocumented behavior in the OpenAI Agents SDK when using MCP servers with streaming.

**Evidence:**
```
MCP Server Logs:
Processing request of type CallToolRequest
Published task.created event: <event-id-1> for task <task-id>
INFO: 10.244.0.154:35598 - "POST / HTTP/1.1" 200 OK

Processing request of type CallToolRequest  <-- DUPLICATE CALL
Published task.created event: <event-id-2> for task <another-task-id>
INFO: 10.244.0.154:35606 - "POST / HTTP/1.1" 200 OK  <-- Different port
```

**Solution: Two-Layer Idempotency Protection**

**Layer 1: MCP Server Tool-Level Idempotency** (PRIMARY FIX)

File: `backend/tools/server.py`

Add idempotency cache to `add_task` function:

```python
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

# In add_task function, after validation:
_clean_task_cache()
cache_key = (user_id, title.strip().lower())

if cache_key in _task_creation_cache:
    cached_task_data, cached_timestamp = _task_creation_cache[cache_key]
    cache_age = (datetime.now(UTC) - cached_timestamp).total_seconds()

    if cache_age < TASK_CACHE_TTL_SECONDS:
        logger.warning(f"⚠️  DUPLICATE TASK CREATION DETECTED - Returning cached task")
        return {"status": "success", "data": cached_task_data, "idempotent": True}

# After creating task:
_task_creation_cache[cache_key] = (task_data, datetime.now(UTC))
```

**Layer 2: Audit Service Event-ID Deduplication**

File: `services/audit-service/audit_service.py`

Fix JSONB query in `write_audit_log` to prevent duplicate audit logs from Dapr pub/sub retries:

```python
# Check for duplicate event_id before creating audit log
event_id = details.get("event_id")
if event_id:
    from sqlalchemy import text
    existing = session.exec(
        select(AuditLog).where(
            text("details->>'event_id' = :event_id")
        ).params(event_id=event_id)
    ).first()

    if existing:
        logger.info(f"⚠️ DUPLICATE EVENT DETECTED - Idempotent skip")
        return True
```

**Note on HTTP-Level Protection:**

No ChatKit endpoint caching needed - testing showed ChatKit does not retry HTTP requests. The MCP tool-level fix is sufficient to prevent duplicate task creation.

**Rebuild and Deploy:**

```bash
# Build MCP server with idempotency
cd backend
docker build -f tools/Dockerfile -t mcp-server:v2-idempotency .
minikube image load mcp-server:v2-idempotency
kubectl set image deployment/mcp-server mcp-server=mcp-server:v2-idempotency -n default
kubectl rollout status deployment/mcp-server -n default

# Build audit service with fixed JSONB query
cd ../services/audit-service
docker build -t audit-service:v3-idempotency-fixed .
minikube image load audit-service:v3-idempotency-fixed
kubectl set image deployment/audit-service audit-service=audit-service:v3-idempotency-fixed -n default
kubectl rollout status deployment/audit-service -n default
```

**Verification:**

1. Create a task via chat interface
2. Check MCP server logs for duplicate detection:
   ```bash
   kubectl logs -n default -l app.kubernetes.io/name=mcp-server -c mcp-server --tail=50 | grep DUPLICATE
   ```

3. Verify only one task created:
   ```bash
   kubectl exec -n default deployment/backend-api -c backend-api -- python3 -c "
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
   kubectl exec -n default deployment/backend-api -c backend-api -- python3 -c "
   from sqlmodel import Session, create_engine, select
   from models import AuditLog
   import os
   engine = create_engine(os.getenv('DATABASE_URL'))
   with Session(engine) as session:
       logs = session.exec(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(3)).all()
       for l in logs: print(f'{l.event_type} | {l.task_id}')
   "
   ```

**Expected Outcome:**

After fix:
- ✅ Single task entry in database
- ✅ Single audit log entry
- ✅ MCP logs show: `⚠️  DUPLICATE TASK CREATION DETECTED - Returning cached task`
- ✅ Cache age typically < 1 second between duplicate calls

**Key Insight:**

This issue demonstrates that **idempotency must be implemented at every layer** in distributed event-driven systems:
- HTTP endpoints (ChatKit retries)
- MCP tools (SDK duplicate calls)
- Event handlers (pub/sub at-least-once delivery)

---

## Minikube Debug Commands

```bash
# Check all pods status
kubectl get pods -o wide

# Check pod logs
kubectl logs -l app.kubernetes.io/name=frontend --tail=50
kubectl logs -l app.kubernetes.io/name=backend-api --tail=50

# Check secrets exist
kubectl get secrets

# Test database connectivity from backend pod
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
conn = psycopg2.connect('YOUR_DATABASE_URL')
print('Database connected!')
conn.close()
"

# Test from frontend pod (after fix applied)
kubectl exec <frontend-pod> -- node -e "
const net = require('net');
net.setDefaultAutoSelectFamily(false);
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.query('SELECT 1').then(() => console.log('DB OK')).catch(e => console.log('Error:', e.message));
"

# Check service endpoints
kubectl get endpoints frontend backend-api

# View Dapr sidecar logs (if using Dapr)
kubectl logs <pod-name> -c daprd
```

---

## Port-Forward Commands

```bash
# Frontend (port 3000)
kubectl port-forward svc/frontend 3000:3000 &

# Backend API (port 8000)
kubectl port-forward svc/backend-api 8000:8000 &

# Optional: View logs while port-forwarding
kubectl port-forward svc/frontend 3000:3000 > /tmp/pf-frontend.log 2>&1 &
kubectl port-forward svc/backend-api 8000:8000 > /tmp/pf-backend.log 2>&1 &

# Check if port-forwards are running
ps aux | grep "port-forward"

# Stop all port-forwards
pkill -f "kubectl port-forward"
```

---

## Getting Help

If issues persist after following this guide:

1. **Check Logs:**
   - Pod logs: `kubectl logs <pod-name>`
   - Dapr sidecar: `kubectl logs <pod-name> -c daprd`

2. **Collect Information:**
   - Exact error message
   - Pod status: `kubectl get pods`
   - Pod describe: `kubectl describe pod <pod-name>`

3. **Common Fixes:**
   - Restart deployments: `kubectl rollout restart deployment <name>`
   - Check secrets are correctly configured
   - Verify database connectivity

---

## Success Indicators

When everything is working correctly, you should see:

**Kubernetes Pods:**
- All pods in `Running` state
- No `CrashLoopBackOff` or `Error` states
- Health checks passing

**Frontend:**
- Sign up page loads
- Sign in page loads
- No errors in browser console
- Redirects to dashboard after login

**Backend:**
- Health endpoint returns healthy: `curl http://localhost:8000/health`
- Database shows connected
- No error messages in logs

**End-to-End:**
- Can create account
- Can log in
- Can access dashboard
- JWT authentication works
- Chat page loads
