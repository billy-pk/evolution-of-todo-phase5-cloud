---
id: "0001"
stage: "green"
feature: "005-event-driven-microservices"
title: "Backend API Helm Chart Implementation (T105-T110)"
date: "2026-01-07"
model: "claude-sonnet-4.5"
status: "completed"
tags: ["helm", "kubernetes", "backend-api", "dapr", "deployment", "infrastructure"]
---

# Prompt History Record: Backend API Helm Chart Implementation

## Prompt

Implement tasks T105 to T110 for Phase V Event-Driven Microservices:

**Tasks:**
- T105: Create backend-api Helm chart structure in infrastructure/helm/backend-api/
- T106: Create backend-api deployment template with Dapr sidecar annotations
- T107: Create backend-api service template (NodePort 30081)
- T108: Create backend-api configmap template
- T109: Create values-local.yaml overrides for Minikube
- T110: Create values-cloud.yaml overrides for Oracle Kubernetes Engine (OKE)

**Context:**
- Phase V transforms the monolithic app into event-driven microservices using Dapr, Redpanda, and Kubernetes
- Backend API is a FastAPI application with MCP server integration
- Deployment targets: Local (Minikube with Redpanda Docker) and Cloud (OKE with Redpanda Cloud)
- Dapr sidecar required for Pub/Sub, State Store, and Jobs API
- Security: No hardcoded secrets, use Kubernetes Secrets
- Stateless microservices for horizontal scaling

## Response

Successfully implemented all 6 tasks (T105-T110) creating a production-ready Helm chart for the Backend API microservice.

### Files Created

**Chart Structure:**
1. `infrastructure/helm/backend-api/Chart.yaml` - Chart metadata (v1.0.0)
2. `infrastructure/helm/backend-api/values.yaml` - Default configuration values
3. `infrastructure/helm/backend-api/.helmignore` - Helm ignore patterns
4. `infrastructure/helm/backend-api/README.md` - Comprehensive documentation

**Templates:**
5. `infrastructure/helm/backend-api/templates/_helpers.tpl` - Reusable template helpers
6. `infrastructure/helm/backend-api/templates/deployment.yaml` - Deployment with Dapr sidecar annotations
7. `infrastructure/helm/backend-api/templates/service.yaml` - Service (NodePort/ClusterIP)
8. `infrastructure/helm/backend-api/templates/configmap.yaml` - Application configuration
9. `infrastructure/helm/backend-api/templates/secrets.yaml` - Secrets for sensitive data (DATABASE_URL, BETTER_AUTH_SECRET, OPENAI_API_KEY)

**Environment-Specific Values:**
10. `infrastructure/helm/backend-api/values-local.yaml` - Minikube overrides (NodePort 30081, debug logging, reduced resources)
11. `infrastructure/helm/backend-api/values-cloud.yaml` - OKE overrides (ClusterIP, 2 replicas, autoscaling, production resources)

### Key Features Implemented

**Dapr Integration:**
- Pod annotations for Dapr sidecar injection (`dapr.io/enabled: "true"`)
- Configurable app ID, port, protocol, and log level
- Separate Dapr component paths for local vs cloud (`/dapr-components/local` vs `/dapr-components/cloud`)

**Security:**
- Kubernetes Secrets for sensitive data (DATABASE_URL, BETTER_AUTH_SECRET, OPENAI_API_KEY)
- Base64 encoding in secrets.yaml
- Hardened security context for production (runAsNonRoot: true, drop ALL capabilities)
- Relaxed security for local debugging

**High Availability:**
- Configurable replica count (1 for local, 2+ for cloud)
- Horizontal Pod Autoscaling (HPA) enabled in cloud (70% CPU threshold, 2-10 replicas)
- Pod Disruption Budget for cloud deployments
- Liveness and readiness probes (GET /health)

**Resource Management:**
- Local: 100m CPU request, 512Mi memory limit (Minikube-friendly)
- Cloud: 500m CPU request, 1Gi memory limit (production workload)

**Environment Parity:**
- Identical application code between local and cloud
- Only Dapr component YAMLs and values files differ
- Local uses Redpanda Docker (no auth), cloud uses Redpanda Cloud (SASL/SSL)

**Configuration Management:**
- ConfigMap for non-sensitive application config (APP_NAME, ENVIRONMENT, DAPR_PUBSUB_NAME)
- Environment variables for runtime configuration (DATABASE_URL, CORS_ORIGINS, LOG_LEVEL)
- Override values via `--set-string` during `helm install`

**Validation:**
- Helm chart passes `helm lint` validation
- All templates use proper Helm template syntax
- Comprehensive README with installation instructions

### Deployment Examples

**Local (Minikube):**
```bash
helm install backend-api ./backend-api -f values-local.yaml \
  --set-string env.DATABASE_URL="postgresql://..." \
  --set-string env.BETTER_AUTH_SECRET="secret" \
  --set-string env.OPENAI_API_KEY="sk-..."
```

**Cloud (OKE):**
```bash
helm install backend-api ./backend-api -f values-cloud.yaml \
  --set-string env.DATABASE_URL="postgresql://..." \
  --set-string env.BETTER_AUTH_SECRET="secret" \
  --set-string env.OPENAI_API_KEY="sk-..." \
  --set image.repository="<region>.ocir.io/<tenancy>/backend-api" \
  --set image.tag="v1.0.0"
```

### Constitution Compliance

✅ **Principle II (Stateless Server Design)**: Deployment supports horizontal scaling without sticky sessions
✅ **Principle III (Security First)**: No hardcoded secrets, uses Kubernetes Secrets
✅ **Principle VII (Infrastructure as Code)**: All deployment configs version-controlled in Helm templates
✅ **Principle IX (Local-First Cloud Development)**: Identical code, environment-specific values files
✅ **Principle XI (Cloud Portability via Dapr)**: Application code unchanged, only Dapr components differ

### Next Steps

- T111-T114: Create Helm charts for microservices (notification, recurring-task, audit, websocket)
- T115-T119: Create Helm chart for frontend (Next.js, no Dapr sidecar)
- T120-T123: Create deployment scripts (deploy-local.sh, deploy-cloud.sh)

## Artifacts

- **Helm Chart**: `infrastructure/helm/backend-api/` (11 files)
- **Documentation**: README.md with installation and troubleshooting guides
- **Validation**: Passes `helm lint` with 0 errors
- **Tasks Updated**: tasks.md marks T105-T110 as completed

## Status

✅ **COMPLETED** - All 6 tasks implemented and validated
