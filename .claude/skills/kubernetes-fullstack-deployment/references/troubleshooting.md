# Troubleshooting Guide

## Authentication Issues

### 401 Unauthorized - JWT Validation Failed

**Symptoms:**
```
ERROR [Better Auth]: JWT validation error
Fail to fetch data from the url, err: "<urlopen error [Errno 111] Connection refused>"
```

**Cause:** Backend cannot fetch JWKS from frontend service.

**Diagnosis:**
```bash
# Check if BETTER_AUTH_URL is set
kubectl get configmap ai-todo-backend-config -o yaml | grep BETTER_AUTH_URL

# Test JWKS endpoint from backend pod
kubectl exec -it $(kubectl get pod -l app=ai-todo-backend -o name | head -1) -- python3 -c "
import urllib.request
print(urllib.request.urlopen('http://ai-todo-frontend-service:3000/api/auth/jwks', timeout=5).read().decode())
"
```

**Solution:**
```bash
# Add BETTER_AUTH_URL to backend ConfigMap
kubectl delete configmap ai-todo-backend-config

kubectl create configmap ai-todo-backend-config \
  --from-literal=BETTER_AUTH_URL='http://ai-todo-frontend-service:3000' \
  --from-literal=BETTER_AUTH_JWKS_URL='http://ai-todo-frontend-service:3000/api/auth/jwks' \
  --from-literal=MCP_SERVER_URL='http://ai-todo-mcp-service:8001'

# Update Helm chart template to include BETTER_AUTH_URL env var
# Then restart backend
kubectl delete pod -l app=ai-todo-backend
```

---

## MCP Server Issues

### 421 Misdirected Request - Invalid Host Header

**Symptoms:**
```
HTTP/1.1 421 Misdirected Request
Invalid Host header: ai-todo-mcp-service:8001
```

**Cause:** MCP server's allowed_hosts list doesn't include Kubernetes service DNS.

**Diagnosis:**
```bash
# Check MCP logs
kubectl logs -l app=ai-todo-mcp --tail=50

# Test from backend
kubectl exec $(kubectl get pod -l app=ai-todo-backend -o name | head -1 | sed 's|pod/||') -- \
  python3 -c "import urllib.request; urllib.request.urlopen('http://ai-todo-mcp-service:8001')"
```

**Solution:**

Edit `backend/tools/server.py`:
```python
allowed_hosts_list = [
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
    "ai-todo-mcp-service",      # Add this
    "ai-todo-mcp-service:*",    # Add this
]
```

Then rebuild and reload:
```bash
./deployment/build-images.sh
minikube image load ai-todo-mcp:latest --overwrite
kubectl delete pod -l app=ai-todo-mcp
```

---

## Port-Forward Issues

### Connection Refused on localhost:3000 (Windows/WSL2)

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 3000: Connection refused
```

**Cause:** Port-forward not listening on all interfaces or stopped.

**Diagnosis:**
```bash
# Check port-forward processes
ps aux | grep "port-forward" | grep -v grep

# Check what's listening
ss -tlnp | grep -E ":(3000|8000)"
```

**Solution:**
```bash
# Kill old port-forwards
pkill -f "kubectl port-forward"

# Restart with --address 0.0.0.0 (critical for WSL2/Windows)
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 &

# Verify
curl http://localhost:3000/
curl http://localhost:8000/health
```

---

## Database Issues

### ETIMEDOUT - Database Connection Timeout

**Symptoms:**
```
ERROR [Better Auth]: AggregateError
code: 'ETIMEDOUT'
```

**Cause:** Frontend pod has stale database connections.

**Diagnosis:**
```bash
# Test database connection from frontend pod
kubectl exec $(kubectl get pod -l app=ai-todo-frontend -o name | head -1 | sed 's|pod/||') -- node -e "
const { Client } = require('pg');
const client = new Client({ connectionString: process.env.DATABASE_URL });
client.connect()
  .then(() => { console.log('✅ Connected'); client.end(); })
  .catch(err => { console.log('❌ Error:', err.message); });
"
```

**Solution:**
```bash
# Restart frontend pod to refresh connections
kubectl delete pod -l app=ai-todo-frontend

# Wait for new pod
kubectl get pods -l app=ai-todo-frontend -w
```

---

## Pod Crash Issues

### CrashLoopBackOff - Backend Pod

**Symptoms:**
```
NAME                             READY   STATUS             RESTARTS
ai-todo-backend-xxx-yyy          0/1     CrashLoopBackOff   6
```

**Diagnosis:**
```bash
# Check logs
kubectl logs -l app=ai-todo-backend --tail=100

# Check events
kubectl describe pod -l app=ai-todo-backend | grep -A 20 "Events:"

# Check liveness/readiness probes
kubectl describe pod -l app=ai-todo-backend | grep -E "(Liveness|Readiness)"
```

**Common Causes:**

1. **Database connection fails** - Check DATABASE_URL secret
2. **Probe timeout** - Health endpoint takes too long to respond
3. **Missing secrets** - OPENAI_API_KEY or BETTER_AUTH_SECRET not set

**Solution:**
```bash
# Verify secrets exist
kubectl get secret ai-todo-backend-secrets -o yaml

# Check if all required env vars are set
kubectl describe pod -l app=ai-todo-backend | grep -A 20 "Environment:"

# Restart with fresh pod
kubectl delete pod -l app=ai-todo-backend
```

---

## Image Update Issues

### Pod Using Old Image After Rebuild

**Symptoms:**
Pod continues to use old image even after rebuild and `kubectl delete pod`.

**Diagnosis:**
```bash
# Check current image ID in pod
kubectl get pod -l app=ai-todo-mcp -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'

# Check new image ID locally
docker images ai-todo-mcp:latest --format "{{.ID}}"

# They don't match!
```

**Solution:**
```bash
# Force remove old image from Minikube
minikube image rm docker.io/library/ai-todo-mcp:latest

# Load new image
docker save ai-todo-mcp:latest | minikube image load --overwrite -

# Restart deployment
kubectl rollout restart deployment/ai-todo-mcp

# Verify new image
kubectl get pod -l app=ai-todo-mcp -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'
```

---

## Minikube Issues

### Minikube API Server Stopped

**Symptoms:**
```
The control-plane node minikube apiserver is not running: (state=Stopped)
```

**Cause:** Minikube cluster was stopped or crashed.

**Solution:**
```bash
# Check status
minikube status

# If stopped, start it
minikube start --driver=docker

# If in bad state, restart
minikube stop
minikube start

# Last resort: delete and recreate
minikube delete
minikube start --driver=docker --kubernetes-version=v1.29.2
```

---

## JWKS Issues

### Old JWKS in Database with Different Secret

**Symptoms:**
Sign-in works, but backend rejects JWT with 401.

**Cause:** JWKS in database was created with a different BETTER_AUTH_SECRET.

**Solution:**

Option 1 - Manual database cleanup (user does this):
```sql
DELETE FROM jwks WHERE id = '...';
```

Option 2 - Restart with clean database:
```bash
# Drop and recreate tables (development only!)
# Then sign up with new user
```

---

## Quick Diagnostic Commands

```bash
# Overall cluster health
kubectl get pods --all-namespaces
kubectl get nodes
minikube status

# Service-specific
kubectl logs -l app=ai-todo-backend --tail=50
kubectl logs -l app=ai-todo-frontend --tail=50
kubectl logs -l app=ai-todo-mcp --tail=50

# Network connectivity
kubectl get svc
kubectl get endpoints

# Configuration
kubectl get configmap
kubectl get secret
helm list

# Test from inside cluster
kubectl run test-curl --rm -it --image=curlimages/curl -- \
  curl http://ai-todo-mcp-service:8001/
```
