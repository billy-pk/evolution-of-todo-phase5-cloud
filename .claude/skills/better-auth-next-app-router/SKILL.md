---
name: better-auth-next-app-router
description: Set up Better Auth in Next.js 15+ App Router with EdDSA JWT signing, JWKS endpoint, PostgreSQL storage, and client-side session management. Works with FastAPI JWT validation. Includes Kubernetes deployment patterns with fixes for Node.js Happy Eyeballs ETIMEDOUT issues, JWKS cleanup after secret changes, and Next.js standalone build configuration for containerized environments.
---

# Better Auth Setup in Next.js App Router

## Overview

Better Auth provides production-ready authentication for Next.js with:
- EdDSA (Ed25519) JWT signing
- JWKS endpoint for backend validation (`/api/auth/jwks`)
- PostgreSQL database storage
- Email/password, OAuth support
- TypeScript-first API

## Quick Start

### 1. Install Dependencies

```bash
npm install better-auth @better-auth/react pg
```

### 2. Environment Variables

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
BETTER_AUTH_SECRET=<32+ character random string>
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Create Auth Configuration

**File**: `lib/auth.ts`

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";
import dns from "dns";
import net from "net";

// CRITICAL: Fix for Kubernetes/container environments
net.setDefaultAutoSelectFamily(false);
dns.setDefaultResultOrder("ipv4first");

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export const auth = betterAuth({
  database: { provider: "postgres", pool },
  emailAndPassword: { enabled: true },
  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
});

export type Session = typeof auth.$Infer.Session;
```

### 4. Create API Route

**File**: `app/api/auth/[...all]/route.ts`

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

### 5. Create Auth Client

**File**: `lib/auth-client.ts`

```typescript
"use client";

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000",
});

export const { useSession, signIn, signUp, signOut } = authClient;
```

### 6. Get JWT for API Calls

```typescript
const { data } = await authClient.token();
fetch(API_URL, {
  headers: { Authorization: `Bearer ${data.token}` }
});
```

**For complete implementation steps, see [reference.md](reference.md).**

---

## Kubernetes Deployment

For deploying to Kubernetes (Minikube, EKS, GKE, AKS), see **[kubernetes.md](kubernetes.md)**.

### Quick Fix: ETIMEDOUT in Kubernetes

If Next.js can't connect to database in containers:

```typescript
// Add to lib/auth.ts BEFORE creating Pool
import dns from "dns";
import net from "net";

net.setDefaultAutoSelectFamily(false);
dns.setDefaultResultOrder("ipv4first");
```

### Quick Fix: Sign-in Redirect Loop After Secret Change

```bash
psql $DATABASE_URL -c "DELETE FROM jwks;"
kubectl rollout restart deployment frontend
```

### Kubernetes Secrets

```bash
# Create matching secrets for frontend and backend
SECRET=$(openssl rand -base64 32)
kubectl create secret generic auth-secret --from-literal=better-auth-secret="$SECRET"

# Verify secrets match
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
```

### Next.js Standalone Build

**next.config.ts:**
```typescript
const nextConfig = {
  output: "standalone",
  serverExternalPackages: ["ws", "pg"],
};
```

**Dockerfile** - Copy external packages:
```dockerfile
COPY --from=builder /app/node_modules/ws ./node_modules/ws
COPY --from=builder /app/node_modules/pg ./node_modules/pg
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| ETIMEDOUT in K8s | Node.js Happy Eyeballs | Add `net.setDefaultAutoSelectFamily(false)` |
| "Failed to decrypt private key" | Secret changed | Delete from jwks table, restart |
| JWKS 404 | Routes not mounted | Check `app/api/auth/[...all]/route.ts` |
| Session not persisting | Cookies blocked | Check CORS, cookie settings |
| "Secret must be 32+ chars" | Short secret | `openssl rand -base64 32` |

---

## File Structure

```
lib/
  auth.ts           # Server auth config (with Happy Eyeballs fix)
  auth-client.ts    # Client hooks and functions
  api.ts            # API client with JWT
app/
  api/auth/[...all]/route.ts  # Auth API routes
  (auth)/signin/page.tsx      # Sign in page
  (auth)/signup/page.tsx      # Sign up page
middleware.ts       # Route protection
```

---

## Backend Integration (FastAPI)

```python
from jose import jwt
import httpx

JWKS_URL = "http://frontend:3000/api/auth/jwks"  # K8s service URL

async def verify_token(token: str) -> str:
    async with httpx.AsyncClient() as client:
        jwks = (await client.get(JWKS_URL)).json()

    payload = jwt.decode(token, jwks, algorithms=["EdDSA"])
    return payload.get("sub")  # user_id
```

---

## Production Checklist

- [ ] Strong `BETTER_AUTH_SECRET` (32+ chars): `openssl rand -base64 32`
- [ ] HTTPS URLs in production
- [ ] Matching secrets across frontend/backend
- [ ] JWKS endpoint accessible from backend
- [ ] Rate limiting on auth endpoints
- [ ] Database connection pooling

---

## Reference Files

| File | Content |
|------|---------|
| [reference.md](reference.md) | Complete implementation steps, database schema, patterns |
| [kubernetes.md](kubernetes.md) | K8s deployment, Happy Eyeballs fix, Helm charts, Dockerfile |
| [examples.md](examples.md) | Working code examples |
| [templates.md](templates.md) | Copy-paste ready templates |

---

## Resources

- [Better Auth Docs](https://www.better-auth.com/docs)
- [Better Auth GitHub](https://github.com/better-auth/better-auth)
- [Next.js App Router](https://nextjs.org/docs/app)

## Related Skills

- **fastapi-jwt-auth-setup** - Backend JWT validation
- **nextjs-fastapi-mcp-architecture** - Full-stack architecture
