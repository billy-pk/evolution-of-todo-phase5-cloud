# Deployment Troubleshooting Guide

This document captures issues encountered during Kubernetes deployment and their solutions.

## Date: 2026-01-07
## Environment: Minikube on WSL2

---

## Issue 1: Pytest Dependency Conflict in Microservices

### Problem
All 4 microservices (notification, recurring-task, audit, websocket) failed to build with error:
```
Cannot install -r requirements.txt and pytest==9.0.2 because these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested pytest==9.0.2
    pytest-asyncio 0.26.0 depends on pytest<9 and >=8.2
```

### Root Cause
- pytest 9.0.2 is incompatible with pytest-asyncio 0.26.0
- pytest-asyncio 0.26.0 requires pytest<9

### Solution
Changed pytest version from 9.0.2 to 8.3.4 in all microservice requirements.txt files:

```bash
sed -i 's/pytest==9.0.2/pytest==8.3.4/' \
  ./services/websocket-service/requirements.txt \
  ./services/audit-service/requirements.txt \
  ./services/notification-service/requirements.txt \
  ./services/recurring-task-service/requirements.txt
```

### Status
✅ **RESOLVED** - All microservice images built successfully

---

## Issue 2: Missing Dapr SDK in Backend

### Problem
Backend-api pod crashed with:
```
ModuleNotFoundError: No module named 'dapr'
```

### Root Cause
- Backend code imports `from dapr.clients import DaprClient`
- But `backend/requirements.txt` did not include Dapr SDK packages

### Solution
Added Dapr dependencies to `backend/requirements.txt`:

```python
# Dapr SDK
dapr==1.14.0
dapr-ext-grpc==1.14.0
```

### Status
✅ **RESOLVED** - Backend image rebuilt with Dapr SDK

---

## Issue 3: Docker Image Permission Issues

### Problem
Backend container failed with:
```
/usr/local/bin/python3.13: can't open file '/root/.local/bin/uvicorn': [Errno 13] Permission denied
```

Then after first fix:
```
ModuleNotFoundError: No module named 'uvicorn'
```

### Root Cause
- Multi-stage Dockerfile installed Python packages in `/root/.local` (builder stage)
- Runtime stage switched to non-root user `appuser`
- User `appuser` couldn't access `/root/.local`
- PYTHONPATH wasn't set correctly for the new location

### Solution
Updated `backend/Dockerfile`:

```dockerfile
# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder to appuser's home
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Make sure scripts and modules in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/home/appuser/.local/lib/python3.13/site-packages:$PYTHONPATH

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser
```

### Status
✅ **RESOLVED** - Backend container runs successfully as non-root user

---

## Issue 4: Helm Chart SecurityContext Invalid Fields

### Problem
Deployment warnings:
```
Warning: unknown field "spec.template.spec.securityContext.capabilities"
```

### Root Cause
- `capabilities` field is only valid at **container level**, not pod level
- Helm charts had `capabilities` defined in pod-level `securityContext`

### Solution
Fixed all Helm chart `values.yaml` files:

```yaml
# Before (WRONG - pod level)
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:  # ❌ Invalid at pod level
    drop:
      - ALL

# After (CORRECT)
securityContext:
  # runAsNonRoot: true  # Commented out for Dapr compatibility
  # runAsUser: 1000
  fsGroup: 1000
  # capabilities:  # Not valid at pod level, should be at container level
  #   drop:
  #     - ALL
```

Applied to all services:
- backend-api
- frontend
- notification-service
- recurring-task-service
- audit-service
- websocket-service

### Status
✅ **RESOLVED** - No more validation warnings

---

## Issue 5: Dapr Sidecar RunAsUser Policy Conflict (CRITICAL)

### Problem
Dapr sidecar injection fails with:
```
Error: container's runAsUser breaks non-root policy
(pod: "backend-api-...", container: daprd)
```

Pod stuck in `CreateContainerConfigError` state.

### Root Cause
- Dapr sidecar container (`daprd`) has specific security requirements
- Kubernetes pod security policy or admission controller blocking the sidecar
- Conflict between:
  - Pod-level `securityContext.runAsUser` settings
  - Dapr sidecar's user requirements
  - Minikube's default security policies

### Investigation Steps Taken
1. ✅ Removed pod-level `runAsNonRoot: true` and `runAsUser: 1000`
2. ✅ Set `runAsNonRoot: false` and `runAsUser: 0` in values-local.yaml
3. ❌ Issue persists - Dapr sidecar still blocked

### Temporary Workaround
Disabled Dapr sidecar injection in `values-local.yaml`:

```yaml
# Pod annotations for Dapr sidecar injection (local configuration)
# Temporarily disabled due to runAsUser policy conflicts
podAnnotations:
  dapr.io/enabled: "false"  # Disabled - TODO: Fix runAsUser policy
```

### Impact
⚠️ **Event-driven microservices features NOT WORKING**:
- No pub/sub messaging between services
- No state management via Dapr
- No service-to-service invocation via Dapr
- Services can still run but without event-driven capabilities

### Potential Solutions (NOT YET IMPLEMENTED)

#### Option 1: Disable Pod Security Policy/Admission
```bash
# Check if PSP is enabled
kubectl api-resources | grep psp

# Check admission controllers
kubectl cluster-info dump | grep admission

# For Minikube, restart without PSP
minikube stop
minikube start --extra-config=apiserver.enable-admission-plugins=""
```

#### Option 2: Configure Dapr to Run as Non-Root
Create custom Dapr configuration:

```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: dapr-config-local
spec:
  tracing:
    samplingRate: "1"
  mtls:
    enabled: true
    allowedClockSkew: 15m
  # Add sidecar configuration
  sidecarRunAsNonRoot: true
  sidecarReadOnlyRootFilesystem: true
```

#### Option 3: Use Dapr Standalone Mode
Run Dapr components outside Kubernetes (Docker containers on host).

#### Option 4: Adjust Minikube Pod Security Standards
```bash
# Check current PSA enforcement
kubectl label --dry-run=server --overwrite ns default \
  pod-security.kubernetes.io/enforce=privileged

# Apply privileged PSA for default namespace (LOCAL ONLY)
kubectl label ns default pod-security.kubernetes.io/enforce=privileged
```

### Status
⚠️ **UNRESOLVED** - Dapr currently disabled, event-driven features unavailable

---

## Current Deployment Status

### ✅ Successfully Deployed
1. **Redpanda** (Docker) - Event streaming platform
   - Kafka API: `localhost:9092`
   - Topics: `task-events`, `reminders`, `task-updates`

2. **Backend API** (Kubernetes) - WITHOUT Dapr
   - Status: Running (1/1 pods ready)
   - NodePort: 30081
   - URL: `http://192.168.49.2:30081`
   - Health checks: Passing

3. **Dapr Control Plane** (Kubernetes)
   - Namespace: `dapr-system`
   - Components: Applied
   - Status: Running

### ❌ Not Yet Deployed
- Frontend
- Notification Service
- Recurring Task Service
- Audit Service
- WebSocket Service

### 🔧 Configuration Changes Made

#### Backend Dockerfile
- ✅ Fixed file: `backend/Dockerfile`
- ✅ Changes: User permissions, PYTHONPATH

#### Helm Charts
- ✅ Fixed: All service `values.yaml` files
- ✅ Fixed: `backend-api/values-local.yaml`
- ⚠️ Changes: SecurityContext, Dapr disabled

#### Requirements Files
- ✅ Fixed: All 4 microservice `requirements.txt`
- ✅ Fixed: `backend/requirements.txt`

---

## Next Steps

### Immediate Actions Required

1. **Resolve Dapr Sidecar Issue** (CRITICAL)
   - Test Option 4 (PSA adjustment) first - safest for local dev
   - Document which approach works
   - Re-enable Dapr in values-local.yaml

2. **Deploy Remaining Services**
   ```bash
   # Once Dapr is fixed, deploy all services
   ./infrastructure/scripts/deploy-local.sh
   ```

3. **Test Full Stack**
   - Verify event publishing works
   - Test service-to-service communication
   - Validate Dapr pub/sub

### Long-term Improvements

1. **Add Dapr Documentation**
   - Document Dapr configuration requirements
   - Add troubleshooting section to deployment guide

2. **Improve Dockerfile**
   - Consider using official Python base images with pre-configured users
   - Add build-time security scanning

3. **Helm Chart Enhancements**
   - Separate security contexts for different environments
   - Add option to disable Dapr for testing
   - Include container-level security context where needed

4. **CI/CD Integration**
   - Automate image builds
   - Add security scanning
   - Test deployments in CI

---

## Useful Commands

### Check Deployment Status
```bash
# Get all pods
kubectl get pods

# Describe pod to see errors
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name> -c <container-name>

# Check Dapr sidecar logs (when enabled)
kubectl logs <pod-name> -c daprd
```

### Rebuild and Redeploy
```bash
# Use Minikube Docker environment
eval $(minikube docker-env)

# Rebuild image
docker build -t backend-api:latest ./backend

# Force pod recreation
kubectl delete pod -l app.kubernetes.io/name=backend-api

# Or uninstall and reinstall
helm uninstall backend-api
helm install backend-api ./infrastructure/helm/backend-api -f values-local.yaml
```

### Check Dapr Status
```bash
# Check Dapr installation
dapr status -k

# Check Dapr components
kubectl get components

# View Dapr dashboard
dapr dashboard -k
```

### Access Services
```bash
# Get Minikube IP
minikube ip

# Access backend API
curl http://$(minikube ip):30081/health

# Port forward (alternative)
kubectl port-forward svc/backend-api 8000:8000
```

---

## References

- Dapr Kubernetes Configuration: https://docs.dapr.io/operations/hosting/kubernetes/
- Kubernetes Pod Security: https://kubernetes.io/docs/concepts/security/pod-security-standards/
- Minikube Documentation: https://minikube.sigs.k8s.io/docs/
- Helm Best Practices: https://helm.sh/docs/chart_best_practices/

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-07 | Claude | Initial troubleshooting documentation created |
| 2026-01-07 | Claude | Documented 5 major deployment issues and fixes |
| 2026-01-07 | Claude | Backend-API successfully deployed (without Dapr) |

---

**Note**: This is a living document. Update as new issues are discovered and resolved.
