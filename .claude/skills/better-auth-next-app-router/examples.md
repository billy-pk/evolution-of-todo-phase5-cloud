---
name: better-auth-next-app-router-examples
description: Complete working examples for Better Auth in Next.js 15 App Router, including auth setup, protected pages, API integration, and testing patterns.
---

# Better Auth in Next.js 15 - Complete Examples

## Example 1: Complete Auth Setup

### Project Structure

```
app/
├── (auth)/
│   ├── signin/
│   │   └── page.tsx
│   └── signup/
│       └── page.tsx
├── (dashboard)/
│   ├── layout.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   └── tasks/
│       └── page.tsx
├── api/
│   └── auth/
│       └── [...all]/
│           └── route.ts
lib/
├── auth.ts              # Server config
├── auth-client.ts       # Client config
└── api.ts               # API client with JWT
middleware.ts            # Route protection
```

### lib/auth.ts (Complete Server Configuration)

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";

// PostgreSQL connection pool for better performance
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,  // Maximum connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

export const auth = betterAuth({
  // Database configuration
  database: {
    provider: "postgres",
    pool,
  },

  // Email and password authentication
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,  // Set true for production
    minPasswordLength: 8,
    maxPasswordLength: 128,
  },

  // Session configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7,  // 7 days
    updateAge: 60 * 60 * 24,      // Update session every 24 hours
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,  // Cache for 5 minutes
    },
  },

  // User configuration
  user: {
    additionalFields: {
      // Add custom fields if needed
      // role: {
      //   type: "string",
      //   defaultValue: "user",
      // },
    },
  },

  // Advanced configuration
  advanced: {
    generateId: () => crypto.randomUUID(),
    cookieName: "better-auth.session_token",
    useSecureCookies: process.env.NODE_ENV === "production",
    crossSubDomainCookies: {
      enabled: false,
    },
  },

  // Security configuration
  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
  trustedOrigins: [
    process.env.BETTER_AUTH_URL || "http://localhost:3000",
  ],
});

// Export types
export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.User;

// Helper function to get session (server-side)
export async function getSession(headers: Headers) {
  return await auth.api.getSession({ headers });
}

// Helper to check if user is authenticated (server-side)
export async function requireAuth(headers: Headers) {
  const session = await getSession(headers);
  if (!session) {
    throw new Error("Unauthorized");
  }
  return session;
}
```

### lib/auth-client.ts (Complete Client Configuration)

```typescript
"use client";

import { createAuthClient } from "better-auth/react";
import type { Session, User } from "./auth";

// Create auth client
export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000",
});

// Re-export hooks and functions
export const {
  useSession,
  signIn,
  signUp,
  signOut,
  updateUser,
  changePassword,
} = authClient;

// Export types
export type { Session, User };

// Helper to check if user is authenticated
export function useAuth() {
  const { data: session, isPending, error } = useSession();

  return {
    user: session?.user ?? null,
    session: session ?? null,
    isAuthenticated: !!session?.user,
    isLoading: isPending,
    error,
  };
}

// Helper to get JWT token
export async function getAuthToken() {
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new Error("Not authenticated");
  }

  return data.token;
}
```

### lib/api.ts (Complete API Client)

```typescript
import { getAuthToken } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = "APIError";
  }
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    // Get JWT token
    const token = await getAuthToken();

    // Make request
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    // Parse response
    const data = await response.json();

    // Handle errors
    if (!response.ok) {
      throw new APIError(
        data.detail || data.message || "API request failed",
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error instanceof Error ? error.message : "Unknown error",
      500
    );
  }
}

// Convenience methods
export const api = {
  get: <T = any>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: "GET" }),

  post: <T = any>(endpoint: string, body: any) =>
    apiRequest<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  put: <T = any>(endpoint: string, body: any) =>
    apiRequest<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: <T = any>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: "DELETE" }),
};

// Usage examples:
// const tasks = await api.get("/api/user123/tasks");
// const newTask = await api.post("/api/user123/tasks", { title: "New task" });
```

## Example 2: Complete Protected Dashboard Layout

```tsx
/**
 * app/(dashboard)/layout.tsx
 *
 * Protected layout for dashboard pages.
 * Automatically redirects unauthenticated users.
 */

"use client";

import { useAuth } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { authClient } from "@/lib/auth-client";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/signin");
    }
  }, [isAuthenticated, isLoading, router]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  // Render dashboard layout
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <nav className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex">
              <div className="flex flex-shrink-0 items-center">
                <h1 className="text-xl font-bold">My App</h1>
              </div>
              <div className="ml-6 flex space-x-8">
                <a
                  href="/dashboard"
                  className="inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-900 hover:border-gray-300"
                >
                  Dashboard
                </a>
                <a
                  href="/tasks"
                  className="inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
                >
                  Tasks
                </a>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">{user?.email}</span>
              <button
                onClick={async () => {
                  await authClient.signOut();
                  router.push("/signin");
                }}
                className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
```

## Example 3: Dashboard Page with API Integration

```tsx
/**
 * app/(dashboard)/dashboard/page.tsx
 *
 * Main dashboard page showing user tasks.
 */

"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-client";
import { api, APIError } from "@/lib/api";

interface Task {
  id: string;
  title: string;
  completed: boolean;
  created_at: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch tasks on mount
  useEffect(() => {
    if (user) {
      fetchTasks();
    }
  }, [user]);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.get<Task[]>(`/api/${user?.id}/tasks`);
      setTasks(data);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError("Failed to load tasks");
      }
    } finally {
      setLoading(false);
    }
  };

  const addTask = async (title: string) => {
    try {
      const newTask = await api.post<Task>(`/api/${user?.id}/tasks`, {
        title,
      });
      setTasks([...tasks, newTask]);
    } catch (err) {
      if (err instanceof APIError) {
        alert(err.message);
      }
    }
  };

  const toggleTask = async (taskId: string) => {
    try {
      const task = tasks.find((t) => t.id === taskId);
      if (!task) return;

      const updated = await api.put<Task>(
        `/api/${user?.id}/tasks/${taskId}`,
        { completed: !task.completed }
      );

      setTasks(tasks.map((t) => (t.id === taskId ? updated : t)));
    } catch (err) {
      if (err instanceof APIError) {
        alert(err.message);
      }
    }
  };

  if (loading) {
    return <div>Loading tasks...</div>;
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-800">
        <p className="font-semibold">Error loading tasks</p>
        <p className="text-sm">{error}</p>
        <button
          onClick={fetchTasks}
          className="mt-2 text-sm underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Tasks</h1>

      {/* Add Task Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const formData = new FormData(e.currentTarget);
          const title = formData.get("title") as string;
          if (title.trim()) {
            addTask(title);
            e.currentTarget.reset();
          }
        }}
        className="mb-6 flex gap-2"
      >
        <input
          name="title"
          type="text"
          placeholder="Add a new task..."
          required
          className="flex-1 rounded-md border px-3 py-2"
        />
        <button
          type="submit"
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Add Task
        </button>
      </form>

      {/* Task List */}
      {tasks.length === 0 ? (
        <p className="text-gray-500">No tasks yet. Add one above!</p>
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => (
            <li
              key={task.id}
              className="flex items-center gap-3 rounded-lg border bg-white p-4"
            >
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
                className="h-5 w-5"
              />
              <span
                className={`flex-1 ${
                  task.completed ? "line-through text-gray-500" : ""
                }`}
              >
                {task.title}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Example 4: Middleware with Custom Logic

```typescript
/**
 * middleware.ts
 *
 * Route protection with custom logic.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { auth } from "./lib/auth";

// Public routes that don't require authentication
const PUBLIC_ROUTES = ["/", "/signin", "/signup", "/about", "/contact"];

// API routes that don't require authentication
const PUBLIC_API_ROUTES = ["/api/auth"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (PUBLIC_ROUTES.includes(pathname)) {
    return NextResponse.next();
  }

  // Allow public API routes
  if (PUBLIC_API_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check authentication for protected routes
  const session = await auth.api.getSession({
    headers: request.headers,
  });

  const isAuthPage = pathname.startsWith("/signin") || pathname.startsWith("/signup");

  // Redirect authenticated users away from auth pages
  if (session && isAuthPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Redirect unauthenticated users to signin
  if (!session && !isAuthPage) {
    const signInUrl = new URL("/signin", request.url);
    // Add return URL for redirect after login
    signInUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Add user ID to request headers (for easy access in API routes)
  if (session) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-user-id", session.user.id);

    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  return NextResponse.next();
}

// Configure which routes to run middleware on
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public folder)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

## Example 5: Testing Setup

### Jest Configuration

```javascript
// jest.config.js
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
}

module.exports = createJestConfig(customJestConfig)
```

### Test Examples

```typescript
// __tests__/auth.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SignInPage from '@/app/(auth)/signin/page';

// Mock auth client
jest.mock('@/lib/auth-client', () => ({
  authClient: {
    signIn: {
      email: jest.fn(),
    },
  },
  useSession: () => ({
    data: null,
    isPending: false,
  }),
}));

// Mock router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

describe('SignInPage', () => {
  it('renders sign in form', () => {
    render(<SignInPage />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('submits form with email and password', async () => {
    const { authClient } = require('@/lib/auth-client');
    const user = userEvent.setup();

    render(<SignInPage />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authClient.signIn.email).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('displays error message on failed sign in', async () => {
    const { authClient } = require('@/lib/auth-client');
    authClient.signIn.email.mockRejectedValueOnce(new Error('Invalid credentials'));

    const user = userEvent.setup();
    render(<SignInPage />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });
});
```

## Example 6: Environment Setup Script

```bash
#!/bin/bash
# scripts/setup-auth.sh

echo "🔧 Setting up Better Auth..."

# Check if .env.local exists
if [ ! -f .env.local ]; then
  echo "📝 Creating .env.local..."

  # Generate secret
  SECRET=$(openssl rand -base64 32)

  # Create .env.local
  cat > .env.local << EOF
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/myapp

# Better Auth
BETTER_AUTH_SECRET=${SECRET}
BETTER_AUTH_URL=http://localhost:3000

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

  echo "✅ Created .env.local with generated secret"
else
  echo "⚠️  .env.local already exists, skipping..."
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install better-auth @better-auth/react pg

echo "✅ Better Auth setup complete!"
echo ""
echo "Next steps:"
echo "1. Update DATABASE_URL in .env.local"
echo "2. Run 'npm run dev' to start the development server"
echo "3. Visit http://localhost:3000/signup to create an account"
```

Make it executable:
```bash
chmod +x scripts/setup-auth.sh
./scripts/setup-auth.sh
```

## Example 7: Production Deployment (Vercel + Render)

### Architecture

```
Frontend (Vercel)              Backend (Render)
┌──────────────────────┐      ┌──────────────────────┐
│ yourapp.vercel.app   │      │ api.yourapp.com      │
│                      │      │                      │
│ Better Auth          │      │ JWT Validation       │
│ /api/auth/jwks ──────┼──────┤ Fetches JWKS         │
│ (Public Endpoint)    │      │ (via HTTPS)          │
└──────────────────────┘      └──────────────────────┘
         │                             │
         └─────────────┬───────────────┘
                       │
                 ┌─────▼─────┐
                 │ Database  │
                 │ (Neon)    │
                 └───────────┘
```

### Step 1: Deploy Frontend to Vercel

**Environment Variables:**
```bash
# Vercel Dashboard → Settings → Environment Variables

# Database
DATABASE_URL=postgresql://user:password@neon.tech:5432/dbname

# Better Auth
BETTER_AUTH_SECRET=<generate-with-openssl-rand-base64-32>
BETTER_AUTH_URL=https://yourapp.vercel.app

# Backend API
NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

**Deployment:**
```bash
# Push to GitHub
git push origin main

# Vercel auto-deploys on push
# Or manually: vercel --prod
```

**Verify JWKS Endpoint:**
```bash
curl https://yourapp.vercel.app/api/auth/jwks

# Expected output:
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
```

### Step 2: Deploy Backend to Render

**Environment Variables:**
```bash
# Render Dashboard → Web Service → Environment

# Database
DATABASE_URL=postgresql://user:password@neon.tech:5432/dbname

# Better Auth (CRITICAL: Use production frontend URL)
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks
BETTER_AUTH_SECRET=<same-as-frontend>

# OpenAI (if using AI features)
OPENAI_API_KEY=sk-proj-...

# MCP Server
MCP_SERVER_URL=https://mcp.yourapp.com
```

**render.yaml:**
```yaml
services:
  - type: web
    name: backend
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port 8000"
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: BETTER_AUTH_JWKS_URL
        value: https://yourapp.vercel.app/api/auth/jwks
      - key: BETTER_AUTH_SECRET
        sync: false
```

### Step 3: Test End-to-End

**Test 1: Sign Up Flow**
```bash
# 1. Visit frontend
open https://yourapp.vercel.app/signup

# 2. Create account (check browser DevTools → Network)
# Should see:
# POST /api/auth/sign-up/email → 200 OK

# 3. Check database
psql $DATABASE_URL -c "SELECT id, email FROM \"user\";"
```

**Test 2: JWKS Accessibility**
```bash
# Test JWKS from backend perspective
curl -v https://yourapp.vercel.app/api/auth/jwks

# Should return:
# HTTP/2 200
# content-type: application/json
# {"keys": [...]}
```

**Test 3: JWT Validation**
```bash
# 1. Sign in and get JWT from browser DevTools:
# Application → Cookies → better-auth.session_token

# 2. Test backend endpoint with JWT
curl -H "Authorization: Bearer <jwt-token>" \
  https://api.yourapp.com/api/user123/tasks

# Should return:
# 200 OK with tasks data
# OR
# 401 if token invalid
# 403 if user_id mismatch
```

### Common Production Errors

#### Error 1: "Cannot connect to host localhost:3000"

**Symptom:** Backend logs show:
```
httpx.ConnectError: Cannot connect to host localhost:3000 ssl:default
```

**Cause:** `BETTER_AUTH_JWKS_URL` not set or using localhost.

**Fix:**
```bash
# Render Dashboard → backend → Environment
# Add/Update:
BETTER_AUTH_JWKS_URL=https://yourapp.vercel.app/api/auth/jwks

# Redeploy backend
```

**Verify:**
```bash
# Check backend logs after redeploy
# Should see successful JWKS fetches
```

#### Error 2: "JWKS endpoint returned 404"

**Symptom:**
```
httpx.HTTPStatusError: Client error '404 Not Found'
```

**Cause:** Frontend not deployed or route incorrect.

**Diagnosis:**
```bash
# Test JWKS endpoint
curl https://yourapp.vercel.app/api/auth/jwks

# If 404:
# 1. Check frontend is deployed: vercel ls
# 2. Check route file: app/api/auth/[...all]/route.ts exists
# 3. Check auth.ts exports auth instance
# 4. Redeploy frontend: vercel --prod
```

#### Error 3: "Invalid signature"

**Symptom:** All JWT validation fails with "Invalid signature".

**Cause:** Algorithm mismatch or wrong JWKS keys.

**Diagnosis:**
```python
# Add to backend verify_token function
print(f"JWKS URL: {settings.BETTER_AUTH_JWKS_URL}")
print(f"Token algorithms: {jwt.get_unverified_header(token)}")
print(f"Payload: {jwt.decode(token, options={'verify_signature': False})}")
```

**Fix:**
```python
# Ensure EdDSA is included
payload = jwt.decode(
    token,
    signing_key.key,
    algorithms=["EdDSA", "ES256", "RS256"],  # EdDSA first!
)
```

#### Error 4: CORS Errors in Browser

**Symptom:**
```
Access to fetch at 'https://api.yourapp.com' blocked by CORS policy
```

**Cause:** Backend CORS not configured for Vercel domain.

**Fix:**
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourapp.vercel.app",  # Add production domain
        "https://yourapp-git-main-xyz.vercel.app",  # Preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production Deployment Checklist

#### Frontend (Vercel)

- [ ] Environment variables set in Vercel dashboard
- [ ] `BETTER_AUTH_URL` uses HTTPS production domain
- [ ] `BETTER_AUTH_SECRET` matches backend
- [ ] `DATABASE_URL` points to production database
- [ ] Frontend builds successfully: `vercel build`
- [ ] JWKS endpoint accessible: `curl https://yourapp.vercel.app/api/auth/jwks`
- [ ] Returns valid JSON with keys array

#### Backend (Render)

- [ ] `BETTER_AUTH_JWKS_URL` points to production frontend
- [ ] Uses HTTPS not HTTP: `https://yourapp.vercel.app/...`
- [ ] `BETTER_AUTH_SECRET` matches frontend
- [ ] Backend can fetch JWKS (test from backend logs)
- [ ] CORS includes production frontend domain
- [ ] Health check passes: `curl https://api.yourapp.com/health`

#### Database (Neon)

- [ ] Database accessible from both services
- [ ] Connection pooling configured
- [ ] SSL mode enabled for production
- [ ] Better Auth tables created (`user`, `session`, `account`)

#### End-to-End

- [ ] Sign up creates user in database
- [ ] Sign in generates JWT
- [ ] JWT includes `user_id` claim
- [ ] Backend validates JWT successfully
- [ ] Protected endpoints require valid JWT
- [ ] User isolation works (user A can't access user B's data)

### Monitoring and Debugging

#### Check Backend Logs

```bash
# Render Dashboard → backend → Logs

# Look for:
"✅ JWKS accessible: 1 keys found"  # Good
"❌ Cannot connect to JWKS"         # Bad - check JWKS URL
"❌ JWKS returned 404"               # Bad - frontend issue
```

#### Check Frontend Logs

```bash
# Vercel Dashboard → Deployments → [latest] → Runtime Logs

# Look for:
"GET /api/auth/jwks 200"  # Good
"GET /api/auth/jwks 404"  # Bad - route not configured
```

#### Test JWKS Locally

```bash
# Fetch JWKS and inspect
curl -s https://yourapp.vercel.app/api/auth/jwks | jq

# Verify key properties:
# - kty: "OKP" (EdDSA)
# - crv: "Ed25519"
# - kid: exists
# - x: base64 string
```

#### Test JWT Generation

```typescript
// Add to signin page for debugging
const { data: session } = await authClient.signIn.email({
  email,
  password,
});

// Get JWT
const { data: token } = await authClient.token();
console.log("JWT:", token);

// Decode (for debugging only, never in production)
const parts = token.token.split('.');
const payload = JSON.parse(atob(parts[1]));
console.log("Payload:", payload);
// Should contain: user_id, exp, iat
```

### Rollback Plan

If production deployment fails:

```bash
# Frontend (Vercel)
vercel rollback  # Rolls back to previous deployment

# Backend (Render)
# Render Dashboard → backend → Rollback
# Or redeploy previous commit

# Database (if migration failed)
# Restore from backup
pg_restore -d $DATABASE_URL backup.sql
```

### Performance Optimization

#### Cache JWKS Keys

```python
# backend/middleware.py
from datetime import datetime, timedelta

class JWKSCache:
    def __init__(self):
        self.keys = None
        self.last_fetch = None
        self.ttl = timedelta(hours=1)

    async def get_keys(self, url: str):
        now = datetime.utcnow()

        if self.keys and self.last_fetch:
            if now - self.last_fetch < self.ttl:
                return self.keys

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            self.keys = response.json()
            self.last_fetch = now
            return self.keys

jwks_cache = JWKSCache()
```

#### Connection Pooling

```typescript
// frontend/lib/auth.ts
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,              // Increase for high traffic
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

### Multi-Environment Setup

```bash
# .env.development
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000

# .env.staging (Vercel preview)
BETTER_AUTH_URL=https://staging-yourapp.vercel.app
NEXT_PUBLIC_API_URL=https://staging-api.yourapp.com

# .env.production (Vercel production)
BETTER_AUTH_URL=https://yourapp.vercel.app
NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

**Vercel Environment Configuration:**
```bash
# Set per environment in Vercel dashboard:
# Production
BETTER_AUTH_URL=https://yourapp.vercel.app

# Preview
BETTER_AUTH_URL=https://$VERCEL_URL  # Auto-generated preview URL
```
