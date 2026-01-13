# Kubernetes Deployment Guide

Deploy the Next.js + FastAPI + MCP architecture to Kubernetes (Minikube, EKS, GKE, AKS).

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Helm Charts Structure](#helm-charts-structure)
4. [Secrets Management](#secrets-management)
5. [Deploy to Minikube](#deploy-to-minikube)
6. [Port Forwarding](#port-forwarding)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │  Backend-API │    │  MCP Server  │  │
│  │   (Next.js)  │───▶│  (FastAPI)   │───▶│  (FastMCP)   │  │
│  │   Port 3000  │    │   Port 8000  │    │   Port 8001  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Neon PostgreSQL (External)                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Secrets:                                                    │
│  - postgres-credentials (DATABASE_URL)                      │
│  - better-auth-secret (BETTER_AUTH_SECRET)                  │
│  - openai-credentials (OPENAI_API_KEY)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

```bash
# Install tools
brew install minikube helm kubectl  # macOS
# OR
choco install minikube helm kubectl  # Windows

# Start Minikube
minikube start --cpus=4 --memory=8192

# Verify
kubectl cluster-info
helm version
```

---

## Helm Charts Structure

```
infrastructure/helm/
├── frontend/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-local.yaml      # Minikube overrides
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── _helpers.tpl
├── backend-api/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-local.yaml
│   └── templates/
├── mcp-server/                 # If running MCP separately
│   └── ...
└── deploy-local.sh             # One-click deployment script
```

### values-local.yaml Example (Frontend)

```yaml
replicaCount: 1

image:
  repository: frontend
  tag: latest
  pullPolicy: Never  # Use local images

service:
  type: ClusterIP
  port: 3000

env:
  - name: NODE_ENV
    value: "production"
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"
  - name: NEXT_PUBLIC_API_URL
    value: "http://backend-api:8000"
  - name: BETTER_AUTH_SECRET
    valueFrom:
      secretKeyRef:
        name: better-auth-secret
        key: better-auth-secret
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi
```

### values-local.yaml Example (Backend)

```yaml
replicaCount: 1

image:
  repository: backend-api
  tag: latest
  pullPolicy: Never

service:
  type: ClusterIP
  port: 8000

env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url
  - name: BETTER_AUTH_SECRET
    valueFrom:
      secretKeyRef:
        name: better-auth-secret
        key: better-auth-secret
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"
  - name: BETTER_AUTH_JWKS_URL
    value: "http://frontend:3000/api/auth/jwks"
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: openai-credentials
        key: openai-api-key
  - name: MCP_SERVER_URL
    value: "http://backend-api:8000/mcp"  # Mounted mode
  - name: MOUNT_MCP_SERVER
    value: "true"
```

---

## Secrets Management

### Create Secrets

```bash
# PostgreSQL credentials
kubectl create secret generic postgres-credentials \
  --from-literal=database-url="postgresql://user:pass@host:5432/db?sslmode=require"

# Better Auth secret (MUST match frontend and backend)
kubectl create secret generic better-auth-secret \
  --from-literal=better-auth-secret="$(openssl rand -base64 32)"

# OpenAI API key
kubectl create secret generic openai-credentials \
  --from-literal=openai-api-key="sk-proj-..."
```

### Verify Secrets Match

```bash
# Frontend and backend MUST have same BETTER_AUTH_SECRET
kubectl get secret better-auth-secret -o jsonpath='{.data.better-auth-secret}' | base64 -d
```

### Update Secrets

```bash
NEW_SECRET="your-new-secret"
kubectl patch secret better-auth-secret \
  -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $NEW_SECRET | base64 -w0)\"}}"

# Clean JWKS and restart (if secret changed)
psql $DATABASE_URL -c "DELETE FROM jwks;"
kubectl rollout restart deployment frontend backend-api
```

---

## Deploy to Minikube

### deploy-local.sh Script

```bash
#!/bin/bash
set -e

echo "🚀 Deploying to Minikube..."

# Use Minikube's Docker daemon
eval $(minikube docker-env)

# Build images
echo "📦 Building Docker images..."
docker build -t frontend:latest ./frontend
docker build -t backend-api:latest ./backend

# Deploy with Helm
echo "⎈ Installing Helm charts..."

helm upgrade --install frontend ./infrastructure/helm/frontend \
  -f ./infrastructure/helm/frontend/values-local.yaml

helm upgrade --install backend-api ./infrastructure/helm/backend-api \
  -f ./infrastructure/helm/backend-api/values-local.yaml

# Wait for pods
echo "⏳ Waiting for pods..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=frontend --timeout=120s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=backend-api --timeout=120s

echo "✅ Deployment complete!"
echo ""
echo "To access the application:"
echo "  kubectl port-forward svc/frontend 3000:3000 &"
echo "  kubectl port-forward svc/backend-api 8000:8000 &"
echo "  open http://localhost:3000"
```

### Run Deployment

```bash
# Create secrets first (one-time)
kubectl create secret generic postgres-credentials --from-literal=database-url="..."
kubectl create secret generic better-auth-secret --from-literal=better-auth-secret="..."
kubectl create secret generic openai-credentials --from-literal=openai-api-key="..."

# Deploy
chmod +x infrastructure/deploy-local.sh
./infrastructure/deploy-local.sh
```

---

## Port Forwarding

### Start Port Forwards

```bash
# Frontend
kubectl port-forward svc/frontend 3000:3000 &

# Backend
kubectl port-forward svc/backend-api 8000:8000 &

# Access
open http://localhost:3000
```

### Background with Logging

```bash
kubectl port-forward svc/frontend 3000:3000 > /tmp/pf-frontend.log 2>&1 &
kubectl port-forward svc/backend-api 8000:8000 > /tmp/pf-backend.log 2>&1 &

# Check logs
tail -f /tmp/pf-frontend.log
```

### Stop Port Forwards

```bash
pkill -f "kubectl port-forward"
```

---

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -o wide
kubectl describe pod <pod-name>
```

### View Logs

```bash
# Frontend logs
kubectl logs -l app.kubernetes.io/name=frontend --tail=100

# Backend logs
kubectl logs -l app.kubernetes.io/name=backend-api --tail=100

# Follow logs
kubectl logs -l app.kubernetes.io/name=frontend -f
```

### Common Issues

#### Issue: ETIMEDOUT to Database

**Symptom:** Frontend can't connect to Neon PostgreSQL

**Fix:** Add Happy Eyeballs fix to `frontend/lib/auth.ts`:

```typescript
import dns from "dns";
import net from "net";

net.setDefaultAutoSelectFamily(false);
dns.setDefaultResultOrder("ipv4first");
```

#### Issue: JWKS Decryption Error

**Symptom:** "Failed to decrypt private key"

**Fix:**
```bash
psql $DATABASE_URL -c "DELETE FROM jwks;"
kubectl rollout restart deployment frontend
```

#### Issue: Service Not Reachable

**Fix:** Check endpoints:
```bash
kubectl get endpoints frontend backend-api
kubectl get svc
```

#### Issue: Image Not Found

**Fix:** Ensure using Minikube's Docker:
```bash
eval $(minikube docker-env)
docker images | grep -E "(frontend|backend)"
```

### Debug Commands

```bash
# Exec into pod
kubectl exec -it <pod-name> -- sh

# Test connectivity from backend to frontend JWKS
kubectl exec <backend-pod> -- curl -s http://frontend:3000/api/auth/jwks

# Test health endpoints
kubectl exec <backend-pod> -- curl -s http://localhost:8000/health

# Check environment variables
kubectl exec <pod-name> -- env | grep -E "(AUTH|DATABASE|MCP)"
```

---

## Multi-Service Microservices

For event-driven microservices (audit, notification, etc.):

### Additional Helm Charts

```
infrastructure/helm/
├── audit-service/
├── notification-service/
├── recurring-task-service/
└── websocket-service/
```

### Deploy All Services

```bash
#!/bin/bash
# deploy-all.sh

SERVICES="frontend backend-api audit-service notification-service"

for svc in $SERVICES; do
  echo "Deploying $svc..."
  helm upgrade --install $svc ./infrastructure/helm/$svc \
    -f ./infrastructure/helm/$svc/values-local.yaml
done

kubectl get pods
```

---

## Quick Reference

### Commands

```bash
# Deploy
./infrastructure/deploy-local.sh

# Port forward
kubectl port-forward svc/frontend 3000:3000 &
kubectl port-forward svc/backend-api 8000:8000 &

# Check status
kubectl get pods
kubectl get svc

# View logs
kubectl logs -l app.kubernetes.io/name=frontend

# Restart
kubectl rollout restart deployment frontend backend-api

# Clean up
helm uninstall frontend backend-api
```

### Required Secrets

| Secret | Keys | Used By |
|--------|------|---------|
| `postgres-credentials` | `database-url` | All services |
| `better-auth-secret` | `better-auth-secret` | Frontend, Backend |
| `openai-credentials` | `openai-api-key` | Backend |

### Service URLs (In-Cluster)

| Service | URL |
|---------|-----|
| Frontend | `http://frontend:3000` |
| Backend | `http://backend-api:8000` |
| JWKS | `http://frontend:3000/api/auth/jwks` |
