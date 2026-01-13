# Kubernetes Deployment Guide for FastAPI JWT Auth

This guide covers deploying FastAPI with JWT authentication to Kubernetes environments.

## Table of Contents

1. [Secrets Management](#secrets-management)
2. [JWKS Endpoint Accessibility](#jwks-endpoint-accessibility)
3. [Helm Chart Configuration](#helm-chart-configuration)
4. [Dockerfile for FastAPI](#dockerfile-for-fastapi)
5. [Troubleshooting](#troubleshooting)

---

## Secrets Management

### Creating Kubernetes Secrets

JWT authentication requires matching secrets between frontend (Better Auth) and backend (FastAPI):

```bash
# Generate a secure secret (32+ characters)
SECRET=$(openssl rand -base64 32)

# Create backend secret
kubectl create secret generic backend-secrets \
  --from-literal=better-auth-secret="$SECRET" \
  --from-literal=database-url="postgresql://user:pass@host:5432/db"

# Create frontend secret (must match!)
kubectl create secret generic frontend-secrets \
  --from-literal=better-auth-secret="$SECRET" \
  --from-literal=database-url="postgresql://user:pass@host:5432/db"
```

### Verifying Secrets Match

**Critical**: Frontend and backend MUST have identical `BETTER_AUTH_SECRET`:

```bash
# Check backend secret
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
echo ""

# Check frontend secret
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
echo ""

# They MUST be EXACTLY the same - character for character
```

### Updating Secrets

```bash
SECRET="YourNewSecretHere"

# Update both secrets atomically
kubectl patch secret backend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"
kubectl patch secret frontend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"

# Restart deployments to pick up new secrets
kubectl rollout restart deployment backend-api frontend
```

### Common Secret Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| JWT signature invalid | Secrets don't match | Verify secrets are identical |
| 401 on all requests | Backend can't reach JWKS | Check JWKS_URL and network |
| Intermittent 401s | Secret rotation mid-flight | Restart both services after change |

---

## JWKS Endpoint Accessibility

### The Problem

In Kubernetes, the backend must reach the frontend's JWKS endpoint to validate JWTs:

```
Backend Pod → http://frontend:3000/api/auth/jwks → Public Keys
```

### Configuration

**Backend environment variables:**

```yaml
env:
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"  # K8s service DNS
  # OR explicit JWKS URL
  - name: BETTER_AUTH_JWKS_URL
    value: "http://frontend:3000/api/auth/jwks"
```

### Testing JWKS Accessibility from Pod

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -l app=backend-api -o jsonpath='{.items[0].metadata.name}')

# Test JWKS endpoint from inside backend pod
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks

# Should return JSON with keys array:
# {"keys":[{"kty":"OKP","crv":"Ed25519","x":"...","kid":"..."}]}
```

### Testing with Python from Pod

```bash
kubectl exec $BACKEND_POD -- python3 -c "
import urllib.request
import json

url = 'http://frontend:3000/api/auth/jwks'
try:
    response = urllib.request.urlopen(url, timeout=5)
    data = json.loads(response.read())
    print(f'JWKS OK - {len(data.get(\"keys\", []))} keys found')
except Exception as e:
    print(f'JWKS ERROR: {e}')
"
```

### Common JWKS Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused | Frontend service not ready | Check frontend pod status |
| DNS resolution failed | Wrong service name | Use `frontend` not `frontend-service` |
| Timeout | Network policy blocking | Check NetworkPolicy rules |
| 404 Not Found | Better Auth not configured | Verify frontend auth routes |

---

## Helm Chart Configuration

### values.yaml for Backend

```yaml
replicaCount: 1

image:
  repository: backend-api
  tag: latest
  pullPolicy: Never  # Use local images in Minikube

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
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: openai-credentials
        key: openai-api-key
  - name: ENVIRONMENT
    value: "production"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Deployment Template

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "backend-api.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "backend-api.name" . }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include "backend-api.name" . }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: 8000
          env:
            {{- toYaml .Values.env | nindent 12 }}
          livenessProbe:
            {{- toYaml .Values.livenessProbe | nindent 12 }}
          readinessProbe:
            {{- toYaml .Values.readinessProbe | nindent 12 }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

---

## Dockerfile for FastAPI

### Multi-Stage Production Dockerfile

```dockerfile
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim AS runner

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Building for Minikube

```bash
# Use Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image
docker build -t backend-api:latest ./backend

# Verify image exists
docker images | grep backend-api

# Deploy with Helm
helm upgrade --install backend-api ./infrastructure/helm/backend-api \
  -f ./infrastructure/helm/backend-api/values-local.yaml
```

---

## Troubleshooting

### Issue: 401 Unauthorized on All Requests

**Check 1: JWKS endpoint accessible?**
```bash
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks
```

**Check 2: Secrets match?**
```bash
# Compare these outputs - must be identical
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
```

**Check 3: Frontend generating JWTs correctly?**
```bash
kubectl logs -l app=frontend --tail=50 | grep -i jwt
```

### Issue: JWT Signature Invalid

**Cause**: Usually secrets mismatch or JWKS cache stale.

**Fix**:
```bash
# 1. Verify secrets match (see above)

# 2. Restart backend to clear JWKS cache
kubectl rollout restart deployment backend-api

# 3. If still failing, restart both
kubectl rollout restart deployment backend-api frontend
```

### Issue: Connection Refused to JWKS

**Cause**: Frontend service not ready or wrong URL.

**Fix**:
```bash
# Check frontend service exists
kubectl get svc frontend

# Check frontend pods are running
kubectl get pods -l app=frontend

# Check endpoints are populated
kubectl get endpoints frontend

# Test DNS resolution from backend
kubectl exec $BACKEND_POD -- nslookup frontend
```

### Issue: Intermittent 401 Errors

**Cause**: JWKS key rotation or pod restarts.

**Fix**: Implement JWKS caching with refresh:

```python
# In middleware.py
from functools import lru_cache
import time

_jwks_cache = {"keys": None, "fetched_at": 0}
JWKS_CACHE_TTL = 3600  # 1 hour

def get_jwks_client():
    now = time.time()
    if _jwks_cache["keys"] is None or (now - _jwks_cache["fetched_at"]) > JWKS_CACHE_TTL:
        _jwks_cache["keys"] = PyJWKClient(JWKS_URL)
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]
```

### Debug Commands

```bash
# Check all pods status
kubectl get pods -o wide

# Check backend logs
kubectl logs -l app=backend-api --tail=100

# Check frontend logs
kubectl logs -l app=frontend --tail=100

# Describe pod for events
kubectl describe pod $BACKEND_POD

# Check environment variables in pod
kubectl exec $BACKEND_POD -- env | grep -E "(AUTH|JWKS|SECRET)"

# Port forward for local testing
kubectl port-forward svc/backend-api 8000:8000

# Test health endpoint
curl http://localhost:8000/health

# Test protected endpoint without token (should 401)
curl http://localhost:8000/api/test-user/tasks

# Test with valid token from frontend
TOKEN=$(curl -s http://localhost:3000/api/auth/token | jq -r '.token')
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/test-user/tasks
```

---

## Quick Reference

### Required Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `BETTER_AUTH_SECRET` | Secret | Must match frontend |
| `BETTER_AUTH_URL` | ConfigMap | Frontend service URL |
| `DATABASE_URL` | Secret | PostgreSQL connection |

### Key Files

| File | Purpose |
|------|---------|
| `middleware.py` | JWT validation with JWKS |
| `config.py` | Settings with BETTER_AUTH_URL |
| `values.yaml` | Helm chart configuration |

### Verification Commands

```bash
# Secrets match
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# JWKS accessible
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks

# Health check
kubectl exec $BACKEND_POD -- curl -s http://localhost:8000/health
```
