# Backend API Helm Chart

Helm chart for deploying the Evolution of Todo Backend API (FastAPI + MCP + Dapr) to Kubernetes.

## Overview

This Helm chart deploys the Backend API microservice with the following features:
- FastAPI application with MCP server integration
- Dapr sidecar for event-driven architecture (Pub/Sub, State Store, Jobs API)
- Health probes (liveness and readiness)
- Configurable resource limits and autoscaling
- Support for both local (Minikube) and cloud (OKE) deployments

## Prerequisites

- Kubernetes 1.28+
- Helm 3.x
- Dapr 1.14+ installed on the cluster
- Container image built and available (local or OCIR)

## Installation

### Local Development (Minikube)

1. Build the Docker image locally:
   ```bash
   cd backend
   docker build -t backend-api:latest .
   ```

2. Install the Helm chart with local values:
   ```bash
   helm install backend-api ./backend-api -f values-local.yaml \
     --set-string env.DATABASE_URL="postgresql://user:pass@host:5432/db" \
     --set-string env.BETTER_AUTH_SECRET="your-secret-key" \
     --set-string env.OPENAI_API_KEY="sk-..."
   ```

3. Access the backend API:
   ```bash
   # Via NodePort (http://localhost:30081)
   curl http://localhost:30081/health
   ```

### Cloud Deployment (Oracle Kubernetes Engine)

1. Push the Docker image to Oracle Container Registry (OCIR):
   ```bash
   docker tag backend-api:latest <region>.ocir.io/<tenancy>/backend-api:v1.0.0
   docker push <region>.ocir.io/<tenancy>/backend-api:v1.0.0
   ```

2. Create OCIR pull secret:
   ```bash
   kubectl create secret docker-registry ocir-secret \
     --docker-server=<region>.ocir.io \
     --docker-username='<tenancy>/<username>' \
     --docker-password='<auth-token>'
   ```

3. Install the Helm chart with cloud values:
   ```bash
   helm install backend-api ./backend-api -f values-cloud.yaml \
     --set-string env.DATABASE_URL="postgresql://user:pass@host:5432/db" \
     --set-string env.BETTER_AUTH_SECRET="your-secret-key" \
     --set-string env.OPENAI_API_KEY="sk-..." \
     --set image.repository="<region>.ocir.io/<tenancy>/backend-api" \
     --set image.tag="v1.0.0"
   ```

## Configuration

### Values Files

- **values.yaml**: Default configuration (base values)
- **values-local.yaml**: Overrides for Minikube development
- **values-cloud.yaml**: Overrides for OKE production deployment

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of pod replicas | `1` (local), `2` (cloud) |
| `image.repository` | Docker image repository | `backend-api` |
| `image.tag` | Docker image tag | `latest` |
| `service.type` | Kubernetes service type | `NodePort` (local), `ClusterIP` (cloud) |
| `service.nodePort` | NodePort number (local only) | `30081` |
| `env.DATABASE_URL` | PostgreSQL connection string | `""` (must be set) |
| `env.BETTER_AUTH_SECRET` | Better Auth JWT secret | `""` (must be set) |
| `env.OPENAI_API_KEY` | OpenAI API key | `""` (must be set) |
| `dapr.enabled` | Enable Dapr sidecar | `true` |
| `dapr.logLevel` | Dapr log level | `debug` (local), `info` (cloud) |
| `autoscaling.enabled` | Enable horizontal autoscaling | `false` (local), `true` (cloud) |
| `resources.limits.cpu` | CPU limit | `500m` (local), `1000m` (cloud) |
| `resources.limits.memory` | Memory limit | `512Mi` (local), `1Gi` (cloud) |

### Secrets Management

The chart creates a Kubernetes Secret with the following keys:
- `database-url`: PostgreSQL connection string
- `better-auth-secret`: Better Auth JWT signing secret
- `openai-api-key`: OpenAI API key

**Best Practice**: Use Kubernetes external secrets management (e.g., Oracle Vault, HashiCorp Vault) for production deployments.

## Dapr Integration

The chart configures Dapr sidecar injection via pod annotations:
- `dapr.io/enabled: "true"` - Enable Dapr sidecar
- `dapr.io/app-id: "backend-api"` - Dapr app ID
- `dapr.io/app-port: "8000"` - Application port
- `dapr.io/log-level: "debug"/"info"` - Dapr logging level

Dapr components (Pub/Sub, State Store, Jobs API) are configured separately in `specs/005-event-driven-microservices/contracts/dapr-components/`.

## Health Checks

The chart configures Kubernetes health probes:
- **Liveness Probe**: `GET /health` (initial delay: 30s, period: 10s)
- **Readiness Probe**: `GET /health` (initial delay: 10s, period: 5s)

## Upgrading

```bash
# Upgrade with new image version
helm upgrade backend-api ./backend-api -f values-cloud.yaml \
  --set image.tag="v1.1.0" \
  --reuse-values
```

## Uninstalling

```bash
helm uninstall backend-api
```

## Troubleshooting

### Check pod status
```bash
kubectl get pods -l app.kubernetes.io/name=backend-api
```

### View logs
```bash
# Application logs
kubectl logs -l app.kubernetes.io/name=backend-api -c backend-api

# Dapr sidecar logs
kubectl logs -l app.kubernetes.io/name=backend-api -c daprd
```

### Check Dapr components
```bash
dapr components -k
```

### Test health endpoint
```bash
# Port-forward to pod
kubectl port-forward service/backend-api 8000:8000

# Test health endpoint
curl http://localhost:8000/health
```

## Chart Structure

```
backend-api/
├── Chart.yaml                    # Chart metadata
├── values.yaml                   # Default values
├── values-local.yaml             # Local Minikube overrides
├── values-cloud.yaml             # OKE cloud overrides
├── .helmignore                   # Helm ignore patterns
├── README.md                     # This file
└── templates/
    ├── _helpers.tpl              # Template helpers
    ├── deployment.yaml           # Deployment with Dapr sidecar
    ├── service.yaml              # Service (NodePort or ClusterIP)
    ├── configmap.yaml            # ConfigMap for app config
    └── secrets.yaml              # Secrets for sensitive data
```

## License

MIT
