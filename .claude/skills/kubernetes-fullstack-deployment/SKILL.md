---
name: kubernetes-fullstack-deployment
description: Deploy and manage Next.js + FastAPI + MCP Server full-stack applications on Kubernetes (Minikube or cloud). Provides deployment workflows, troubleshooting for JWT/JWKS authentication errors, port-forwarding for WSL2/Windows, hot-reloading for development, and cloud deployment patterns. Use when: (1) Deploying multi-service applications to Kubernetes, (2) Setting up Better Auth JWT with JWKS validation between services, (3) Configuring development environments with port-forwards on WSL2/Windows, (4) Troubleshooting 401 Unauthorized or 421 Misdirected Request errors in service mesh, (5) Hot-reloading code changes in Minikube, (6) Deploying to Oracle Cloud Always Free tier or similar cloud platforms.
---

# Kubernetes Full-Stack Deployment

Deploy and troubleshoot Next.js + FastAPI + MCP application on Kubernetes with Better Auth JWT validation.

## Prerequisites

- Minikube running with Docker driver
- kubectl configured
- Helm 3.x installed
- Docker images built locally

## Quick Start

### 1. Initial Deployment

```bash
# Set environment variables
export DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'
export BETTER_AUTH_SECRET='your-secret-key'
export OPENAI_API_KEY='sk-...'

# Deploy all services
./deployment/deploy.sh
```

### 2. Port-Forward for Development (WSL2/Windows)

```bash
# Must use --address 0.0.0.0 for Windows browser access
kubectl port-forward --address 0.0.0.0 svc/ai-todo-frontend-service 3000:3000 &
kubectl port-forward --address 0.0.0.0 svc/ai-todo-backend-service 8000:8000 &

# Access from Windows browser: http://localhost:3000
```

### 3. Update Code and Reload

```bash
# Rebuild images
./deployment/build-images.sh

# Load into Minikube
minikube image load ai-todo-mcp:latest --overwrite

# Restart pods
kubectl delete pod -l app=ai-todo-mcp
```

## Critical Configuration

### Backend ConfigMap (BETTER_AUTH_URL)

Backend MUST know where to fetch JWKS:

```bash
kubectl create configmap ai-todo-backend-config \
  --from-literal=BETTER_AUTH_URL='http://ai-todo-frontend-service:3000' \
  --from-literal=MCP_SERVER_URL='http://ai-todo-mcp-service:8001'
```

### MCP Allowed Hosts

MCP server must trust Kubernetes DNS:

```python
allowed_hosts_list = [
    "localhost:*",
    "ai-todo-mcp-service:*",  # Critical for K8s
]
```

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | JWKS fetch fails | Set `BETTER_AUTH_URL` in backend ConfigMap |
| 421 Misdirected Request | MCP rejects hostname | Add `ai-todo-mcp-service:*` to allowed_hosts |
| Connection refused (3000) | Port-forward stopped | Restart with `--address 0.0.0.0` |
| Database timeout | Old connections | Restart frontend pod |

See [troubleshooting.md](./references/troubleshooting.md) for detailed solutions.

## Architecture

```
Browser (Windows)
    ↓
localhost:3000 (port-forward)
    ↓
Frontend Pod → Backend Pod → MCP Pod
                    ↓
            Neon PostgreSQL (external)
```

## Deployment Options

- **Local Development:** Minikube (see above)
- **Cloud Production:** Oracle Cloud Always Free tier (see [cloud-deployment.md](./references/cloud-deployment.md))

## Reference Files

- **[reference.md](./references/reference.md)** - Detailed commands and configurations
- **[troubleshooting.md](./references/troubleshooting.md)** - Issue diagnosis and solutions
- **[workflow.md](./references/workflow.md)** - Step-by-step deployment procedures
- **[cloud-deployment.md](./references/cloud-deployment.md)** - Oracle Cloud deployment guide (Always Free tier)
