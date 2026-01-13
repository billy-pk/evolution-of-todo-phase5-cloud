# Dapr Troubleshooting Guide for Local Minikube Development

This document describes common Dapr issues encountered in local Minikube development and their solutions.

## Issue 1: mTLS Certificate Error

### Symptom
The Dapr sidecar (daprd) crashes with:
```
level=fatal msg="Fatal error from runtime: failed to retrieve the initial identity: error from sentry SignCertificate: rpc error: code = PermissionDenied desc = failed to get configuration\nno X509 SVID available"
```

### Root Cause
The `dapr-config-local` Configuration resource had `mtls.enabled: true` in the cluster, even though the intent was to disable mTLS for local development. Additionally:
1. Dapr Configuration requires specific fields (`controlPlaneTrustDomain`, `sentryAddress`) even when mTLS is disabled
2. The configuration must exist in the same namespace as the application pods (e.g., `default`)

### Solution
1. Update the Dapr Configuration to properly disable mTLS while including required fields:
   ```yaml
   spec:
     mtls:
       enabled: false  # Disabled for local development
       allowedClockSkew: 15m
       controlPlaneTrustDomain: cluster.local
       sentryAddress: dapr-sentry.dapr-system.svc.cluster.local:443
   ```

2. Apply the configuration to both `default` and `dapr-system` namespaces:
   ```bash
   kubectl apply -f infrastructure/k8s/dapr-config-local.yaml
   ```

3. Restart the deployment:
   ```bash
   kubectl rollout restart deployment/backend-api -n default
   ```

### Files Modified
- `/infrastructure/k8s/dapr-config-local.yaml` - Updated with correct mTLS configuration

---

## Issue 2: Duplicate Kubernetes SecretStore Component

### Symptom
```
level=error msg="Failed to init component kubernetes (secretstores.kubernetes/v1): component kubernetes already exists"
```

### Root Cause
Dapr 1.16+ automatically creates a built-in `kubernetes` secretstore component. Defining it manually in `secrets.yaml` causes a duplicate component error.

### Solution
Remove the explicit `kubernetes` secretstore component from the Dapr components. Dapr provides this component by default.

### Files Modified
- `/specs/005-event-driven-microservices/contracts/dapr-components/local/secrets.yaml` - Removed explicit kubernetes component

---

## Issue 3: Invalid Jobs Component Type

### Symptom
```
level=warning msg="Error processing component, daprd will exit gracefully: process component jobs error: incorrect type jobs.postgresql"
```

### Root Cause
`jobs.postgresql` is not a valid Dapr component type. The Dapr Jobs API uses the Scheduler service with an embedded etcd database - it does not require a separate component.

### Solution
Remove the invalid `jobs` component. The Dapr Scheduler service handles job storage internally.

Reference: https://docs.dapr.io/concepts/dapr-services/scheduler/

### Files Modified
- `/specs/005-event-driven-microservices/contracts/dapr-components/local/jobs.yaml` - Removed invalid component

---

## Issue 4: Kafka/Redpanda Connection from Minikube

### Symptom
```
level=error msg="Failed to init component pubsub (pubsub.kafka/v1): ... dial tcp: lookup redpanda on 10.96.0.10:53: server misbehaving"
```

### Root Cause
When Redpanda runs in Docker on the host (not in Kubernetes), pods cannot resolve the `redpanda` hostname inside the cluster.

### Solution
Create a Kubernetes Service with explicit Endpoints pointing to the host IP:

```yaml
# infrastructure/k8s/redpanda-host-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: redpanda
  namespace: default
spec:
  ports:
  - port: 9092
    targetPort: 9092
    name: kafka
---
apiVersion: v1
kind: Endpoints
metadata:
  name: redpanda
  namespace: default
subsets:
- addresses:
  - ip: 192.168.49.1  # host.minikube.internal IP
  ports:
  - port: 9092
    name: kafka
```

Apply:
```bash
kubectl apply -f infrastructure/k8s/redpanda-host-service.yaml
```

### Files Created
- `/infrastructure/k8s/redpanda-host-service.yaml` - Service to expose host Redpanda to Kubernetes

---

## Issue 5: PostgreSQL Statestore Timeout

### Symptom
```
level=error msg="Failed to init component statestore (state.postgresql/v1): ... failed to create metadata table: timeout: context deadline exceeded"
```

### Root Cause
Neon PostgreSQL has cold starts that can exceed the default timeout. The statestore initialization times out before the connection completes.

### Solution
Increase the timeout and add `ignoreErrors` to allow Dapr to continue if the statestore fails to initialize:

```yaml
spec:
  type: state.postgresql
  version: v1
  initTimeout: 120s  # Increased init timeout for Neon cold starts
  ignoreErrors: true  # Allow Dapr to continue if statestore fails
  metadata:
  - name: timeout
    value: "120"  # Increased for Neon PostgreSQL cold starts
```

### Files Modified
- `/specs/005-event-driven-microservices/contracts/dapr-components/local/statestore-postgresql.yaml`

---

## Verification Commands

### Check Pod Status
```bash
kubectl get pods -n default
```
Expected: All pods should show `2/2 Running` (app + daprd sidecar)

### Verify Dapr Security Initialization
```bash
kubectl logs <pod-name> -c daprd -n default | grep "Security"
```
Expected: `Security is initialized successfully`

### Check Dapr Components
```bash
kubectl get components -n default
```
Expected: `pubsub` and `statestore` components should be present

### View Dapr Configuration
```bash
kubectl get configuration -n default -o yaml
```

---

## Quick Fix Checklist

1. Apply correct Dapr configuration:
   ```bash
   kubectl apply -f infrastructure/k8s/dapr-config-local.yaml
   ```

2. Apply Redpanda host service:
   ```bash
   kubectl apply -f infrastructure/k8s/redpanda-host-service.yaml
   ```

3. Apply Dapr components:
   ```bash
   kubectl apply -f specs/005-event-driven-microservices/contracts/dapr-components/local/
   ```

4. Restart deployments:
   ```bash
   kubectl rollout restart deployment/backend-api -n default
   ```
