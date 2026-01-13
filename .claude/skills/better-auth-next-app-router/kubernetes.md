# Kubernetes Deployment Guide for Better Auth

This guide covers deploying Better Auth with Next.js to Kubernetes environments (Minikube, EKS, GKE, AKS).

## Table of Contents

1. [Critical: Node.js Happy Eyeballs Fix](#critical-nodejs-happy-eyeballs-fix)
2. [JWKS Management After Secret Changes](#jwks-management-after-secret-changes)
3. [Kubernetes Secrets Management](#kubernetes-secrets-management)
4. [Next.js Standalone Build Configuration](#nextjs-standalone-build-configuration)
5. [Dockerfile for Kubernetes](#dockerfile-for-kubernetes)
6. [Helm Chart Configuration](#helm-chart-configuration)
7. [Troubleshooting](#troubleshooting)

---

## Critical: Node.js Happy Eyeballs Fix

### The Problem

In Kubernetes/containerized environments, Node.js connections to external databases (Neon, Supabase, PlanetScale) fail with:

```
Error: AggregateError
  code: 'ETIMEDOUT'
```

**Symptoms:**
- Frontend pod cannot connect to PostgreSQL
- Backend pod (Python) CAN connect to same database
- `nc` and `wget` from frontend pod work, but Node.js fails
- Error occurs with both direct and pooler database URLs

### Root Cause

Node.js 18+ implements "Happy Eyeballs" (RFC 6555) via `autoSelectFamily`, which tries IPv4 and IPv6 connections concurrently. In containerized Kubernetes environments, this concurrent connection attempt causes timeouts.

### The Fix

Add to `lib/auth.ts` (or any file that loads early in the application):

```typescript
import { betterAuth } from "better-auth";
import { Pool } from "pg";
import dns from "dns";
import net from "net";

// CRITICAL: Fix for Node.js Happy Eyeballs issue in containerized environments
// Disable concurrent IPv4/IPv6 connection attempts - use sequential instead
net.setDefaultAutoSelectFamily(false);

// Also prioritize IPv4 for DNS resolution
dns.setDefaultResultOrder("ipv4first");

// Now create the pool - connections will work in Kubernetes
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export const auth = betterAuth({
  database: {
    provider: "postgres",
    pool,
  },
  // ... rest of config
});
```

### Why This Works

- `net.setDefaultAutoSelectFamily(false)` disables concurrent connection attempts
- `dns.setDefaultResultOrder("ipv4first")` ensures IPv4 addresses are tried first
- Together, these make Node.js behave like Python/curl which work in containers

### Verification

Test from inside the pod:

```bash
kubectl exec <frontend-pod> -- node -e '
const net = require("net");
net.setDefaultAutoSelectFamily(false);
const socket = net.connect(5432, "your-db-host.neon.tech", () => {
  console.log("Connected!");
  socket.end();
});
socket.on("error", (e) => console.log("Error:", e.message));
'
```

---

## JWKS Management After Secret Changes

### The Problem

After changing `BETTER_AUTH_SECRET`, sign-in fails with:

```
BetterAuthError: Failed to decrypt private key. Make sure the secret currently
in use is the same as the one used to encrypt the private key.
```

**Symptoms:**
- Sign-in redirects back to sign-in page
- User appears to authenticate but session doesn't persist
- No explicit error shown to user

### Root Cause

Better Auth stores JWKS (JSON Web Key Set) keys in the database, encrypted with `BETTER_AUTH_SECRET`. When the secret changes, existing encrypted keys cannot be decrypted.

### The Fix

Clean the JWKS table in the database:

```bash
# Option 1: Using psql directly
psql $DATABASE_URL -c "DELETE FROM jwks;"

# Option 2: From a Kubernetes pod with database access
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('DELETE FROM jwks')
conn.commit()
print('JWKS table cleaned - restart frontend to regenerate keys')
conn.close()
"
```

Then restart the frontend to regenerate keys:

```bash
kubectl rollout restart deployment frontend
```

### Prevention

- Never change `BETTER_AUTH_SECRET` in production without planning for JWKS cleanup
- Keep the secret consistent across all deployments
- Store the secret securely and don't regenerate unnecessarily
- Document the secret rotation procedure for your team

---

## Kubernetes Secrets Management

### Creating Secrets

Better Auth requires matching secrets across frontend and backend:

```bash
# Generate a secure secret (32+ characters)
SECRET=$(openssl rand -base64 32)

# Create Kubernetes secret for frontend
kubectl create secret generic frontend-secrets \
  --from-literal=better-auth-secret="$SECRET" \
  --from-literal=database-url="postgresql://..."

# Create Kubernetes secret for backend (must match!)
kubectl create secret generic backend-secrets \
  --from-literal=better-auth-secret="$SECRET" \
  --from-literal=database-url="postgresql://..."
```

### Verifying Secrets Match

```bash
# Check frontend secret
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# Check backend secret
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# They MUST be EXACTLY the same
```

### Updating Secrets

```bash
SECRET="YourNewSecretHere"

# Update both secrets
kubectl patch secret frontend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"
kubectl patch secret backend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"

# Clean JWKS table (see above)
psql $DATABASE_URL -c "DELETE FROM jwks;"

# Restart deployments
kubectl rollout restart deployment frontend backend
```

### Helm Values Example

```yaml
# values.yaml
secrets:
  existingSecret: frontend-secrets
  keys:
    betterAuthSecret: better-auth-secret
    databaseUrl: database-url

env:
  - name: BETTER_AUTH_SECRET
    valueFrom:
      secretKeyRef:
        name: {{ .Values.secrets.existingSecret }}
        key: {{ .Values.secrets.keys.betterAuthSecret }}
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: {{ .Values.secrets.existingSecret }}
        key: {{ .Values.secrets.keys.databaseUrl }}
```

---

## Next.js Standalone Build Configuration

### The Problem

Next.js standalone builds don't include all node_modules. Better Auth dependencies like `pg` and `ws` may be missing, causing runtime errors.

### next.config.ts Configuration

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // CRITICAL: Include packages that aren't bundled by Next.js standalone
  serverExternalPackages: ["ws", "@neondatabase/serverless", "pg"],

  // Other common config
  reactStrictMode: true,
};

export default nextConfig;
```

### Why serverExternalPackages?

- Next.js standalone output bundles most dependencies
- Some packages (native modules, WebSocket libs) can't be bundled
- `serverExternalPackages` tells Next.js to keep them external
- These must then be copied in the Dockerfile

---

## Dockerfile for Kubernetes

### Complete Multi-Stage Dockerfile

```dockerfile
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables needed at build time
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_URL

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AUTH_URL=$NEXT_PUBLIC_AUTH_URL

# Build the application
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# CRITICAL: Copy external packages that aren't bundled by Next.js standalone
# These correspond to serverExternalPackages in next.config.ts
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/ws ./node_modules/ws
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pg ./node_modules/pg
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pg-protocol ./node_modules/pg-protocol
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pg-types ./node_modules/pg-types
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pg-pool ./node_modules/pg-pool
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pgpass ./node_modules/pgpass
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/pg-connection-string ./node_modules/pg-connection-string
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/postgres-array ./node_modules/postgres-array
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/postgres-bytea ./node_modules/postgres-bytea
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/postgres-date ./node_modules/postgres-date
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/postgres-interval ./node_modules/postgres-interval
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/postgres-range ./node_modules/postgres-range

# If using Neon serverless driver
COPY --from=builder --chown=nextjs:nodejs /app/node_modules/@neondatabase ./node_modules/@neondatabase

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### Building for Minikube

```bash
# Use Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://backend-api:8000 \
  --build-arg NEXT_PUBLIC_AUTH_URL=http://frontend:3000 \
  -t frontend:latest \
  ./frontend

# Deploy with Helm
helm upgrade --install frontend ./infrastructure/helm/frontend \
  -f ./infrastructure/helm/frontend/values-local.yaml
```

---

## Helm Chart Configuration

### values-local.yaml for Minikube

```yaml
replicaCount: 1

image:
  repository: frontend
  tag: latest
  pullPolicy: Never  # Use local images in Minikube

service:
  type: ClusterIP
  port: 3000

env:
  - name: NODE_ENV
    value: "production"
  - name: BETTER_AUTH_URL
    value: "http://frontend:3000"
  - name: NEXT_PUBLIC_API_URL
    value: "http://backend-api:8000"
  - name: BETTER_AUTH_SECRET
    valueFrom:
      secretKeyRef:
        name: better-auth-secret
        key: better-auth-secret
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database-url

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

livenessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Troubleshooting

### Issue: Sign-in Redirects Back to Sign-in Page

**Possible causes:**

1. **JWKS decryption error** (most common after secret change)
   - Check pod logs: `kubectl logs -l app=frontend`
   - Look for: "Failed to decrypt private key"
   - Fix: Clean JWKS table and restart

2. **Secrets mismatch between frontend and backend**
   - Verify: `kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d`
   - Compare with backend secret
   - Fix: Update secrets to match

3. **Database connection timeout**
   - Check pod logs for ETIMEDOUT
   - Fix: Apply Happy Eyeballs fix in auth.ts

### Issue: ETIMEDOUT to Database

**Checklist:**
1. Is Happy Eyeballs fix applied in `lib/auth.ts`?
2. Are `dns` and `net` imports present?
3. Is `net.setDefaultAutoSelectFamily(false)` called before Pool creation?
4. Rebuild and redeploy after fix

### Issue: Module Not Found in Production

**Symptoms:**
```
Error: Cannot find module 'ws'
Error: Cannot find module 'pg'
```

**Checklist:**
1. Is package in `serverExternalPackages` in next.config.ts?
2. Is package COPY'd in Dockerfile?
3. Are all transitive dependencies copied?

### Issue: Health Check Failing

**Check the health endpoint:**
```bash
kubectl exec <pod> -- wget -qO- http://localhost:3000/api/health
```

**Create health endpoint if missing:**

```typescript
// app/api/health/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ status: "ok" });
}
```

### Debug Commands

```bash
# Check pod status
kubectl get pods -l app=frontend

# View pod logs
kubectl logs -l app=frontend --tail=100

# Exec into pod
kubectl exec -it <pod-name> -- sh

# Test database connectivity from pod
kubectl exec <pod> -- node -e "
const net = require('net');
net.setDefaultAutoSelectFamily(false);
const socket = net.connect(5432, 'your-db-host', () => {
  console.log('DB connected!');
  socket.end();
});
"

# Check environment variables
kubectl exec <pod> -- env | grep -E "(AUTH|DATABASE)"

# Port forward for local testing
kubectl port-forward svc/frontend 3000:3000
```

---

## Quick Reference

### Required Environment Variables (Kubernetes)

| Variable | Source | Description |
|----------|--------|-------------|
| `BETTER_AUTH_SECRET` | Secret | 32+ char encryption key |
| `DATABASE_URL` | Secret | PostgreSQL connection string |
| `BETTER_AUTH_URL` | ConfigMap/Env | Frontend service URL |
| `NEXT_PUBLIC_API_URL` | Build arg | Backend API URL |

### Files to Modify for Kubernetes

| File | Change |
|------|--------|
| `lib/auth.ts` | Add Happy Eyeballs fix |
| `next.config.ts` | Add `serverExternalPackages` |
| `Dockerfile` | COPY external packages |
| `values.yaml` | Configure secrets and env |

### Common Commands

```bash
# Deploy to Minikube
eval $(minikube docker-env)
docker build -t frontend:latest ./frontend
helm upgrade --install frontend ./helm/frontend -f values-local.yaml

# Clean JWKS after secret change
psql $DATABASE_URL -c "DELETE FROM jwks;"
kubectl rollout restart deployment frontend

# Verify secrets match
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
kubectl get secret backend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d
```
