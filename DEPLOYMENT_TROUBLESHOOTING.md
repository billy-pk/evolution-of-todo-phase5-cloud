# Deployment Troubleshooting Guide

This guide helps you troubleshoot common issues when deploying the Evolution of Todo app to Kubernetes/Minikube.

---

## Kubernetes/Minikube Deployment Issues

### Issue 1: ETIMEDOUT Connecting to Neon from Node.js in Kubernetes

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

---

### Issue 2: JWKS Decryption Error After Changing BETTER_AUTH_SECRET

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

---

### Issue 3: Port-Forward Issues with Kubernetes Services

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

---

### Issue 4: Secrets Mismatch Between Services

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

---

## Minikube Debug Commands

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

## Port-Forward Commands

```bash
# Frontend (port 3000)
kubectl port-forward svc/frontend 3000:3000 &

# Backend API (port 8000)
kubectl port-forward svc/backend-api 8000:8000 &

# Optional: View logs while port-forwarding
kubectl port-forward svc/frontend 3000:3000 > /tmp/pf-frontend.log 2>&1 &
kubectl port-forward svc/backend-api 8000:8000 > /tmp/pf-backend.log 2>&1 &

# Check if port-forwards are running
ps aux | grep "port-forward"

# Stop all port-forwards
pkill -f "kubectl port-forward"
```

---

## Getting Help

If issues persist after following this guide:

1. **Check Logs:**
   - Pod logs: `kubectl logs <pod-name>`
   - Dapr sidecar: `kubectl logs <pod-name> -c daprd`

2. **Collect Information:**
   - Exact error message
   - Pod status: `kubectl get pods`
   - Pod describe: `kubectl describe pod <pod-name>`

3. **Common Fixes:**
   - Restart deployments: `kubectl rollout restart deployment <name>`
   - Check secrets are correctly configured
   - Verify database connectivity

---

## Success Indicators

When everything is working correctly, you should see:

**Kubernetes Pods:**
- All pods in `Running` state
- No `CrashLoopBackOff` or `Error` states
- Health checks passing

**Frontend:**
- Sign up page loads
- Sign in page loads
- No errors in browser console
- Redirects to dashboard after login

**Backend:**
- Health endpoint returns healthy: `curl http://localhost:8000/health`
- Database shows connected
- No error messages in logs

**End-to-End:**
- Can create account
- Can log in
- Can access dashboard
- JWT authentication works
- Chat page loads
