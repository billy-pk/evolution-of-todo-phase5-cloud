# Better Auth Reference Guide

Detailed implementation guide for Better Auth in Next.js App Router.

## Table of Contents

1. [Step-by-Step Implementation](#step-by-step-implementation)
2. [Database Setup](#database-setup)
3. [Common Patterns](#common-patterns)
4. [Backend Integration](#backend-integration)
5. [Production Issues](#production-issues)
6. [Troubleshooting](#troubleshooting)

---

## Step-by-Step Implementation

### Step 1: Create Auth Configuration (Server)

**File**: `lib/auth.ts`

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";
import dns from "dns";
import net from "net";

// CRITICAL: Fix for Node.js Happy Eyeballs in Kubernetes/containers
// Add these lines BEFORE creating the pool
net.setDefaultAutoSelectFamily(false);
dns.setDefaultResultOrder("ipv4first");

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export const auth = betterAuth({
  database: {
    provider: "postgres",
    pool,
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,  // Set true for production
  },
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,  // 5 minutes
    },
  },
  advanced: {
    generateId: () => crypto.randomUUID(),
  },
  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
});

export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.User;
```

### Step 2: Create Auth API Routes

**File**: `app/api/auth/[...all]/route.ts`

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);

// Automatically creates:
// POST /api/auth/sign-up/email
// POST /api/auth/sign-in/email
// POST /api/auth/sign-out
// GET  /api/auth/session
// GET  /api/auth/jwks
```

### Step 3: Create Auth Client (Client-Side)

**File**: `lib/auth-client.ts`

```typescript
"use client";

import { createAuthClient } from "better-auth/react";
import type { Session, User } from "./auth";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000",
});

export const { useSession, signIn, signUp, signOut } = authClient;
export type { Session, User };
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
      await authClient.signUp.email({ email, password, name });
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
            <label htmlFor="name" className="block text-sm font-medium">Name</label>
            <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)}
              required className="mt-1 block w-full rounded border px-3 py-2" />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium">Email</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              required className="mt-1 block w-full rounded border px-3 py-2" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required minLength={8} className="mt-1 block w-full rounded border px-3 py-2" />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
            Sign Up
          </button>
        </form>
        <p className="text-center text-sm">
          Already have an account? <a href="/signin" className="text-blue-600 hover:underline">Sign in</a>
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
      await authClient.signIn.email({ email, password });
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
            <label htmlFor="email" className="block text-sm font-medium">Email</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              required className="mt-1 block w-full rounded border px-3 py-2" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required className="mt-1 block w-full rounded border px-3 py-2" />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
            Sign In
          </button>
        </form>
        <p className="text-center text-sm">
          Don't have an account? <a href="/signup" className="text-blue-600 hover:underline">Sign up</a>
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
  const session = await auth.api.getSession({ headers: request.headers });
  const isAuthPage = request.nextUrl.pathname.startsWith("/signin") ||
                     request.nextUrl.pathname.startsWith("/signup");

  if (session && isAuthPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (!session && !isAuthPage) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/tasks/:path*", "/chat/:path*", "/signin", "/signup"],
};
```

### Step 7: Get JWT Token for Backend API Calls

**File**: `lib/api.ts`

```typescript
import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new Error("Not authenticated");
  }

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
```

---

## Database Setup

Better Auth automatically creates these tables:

```sql
CREATE TABLE "user" (
  "id" TEXT PRIMARY KEY,
  "email" TEXT UNIQUE NOT NULL,
  "emailVerified" BOOLEAN DEFAULT FALSE,
  "name" TEXT,
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "session" (
  "id" TEXT PRIMARY KEY,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "expiresAt" TIMESTAMP NOT NULL,
  "token" TEXT UNIQUE NOT NULL,
  "ipAddress" TEXT,
  "userAgent" TEXT
);

CREATE TABLE "account" (
  "id" TEXT PRIMARY KEY,
  "userId" TEXT NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
  "accountId" TEXT NOT NULL,
  "providerId" TEXT NOT NULL,
  "accessToken" TEXT,
  "refreshToken" TEXT,
  "expiresAt" TIMESTAMP,
  "password" TEXT
);

CREATE TABLE "jwks" (
  "id" TEXT PRIMARY KEY,
  "publicKey" TEXT NOT NULL,
  "privateKey" TEXT NOT NULL,  -- Encrypted with BETTER_AUTH_SECRET
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Common Patterns

### Protected Page Component

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

### Sign Out Button

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
    <button onClick={handleSignOut} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">
      Sign Out
    </button>
  );
}
```

### User Profile Display

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

---

## Backend Integration

Better Auth JWT tokens work with FastAPI JWT validation:

```python
# backend/middleware.py
from fastapi import Request, HTTPException
from jose import jwt, JWTError
import httpx

JWKS_URL = "http://localhost:3000/api/auth/jwks"  # Update for production

async def verify_token(token: str) -> str:
    """Validate JWT from Better Auth using JWKS."""
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        jwks = response.json()

    try:
        payload = jwt.decode(token, jwks, algorithms=["EdDSA"])
        return payload.get("sub")  # user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Production Issues

### Backend Can't Access JWKS Endpoint

**Symptom:** `httpx.ConnectError: Cannot connect to host localhost:3000`

**Fix:** Use production URL:
```bash
BETTER_AUTH_JWKS_URL=https://yourapp.com/api/auth/jwks
```

### JWKS Endpoint Returns 404

**Checklist:**
- `lib/auth.ts` exports auth instance
- `app/api/auth/[...all]/route.ts` exists
- Both GET and POST exported

### Frontend/Backend URL Mismatch

```bash
# ❌ WRONG
BETTER_AUTH_URL=http://localhost:3000

# ✅ CORRECT
BETTER_AUTH_URL=https://yourapp.com
```

---

## Troubleshooting

### "Secret must be at least 32 characters"

Generate secure secret:
```bash
openssl rand -base64 32
```

### Database Connection Errors

Verify `DATABASE_URL` format:
```
postgresql://user:password@host:5432/dbname?sslmode=require
```

### Session Not Persisting

Check:
- Cookies enabled in browser
- `cookieCache` enabled in auth config
- No CORS issues blocking cookies

### EdDSA vs RS256

Better Auth uses EdDSA (Ed25519) by default:
- Faster than RS256
- Smaller signatures
- Backend must use `algorithms=["EdDSA"]`

---

## Production Checklist

### Security
- [ ] Strong `BETTER_AUTH_SECRET` (32+ characters)
- [ ] `requireEmailVerification: true`
- [ ] HTTPS for `BETTER_AUTH_URL`
- [ ] Rate limiting on auth endpoints

### Database
- [ ] Migrations run
- [ ] Connection pooling configured
- [ ] Backups configured

### Frontend
- [ ] Correct `BETTER_AUTH_URL`
- [ ] CORS configured
- [ ] Error handling for auth failures

### Backend
- [ ] Production `BETTER_AUTH_JWKS_URL`
- [ ] JWKS caching (refresh hourly)
- [ ] JWT validation on protected endpoints
