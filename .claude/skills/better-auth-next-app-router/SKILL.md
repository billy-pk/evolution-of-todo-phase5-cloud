---
name: better-auth-next-app-router
description: Set up Better Auth in Next.js 15+ App Router with EdDSA JWT signing, JWKS endpoint, PostgreSQL storage, and client-side session management. Works with FastAPI JWT validation.
---

# Better Auth Setup in Next.js 15 App Router

## Overview

This skill documents setting up Better Auth in Next.js 15+ applications using the App Router. Better Auth provides production-ready authentication with JWT tokens, session management, and seamless integration with backend APIs.

### What is Better Auth?

Better Auth is a modern authentication framework for TypeScript/JavaScript applications with:
- Built-in JWT token generation with EdDSA (Ed25519) signing
- JWKS endpoint for backend JWT validation
- PostgreSQL/MySQL database storage
- Email/password, OAuth, and magic link support
- Server and client components support
- TypeScript-first API

### When to Use This Skill

Use this skill when you need to:
- Add authentication to Next.js 15+ App Router applications
- Generate JWTs for backend API authentication
- Implement sign up/sign in/sign out flows
- Protect routes with session-based access control
- Integrate Next.js frontend with FastAPI/Express backends

## Prerequisites

**Dependencies:**
```bash
npm install better-auth
npm install @better-auth/react  # For client hooks
```

**Database:**
- PostgreSQL (recommended) or MySQL
- Connection string in environment variables

**Environment Variables:**
```env
# Frontend (.env.local)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
BETTER_AUTH_SECRET=<32+ character random string>
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000  # Your backend API
```

## Implementation Steps

### Step 1: Create Auth Configuration (Server)

**File**: `lib/auth.ts`

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export const auth = betterAuth({
  // Database configuration
  database: {
    provider: "postgres",
    pool,  // Pass pool for connection reuse
  },

  // Email/password authentication
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,  // Set true for production
  },

  // JWT configuration with EdDSA (Ed25519)
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,  // 5 minutes
    },
  },

  // Advanced configuration
  advanced: {
    generateId: () => crypto.randomUUID(),  // Custom ID generation
  },

  // Secret for JWT signing (32+ characters)
  secret: process.env.BETTER_AUTH_SECRET!,

  // Base URL for redirects and JWKS endpoint
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
});

// Export types for TypeScript
export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.User;
```

**Key Points:**
- Uses EdDSA (Ed25519) algorithm for JWT signing (faster than RS256)
- JWKS endpoint automatically created at `/api/auth/jwks`
- Connection pooling for better performance
- TypeScript types inferred from config

### Step 2: Create Auth API Routes

**File**: `app/api/auth/[...all]/route.ts`

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

// Export HTTP method handlers
export const { GET, POST } = toNextJsHandler(auth);

// IMPORTANT: Better Auth automatically creates these endpoints:
// POST /api/auth/sign-up/email
// POST /api/auth/sign-in/email
// POST /api/auth/sign-out
// GET  /api/auth/session
// GET  /api/auth/jwks  (for backend JWT validation)
```

**What This Does:**
- Mounts Better Auth at `/api/auth/*`
- Handles all auth operations automatically
- Creates JWKS endpoint for backend validation

### Step 3: Create Auth Client (Client-Side)

**File**: `lib/auth-client.ts`

```typescript
"use client";

import { createAuthClient } from "better-auth/react";
import type { Session, User } from "./auth";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000",
});

// Export hooks
export const {
  useSession,      // Get current session
  signIn,          // Sign in function
  signUp,          // Sign up function
  signOut,         // Sign out function
} = authClient;

// Export types
export type { Session, User };
```

**Usage in Components:**
```tsx
"use client";

import { useSession } from "@/lib/auth-client";

export default function ProfilePage() {
  const { data: session, isPending } = useSession();

  if (isPending) return <div>Loading...</div>;
  if (!session?.user) return <div>Not authenticated</div>;

  return <div>Welcome, {session.user.email}!</div>;
}
```

### Step 4: Create Sign Up Page

**File**: `app/(auth)/signup/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      await authClient.signUp.email({
        email,
        password,
        name,
      });

      // Redirect to dashboard on success
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Sign up failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 rounded-lg border p-8">
        <h2 className="text-2xl font-bold text-center">Create Account</h2>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            Sign Up
          </button>
        </form>

        <p className="text-center text-sm">
          Already have an account?{" "}
          <a href="/signin" className="text-blue-600 hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
```

### Step 5: Create Sign In Page

**File**: `app/(auth)/signin/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      await authClient.signIn.email({
        email,
        password,
      });

      // Redirect to dashboard on success
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Sign in failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md space-y-8 rounded-lg border p-8">
        <h2 className="text-2xl font-bold text-center">Sign In</h2>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            Sign In
          </button>
        </form>

        <p className="text-center text-sm">
          Don't have an account?{" "}
          <a href="/signup" className="text-blue-600 hover:underline">
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}
```

### Step 6: Protect Routes with Middleware

**File**: `middleware.ts`

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { auth } from "./lib/auth";

export async function middleware(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: request.headers,
  });

  const isAuthPage = request.nextUrl.pathname.startsWith("/signin") ||
                     request.nextUrl.pathname.startsWith("/signup");

  // Redirect authenticated users away from auth pages
  if (session && isAuthPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Redirect unauthenticated users to signin
  if (!session && !isAuthPage) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }

  return NextResponse.next();
}

// Protect these routes
export const config = {
  matcher: [
    "/dashboard/:path*",
    "/tasks/:path*",
    "/chat/:path*",
    "/signin",
    "/signup",
  ],
};
```

### Step 7: Get JWT Token for Backend API Calls

**File**: `lib/api.ts`

```typescript
import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  // Get JWT token from Better Auth
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new Error("Not authenticated");
  }

  // Make request with JWT in Authorization header
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${data.token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

// Usage example:
// const tasks = await apiRequest("/api/user123/tasks");
```

## Database Setup

Better Auth automatically creates these tables:

```sql
-- users table
CREATE TABLE "user" (
  "id" TEXT PRIMARY KEY,
  "email" TEXT UNIQUE NOT NULL,
  "emailVerified" BOOLEAN DEFAULT FALSE,
  "name" TEXT,
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sessions table
CREATE TABLE "session" (
  "id" TEXT PRIMARY KEY,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "expiresAt" TIMESTAMP NOT NULL,
  "token" TEXT UNIQUE NOT NULL,
  "ipAddress" TEXT,
  "userAgent" TEXT,
  FOREIGN KEY ("userId") REFERENCES "user"("id")
);

-- accounts table (for password storage)
CREATE TABLE "account" (
  "id" TEXT PRIMARY KEY,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "accountId" TEXT NOT NULL,
  "providerId" TEXT NOT NULL,
  "accessToken" TEXT,
  "refreshToken" TEXT,
  "expiresAt" TIMESTAMP,
  "password" TEXT,  -- Hashed password
  FOREIGN KEY ("userId") REFERENCES "user"("id")
);
```

**Run migrations:**
```bash
# Better Auth CLI will create tables automatically on first run
# Or use your own migration tool (Prisma, Drizzle, etc.)
```

## Common Patterns

### Pattern 1: Protected Page Component

```tsx
"use client";

import { useSession } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/signin");
    }
  }, [session, isPending, router]);

  if (isPending) return <div>Loading...</div>;
  if (!session) return null;

  return <div>Protected content for {session.user.email}</div>;
}
```

### Pattern 2: Sign Out Button

```tsx
"use client";

import { authClient } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

export function SignOutButton() {
  const router = useRouter();

  const handleSignOut = async () => {
    await authClient.signOut();
    router.push("/signin");
  };

  return (
    <button
      onClick={handleSignOut}
      className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
    >
      Sign Out
    </button>
  );
}
```

### Pattern 3: Get User Info

```tsx
"use client";

import { useSession } from "@/lib/auth-client";

export function UserProfile() {
  const { data: session } = useSession();

  if (!session) return null;

  return (
    <div>
      <p>Email: {session.user.email}</p>
      <p>Name: {session.user.name}</p>
      <p>ID: {session.user.id}</p>
    </div>
  );
}
```

## Backend Integration (FastAPI)

Better Auth JWT tokens work seamlessly with FastAPI JWT validation.

**Backend setup** (uses `fastapi-jwt-auth-setup` skill):

```python
# backend/middleware.py
from fastapi import Request, HTTPException
from jose import jwt, JWTError
import httpx

# JWKS endpoint from Better Auth
JWKS_URL = "http://localhost:3000/api/auth/jwks"

async def verify_token(token: str) -> str:
    """Validate JWT from Better Auth using JWKS."""
    # Fetch JWKS keys
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        jwks = response.json()

    # Verify JWT signature
    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["EdDSA"],  # Better Auth uses EdDSA
        )
        return payload.get("sub")  # user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Production Deployment Issues (Critical)

### Issue: Backend Can't Access JWKS Endpoint

**Symptom:** Backend returns 401 for all requests, logs show:
```
httpx.ConnectError: Cannot connect to host localhost:3000
```

**Cause:** Backend configured with localhost URL in production.

**Solution:** Use production frontend URL:

```bash
# Backend environment (Render/Railway)
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks
```

**Test JWKS accessibility:**
```bash
# Must return public keys
curl https://yourapp.vercel.app/api/auth/jwks
```

### Issue: JWKS Endpoint Returns 404

**Cause:** Better Auth not properly initialized.

**Checklist:**
- [ ] `lib/auth.ts` exports auth instance
- [ ] `app/api/auth/[...all]/route.ts` exists
- [ ] Both GET and POST exported: `export const { GET, POST } = toNextJsHandler(auth);`
- [ ] Frontend deployed to Vercel

### Issue: Frontend/Backend URL Mismatch

**Common mistake:**
```bash
# ❌ WRONG - Using localhost in production
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000

# ✅ CORRECT - Production URLs
BETTER_AUTH_URL=https://yourapp.vercel.app
NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

**See examples.md for complete production deployment guide.**

## Common Pitfalls and Solutions

### 1. "Secret must be at least 32 characters"

**Problem**: `BETTER_AUTH_SECRET` too short.

**Solution**: Generate a secure secret:
```bash
openssl rand -base64 32
```

### 2. Database Connection Errors

**Problem**: Better Auth can't connect to database.

**Solution**: Verify `DATABASE_URL` format:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 3. JWKS Endpoint 404

**Problem**: Backend can't fetch JWKS from `/api/auth/jwks`.

**Solution**: Ensure:
- Better Auth routes are mounted at `/api/auth/[...all]/route.ts`
- `BETTER_AUTH_URL` is set correctly
- Frontend is running when backend tries to fetch JWKS

### 4. Session Not Persisting

**Problem**: User gets logged out on page refresh.

**Solution**: Check:
- Cookies are enabled in browser
- `cookieCache` is enabled in auth config
- No CORS issues blocking cookies

### 5. EdDSA vs RS256

**Why EdDSA?**
- Faster than RS256 (better performance)
- Smaller signatures
- Same security level
- Better Auth default

Backend must use `algorithms=["EdDSA"]` when validating JWTs.

## Production Checklist

### Security
- [ ] Use strong `BETTER_AUTH_SECRET` (32+ characters)
- [ ] Enable `requireEmailVerification` for production
- [ ] Use HTTPS for `BETTER_AUTH_URL`
- [ ] Set secure cookie flags in production
- [ ] Add rate limiting to auth endpoints

### Database
- [ ] Run database migrations
- [ ] Set up connection pooling
- [ ] Add indexes on frequently queried fields
- [ ] Configure database backups

### Frontend
- [ ] Set correct `BETTER_AUTH_URL` (production domain)
- [ ] Configure CORS properly
- [ ] Add loading states for auth operations
- [ ] Handle auth errors gracefully

### Backend
- [ ] Update `BETTER_AUTH_JWKS_URL` to production URL
- [ ] Cache JWKS keys (refresh every 1 hour)
- [ ] Add JWT validation to all protected endpoints
- [ ] Set proper CORS origins

## Next Steps

1. See `examples.md` for complete working implementations
2. Check `templates.md` for copy-paste ready code
3. Read official docs: https://www.better-auth.com/docs

## Related Skills

- **fastapi-jwt-auth-setup** - Backend JWT validation for FastAPI
- **OpenAI ChatKit Integration** - Uses Better Auth for chat authentication
- **Multi-Tenant Architecture** - User isolation patterns

## Resources

### Official Documentation
- [Better Auth Documentation](https://www.better-auth.com/docs)
- [Better Auth GitHub](https://github.com/better-auth/better-auth)
- [Next.js App Router](https://nextjs.org/docs/app)

### Community
- [Better Auth Discord](https://discord.gg/better-auth)
- [GitHub Issues](https://github.com/better-auth/better-auth/issues)
