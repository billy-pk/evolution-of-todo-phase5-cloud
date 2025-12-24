---
name: better-auth-next-app-router-templates
description: Ready-to-use code templates for Better Auth in Next.js 15 App Router, including auth config, pages, middleware, and utility functions.
---

# Better Auth in Next.js 15 - Code Templates

## Template 1: Basic Auth Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { Pool } from "pg";

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
    requireEmailVerification: false,
  },
  secret: process.env.BETTER_AUTH_SECRET!,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
});

export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.User;
```

## Template 2: Auth Client Configuration

```typescript
// lib/auth-client.ts
"use client";

import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000",
});

export const {
  useSession,
  signIn,
  signUp,
  signOut,
} = authClient;
```

## Template 3: API Routes

```typescript
// app/api/auth/[...all]/route.ts
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

## Template 4: Sign In Page Template

```tsx
// app/(auth)/signin/page.tsx
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

## Template 5: Sign Up Page Template

```tsx
// app/(auth)/signup/page.tsx
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

## Template 6: Middleware Template

```typescript
// middleware.ts
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

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/signin",
    "/signup",
  ],
};
```

## Template 7: Protected Page Component

```tsx
// app/(dashboard)/[page]/page.tsx
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

  if (isPending) {
    return <div>Loading...</div>;
  }

  if (!session) {
    return null;
  }

  return (
    <div>
      <h1>Protected Page</h1>
      <p>Welcome, {session.user.email}!</p>
    </div>
  );
}
```

## Template 8: API Client with JWT

```typescript
// lib/api.ts
import { authClient } from "./auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  // Get JWT token
  const { data, error } = await authClient.token();

  if (error || !data?.token) {
    throw new Error("Not authenticated");
  }

  // Make request with JWT
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

// Usage:
// const data = await apiRequest("/api/user123/tasks");
```

## Template 9: Sign Out Button

```tsx
// components/SignOutButton.tsx
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

## Template 10: useAuth Hook

```typescript
// lib/hooks/useAuth.ts
"use client";

import { useSession } from "@/lib/auth-client";

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

// Usage:
// const { user, isAuthenticated, isLoading } = useAuth();
```

## Template 11: Environment Variables

```env
# .env.local

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Better Auth (generate secret: openssl rand -base64 32)
BETTER_AUTH_SECRET=your-32-character-secret-here
BETTER_AUTH_URL=http://localhost:3000

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth URL (for client)
NEXT_PUBLIC_AUTH_URL=http://localhost:3000
```

## Template 12: Server-Side Session Check

```typescript
// lib/server-auth.ts
import { headers } from "next/headers";
import { auth } from "./auth";

export async function getServerSession() {
  const headersList = headers();
  return await auth.api.getSession({ headers: headersList });
}

export async function requireServerAuth() {
  const session = await getServerSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  return session;
}

// Usage in Server Component:
// const session = await getServerSession();
// if (!session) redirect("/signin");
```

## Template 13: Protected API Route

```typescript
// app/api/protected/route.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export async function GET(request: NextRequest) {
  // Check authentication
  const session = await auth.api.getSession({
    headers: request.headers,
  });

  if (!session) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  // Return protected data
  return NextResponse.json({
    message: "Protected data",
    userId: session.user.id,
  });
}
```

## Template 14: User Profile Component

```tsx
// components/UserProfile.tsx
"use client";

import { useSession } from "@/lib/auth-client";

export function UserProfile() {
  const { data: session } = useSession();

  if (!session) return null;

  return (
    <div className="flex items-center space-x-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white">
        {session.user.name?.[0] || session.user.email[0].toUpperCase()}
      </div>
      <div>
        <p className="text-sm font-medium">{session.user.name}</p>
        <p className="text-xs text-gray-500">{session.user.email}</p>
      </div>
    </div>
  );
}
```

## Template 15: Loading Skeleton

```tsx
// components/LoadingSkeleton.tsx
export function LoadingSkeleton() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <div className="inline-block">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        </div>
        <p className="text-gray-600 mt-4">Loading...</p>
      </div>
    </div>
  );
}
```

## Template 16: Error Boundary

```tsx
// components/ErrorBoundary.tsx
"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex h-screen items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-red-600 mb-2">
                Something went wrong
              </h2>
              <p className="text-gray-600">{this.state.error?.message}</p>
              <button
                onClick={() => this.setState({ hasError: false })}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Try again
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
```

## Template 17: Setup Script

```bash
#!/bin/bash
# scripts/setup-auth.sh

echo "🔧 Setting up Better Auth..."

# Generate secret
SECRET=$(openssl rand -base64 32)

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
  cat > .env.local << EOF
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
BETTER_AUTH_SECRET=${SECRET}
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_URL=http://localhost:3000
EOF
  echo "✅ Created .env.local"
else
  echo "⚠️  .env.local already exists"
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install better-auth @better-auth/react pg

echo "✅ Setup complete!"
```

## Template 18: TypeScript Types

```typescript
// types/auth.ts
export interface User {
  id: string;
  email: string;
  name: string;
  emailVerified: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Session {
  user: User;
  session: {
    id: string;
    userId: string;
    expiresAt: Date;
    token: string;
  };
}

export interface AuthState {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
}
```

## Quick Copy-Paste Snippets

### Generate Secret

```bash
openssl rand -base64 32
```

### Check Session (Client)

```tsx
const { data: session } = useSession();
if (session) {
  console.log("Authenticated:", session.user.email);
}
```

### Get JWT Token

```typescript
const { data, error } = await authClient.token();
const token = data?.token;
```

### Redirect After Auth

```typescript
await authClient.signIn.email({ email, password });
router.push("/dashboard");
```

### Sign Out

```typescript
await authClient.signOut();
router.push("/signin");
```

### API Call with JWT

```typescript
const { data } = await authClient.token();
const response = await fetch("/api/endpoint", {
  headers: {
    "Authorization": `Bearer ${data.token}`,
  },
});
```
