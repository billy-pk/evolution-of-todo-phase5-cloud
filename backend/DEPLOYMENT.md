# Backend Deployment Guide

This guide covers deploying the backend in Kubernetes environments.

## Deployment Modes

### Mode 1: Unified Deployment (Single Container)

In this mode, the MCP server is mounted on the FastAPI application as a sub-app. This is ideal for simpler deployments.

**Configuration:**

```bash
# Environment variables
MOUNT_MCP_SERVER=true
MCP_SERVER_URL=  # Leave empty for auto-detection
```

**How it works:**
- FastAPI starts on port 8000
- MCP server is automatically mounted at `/mcp` endpoint
- Agent connects to `http://localhost:8000/mcp`
- **Single container handles both REST API and MCP requests**

### Mode 2: Separate Deployment (Kubernetes)

In this mode, the FastAPI backend and MCP server run as separate services. This is ideal for:
- Container orchestration (Kubernetes)
- Separate scaling of REST API vs MCP tools
- Microservices architecture

**Configuration:**

**Backend service (.env):**
```bash
MOUNT_MCP_SERVER=false
MCP_SERVER_URL=http://mcp-service:8001/mcp
```

**MCP service (.env):**
```bash
DATABASE_URL=<your-neon-postgresql-url>
```

**How it works:**
- FastAPI runs on port 8000 (REST API endpoints)
- MCP server runs separately on port 8001 (`python tools/server.py`)
- Agent connects to MCP server via `MCP_SERVER_URL`
- **Two separate containers**

---

## Kubernetes Deployment

### Prerequisites

- Minikube or Kubernetes cluster
- Helm 3.x installed
- Docker for building images

### Build Docker Image

```bash
# Use Minikube Docker environment
eval $(minikube docker-env)

# Build backend image
docker build -t backend-api:latest ./backend
```

### Deploy with Helm

```bash
# Create secrets first
kubectl create secret generic postgres-credentials \
  --from-literal=database-url="postgresql://..."

kubectl create secret generic better-auth-secret \
  --from-literal=better-auth-secret="your-secret"

kubectl create secret generic openai-credentials \
  --from-literal=openai-api-key="sk-..."

# Deploy backend
helm install backend-api ./infrastructure/helm/backend-api \
  -f ./infrastructure/helm/backend-api/values-local.yaml
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -l app.kubernetes.io/name=backend-api

# Check logs
kubectl logs -l app.kubernetes.io/name=backend-api

# Port forward for local access
kubectl port-forward svc/backend-api 8000:8000

# Test health endpoint
curl http://localhost:8000/health
```

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Neon PostgreSQL connection string |
| `BETTER_AUTH_SECRET` | Yes | - | Shared secret with frontend |
| `BETTER_AUTH_URL` | Yes | - | Frontend URL for JWKS endpoint |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `MOUNT_MCP_SERVER` | No | `false` | `true` = unified, `false` = separate |
| `MCP_SERVER_URL` | No | Auto | Override MCP server URL |
| `ENVIRONMENT` | No | `development` | `production` or `development` |
| `API_HOST` | No | `0.0.0.0` | API bind address |
| `API_PORT` | No | `8000` | API port |

---

## Troubleshooting

### Unified mode: "MCP server not responding"

1. Check logs for MCP mounting: Should see "MCP server mounted at /mcp"
2. Test endpoint: `curl http://localhost:8000/mcp`
3. Verify `MOUNT_MCP_SERVER=true` in environment

### Separate mode: "Connection refused to MCP server"

1. Ensure MCP server is running: `cd tools && python server.py`
2. Check MCP server logs: Should see "Server running on port 8001"
3. Test MCP endpoint: `curl http://localhost:8001/mcp`
4. Verify `MCP_SERVER_URL` points to correct host:port

### Database connection errors

1. Check `DATABASE_URL` format: `postgresql://user:pass@host/dbname?sslmode=require`
2. Verify database is accessible from pod
3. Check `/health` endpoint for database status

### Pod not starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check if secrets exist
kubectl get secrets
```

---

## Production Checklist

- [ ] Set strong `BETTER_AUTH_SECRET` (min 32 characters)
- [ ] Use production database (Neon, RDS, etc.)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure resource limits in Helm values
- [ ] Set up monitoring and logging
- [ ] Test health endpoint returns database connected
- [ ] Verify JWT authentication works end-to-end
- [ ] Test chat functionality with MCP tools

---

## Quick Start Commands

**Local development (separate mode - default):**
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: MCP Server
cd backend/tools
python server.py
```

**Local development (unified mode):**
```bash
# .env
echo "MOUNT_MCP_SERVER=true" >> .env

# Single terminal
cd backend
uvicorn main:app --reload --port 8000
```

**Kubernetes deployment:**
```bash
# Build and deploy
eval $(minikube docker-env)
docker build -t backend-api:latest ./backend
helm upgrade --install backend-api ./infrastructure/helm/backend-api \
  -f ./infrastructure/helm/backend-api/values-local.yaml

# Access via port-forward
kubectl port-forward svc/backend-api 8000:8000
```
