---
name: fastapi-jwt-auth-setup-reference
description: Technical reference for JWT authentication troubleshooting, JWKS endpoint validation, production deployment patterns, and multi-service authentication debugging.
---

# FastAPI JWT Authentication - Technical Reference

## Production JWKS Troubleshooting

### Understanding JWKS Architecture

**Development (Single Host):**
```
┌─────────────────────┐
│  localhost:3000     │
│  ┌───────────────┐  │
│  │ Frontend      │  │
│  │ Better Auth   │  │
│  │ /api/auth/jwks│  │
│  └───────────────┘  │
│         ↓           │
│  ┌───────────────┐  │
│  │ Backend       │  │
│  │ Fetches JWKS  │  │
│  └───────────────┘  │
└─────────────────────┘
```

**Production (Multi-Host):**
```
Frontend (Vercel)              Backend (Render)
┌──────────────────────┐      ┌──────────────────────┐
│ yourapp.vercel.app   │      │ api.yourapp.com      │
│ /api/auth/jwks       │◄─────│ Fetches JWKS via HTTP│
└──────────────────────┘      └──────────────────────┘
   Must be publicly accessible!
```

### Common Production Errors

#### Error 1: Connection Refused (localhost in production)

**Full Error:**
```
httpx.ConnectError: [Errno 111] Connection refused
Error connecting to http://localhost:3000/api/auth/jwks
```

**Cause:** Backend trying to fetch JWKS from localhost, but frontend is on different host.

**Diagnosis:**
```bash
# Check backend environment variable
echo $BETTER_AUTH_JWKS_URL
# If shows: http://localhost:3000/api/auth/jwks → WRONG

# Should show: https://yourapp.vercel.app/api/auth/jwks
```

**Fix:**
```python
# backend/config.py
class Settings:
    BETTER_AUTH_JWKS_URL: str = os.getenv(
        "BETTER_AUTH_JWKS_URL",
        "http://localhost:3000/api/auth/jwks"  # Development default
    )

# backend/.env (production)
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks
```

**Deploy:**
```bash
# Update environment variable in Render/Railway dashboard
# Redeploy backend service
```

#### Error 2: JWKS Endpoint 404

**Full Error:**
```
httpx.HTTPStatusError: Client error '404 Not Found' for url 'https://yourapp.vercel.app/api/auth/jwks'
```

**Cause:** JWKS endpoint not properly configured or frontend not deployed.

**Diagnosis:**
```bash
# Test JWKS endpoint directly
curl https://yourapp.vercel.app/api/auth/jwks

# Should return (example):
{
  "keys": [
    {
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "base64-encoded-public-key",
      "use": "sig",
      "kid": "key-id"
    }
  ]
}

# If 404:
# 1. Check frontend is deployed
# 2. Verify route file exists: app/api/auth/[...all]/route.ts
# 3. Check Better Auth initialization in lib/auth.ts
```

**Fix:**
```typescript
// frontend/app/api/auth/[...all]/route.ts
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

// Export both GET and POST
export const { GET, POST } = toNextJsHandler(auth);

// This automatically creates /api/auth/jwks endpoint
```

#### Error 3: CORS Blocking JWKS Request

**Full Error:**
```
Access to fetch at 'https://yourapp.vercel.app/api/auth/jwks' from origin 'https://api.yourapp.com'
has been blocked by CORS policy
```

**Cause:** Frontend CORS not allowing backend to fetch JWKS.

**Solution:** JWKS endpoint must be publicly accessible (no CORS needed for server-to-server):

```typescript
// frontend/app/api/auth/[...all]/route.ts

// Better Auth handles CORS automatically
// But if you have custom middleware, ensure JWKS is excluded:

// middleware.ts
export const config = {
  matcher: [
    // Don't apply auth middleware to JWKS endpoint
    "/((?!api/auth/jwks).*)",
  ],
};
```

**Note:** Better Auth's JWKS endpoint is public by design (only public keys, safe to expose).

#### Error 4: Invalid Signature (Algorithm Mismatch)

**Full Error:**
```
jwt.exceptions.InvalidSignatureError: Signature verification failed
```

**Cause:** Backend using wrong algorithm to verify JWT.

**Diagnosis:**
```python
# Check what algorithm Better Auth uses
import jwt
import httpx

jwks_url = "https://yourapp.vercel.app/api/auth/jwks"
response = httpx.get(jwks_url)
keys = response.json()["keys"]

print(keys[0]["kty"])  # Should be "OKP" for EdDSA
print(keys[0]["crv"])  # Should be "Ed25519"
```

**Fix:**
```python
# backend/middleware.py

# ✅ CORRECT - Include EdDSA for Better Auth
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["EdDSA", "ES256", "RS256"],  # EdDSA first for Better Auth
)

# ❌ WRONG - Missing EdDSA
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],  # Won't work with Better Auth!
)
```

#### Error 5: Token Missing user_id Claim

**Full Error:**
```
JWT validation error: Token missing user_id claim. Payload keys: dict_keys(['sub', 'iat', 'exp'])
```

**Cause:** Trying to extract wrong claim name.

**Diagnosis:**
```python
# Add logging to see actual JWT payload
def verify_token(token: str) -> Optional[str]:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["EdDSA"])

        # Log payload to see available claims
        print(f"JWT payload keys: {payload.keys()}")
        print(f"JWT payload: {payload}")

        # Check which claim contains user ID
        user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")
        return user_id
```

**Fix:**
```python
# Check your auth provider's claim name:
# - Better Auth: "user_id" or "sub"
# - Auth0: "sub"
# - Clerk: "sub"
# - Custom: depends on your config

# Use fallback pattern
user_id = payload.get("user_id") or payload.get("sub") or payload.get("id")

if not user_id:
    print(f"Available claims: {list(payload.keys())}")
    return None
```

### Testing JWKS Integration

#### Test 1: JWKS Endpoint Accessibility

```bash
# From your local machine (public internet)
curl -v https://yourapp.vercel.app/api/auth/jwks

# Expected response (200 OK):
{
  "keys": [
    {
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "...",
      "use": "sig",
      "kid": "..."
    }
  ]
}

# If 404:
# - Frontend not deployed
# - Route not configured

# If 500:
# - Better Auth initialization error
# - Database connection issue
```

#### Test 2: Backend Can Reach JWKS

```python
# Add to backend startup or health check
import httpx

async def test_jwks_connectivity():
    """Test if backend can reach JWKS endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.BETTER_AUTH_JWKS_URL)

            if response.status_code == 200:
                keys = response.json().get("keys", [])
                print(f"✅ JWKS accessible: {len(keys)} keys found")
                return True
            else:
                print(f"❌ JWKS returned {response.status_code}")
                return False

    except httpx.ConnectError as e:
        print(f"❌ Cannot connect to JWKS: {e}")
        return False
    except Exception as e:
        print(f"❌ JWKS test failed: {e}")
        return False

# Run on startup
@app.on_event("startup")
async def startup_tests():
    await test_jwks_connectivity()
```

#### Test 3: End-to-End JWT Validation

```python
# Test with real JWT from frontend
async def test_jwt_validation():
    """Test JWT validation with real token."""
    # Get a real JWT token from frontend (sign in first)
    test_token = "eyJ..."  # Paste actual token here

    try:
        user_id = verify_token(test_token)
        if user_id:
            print(f"✅ JWT valid, user_id: {user_id}")
        else:
            print(f"❌ JWT validation failed")
    except Exception as e:
        print(f"❌ JWT validation error: {e}")

# Manual testing with curl
# 1. Sign in on frontend, get JWT from browser DevTools
# 2. Copy token
# 3. Test backend endpoint:
curl -H "Authorization: Bearer <token>" https://api.yourapp.com/api/user123/tasks
```

### Production Deployment Checklist

#### Frontend (Vercel/Netlify)

- [ ] Better Auth configured in `lib/auth.ts`
- [ ] Routes mounted at `/api/auth/[...all]/route.ts`
- [ ] `BETTER_AUTH_SECRET` set (32+ chars)
- [ ] `BETTER_AUTH_URL` set to production domain
- [ ] JWKS endpoint returns 200: `curl https://yourapp.vercel.app/api/auth/jwks`
- [ ] Frontend deployed and accessible

#### Backend (Render/Railway/Fly.io)

- [ ] `BETTER_AUTH_JWKS_URL` points to production frontend
- [ ] Backend can reach JWKS endpoint (test with curl from backend server)
- [ ] JWT middleware configured with EdDSA algorithm
- [ ] User ID claim extraction matches auth provider
- [ ] Health check verifies JWKS connectivity
- [ ] Logs show successful JWKS fetches

#### Testing

- [ ] Sign in on frontend generates JWT
- [ ] JWT includes `user_id` or `sub` claim
- [ ] Backend validates JWT successfully
- [ ] Protected endpoints require valid JWT
- [ ] User ID mismatch returns 403
- [ ] Expired tokens return 401

### Network Debugging Tools

#### Check DNS Resolution

```bash
# Verify frontend domain resolves
nslookup yourapp.vercel.app

# Test from backend server
ssh backend-server
curl https://yourapp.vercel.app/api/auth/jwks
```

#### Check Firewall/Network Policies

```bash
# Test if backend can make external HTTPS requests
curl https://httpbin.org/get

# If this fails, backend has network restrictions
# Check cloud provider firewall/security groups
```

#### Check SSL/TLS Issues

```bash
# Test SSL certificate
curl -v https://yourapp.vercel.app/api/auth/jwks

# Look for:
# * SSL connection using TLSv1.3
# * Server certificate verification: OK

# If SSL errors, backend may not trust certificate
# Update CA certificates on backend server
```

#### Monitor JWKS Requests

```typescript
// frontend/app/api/auth/[...all]/route.ts

// Add logging to track JWKS requests
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

const handlers = toNextJsHandler(auth);

export async function GET(req: Request) {
  const url = new URL(req.url);

  if (url.pathname.endsWith('/jwks')) {
    console.log(`JWKS request from: ${req.headers.get('x-forwarded-for') || 'unknown'}`);
  }

  return handlers.GET(req);
}

export const POST = handlers.POST;
```

### JWKS Caching Strategy

**Problem:** Fetching JWKS on every request is slow.

**Solution:** Cache JWKS keys with periodic refresh:

```python
from datetime import datetime, timedelta
from typing import Optional

class JWKSCache:
    """Cache JWKS keys with TTL."""

    def __init__(self, ttl_minutes: int = 60):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.keys: Optional[dict] = None
        self.last_fetch: Optional[datetime] = None

    async def get_keys(self, jwks_url: str) -> dict:
        """Get JWKS keys from cache or fetch if expired."""
        now = datetime.utcnow()

        # Check if cache is valid
        if self.keys and self.last_fetch:
            age = now - self.last_fetch
            if age < self.ttl:
                return self.keys

        # Fetch new keys
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            self.keys = response.json()
            self.last_fetch = now
            return self.keys

# Global cache instance
jwks_cache = JWKSCache(ttl_minutes=60)

# Use in verify_token
async def verify_token(token: str) -> Optional[str]:
    keys = await jwks_cache.get_keys(settings.BETTER_AUTH_JWKS_URL)
    # ... validation logic
```

### Multi-Environment Configuration

```python
# backend/config.py

import os
from typing import Optional

class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Frontend URL (for JWKS)
    @property
    def frontend_url(self) -> str:
        if self.ENVIRONMENT == "production":
            return "https://yourapp.vercel.app"
        elif self.ENVIRONMENT == "staging":
            return "https://staging.yourapp.vercel.app"
        else:
            return "http://localhost:3000"

    # JWKS URL derived from frontend URL
    @property
    def jwks_url(self) -> str:
        # Allow override via env var
        override = os.getenv("BETTER_AUTH_JWKS_URL")
        if override:
            return override

        # Otherwise construct from frontend URL
        return f"{self.frontend_url}/api/auth/jwks"

settings = Settings()

# Usage
jwks_client = PyJWKClient(settings.jwks_url)
```

### Monitoring and Alerts

#### Log JWKS Fetch Failures

```python
import logging

logger = logging.getLogger(__name__)

def verify_token(token: str) -> Optional[str]:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # ... validation
    except Exception as e:
        # Log with context for debugging
        logger.error(
            "JWKS fetch failed",
            extra={
                "jwks_url": settings.BETTER_AUTH_JWKS_URL,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
        return None
```

#### Set Up Alerts

```python
# Example: Send alert if JWKS fails repeatedly

from collections import defaultdict
from datetime import datetime, timedelta

jwks_failures = defaultdict(list)

def check_jwks_health(jwks_url: str):
    """Alert if JWKS failures exceed threshold."""
    now = datetime.utcnow()
    recent = now - timedelta(minutes=5)

    # Clean old failures
    jwks_failures[jwks_url] = [
        t for t in jwks_failures[jwks_url] if t > recent
    ]

    # Alert if > 10 failures in 5 minutes
    if len(jwks_failures[jwks_url]) > 10:
        send_alert(f"JWKS endpoint {jwks_url} failing repeatedly")
```

### Common Gotchas

#### Gotcha 1: Preview Deployments

**Problem:** Vercel preview deployments have different URLs.

**Solution:** Update JWKS URL for each environment:
```bash
# Vercel production
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks

# Vercel preview (update per deployment)
BETTER_AUTH_JWKS_URL=https://yourapp-git-branch-xyz.vercel.app/api/auth/jwks
```

#### Gotcha 2: HTTPS in Production Only

**Problem:** Development uses HTTP, production uses HTTPS.

**Solution:** Don't hardcode protocol:
```python
# ✅ CORRECT - protocol depends on environment
JWKS_URL = f"{settings.BETTER_AUTH_URL}/api/auth/jwks"

# settings.BETTER_AUTH_URL should be:
# - Development: http://localhost:3000
# - Production: https://yourapp.vercel.app
```

#### Gotcha 3: Clock Skew

**Problem:** JWT expiration fails due to time difference between servers.

**Solution:** Allow clock skew in validation:
```python
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["EdDSA"],
    options={
        "verify_exp": True,
        "leeway": 60,  # Allow 60 seconds clock skew
    }
)
```

#### Gotcha 4: Private Networks

**Problem:** Backend in private network can't reach public JWKS.

**Solution:** Add JWKS URL to firewall whitelist or use internal JWKS endpoint.

## Integration Patterns

### Pattern 1: Async JWKS Fetching

```python
# For FastAPI with async routes
import asyncio
from jwt import PyJWKClient

# Async JWKS client (not supported by PyJWT yet)
# Use httpx directly:

async def get_signing_key(token: str, jwks_url: str):
    """Fetch JWKS keys asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        jwks = response.json()

        # Extract key ID from token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Find matching key
        for key in jwks["keys"]:
            if key["kid"] == kid:
                return key

    raise ValueError("No matching key found")
```

### Pattern 2: Health Check Integration

```python
@app.get("/health")
async def health_check():
    """Health check with JWKS validation."""
    health = {
        "status": "healthy",
        "jwks": "unknown"
    }

    try:
        # Test JWKS connectivity
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.BETTER_AUTH_JWKS_URL)

            if response.status_code == 200:
                health["jwks"] = "connected"
            else:
                health["jwks"] = f"status_{response.status_code}"
                health["status"] = "degraded"

    except Exception as e:
        health["jwks"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    return health
```

### Pattern 3: Graceful Degradation

```python
# Allow requests to proceed if JWKS temporarily unavailable
# (use with caution, only for non-critical endpoints)

def verify_token_with_fallback(token: str) -> Optional[str]:
    """Verify token with graceful degradation."""
    try:
        return verify_token(token)
    except httpx.ConnectError:
        # JWKS endpoint unreachable
        # Option 1: Fail closed (recommended)
        logger.error("JWKS unreachable, rejecting request")
        return None

        # Option 2: Fail open (dangerous, use only for non-critical endpoints)
        # logger.warning("JWKS unreachable, allowing request")
        # return extract_user_id_without_verification(token)
```

## Summary

Production JWKS integration requires:
- ✅ Correct environment variables (production URLs, not localhost)
- ✅ Network accessibility (backend can reach frontend JWKS endpoint)
- ✅ Proper algorithm support (EdDSA for Better Auth)
- ✅ Correct claim extraction (user_id vs sub)
- ✅ JWKS caching for performance
- ✅ Comprehensive error handling and logging
- ✅ Health checks and monitoring
