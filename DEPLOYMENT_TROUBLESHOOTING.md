# Deployment Troubleshooting Guide

This guide helps you troubleshoot common issues when deploying the Evolution of Todo app to Vercel (frontend) and Render (backend).

## Current Issue: 403 Error on Sign In

**Error Message:**
```
Failed to load resource: the server responded with a status of 403 ()
/api/auth/sign-in/email:1
```

**Root Cause:** Better Auth's `trustedOrigins` configuration was not set up to dynamically handle Vercel URLs.

**✅ SOLUTION IMPLEMENTED:**
Updated `frontend/lib/auth.ts` to automatically detect Vercel URLs using the `VERCEL_URL` environment variable.

---

## Fix Steps for Your Deployment

### Step 1: Update Your Code

Pull the latest changes:
```bash
git pull origin main
# Or if you're on a branch:
git pull origin <your-branch>
```

The following files were updated:
- `frontend/lib/auth.ts` - Dynamic trustedOrigins
- `frontend/.env.vercel.example` - Updated instructions

### Step 2: Verify Vercel Environment Variables

Go to **Vercel Dashboard → Your Project → Settings → Environment Variables**

**Required Variables:**

| Variable | Example Value | Where to Get It |
|----------|--------------|-----------------|
| `DATABASE_URL` | `postgresql://user:pass@host/db?sslmode=require` | Neon PostgreSQL dashboard |
| `BETTER_AUTH_SECRET` | `abcd1234...` (32+ chars) | Generate with `openssl rand -base64 32` |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.onrender.com` | Your Render backend URL |

**DO NOT SET (Auto-detected by Vercel):**
- ❌ `BETTER_AUTH_URL` - Leave empty or remove entirely
- ❌ `VERCEL_URL` - Automatically provided by Vercel

**Optional (only if using custom domain):**
- `NEXT_PUBLIC_SITE_URL` - Your custom domain (e.g., `https://yourdomain.com`)

### Step 3: Redeploy Frontend on Vercel

After updating environment variables:

1. Go to **Deployments** tab
2. Click the **"..."** menu on the latest deployment
3. Click **"Redeploy"**
4. ✅ Enable "Use existing build cache" (faster)
5. Click **"Redeploy"**

Wait for deployment to complete (usually 1-2 minutes).

### Step 4: Verify Backend Environment Variables on Render

Go to **Render Dashboard → Your Service → Environment**

**Required Variables:**

| Variable | Example Value | Notes |
|----------|--------------|-------|
| `DATABASE_URL` | `postgresql://...` | Same as frontend |
| `BETTER_AUTH_SECRET` | Same as frontend | **MUST MATCH** frontend |
| `BETTER_AUTH_URL` | `https://your-app.vercel.app` | Your Vercel frontend URL |
| `OPENAI_API_KEY` | `sk-...` | Your OpenAI API key |
| `MOUNT_MCP_SERVER` | `true` | Enable unified deployment |
| `ENVIRONMENT` | `production` | Set to production mode |

**Optional Override:**
- `MCP_SERVER_URL` - Leave empty for auto-detection

### Step 5: Update Backend CORS for Production

The backend CORS is currently set to `allow_origins=["*"]` which is fine for testing but not recommended for production.

**Recommended:** Update `backend/main.py` to include your Vercel URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://your-app.vercel.app",  # Your production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization"]
)
```

Then redeploy on Render.

### Step 6: Test the Fix

1. **Clear browser cache and cookies** (Important!)
   - Chrome: Settings → Privacy → Clear browsing data
   - Or use Incognito/Private mode

2. **Open your Vercel URL** (e.g., `https://your-app.vercel.app`)

3. **Try to sign up** with a new account:
   - Email: `test@example.com`
   - Password: `Testpassword123`

4. **Check for errors:**
   - Open DevTools (F12)
   - Go to Console tab
   - Should see no 403 errors

5. **Verify sign in works:**
   - Sign out
   - Sign in with same credentials
   - Should redirect to dashboard

---

## Common Issues & Solutions

### Issue 1: 403 Forbidden on Sign In/Sign Up

**Symptoms:**
```
POST /api/auth/sign-in/email 403 Forbidden
```

**Root Cause:**
Better Auth's CSRF protection checks that the request `Origin` header matches one of the `trustedOrigins`. Vercel's `VERCEL_URL` environment variable contains deployment-specific URLs (like `your-app-abc123.vercel.app`) that change with each deployment, but your production URL is stable (`your-app.vercel.app`).

**Causes:**
1. `BETTER_AUTH_SECRET` not set on Vercel
2. Stale JWKS keys in database after changing `BETTER_AUTH_SECRET`
3. Production Vercel URL not explicitly added to trustedOrigins
4. `VERCEL_URL` mismatch with actual production URL

**Solutions:**

**A. If you changed BETTER_AUTH_SECRET:**
```sql
-- Clear stale keys in Neon database
DELETE FROM jwks;
DELETE FROM session;
```

**B. Verify BETTER_AUTH_SECRET matches:**
- Check Vercel and Render both have EXACTLY the same secret
- No extra spaces or newlines
- Generate new: `openssl rand -base64 32`

**C. Explicit production URL (FIXED):**
The code now includes your production URL explicitly:
```typescript
origins.push("https://evolution-of-todo-ai-chatbot-phase3.vercel.app");
```

**D. Redeploy after changes:**
- Vercel: Auto-deploys on git push or manual redeploy
- Clear browser cache after redeployment

### Issue 2: Database Connection Errors

**Symptoms:**
```
Error: Connection refused
FATAL: password authentication failed
```

**Solutions:**
1. Verify `DATABASE_URL` format:
   ```
   postgresql://username:password@host/database?sslmode=require
   ```
2. Check Neon dashboard that database is active
3. Verify IP allowlist in Neon (should allow all IPs for Vercel)

### Issue 3: CORS Errors from Frontend to Backend

**Symptoms:**
```
Access to fetch at 'https://backend.onrender.com/api/...' from origin 'https://app.vercel.app' has been blocked by CORS policy
```

**Solutions:**
1. Update backend CORS to include your Vercel URL (see Step 5 above)
2. Ensure `allow_credentials=True` is set
3. Redeploy backend after changes

### Issue 4: Environment Variables Not Taking Effect

**Symptoms:**
- Changes to env vars don't seem to work
- Old values still being used

**Solutions:**
1. **Vercel:** Must redeploy after changing env vars
2. **Render:** Automatically redeploys when env vars change
3. Clear browser cache
4. Check correct environment (Production vs Preview)

### Issue 5: Chat Not Working (Backend Deployed)

**Symptoms:**
```
Error: Failed to connect to MCP server
Connection refused to http://localhost:8001/mcp
```

**Solutions:**
1. Verify `MOUNT_MCP_SERVER=true` on Render
2. Check backend logs for "✅ MCP server mounted at /mcp"
3. Test MCP endpoint: `https://your-backend.onrender.com/mcp`
4. Ensure `OPENAI_API_KEY` is set

### Issue 6: Better Auth Secret Mismatch

**Symptoms:**
```
Invalid token signature
JWT verification failed
```

**Solutions:**
1. Ensure `BETTER_AUTH_SECRET` is **EXACTLY** the same on:
   - Vercel (frontend)
   - Render (backend)
2. No extra spaces or newlines
3. Generate once, use everywhere: `openssl rand -base64 32`

---

## Verification Checklist

After following all steps, verify:

- [ ] Frontend loads without errors
- [ ] Can sign up with new account
- [ ] Can sign in with existing account
- [ ] No 403 errors in DevTools Console
- [ ] Backend health check works: `https://your-backend.onrender.com/health`
- [ ] Backend shows: `{"status": "healthy", "database": "connected"}`
- [ ] MCP endpoint accessible: `https://your-backend.onrender.com/mcp`
- [ ] Can access dashboard after login
- [ ] Tasks page loads (even if empty)
- [ ] Chat page loads (if OpenAI key is set)

---

## Debug Commands

### Check Vercel Environment Variables
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# List env vars
vercel env ls
```

### Check Render Logs
1. Go to Render Dashboard
2. Click your service
3. Click "Logs" tab
4. Look for errors or MCP mounting message

### Test Backend Health
```bash
curl https://your-backend.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "connected"
}
```

### Test MCP Endpoint
```bash
curl https://your-backend.onrender.com/mcp
```

Should return MCP server information (not an error).

---

## Kubernetes/Minikube Deployment Issues

### Issue 7: ETIMEDOUT Connecting to Neon from Node.js in Kubernetes

**Symptoms:**
```
Error: AggregateError
  code: 'ETIMEDOUT'
```
- Frontend pod cannot connect to Neon PostgreSQL
- Backend pod (Python) CAN connect to same database
- `nc` and `wget` from frontend pod work, but Node.js fails
- Error occurs with both direct and pooler Neon URLs

**Root Cause:**
Node.js's Happy Eyeballs implementation (`autoSelectFamily`) tries to connect to IPv4 and IPv6 addresses concurrently. In containerized Kubernetes environments, this concurrent connection attempt causes timeouts, even though sequential connections work fine.

**Solution:**
Add the following to `frontend/lib/auth.ts` (or any file that loads early):

```typescript
import dns from "dns";
import net from "net";

// Fix for Node.js Happy Eyeballs issue in containerized environments
// Disable concurrent IPv4/IPv6 connection attempts
net.setDefaultAutoSelectFamily(false);

// Also prioritize IPv4 for DNS resolution
dns.setDefaultResultOrder("ipv4first");
```

**Verification:**
```bash
# Test from frontend pod - should work after fix
kubectl exec <frontend-pod> -- node -e '
const net = require("net");
net.setDefaultAutoSelectFamily(false);
const socket = net.connect(443, "ep-divine-feather-a4qc11zk.us-east-1.aws.neon.tech", () => {
  console.log("Connected!");
  socket.end();
});
'
```

**After fix, rebuild and redeploy:**
```bash
eval $(minikube docker-env)
docker build -t frontend:latest ./frontend
kubectl rollout restart deployment frontend
```

### Issue 8: JWKS Decryption Error After Changing BETTER_AUTH_SECRET

**Symptoms:**
```
BetterAuthError: Failed to decrypt private key. Make sure the secret currently
in use is the same as the one used to encrypt the private key.
```
- Sign-in redirects back to sign-in page
- User appears to authenticate but session doesn't persist

**Root Cause:**
Better Auth stores JWKS (JSON Web Key Set) keys in the database, encrypted with the `BETTER_AUTH_SECRET`. If the secret changes, the stored keys cannot be decrypted.

**Solution:**
Clean the JWKS table in the database:

```bash
# Option 1: Using backend pod with psycopg2
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
conn = psycopg2.connect('YOUR_DATABASE_URL')
cur = conn.cursor()
cur.execute('DELETE FROM jwks')
conn.commit()
print('JWKS table cleaned')
conn.close()
"

# Option 2: Using psql directly
psql YOUR_DATABASE_URL -c "DELETE FROM jwks;"
```

Then restart the frontend to regenerate keys:
```bash
kubectl rollout restart deployment frontend
```

**Prevention:**
- Never change `BETTER_AUTH_SECRET` in production without cleaning JWKS
- Keep the secret consistent across all deployments (frontend and backend)
- Store the secret securely and don't regenerate unnecessarily

### Issue 9: Port-Forward Issues with Kubernetes Services

**Symptoms:**
- Cannot access services at localhost
- Connection refused or timeout when accessing localhost:3000 or localhost:8000

**Solution:**
Ensure port-forwards are running:
```bash
# Kill any stale port-forwards
pkill -f "kubectl port-forward" 2>/dev/null

# Start fresh port-forwards
kubectl port-forward svc/frontend 3000:3000 &
kubectl port-forward svc/backend-api 8000:8000 &

# Verify they're running
ps aux | grep "port-forward"
```

**Check service endpoints:**
```bash
kubectl get svc
kubectl get endpoints
```

### Issue 10: Secrets Mismatch Between Services

**Symptoms:**
- JWT validation fails
- "Invalid token signature" errors
- Sign-in works but API calls fail

**Solution:**
Verify secrets match across all services:
```bash
# Check frontend secret
kubectl get secret frontend-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# Check backend secret
kubectl get secret backend-api-secrets -o jsonpath='{.data.better-auth-secret}' | base64 -d

# They must be EXACTLY the same
```

If they don't match, update the secrets:
```bash
SECRET="YourSecretHere"
kubectl patch secret frontend-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"
kubectl patch secret backend-api-secrets -p "{\"data\":{\"better-auth-secret\":\"$(echo -n $SECRET | base64 -w0)\"}}"

# Restart deployments
kubectl rollout restart deployment frontend backend-api
```

### Minikube Debug Commands

```bash
# Check all pods status
kubectl get pods -o wide

# Check pod logs
kubectl logs -l app.kubernetes.io/name=frontend --tail=50
kubectl logs -l app.kubernetes.io/name=backend-api --tail=50

# Check secrets exist
kubectl get secrets

# Test database connectivity from backend pod
kubectl exec <backend-pod> -- python3 -c "
import psycopg2
conn = psycopg2.connect('YOUR_DATABASE_URL')
print('Database connected!')
conn.close()
"

# Test from frontend pod (after fix applied)
kubectl exec <frontend-pod> -- node -e "
const net = require('net');
net.setDefaultAutoSelectFamily(false);
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.query('SELECT 1').then(() => console.log('DB OK')).catch(e => console.log('Error:', e.message));
"

# Check service endpoints
kubectl get endpoints frontend backend-api

# View Dapr sidecar logs (if using Dapr)
kubectl logs <pod-name> -c daprd
```

---

## Getting Help

If issues persist after following this guide:

1. **Check Logs:**
   - Vercel: Deployment logs (Functions tab)
   - Render: Service logs (Logs tab)

2. **Collect Information:**
   - Exact error message
   - Browser console screenshot
   - Vercel URL
   - Render URL
   - Environment variables (without secrets)

3. **Common Fixes:**
   - Clear browser cache completely
   - Try incognito/private mode
   - Redeploy both frontend and backend
   - Check all env vars are set correctly

4. **Last Resort:**
   - Delete and recreate Vercel deployment
   - Delete and recreate Render service
   - Ensure you're using the updated code

---

## Success Indicators

When everything is working correctly, you should see:

**Vercel Frontend:**
- ✅ Sign up page loads
- ✅ Sign in page loads
- ✅ No 403 errors in console
- ✅ Redirects to dashboard after login

**Render Backend:**
- ✅ Health endpoint returns healthy
- ✅ Database shows connected
- ✅ Logs show "MCP server mounted at /mcp"
- ✅ No error messages in logs

**End-to-End:**
- ✅ Can create account
- ✅ Can log in
- ✅ Can access dashboard
- ✅ JWT authentication works
- ✅ Chat page loads (if OpenAI key set)
