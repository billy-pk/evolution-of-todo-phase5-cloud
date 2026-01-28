# Kubernetes Deployment Guide for FastAPI JWT Auth

This guide covers **backend-specific JWT validation concerns** in Kubernetes environments.

> **Note:** For complete Kubernetes deployment with Helm charts, secrets management, and full-stack deployment patterns, see the **[nextjs-fastapi-mcp-architecture](../nextjs-fastapi-mcp-architecture/SKILL.md)** skill. This guide focuses exclusively on JWT validation debugging and backend-specific issues.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [JWKS Endpoint Accessibility](#jwks-endpoint-accessibility)
3. [Backend JWT Configuration](#backend-jwt-configuration)
4. [Troubleshooting JWT Validation](#troubleshooting-jwt-validation)
5. [Advanced Patterns](#advanced-patterns)

---

## Prerequisites

Before debugging JWT validation, ensure:

1. **Frontend and backend are deployed** - See nextjs-fastapi-mcp-architecture skill
2. **Secrets are configured** - Frontend and backend must share `BETTER_AUTH_SECRET`
3. **Services are accessible** - Pods can reach each other via Kubernetes DNS

**Quick verification:**
```bash
# Verify secrets match (critical for JWT validation)
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
# These MUST be identical

# Check both services exist
kubectl get svc frontend backend-api
```

---

## JWKS Endpoint Accessibility

### The Problem

In Kubernetes, the FastAPI backend must reach the frontend's JWKS endpoint to validate JWTs:

```
User → Frontend → Backend (validates JWT) → Frontend JWKS endpoint → Public Keys
```

If the backend cannot reach the JWKS endpoint, **all authenticated requests will fail with 401**.

### Testing JWKS Accessibility

**From backend pod (most reliable test):**

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -l app.kubernetes.io/name=backend-api -o jsonpath='{.items[0].metadata.name}')

# Test JWKS endpoint from inside backend pod
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks

# Expected output:
# {"keys":[{"kty":"OKP","crv":"Ed25519","x":"...","kid":"..."}]}
```

**Using Python from pod (matches middleware behavior):**

```bash
kubectl exec $BACKEND_POD -- python3 -c "
import urllib.request
import json

url = 'http://frontend:3000/api/auth/jwks'
try:
    response = urllib.request.urlopen(url, timeout=5)
    data = json.loads(response.read())
    print(f'✓ JWKS OK - {len(data.get(\"keys\", []))} keys found')
except Exception as e:
    print(f'✗ JWKS ERROR: {e}')
"
```

### Common JWKS Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused | Frontend service not ready | `kubectl get pods -l app=frontend` |
| DNS resolution failed | Wrong service name | Use `frontend` not `frontend-service` |
| Timeout | Network policy blocking | Check NetworkPolicy rules |
| 404 Not Found | Better Auth not configured | Verify `app/api/auth/[...all]/route.ts` exists |
| Empty keys array | JWKS not generated | Check frontend logs, restart frontend |

---

## Backend JWT Configuration

### Environment Variables

**Critical for JWT validation:**

```yaml
env:
  # Option 1: Use base URL (middleware constructs JWKS URL)
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"  # K8s service DNS name

  # Option 2: Explicit JWKS URL (overrides base URL)
  - name: BETTER_AUTH_JWKS_URL
    value: "http://frontend:3000/api/auth/jwks"

  # Secret MUST match frontend secret
  - name: BETTER_AUTH_SECRET
    valueFrom:
      secretKeyRef:
        name: better-auth-secret
        key: better-auth-secret
```

### Middleware Configuration

**middleware.py:**

```python
import os
from jwt import PyJWKClient

# Construct JWKS URL
BETTER_AUTH_URL = os.getenv("BETTER_AUTH_URL", "http://localhost:3000")
JWKS_URL = os.getenv("BETTER_AUTH_JWKS_URL") or f"{BETTER_AUTH_URL}/api/auth/jwks"

# Initialize JWKS client
jwks_client = PyJWKClient(JWKS_URL)
```

### Testing Configuration from Pod

```bash
# Check environment variables
kubectl exec $BACKEND_POD -- env | grep -E "(AUTH|JWKS)"

# Should see:
# BETTER_AUTH_URL=http://frontend:3000
# BETTER_AUTH_SECRET=<secret>
# (or BETTER_AUTH_JWKS_URL if explicitly set)
```

---

## Troubleshooting JWT Validation

### Issue: 401 Unauthorized on All Requests

**Symptoms:**
- All authenticated API requests return 401
- Backend logs show JWT validation errors
- Frontend authentication works (users can sign in)

**Diagnosis Steps:**

**Step 1: Verify JWKS endpoint is reachable**
```bash
BACKEND_POD=$(kubectl get pods -l app.kubernetes.io/name=backend-api -o jsonpath='{.items[0].metadata.name}')
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks

# If this fails → JWKS connectivity issue
# If this succeeds → Check secrets or backend logs
```

**Step 2: Verify secrets match**
```bash
# Compare these outputs - must be EXACTLY identical
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
echo ""
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
echo ""

# If different → Update secrets to match
```

**Step 3: Check backend logs for JWT errors**
```bash
kubectl logs -l app.kubernetes.io/name=backend-api --tail=50 | grep -i "jwt\|auth\|401"

# Look for:
# - "Invalid signature" → Secrets mismatch
# - "Unable to find matching key" → JWKS not accessible
# - "Token expired" → Clock skew or expired token
```

**Step 4: Check frontend is generating JWTs**
```bash
kubectl logs -l app.kubernetes.io/name=frontend --tail=50 | grep -i jwt

# Should see sign-in events, no decryption errors
```

---

### Issue: JWT Signature Invalid

**Symptoms:**
```
PyJWTError: Signature verification failed
```

**Cause:** Usually secrets mismatch or stale JWKS cache.

**Fix:**

```bash
# 1. Verify secrets match (see above)

# 2. Restart backend to clear JWKS cache
kubectl rollout restart deployment backend-api

# 3. If still failing, check frontend JWKS
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks | jq .

# 4. Restart both services
kubectl rollout restart deployment backend-api frontend
```

---

### Issue: Connection Refused to JWKS

**Symptoms:**
```
ConnectionError: Connection refused
URLError: <urlopen error [Errno 111] Connection refused>
```

**Cause:** Frontend service not ready or wrong URL.

**Fix:**

```bash
# Check frontend service exists and has endpoints
kubectl get svc frontend
kubectl get endpoints frontend

# If no endpoints → Frontend pods not ready
kubectl get pods -l app.kubernetes.io/name=frontend

# Check frontend pod status
kubectl describe pod <frontend-pod-name>

# Test DNS resolution from backend
kubectl exec $BACKEND_POD -- nslookup frontend

# If DNS fails → Check service name matches deployment
kubectl get svc | grep frontend
```

---

### Issue: Intermittent 401 Errors

**Symptoms:**
- Most requests succeed
- Occasional 401 errors
- No pattern to failures

**Cause:** JWKS key rotation or pod restarts.

**Fix:** Implement JWKS caching with refresh:

```python
# In middleware.py
from functools import lru_cache
import time

_jwks_cache = {"client": None, "fetched_at": 0}
JWKS_CACHE_TTL = 3600  # 1 hour

def get_jwks_client():
    """Get JWKS client with caching."""
    now = time.time()
    if _jwks_cache["client"] is None or (now - _jwks_cache["fetched_at"]) > JWKS_CACHE_TTL:
        _jwks_cache["client"] = PyJWKClient(JWKS_URL)
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["client"]

# Use in verify_token
def verify_token(token: str) -> str | None:
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["EdDSA", "ES256", "RS256"])
        return payload.get("user_id") or payload.get("sub")
    except jwt.PyJWTError:
        return None
```

---

### Issue: Token Expired Errors

**Symptoms:**
```
jwt.ExpiredSignatureError: Signature has expired
```

**Cause:** Token TTL exceeded or clock skew between frontend/backend.

**Fix:**

```bash
# Check pod clocks are synchronized
kubectl exec $BACKEND_POD -- date
kubectl exec $FRONTEND_POD -- date

# If clocks differ > 30 seconds → NTP issue
# For Minikube, restart minikube to sync time:
minikube stop && minikube start

# For cloud K8s → Check node time synchronization
```

---

## Advanced Patterns

### Multi-Provider JWT Validation

Support multiple auth providers (Better Auth + Auth0):

```python
# middleware.py
from typing import Dict, List

AUTH_PROVIDERS = {
    "better-auth": {
        "jwks_url": "http://frontend:3000/api/auth/jwks",
        "algorithms": ["EdDSA", "ES256"],
        "user_claim": "user_id",
    },
    "auth0": {
        "jwks_url": "https://your-domain.auth0.com/.well-known/jwks.json",
        "algorithms": ["RS256"],
        "user_claim": "sub",
    },
}

def verify_token_multi_provider(token: str) -> str | None:
    """Try validating token against multiple providers."""
    for provider_name, config in AUTH_PROVIDERS.items():
        try:
            jwks_client = PyJWKClient(config["jwks_url"])
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token, signing_key.key,
                algorithms=config["algorithms"],
                options={"verify_exp": True}
            )
            user_id = payload.get(config["user_claim"])
            if user_id:
                return user_id
        except jwt.PyJWTError:
            continue  # Try next provider
    return None  # No provider validated token
```

### JWT Validation with User Context Injection

Inject user context into request state for dependency injection:

```python
# middleware.py
from fastapi import Request, HTTPException

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials = await super().__call__(request)

        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")

        user_id = verify_token(credentials.credentials)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Inject user context into request state
        request.state.user_id = user_id
        request.state.authenticated = True

        return credentials.credentials

# Usage in routes
from fastapi import Depends, Request

async def get_current_user(request: Request) -> str:
    """Dependency to get current user from request state."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id

@app.get("/api/{user_id}/tasks")
async def get_tasks(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    # Verify path user_id matches token user_id
    if user_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"tasks": []}
```

---

## Debug Commands Reference

```bash
# Get pod names
BACKEND_POD=$(kubectl get pods -l app.kubernetes.io/name=backend-api -o jsonpath='{.items[0].metadata.name}')
FRONTEND_POD=$(kubectl get pods -l app.kubernetes.io/name=frontend -o jsonpath='{.items[0].metadata.name}')

# Check all services
kubectl get svc

# Check pod status
kubectl get pods -o wide

# Check backend logs for JWT errors
kubectl logs $BACKEND_POD --tail=100 | grep -i "jwt\|401\|auth"

# Check frontend logs for auth errors
kubectl logs $FRONTEND_POD --tail=100 | grep -i "auth\|jwks"

# Test JWKS from backend
kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks | jq .

# Check environment variables
kubectl exec $BACKEND_POD -- env | grep -E "(AUTH|JWKS|SECRET)"

# Verify secrets match
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d && echo
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d && echo

# Describe pod for events
kubectl describe pod $BACKEND_POD

# Port forward for local testing
kubectl port-forward svc/backend-api 8000:8000 &
kubectl port-forward svc/frontend 3000:3000 &

# Restart services
kubectl rollout restart deployment backend-api
kubectl rollout restart deployment frontend
```

---

## Related Documentation

- **[nextjs-fastapi-mcp-architecture](../nextjs-fastapi-mcp-architecture/kubernetes.md)** - Complete Kubernetes deployment with Helm charts, secrets management, and multi-service orchestration
- **[better-auth-next-app-router](../better-auth-next-app-router/kubernetes.md)** - Frontend-specific Kubernetes issues (Happy Eyeballs fix, JWKS cleanup)
- **[SKILL.md](SKILL.md)** - FastAPI JWT authentication middleware implementation

---

## Quick Reference

### Environment Variables (Backend)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BETTER_AUTH_URL` | Yes (or JWKS_URL) | Frontend service URL | `http://frontend:3000` |
| `BETTER_AUTH_JWKS_URL` | No | Explicit JWKS URL | `http://frontend:3000/api/auth/jwks` |
| `BETTER_AUTH_SECRET` | Yes | Shared secret (must match frontend) | `<32+ char secret>` |

### Critical Checks

1. ✅ JWKS endpoint reachable from backend pod
2. ✅ Secrets match exactly between frontend and backend
3. ✅ Frontend service has ready endpoints
4. ✅ Backend logs show no JWT validation errors
5. ✅ Clock synchronization (for exp claim validation)

### Common 401 Fixes

| Issue | Quick Fix |
|-------|-----------|
| JWKS unreachable | `kubectl exec $BACKEND_POD -- curl http://frontend:3000/api/auth/jwks` |
| Secrets mismatch | Verify secrets, update if needed, restart pods |
| Stale cache | `kubectl rollout restart deployment backend-api` |
| Frontend not ready | `kubectl get pods -l app=frontend` |
| Wrong algorithms | Check middleware algorithms match JWT `alg` |
