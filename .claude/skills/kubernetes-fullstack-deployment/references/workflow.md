# Deployment Workflows

## Initial Setup (Fresh Cluster)

### 1. Prepare Environment
```bash
# Start Minikube
minikube start --driver=docker

# Verify cluster
minikube status
kubectl get nodes
```

### 2. Build Images
```bash
cd /path/to/evolution-of-todo/phase4-k8s

# Build all images
./deployment/build-images.sh

# Verify images
docker images | grep ai-todo
```

### 3. Load Images into Minikube
```bash
./deployment/load-images.sh

# Or manually:
minikube image load ai-todo-backend:latest
minikube image load ai-todo-frontend:latest
minikube image load ai-todo-mcp:latest

# Verify
minikube image ls | grep ai-todo
```

### 4. Deploy with Helm
```bash
# Set environment variables
export DATABASE_URL='postgresql://user:pass@host:5432/db?sslmode=require'
export BETTER_AUTH_SECRET='your-base64-secret-32-chars-minimum'
export OPENAI_API_KEY='sk-proj-...'

# Deploy all services
./deployment/deploy.sh

# Wait for pods to be ready
kubectl get pods -w
```

### 5. Setup Port-Forwards (WSL2/Windows)
```bash
# CRITICAL: Use --address 0.0.0.0 for Windows browser access
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 > /tmp/frontend-pf.log 2>&1 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 > /tmp/backend-pf.log 2>&1 &

# Verify
curl http://localhost:3000/
curl http://localhost:8000/health
```

### 6. Validate Deployment
```bash
./deployment/validate.sh

# Or manually:
kubectl get pods
kubectl get svc
kubectl get configmap
kubectl get secret
helm list
```

### 7. Test Application
```bash
# Open in Windows browser
# http://localhost:3000

# Sign up / Sign in
# Test chat functionality
```

---

## Update Code Workflow

### Backend Code Changes

```bash
# 1. Edit backend code
vim backend/main.py

# 2. Rebuild image
docker build -t ai-todo-backend:latest -f dockerfiles/backend.Dockerfile backend/

# 3. Load into Minikube
minikube image load ai-todo-backend:latest --overwrite

# 4. Restart pods
kubectl delete pod -l app=ai-todo-backend

# 5. Wait for new pod
kubectl get pods -l app=ai-todo-backend -w

# 6. Test
curl http://localhost:8000/health
```

### MCP Server Code Changes

```bash
# 1. Edit MCP server code
vim backend/tools/server.py

# 2. Rebuild image
docker build -t ai-todo-mcp:latest -f dockerfiles/mcp.Dockerfile backend/

# 3. Force reload into Minikube
minikube image rm docker.io/library/ai-todo-mcp:latest
docker save ai-todo-mcp:latest | minikube image load --overwrite -

# 4. Restart deployment
kubectl rollout restart deployment/ai-todo-mcp

# 5. Verify new image is used
kubectl get pod -l app=ai-todo-mcp -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'

# 6. Test from backend pod
kubectl exec $(kubectl get pod -l app=ai-todo-backend -o name | head -1 | sed 's|pod/||') -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://ai-todo-mcp-service:8001').status)"
```

### Frontend Code Changes

```bash
# 1. Edit frontend code
vim frontend/app/page.tsx

# 2. Rebuild image
docker build -t ai-todo-frontend:latest -f dockerfiles/frontend.Dockerfile frontend/

# 3. Load into Minikube
minikube image load ai-todo-frontend:latest --overwrite

# 4. Restart pods
kubectl delete pod -l app=ai-todo-frontend

# 5. Wait for new pod
kubectl get pods -l app=ai-todo-frontend -w

# 6. Test
curl http://localhost:3000/
```

### Helm Chart Changes

```bash
# 1. Edit chart
vim charts/ai-todo-backend/templates/deployment.yaml

# 2. Upgrade release
helm upgrade ai-todo-backend ./charts/ai-todo-backend \
  --set env.DATABASE_URL="$DATABASE_URL" \
  --set env.BETTER_AUTH_SECRET="$BETTER_AUTH_SECRET" \
  --set env.OPENAI_API_KEY="$OPENAI_API_KEY"

# 3. Check rollout
kubectl rollout status deployment/ai-todo-backend

# 4. Verify changes
kubectl describe deployment ai-todo-backend
```

---

## Configuration Update Workflow

### Update Secrets

```bash
# 1. Delete old secret
kubectl delete secret ai-todo-backend-secrets

# 2. Create new secret
kubectl create secret generic ai-todo-backend-secrets \
  --from-literal=DATABASE_URL='new-database-url' \
  --from-literal=OPENAI_API_KEY='new-api-key' \
  --from-literal=BETTER_AUTH_SECRET='new-secret'

# 3. Restart pods to pick up new secret
kubectl delete pod -l app=ai-todo-backend

# 4. Verify new secret is used
kubectl get pod -l app=ai-todo-backend -o jsonpath='{.items[0].spec.containers[0].env[?(@.name=="DATABASE_URL")].valueFrom.secretKeyRef.name}'
```

### Update ConfigMaps

```bash
# 1. Delete old configmap
kubectl delete configmap ai-todo-backend-config

# 2. Create new configmap
kubectl create configmap ai-todo-backend-config \
  --from-literal=BETTER_AUTH_URL='http://ai-todo-frontend-service:3000' \
  --from-literal=MCP_SERVER_URL='http://ai-todo-mcp-service:8001'

# 3. Restart pods
kubectl delete pod -l app=ai-todo-backend

# 4. Verify
kubectl get configmap ai-todo-backend-config -o yaml
```

---

## Shutdown Workflow

### Daily Shutdown (Preserve Cluster)

```bash
# 1. Stop port-forwards
pkill -f "kubectl port-forward"

# 2. Stop Minikube
minikube stop

# Pods and data are preserved
```

### Restart After Shutdown

```bash
# 1. Start Minikube
minikube start

# 2. Wait for pods to come up
kubectl get pods -w

# 3. Restart port-forwards
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 &

# 4. Test
curl http://localhost:3000/
curl http://localhost:8000/health
```

### Complete Cleanup

```bash
# 1. Uninstall Helm releases
helm uninstall ai-todo-backend ai-todo-frontend ai-todo-mcp

# 2. Delete Minikube cluster
minikube delete

# 3. Remove local images (optional)
docker rmi ai-todo-backend:latest
docker rmi ai-todo-frontend:latest
docker rmi ai-todo-mcp:latest
```

---

## Debugging Workflow

### When Chat Doesn't Work

```bash
# 1. Check all pods are running
kubectl get pods

# 2. Check backend logs for JWT errors
kubectl logs -l app=ai-todo-backend --tail=100 | grep -E "(401|JWT|JWKS)"

# 3. Check MCP logs for 421 errors
kubectl logs -l app=ai-todo-mcp --tail=100 | grep -E "(421|Invalid Host)"

# 4. Test JWKS endpoint from backend
kubectl exec $(kubectl get pod -l app=ai-todo-backend -o name | head -1 | sed 's|pod/||') -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://ai-todo-frontend-service:3000/api/auth/jwks').read().decode())"

# 5. Test MCP from backend
kubectl exec $(kubectl get pod -l app=ai-todo-backend -o name | head -1 | sed 's|pod/||') -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://ai-todo-mcp-service:8001').status)"

# 6. Check ConfigMaps
kubectl get configmap ai-todo-backend-config -o yaml
kubectl get configmap ai-todo-frontend-config -o yaml
```

### When Sign-In Doesn't Work

```bash
# 1. Check frontend logs
kubectl logs -l app=ai-todo-frontend --tail=100 | grep -E "(ERROR|Database)"

# 2. Test database from frontend pod
kubectl exec $(kubectl get pod -l app=ai-todo-frontend -o name | head -1 | sed 's|pod/||') -- node -e "
const { Client } = require('pg');
const client = new Client({ connectionString: process.env.DATABASE_URL });
client.connect().then(() => { console.log('✅ DB OK'); client.end(); });
"

# 3. Restart frontend pod if stale connections
kubectl delete pod -l app=ai-todo-frontend
```

### When Port-Forward Stops

```bash
# 1. Check processes
ps aux | grep "port-forward" | grep -v grep

# 2. Kill all
pkill -f "kubectl port-forward"

# 3. Restart with correct flags
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 &

# 4. Verify
ss -tlnp | grep -E ":(3000|8000)"
curl http://localhost:3000/
```
