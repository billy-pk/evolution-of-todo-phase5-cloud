---
name: fastapi-jwt-auth-setup
description: Set up JWT authentication middleware for FastAPI projects using JWKS validation. Use when adding JWT authentication to a new FastAPI project, integrating with Better Auth, Auth0, Clerk, or any JWKS-based auth provider, or implementing multi-tenant user isolation with JWT tokens. For full-stack Kubernetes deployment, see nextjs-fastapi-mcp-architecture skill.
---

# FastAPI JWT Authentication Setup

## Overview

Set up JWT authentication middleware for FastAPI with:
- JWKS-based token validation
- Multi-algorithm support (EdDSA, ES256, RS256)
- User ID extraction and request state injection
- Multi-tenant user isolation patterns

## Quick Start

### 1. Install Dependencies

```bash
cd backend && uv add 'pyjwt[crypto]'
# OR
pip install 'PyJWT[crypto]'
```

### 2. Add Configuration

**config.py:**
```python
class Settings(BaseSettings):
    BETTER_AUTH_URL: str = "http://localhost:3000"
    BETTER_AUTH_SECRET: str
    JWKS_URL: Optional[str] = None  # Override if needed

settings = Settings()
```

### 3. Create JWT Middleware

**middleware.py:**
```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from config import settings

JWKS_URL = settings.JWKS_URL or f"{settings.BETTER_AUTH_URL}/api/auth/jwks"
jwks_client = PyJWKClient(JWKS_URL)

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")

        user_id = verify_token(credentials.credentials)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        request.state.user_id = user_id
        return credentials.credentials

def verify_token(token: str) -> str | None:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key,
            algorithms=["EdDSA", "ES256", "RS256"],
            options={"verify_exp": True}
        )
        return payload.get("user_id") or payload.get("sub")
    except jwt.PyJWTError:
        return None
```

### 4. Create User Access Verification

```python
from fastapi import Request, HTTPException, Path

def verify_user_access(request: Request, user_id: str = Path(...)) -> str:
    """Verify JWT user_id matches path user_id."""
    token_user_id = getattr(request.state, "user_id", None)

    if not token_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if token_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return user_id
```

### 5. Apply to Routes

```python
from fastapi import APIRouter, Depends
from middleware import JWTBearer

router = APIRouter(prefix="/api", dependencies=[Depends(JWTBearer())])

@router.get("/{user_id}/tasks")
async def get_tasks(user_id: str = Depends(verify_user_access)):
    # user_id is validated
    return {"user_id": user_id}
```

**For complete implementation details, see [reference.md](reference.md).**

---

## Kubernetes Deployment

> **Note:** For complete Kubernetes deployment with Helm charts and full-stack deployment patterns, see the **[nextjs-fastapi-mcp-architecture](../nextjs-fastapi-mcp-architecture/SKILL.md)** skill. This section covers backend-specific JWT validation concerns only.

### Backend-Specific JWT Configuration

**Critical for JWT validation in Kubernetes:**

1. **JWKS Endpoint Must Be Reachable**
   ```bash
   # Test JWKS accessibility from backend pod
   BACKEND_POD=$(kubectl get pods -l app=backend-api -o jsonpath='{.items[0].metadata.name}')
   kubectl exec $BACKEND_POD -- curl -s http://frontend:3000/api/auth/jwks
   ```

2. **Secrets Must Match Between Frontend and Backend**
   ```bash
   # Quick verification
   kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
   kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
   # These MUST be identical
   ```

3. **Environment Variables**
   ```yaml
   env:
     - name: BETTER_AUTH_URL
       value: "http://frontend:3000"  # K8s service DNS
     - name: BETTER_AUTH_JWKS_URL
       value: "http://frontend:3000/api/auth/jwks"
   ```

For detailed Kubernetes troubleshooting, see **[kubernetes.md](kubernetes.md)** (backend-specific JWT issues).

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 401 on all requests | JWKS unreachable | Check `BETTER_AUTH_URL` |
| Invalid signature | Secrets mismatch | Verify secrets match |
| Token expired | Clock skew | Sync system clocks |
| Missing user_id claim | Wrong claim name | Use `sub` for Auth0/Clerk |
| JWKS 404 | Auth not configured | Check frontend routes |

---

## Auth Provider Configurations

### Better Auth (Default)
```python
JWKS_URL = f"{BETTER_AUTH_URL}/api/auth/jwks"
USER_ID_CLAIM = "user_id"
ALGORITHMS = ["EdDSA", "ES256", "RS256"]
```

### Auth0
```python
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
USER_ID_CLAIM = "sub"
ALGORITHMS = ["RS256"]
```

### Clerk
```python
JWKS_URL = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"
USER_ID_CLAIM = "sub"
ALGORITHMS = ["RS256"]
```

---

## Test Fixtures

**conftest.py:**
```python
import pytest
from fastapi.testclient import TestClient
from main import create_app
from middleware import JWTBearer

@pytest.fixture
def client(test_db):
    app = create_app()

    async def override_jwt(request):
        request.state.user_id = "test_user_123"
        return "mock_token"

    app.dependency_overrides[JWTBearer] = override_jwt

    with TestClient(app) as c:
        yield c

@pytest.fixture
def authenticated_headers():
    return {"Authorization": "Bearer test_token"}
```

---

## Security Checklist

- [ ] `verify_exp: True` in JWT decode options
- [ ] HTTPS for JWKS URL in production
- [ ] All queries filtered by validated `user_id`
- [ ] Strong secret (32+ chars): `openssl rand -base64 32`
- [ ] Never log full tokens
- [ ] Secrets match between frontend/backend

---

## Reference Files

| File | Content |
|------|---------|
| [reference.md](reference.md) | Complete implementation, templates, troubleshooting |
| [kubernetes.md](kubernetes.md) | **Backend-specific** JWT validation in K8s (JWKS testing, 401 debugging). For full deployment, see nextjs-fastapi-mcp-architecture |
| [templates/](templates/) | Copy-paste ready code templates |

---

## Resources

- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Better Auth](https://www.better-auth.com/docs)

## Related Skills

- **nextjs-fastapi-mcp-architecture** - Full-stack architecture with complete Kubernetes deployment patterns
- **better-auth-next-app-router** - Frontend Better Auth setup, EdDSA JWT signing, JWKS endpoint configuration
- **fastmcp-database-tools** - MCP server implementation with database tools
