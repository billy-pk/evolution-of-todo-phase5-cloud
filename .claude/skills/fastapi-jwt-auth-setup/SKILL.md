---
name: fastapi-jwt-auth-setup
description: Set up JWT authentication middleware for FastAPI projects using JWKS validation. Use when adding JWT authentication to a new FastAPI project, integrating with Better Auth, Auth0, Clerk, or any JWKS-based auth provider, or implementing multi-tenant user isolation with JWT tokens.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# FastAPI JWT Authentication Setup Skill

## Purpose
Automatically set up JWT authentication middleware for FastAPI projects with:
- JWT validation using JWKS (JSON Web Key Set)
- Multi-algorithm support (EdDSA, ES256, RS256)
- User ID extraction from JWT payload
- Request state management for user context
- FastAPI dependency injection patterns
- Test fixtures for mocking authentication

## When to Use This Skill
- Starting a new FastAPI project that requires JWT authentication
- Integrating with Better Auth, Auth0, Clerk, or custom JWKS-based auth providers
- Implementing multi-tenant applications with user isolation
- Adding JWT validation to existing FastAPI routes
- Setting up authentication test fixtures

## Authentication Flow
```
Client Request
    ↓
Authorization: Bearer <JWT>
    ↓
JWTBearer Middleware
    ↓
1. Extract Bearer token
2. Fetch public key from JWKS endpoint
3. Validate signature (EdDSA/ES256/RS256)
4. Verify expiration time
5. Extract user_id from payload
    ↓
request.state.user_id = <validated_user_id>
    ↓
Route Handler (with user context)
```

## What This Skill Creates

### 1. JWT Middleware (`middleware.py` or `auth/middleware.py`)
- `JWTBearer` class extending FastAPI's `HTTPBearer`
- JWKS client for fetching public keys
- Token verification with signature and expiration validation
- User ID extraction and request state injection

### 2. Configuration Setup (`config.py` updates)
- `BETTER_AUTH_URL` or `JWKS_URL` configuration
- `BETTER_AUTH_SECRET` or JWT secret configuration
- Environment variable support

### 3. Route Protection Pattern (`verify_user_access` function)
- User ID verification (JWT user_id matches path user_id)
- 403 Forbidden enforcement for unauthorized access
- FastAPI dependency for route-level protection

### 4. Test Fixtures (`tests/conftest.py`)
- Mock JWT validation for testing
- Bypass authentication in test client
- Test user ID injection

## Workflow

### Step 1: Understand Current Project Structure
First, determine where to place the authentication code:

```bash
# Check if project has existing auth structure
ls backend/auth/ 2>/dev/null || echo "No auth directory"
ls backend/middleware.py 2>/dev/null || echo "No middleware.py"
```

**Decision Tree**:
- If `backend/auth/` exists → Create `backend/auth/middleware.py`
- If `backend/middleware.py` exists → Add JWT code there
- Otherwise → Create `backend/middleware.py` (recommended)

### Step 2: Gather Authentication Provider Information
Ask the user or infer from context:

**Required Information**:
1. **Auth Provider**: Better Auth, Auth0, Clerk, Custom
2. **JWKS Endpoint URL**: Where to fetch public keys
3. **JWT User ID Claim**: Which field contains user_id (e.g., `user_id`, `sub`, `id`)
4. **Supported Algorithms**: EdDSA, ES256, RS256 (default: all three)

**Example Configurations**:

**Better Auth**:
```python
JWKS_URL = f"{settings.BETTER_AUTH_URL}/api/auth/jwks"
USER_ID_CLAIM = "user_id"
ALGORITHMS = ["EdDSA", "ES256", "RS256"]
```

**Auth0**:
```python
JWKS_URL = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
USER_ID_CLAIM = "sub"
ALGORITHMS = ["RS256"]
```

**Clerk**:
```python
JWKS_URL = f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"
USER_ID_CLAIM = "sub"
ALGORITHMS = ["RS256"]
```

### Step 3: Install Required Dependencies
Check if `PyJWT` and `cryptography` are installed:

```bash
# Check if dependencies exist in pyproject.toml or requirements.txt
grep -E "(pyjwt|PyJWT)" backend/pyproject.toml backend/requirements.txt 2>/dev/null || echo "PyJWT not found"
```

**If missing, add to dependencies**:
```toml
# pyproject.toml (for UV or Poetry)
[project.dependencies]
pyjwt = {extras = ["crypto"], version = "^2.8.0"}

# OR requirements.txt
PyJWT[crypto]>=2.8.0
```

**Install command**:
```bash
cd backend && uv add 'pyjwt[crypto]' || pip install 'PyJWT[crypto]'
```

### Step 4: Update Configuration File
Add authentication settings to `config.py`:

**Template**:
```python
class Settings(BaseSettings):
    # Existing settings...

    # Authentication - JWKS-based JWT validation
    BETTER_AUTH_URL: str = "http://localhost:3000"  # Or AUTH0_DOMAIN, CLERK_DOMAIN
    BETTER_AUTH_SECRET: str  # Optional: for symmetric algorithms

    # Optional: Customize JWKS URL if needed
    JWKS_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
```

**Environment Variable Example (`.env.example`)**:
```bash
# Better Auth Configuration
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_SECRET=your-secret-key-here

# Auth0 Configuration (alternative)
# AUTH0_DOMAIN=your-tenant.auth0.com
# JWKS_URL=https://your-tenant.auth0.com/.well-known/jwks.json
```

### Step 5: Create JWT Middleware
Create `backend/middleware.py` (or appropriate location):

**Use the template from `templates/middleware.py.template`** (see below).

**Key Components**:
1. **JWTBearer Class**: FastAPI HTTPBearer extension
2. **verify_token Function**: JWKS validation logic
3. **JWKS Client Initialization**: PyJWKClient setup
4. **Error Handling**: 401 for invalid/expired tokens

### Step 6: Create User Access Verification Function
Add to routes or create `backend/auth/verify.py`:

**Template**:
```python
from fastapi import Request, HTTPException, Path

def verify_user_access(request: Request, user_id: str = Path(...)) -> str:
    """
    Verify user_id in URL path matches user_id from JWT token.

    Use this as a FastAPI dependency on routes that require user isolation.

    Args:
        request: FastAPI request with user_id in state (set by JWTBearer)
        user_id: User ID from URL path parameter

    Returns:
        Validated user_id

    Raises:
        HTTPException: 401 if not authenticated, 403 if user_id mismatch

    Example:
        @router.get("/{user_id}/tasks")
        async def get_tasks(user_id: str = Depends(verify_user_access)):
            # user_id is validated and safe to use
            pass
    """
    token_user_id = getattr(request.state, "user_id", None)

    if not token_user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    if token_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Cannot access another user's resources"
        )

    return user_id
```

### Step 7: Apply Middleware to Routes
Update `main.py` to apply JWT middleware:

**Option A: Global Application** (all routes under `/api`):
```python
from fastapi import FastAPI, Depends
from middleware import JWTBearer
from routes import tasks

app = FastAPI()

# Apply JWT middleware to all /api routes
app.include_router(
    tasks.router,
    prefix="/api",
    dependencies=[Depends(JWTBearer())]  # Requires JWT on all endpoints
)
```

**Option B: Per-Route Application**:
```python
from fastapi import APIRouter, Depends
from middleware import JWTBearer

router = APIRouter()

@router.get("/protected", dependencies=[Depends(JWTBearer())])
async def protected_route():
    return {"message": "This route requires JWT"}
```

**Option C: With User Access Verification** (recommended for multi-tenant):
```python
from routes.tasks import verify_user_access

@router.get("/{user_id}/tasks")
async def get_tasks(
    user_id: str = Depends(verify_user_access),  # Validates JWT AND user_id match
    session: Session = Depends(get_session)
):
    # Query filtered by validated user_id
    tasks = session.exec(select(Task).where(Task.user_id == user_id)).all()
    return tasks
```

### Step 8: Create Test Fixtures
Update `backend/tests/conftest.py` to mock JWT authentication:

**Template**:
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import create_app
from middleware import JWTBearer
from routes.tasks import verify_user_access

@pytest.fixture
def client(test_db):
    """Test client with mocked JWT validation"""
    app = create_app()

    # Override JWTBearer to bypass actual token validation
    async def override_jwt_bearer():
        return "test_token"  # Dummy token

    # Override verify_user_access to use test user_id
    async def mock_verify_user_access(request, user_id: str):
        # In tests, accept any user_id without validation
        return user_id

    app.dependency_overrides[JWTBearer] = override_jwt_bearer
    app.dependency_overrides[verify_user_access] = mock_verify_user_access

    with TestClient(app) as c:
        yield c

@pytest.fixture
def authenticated_headers():
    """Helper to create authenticated request headers for tests"""
    return {
        "Authorization": "Bearer test_token_123"
    }
```

### Step 9: Validation Checklist
After setup, verify the implementation:

- [ ] **Dependency Installed**: PyJWT[crypto] in dependencies
- [ ] **Configuration Added**: JWKS_URL or BETTER_AUTH_URL in config.py
- [ ] **Middleware Created**: JWTBearer class with verify_token function
- [ ] **JWKS Client Initialized**: PyJWKClient connects to JWKS endpoint
- [ ] **Algorithms Supported**: EdDSA, ES256, RS256 (or provider-specific)
- [ ] **User ID Extraction**: Extracts correct claim (user_id, sub, etc.)
- [ ] **Request State Injection**: request.state.user_id is set
- [ ] **Routes Protected**: Middleware applied via Depends(JWTBearer())
- [ ] **User Access Verification**: verify_user_access function implemented
- [ ] **Test Fixtures Created**: conftest.py mocks JWT validation
- [ ] **Error Handling**: 401 for missing/invalid tokens, 403 for user_id mismatch

### Step 10: Testing the Implementation

**Manual Test with curl**:
```bash
# Without token (should return 401)
curl -X GET http://localhost:8000/api/test-user-123/tasks

# With invalid token (should return 401)
curl -X GET http://localhost:8000/api/test-user-123/tasks \
  -H "Authorization: Bearer invalid-token"

# With valid token (should return 200)
curl -X GET http://localhost:8000/api/test-user-123/tasks \
  -H "Authorization: Bearer <valid-jwt-from-auth-provider>"
```

**Automated Test**:
```python
def test_jwt_required(client):
    """Test that endpoints require JWT"""
    response = client.get("/api/test-user/tasks")
    assert response.status_code == 401

def test_jwt_user_id_mismatch(client):
    """Test that user_id in path must match JWT"""
    # Mock JWT with user_id = "user-a"
    # Try to access user-b's resources
    response = client.get("/api/user-b/tasks")
    assert response.status_code == 403
```

## Templates

### Middleware Template (middleware.py)
```python
"""
JWT Authentication Middleware for FastAPI

Validates JWT tokens using JWKS (JSON Web Key Set) from auth provider.
Supports EdDSA, ES256, and RS256 algorithms.
Extracts user_id from JWT payload and adds to request.state.
"""

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from config import settings
from typing import Optional


class JWTBearer(HTTPBearer):
    """
    HTTP Bearer authentication scheme that validates JWT tokens.

    This middleware:
    1. Extracts the Bearer token from Authorization header
    2. Validates JWT signature using JWKS public key
    3. Checks expiration time
    4. Extracts user_id from payload
    5. Adds user_id to request.state for route handlers

    Usage:
        @app.get("/protected", dependencies=[Depends(JWTBearer())])
        async def protected_route(request: Request):
            user_id = request.state.user_id
            return {"user_id": user_id}
    """

    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme. Use 'Bearer <token>'"
                )

            token = credentials.credentials
            user_id = verify_token(token)

            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token"
                )

            # Add user_id to request state for later use in route handlers
            request.state.user_id = user_id
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=401,
                detail="Missing authorization credentials"
            )


# Initialize JWKS client to fetch public keys from auth provider
# Customize JWKS_URL based on your auth provider:
# - Better Auth: {BETTER_AUTH_URL}/api/auth/jwks
# - Auth0: https://{domain}/.well-known/jwks.json
# - Clerk: https://{domain}/.well-known/jwks.json
JWKS_URL = getattr(settings, 'JWKS_URL', None) or f"{settings.BETTER_AUTH_URL}/api/auth/jwks"
jwks_client = PyJWKClient(JWKS_URL)


def verify_token(token: str) -> Optional[str]:
    """
    Verify the JWT token and return the user_id if valid.

    Validates:
    - JWT signature using JWKS public key
    - Token expiration time
    - Presence of user_id claim

    Args:
        token: JWT token string from Authorization header

    Returns:
        user_id if token is valid, None otherwise

    Supported Algorithms:
        - EdDSA: Edwards-curve Digital Signature Algorithm
        - ES256: ECDSA with SHA-256
        - RS256: RSA with SHA-256
    """
    try:
        # Get the signing key from JWKS endpoint
        # The PyJWKClient fetches the public key matching the token's key ID
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify the JWT token using the public key
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA", "ES256", "RS256"],  # Customize based on provider
            options={
                "verify_exp": True,   # Verify expiration
                "verify_aud": False,  # Don't verify audience claim (customize if needed)
            }
        )

        # Extract user_id from the payload
        # Customize claim name based on your auth provider:
        # - Better Auth: "user_id"
        # - Auth0/Clerk: "sub"
        user_id = payload.get("user_id") or payload.get("sub")

        if not user_id:
            print(f"JWT validation error: Token missing user_id claim. Payload keys: {payload.keys()}")
            return None

        return user_id

    except jwt.ExpiredSignatureError:
        print("JWT validation error: Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"JWT validation error: {e}")
        return None
    except Exception as e:
        print(f"JWT validation error: Unexpected error: {e}")
        return None
```

### Config Template (config.py addition)
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ... existing settings ...

    # JWT Authentication Configuration
    BETTER_AUTH_URL: str = "http://localhost:3000"
    BETTER_AUTH_SECRET: str  # Required: shared secret for JWT validation

    # Optional: Override JWKS URL if using custom auth provider
    JWKS_URL: Optional[str] = None

    # Optional: Customize JWT user ID claim name
    JWT_USER_ID_CLAIM: str = "user_id"  # Or "sub" for Auth0/Clerk

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### Test Fixtures Template (conftest.py)
```python
import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from main import create_app
from middleware import JWTBearer
from routes.tasks import verify_user_access  # Adjust import path


@pytest.fixture
def client(test_db):
    """
    Create a test client with mocked JWT validation.

    This fixture overrides JWT authentication to allow testing
    without needing real JWT tokens.
    """
    app = create_app()

    # Override JWTBearer to bypass actual token validation
    async def override_jwt_bearer(request: Request):
        # Inject a test user_id into request.state
        request.state.user_id = "test_user_123"
        return "mock_token"

    app.dependency_overrides[JWTBearer] = override_jwt_bearer

    # Optional: Override verify_user_access for more flexible testing
    async def mock_verify_user_access(request: Request, user_id: str):
        # In tests, allow any user_id without strict validation
        return user_id

    app.dependency_overrides[verify_user_access] = mock_verify_user_access

    with TestClient(app) as c:
        yield c


@pytest.fixture
def authenticated_headers():
    """Helper fixture for authenticated request headers in tests"""
    return {
        "Authorization": "Bearer test_token_123",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_user_id():
    """Consistent test user ID across tests"""
    return "test_user_123"
```

## Common Use Cases

### Use Case 1: New FastAPI Project with Better Auth
```
User: "Set up JWT authentication for my new FastAPI project using Better Auth"

Steps:
1. Ask: "What is your Better Auth frontend URL?" (e.g., http://localhost:3000)
2. Install PyJWT[crypto] dependency
3. Update config.py with BETTER_AUTH_URL and BETTER_AUTH_SECRET
4. Create middleware.py with JWTBearer class
5. Create verify_user_access function
6. Update main.py to apply middleware to routes
7. Create test fixtures in conftest.py
8. Provide .env.example with required variables
```

### Use Case 2: Migrate from API Key to JWT
```
User: "I currently use API keys but want to switch to JWT authentication"

Steps:
1. Identify current authentication mechanism
2. Create JWT middleware (keep API key middleware temporarily)
3. Add optional JWT support to routes (dual authentication)
4. Update frontend to use JWT tokens
5. Gradually migrate routes from API key to JWT
6. Remove API key authentication when migration complete
```

### Use Case 3: Multi-Tenant SaaS with User Isolation
```
User: "Add JWT authentication with strict user isolation for my multi-tenant app"

Steps:
1. Set up JWT middleware
2. Create verify_user_access dependency
3. Apply to all routes: @router.get("/{user_id}/resources", dependencies=[Depends(verify_user_access)])
4. Update database queries to filter by user_id
5. Add tests to verify user isolation (user A cannot access user B's data)
6. Document multi-tenant security patterns
```

### Use Case 4: Auth0 Integration
```
User: "Integrate Auth0 JWT authentication into my FastAPI app"

Steps:
1. Ask: "What is your Auth0 domain?" (e.g., your-tenant.auth0.com)
2. Set JWKS_URL to https://{domain}/.well-known/jwks.json
3. Update verify_token to use "sub" claim instead of "user_id"
4. Set algorithms to ["RS256"] (Auth0 default)
5. Create middleware.py with Auth0 configuration
6. Provide Auth0-specific .env.example
```

## Error Handling Patterns

### 401 Unauthorized - Missing or Invalid Token
```python
# Triggered when:
# - No Authorization header
# - Invalid Bearer format
# - Expired token
# - Invalid signature

raise HTTPException(
    status_code=401,
    detail="Invalid or expired token"
)
```

### 403 Forbidden - User ID Mismatch
```python
# Triggered when:
# - JWT user_id ≠ path user_id
# - User trying to access another user's resources

raise HTTPException(
    status_code=403,
    detail="Access denied: Cannot access another user's resources"
)
```

### 422 Unprocessable Entity - Malformed JWT
```python
# Triggered when:
# - Token cannot be decoded
# - Missing required claims

raise HTTPException(
    status_code=422,
    detail="Malformed JWT token"
)
```

## Security Best Practices

### 1. Always Verify Expiration
```python
options={
    "verify_exp": True,  # ALWAYS enable expiration check
}
```

### 2. Use HTTPS in Production
```python
# In config.py
JWKS_URL: str  # Must be HTTPS in production

# Validate in middleware
if settings.ENVIRONMENT == "production" and not JWKS_URL.startswith("https"):
    raise ValueError("JWKS_URL must use HTTPS in production")
```

### 3. Filter All Queries by user_id
```python
# CORRECT: Always filter by validated user_id
tasks = session.exec(
    select(Task).where(Task.user_id == user_id)
).all()

# WRONG: Never query without user_id filter in multi-tenant apps
tasks = session.exec(select(Task)).all()  # ❌ SECURITY RISK
```

### 4. Use Strong Secrets
```python
# .env
BETTER_AUTH_SECRET=<generate-with>: openssl rand -base64 32
```

### 5. Log Authentication Failures (But Not Token Contents)
```python
# CORRECT: Log without exposing token
print(f"JWT validation failed for user_id: {payload.get('user_id')}")

# WRONG: Never log full token
print(f"JWT validation failed: {token}")  # ❌ SECURITY RISK
```

## Production JWKS Issues (Critical)

### Issue: Backend Can't Reach JWKS Endpoint

**Symptom:**
```
httpx.ConnectError: Cannot connect to host localhost:3000
```

**Common in:** Backend on Render/Railway, Frontend on Vercel

**Solution:** Use production URL, not localhost:

```python
# ❌ WRONG - localhost doesn't work in production
JWKS_URL = "http://localhost:3000/api/auth/jwks"

# ✅ CORRECT - use production frontend URL
JWKS_URL = "https://yourapp.vercel.app/api/auth/jwks"
```

**Environment Variables:**
```bash
# Backend .env
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks
```

### Testing JWKS Accessibility

```bash
# Test from backend server
curl https://yourapp.vercel.app/api/auth/jwks
# Should return: {"keys": [...]}

# Test from local machine
curl https://backend.onrender.com/health
# Verify backend can make external requests
```

**See reference.md for complete production troubleshooting guide.**

## Debugging Tips

### Enable Verbose Logging
```python
# In verify_token function (remove in production)
print(f"Decoded JWT payload: {payload}")
print(f"Extracted user_id: {user_id}")
print(f"JWKS URL: {JWKS_URL}")
```

### Common Issues

**Issue**: "Invalid signature"
**Solution**: Verify JWKS_URL is correct and accessible. Check network connectivity.

**Issue**: "Token has expired"
**Solution**: Check system clock synchronization. Verify token generation time.

**Issue**: "Missing user_id claim"
**Solution**: Check JWT payload structure. Ensure auth provider includes user_id or sub claim.

**Issue**: "JWKS endpoint not found"
**Solution**: Verify auth provider URL. Check CORS settings if browser-based.

## Integration Examples

### With FastAPI Router
```python
from fastapi import APIRouter, Depends
from middleware import JWTBearer
from routes.tasks import verify_user_access

router = APIRouter(prefix="/api", dependencies=[Depends(JWTBearer())])

@router.get("/{user_id}/tasks")
async def get_tasks(user_id: str = Depends(verify_user_access)):
    # user_id is validated and safe to use
    return {"user_id": user_id}
```

### With SQLModel Queries
```python
from sqlmodel import Session, select
from models import Task

@router.get("/{user_id}/tasks")
async def get_tasks(
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session)
):
    # Always filter by validated user_id
    statement = select(Task).where(Task.user_id == user_id)
    tasks = session.exec(statement).all()
    return tasks
```

### With Background Tasks
```python
from fastapi import BackgroundTasks

@router.post("/{user_id}/tasks")
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_user_access)
):
    # user_id is available in background tasks
    background_tasks.add_task(send_notification, user_id, task_data)
    return {"status": "created"}
```

## Summary
This skill automates the complete setup of JWT authentication for FastAPI projects, including:
- ✅ JWKS-based token validation
- ✅ Multi-algorithm support (EdDSA, ES256, RS256)
- ✅ User ID extraction and request state management
- ✅ Multi-tenant user isolation patterns
- ✅ Test fixtures for authentication mocking
- ✅ Security best practices and error handling

Use this skill to quickly bootstrap secure, production-ready JWT authentication in any FastAPI project.
