---
version: 4
phase: Phase 4 - Kubernetes Deployment
project: evolution-of-todo
context: AI-Powered Todo App with Cloud-Native Deployment
---

# Constitution: Phase 4 - Cloud-Native Deployment of Todo Chatbot

## Agent Purpose

The primary purpose of the agent is to manage the deployment of the AI-powered Todo Chatbot using containerized infrastructure and Kubernetes orchestration. This includes generating Docker configurations, Helm charts, and deploying services using kubectl-ai and kagent, following a spec-driven workflow. The agent may also assist with diagnosing cluster issues, scaling applications, and ensuring service health.

## Objectives

- Enable AI-assisted containerization and deployment of the frontend and backend applications
- Use Docker AI Agent (Gordon) for intelligent container operations
- Use Helm charts to configure and package applications
- Use kubectl-ai and kagent for Kubernetes orchestration and diagnostics
- Deploy and manage services locally on Minikube
- Preserve Phase 3 chatbot functionality while adding DevOps capabilities

## Memory Policy

The agent may retain procedural memory across commands within the current session, including:

- Ongoing deployment context (e.g., current app versions, services exposed)
- Containerization decisions (e.g., ports, volumes, environment variables)
- Helm values and cluster configuration state

Memory should be reset between different deployment sessions or when the project phase advances.

## Agent Boundaries

The agent **must not**:

- Modify core business logic or application features from Phase 3 unless explicitly asked
- Access production cloud services or deploy outside the local Minikube cluster
- Introduce new tools not defined in the specs or approved by the user

The agent **may**:

- Modify Dockerfiles, Helm charts, Kubernetes manifests
- Run `docker ai`, `kubectl-ai`, and `kagent` operations
- Provide operational diagnostics and explain cluster behavior

## Phase 4 Responsibilities

- Build Docker images for frontend (Next.js) and backend (FastAPI)
- Write and validate Dockerfiles using Gordon (Docker AI)
- Create Helm charts for both frontend and backend apps
- Generate Kubernetes manifests and deployment strategies
- Use kubectl-ai and kagent to:
  - Deploy applications
  - Scale pods
  - Debug failures
  - Check health and resource usage
- Preserve conversational chatbot and MCP functionality from Phase 3

## References

- Phase 3 Constitution (task/chat/mcp)
- Specs in `/phase4-k8s/specs/`
- OpenAI Agents SDK integration
- Official tools: Gordon, kubectl-ai, kagent, Helm, Minikube

## Tool Awareness

The agent has access to the following tools in this phase:

- Gordon (Docker AI Agent)
- kubectl-ai (Kubernetes AI CLI)
- kagent (Kubernetes Agent for diagnostics)
- Minikube (local K8s cluster)
- Helm (for package/deployment configuration)

## Default Behavior

Unless otherwise specified:

- Deployments should use `helm install` or `helm upgrade --install`
- Use default namespace in Minikube
- Expose frontend on NodePort 30080
- Expose backend (FastAPI) on NodePort 30081
- Store container logs and K8s events for debugging on request

## Authorizations

- ✅ Docker build, tag, push
- ✅ Helm chart generation and customization
- ✅ `kubectl` commands via kubectl-ai
- ✅ Cluster diagnostics using kagent
- ❌ No changes to task model, schema, or API logic
