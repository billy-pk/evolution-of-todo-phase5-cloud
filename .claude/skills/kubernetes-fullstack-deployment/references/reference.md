# Reference - Kubernetes Full-Stack Deployment

Detailed commands and configuration examples.

## Environment Variables

### Backend (.env)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
BETTER_AUTH_SECRET=YYv2gWmo8LIo/zoU7jzpCgNI/Jxq/c8BMNv2Bgxn1EU=
BETTER_AUTH_URL=http://localhost:3000
OPENAI_API_KEY=sk-proj-...
MCP_SERVER_URL=http://localhost:8001
```

### Frontend (.env.local)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
BETTER_AUTH_SECRET=YYv2gWmo8LIo/zoU7jzpCgNI/Jxq/c8BMNv2Bgxn1EU=
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Kubernetes Secrets

```bash
# Backend secrets
kubectl create secret generic ai-todo-backend-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=BETTER_AUTH_SECRET='your-secret'

# Frontend secrets
kubectl create secret generic ai-todo-frontend-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=BETTER_AUTH_SECRET='your-secret'

# MCP secrets
kubectl create secret generic ai-todo-mcp-secrets \
  --from-literal=DATABASE_URL='postgresql://...'
```

### Kubernetes ConfigMaps

```bash
# Backend ConfigMap (Critical for JWKS)
kubectl create configmap ai-todo-backend-config \
  --from-literal=MCP_SERVER_URL='http://ai-todo-mcp-service:8001' \
  --from-literal=BETTER_AUTH_URL='http://ai-todo-frontend-service:3000' \
  --from-literal=BETTER_AUTH_ISSUER='http://ai-todo-frontend-service:3000' \
  --from-literal=BETTER_AUTH_JWKS_URL='http://ai-todo-frontend-service:3000/api/auth/jwks'

# Frontend ConfigMap
kubectl create configmap ai-todo-frontend-config \
  --from-literal=NEXT_PUBLIC_API_URL='http://localhost:8000' \
  --from-literal=BETTER_AUTH_URL='http://localhost:3000'
```

## Image Build & Load

### Build All Images
```bash
./deployment/build-images.sh

# Or individually:
docker build -t ai-todo-backend:latest -f dockerfiles/backend.Dockerfile backend/
docker build -t ai-todo-mcp:latest -f dockerfiles/mcp.Dockerfile backend/
docker build -t ai-todo-frontend:latest -f dockerfiles/frontend.Dockerfile frontend/
```

### Load into Minikube
```bash
# Load all
./deployment/load-images.sh

# Or individually
minikube image load ai-todo-backend:latest
minikube image load ai-todo-mcp:latest
minikube image load ai-todo-frontend:latest

# Force overwrite
minikube image load ai-todo-mcp:latest --overwrite

# Verify
minikube image ls | grep ai-todo
```

## Helm Operations

### Install/Upgrade
```bash
# Install with environment variables
DATABASE_URL='postgresql://...' \
BETTER_AUTH_SECRET='...' \
OPENAI_API_KEY='sk-...' \
./deployment/deploy.sh

# Upgrade specific chart
helm upgrade ai-todo-backend ./charts/ai-todo-backend \
  --set env.DATABASE_URL="postgresql://..." \
  --set env.BETTER_AUTH_SECRET="..." \
  --set env.OPENAI_API_KEY="sk-..."
```

### Uninstall
```bash
helm uninstall ai-todo-backend ai-todo-frontend ai-todo-mcp
```

## Pod Management

### Restart Pods
```bash
# Restart specific service
kubectl delete pod -l app=ai-todo-backend
kubectl delete pod -l app=ai-todo-frontend
kubectl delete pod -l app=ai-todo-mcp

# Force deployment rollout
kubectl rollout restart deployment/ai-todo-backend
kubectl rollout restart deployment/ai-todo-frontend
kubectl rollout restart deployment/ai-todo-mcp
```

### Check Status
```bash
# All pods
kubectl get pods

# Specific service
kubectl get pods -l app=ai-todo-backend

# Detailed info
kubectl describe pod -l app=ai-todo-backend

# Logs
kubectl logs -l app=ai-todo-backend --tail=50
kubectl logs -l app=ai-todo-backend -f  # Follow
```

## Port-Forward

### WSL2/Windows Setup
```bash
# MUST use --address 0.0.0.0 for Windows browser access
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 > /tmp/frontend-pf.log 2>&1 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 > /tmp/backend-pf.log 2>&1 &

# Check processes
ps aux | grep "port-forward" | grep -v grep

# Kill all
pkill -f "kubectl port-forward"

# Check what's listening
ss -tlnp | grep -E ":(3000|8000)"
```

### NodePort (Alternative)
```bash
# Get Minikube IP
minikube ip  # e.g., 192.168.49.2

# Access via NodePort
# Frontend: http://192.168.49.2:30080
# Backend:  http://192.168.49.2:30081
```

## Database Operations

### Test Connection from Pod
```bash
# Backend pod
kubectl get pod -l app=ai-todo-backend -o name | sed 's|pod/||' | head -1 | xargs -I {} kubectl exec {} -- python3 -c "
from db import engine
from sqlmodel import Session, text
with Session(engine) as session:
    result = session.exec(text('SELECT 1'))
    print('✅ Database connected')
"

# Frontend pod
kubectl get pod -l app=ai-todo-frontend -o name | sed 's|pod/||' | head -1 | xargs -I {} kubectl exec {} -- node -e "
const { Client } = require('pg');
const client = new Client({ connectionString: process.env.DATABASE_URL });
client.connect()
  .then(() => { console.log('✅ DB connected'); client.end(); })
  .catch(err => { console.log('❌ DB error:', err.message); });
"
```

## Verification Commands

### Check Deployment
```bash
./deployment/validate.sh

# Or manually:
kubectl get pods
kubectl get svc
kubectl get configmap
kubectl get secret
helm list
```

### Test Endpoints
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Frontend
curl -I http://localhost:3000/

# JWKS endpoint
curl http://localhost:3000/api/auth/jwks
```

## MCP Server Configuration

### Allowed Hosts (backend/tools/server.py)
```python
allowed_hosts_list = [
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
    "ai-todo-mcp-service",      # Kubernetes DNS
    "ai-todo-mcp-service:*",    # Kubernetes DNS with port
]
```

### Test MCP from Backend
```bash
kubectl get pod -l app=ai-todo-backend -o name | sed 's|pod/||' | head -1 | xargs -I {} kubectl exec {} -- python3 -c "
import urllib.request
response = urllib.request.urlopen('http://ai-todo-mcp-service:8001', timeout=5)
print('MCP Status:', response.status)
"
```

## Minikube Management

### Start/Stop
```bash
# Start
minikube start --driver=docker

# Stop
minikube stop

# Status
minikube status

# Delete cluster
minikube delete
```

### Service Access
```bash
# Open service in browser
minikube service ai-todo-frontend-service
minikube service ai-todo-backend-service

# Get service URL
minikube service ai-todo-frontend-service --url
```
