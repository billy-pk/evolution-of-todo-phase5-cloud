<!--
Sync Impact Report:
- Version change: 2.0.0 → 3.0.0
- Modified principles:
  * Principle II: "Stateless Server Design" → EXPANDED (now covers Kubernetes stateless pod requirements)
  * Principle VI: "Extensibility and Modularity" → EXPANDED (added containerization and orchestration requirements)
- Added sections:
  * New Principle VII: "Infrastructure as Code" (Dockerfiles, Helm charts, K8s manifests)
  * New Principle VIII: "AI-Assisted DevOps" (Gordon, kubectl-ai, kagent integration)
  * New Principle IX: "Local-First Cloud Development" (Minikube development workflow)
  * Phase 4 Technology Stack section
  * Phase 4 Deployment Components section
  * Multi-Server Deployment section
- Modified sections:
  * Architecture Strategy: Added containerization layer
  * Development Workflow: Added deployment validation steps
  * Quality Gates: Added cluster health checks
- Removed sections: None (Phase 4 builds on Phase 3)
- Templates requiring updates:
  ✅ plan-template.md: No update required (generic template, constitution check adapts)
  ✅ spec-template.md: No update required (generic template)
  ✅ tasks-template.md: No update required (generic template)
- Ratification date: 2025-12-10 (original)
- Last amended: 2025-12-24 (Phase 4 cloud-native deployment principles)
- Breaking changes: MAJOR version bump due to new architectural principles and deployment requirements
-->

# Evolution of Todo - Phase 4: Kubernetes Deployment Constitution

## Core Principles

### I. Conversational Interface Primary (NON-NEGOTIABLE)

**Rule**: All task management operations MUST be accessible through conversational interface.

- Users interact with tasks via natural language chat
- AI agent interprets user intent and executes operations
- No traditional UI forms or buttons for task CRUD
- Conversational interface is the primary interaction model

**Rationale**: Phase 3 established conversational AI as the primary interface. Phase 4 preserves this core functionality while adding cloud-native deployment capabilities.

### II. Stateless Server Design (NON-NEGOTIABLE)

**Rule**: All chat endpoints, MCP tools, and Kubernetes pods MUST be fully stateless.

- No in-memory session storage allowed
- Chat endpoint MUST reconstruct context from the database on every request
- MCP tools MUST be stateless and store all state in the database
- Each request MUST be independently processable with JWT and conversation ID
- Pods MUST be horizontally scalable without sticky sessions
- Pod restart or scaling events MUST NOT disrupt functionality

**Rationale**: Stateless design enables horizontal scaling, simplifies debugging, and is essential for Kubernetes orchestration. Stateless pods can be scaled, restarted, and moved without data loss.

### III. Security First

**Rule**: User isolation and authentication MUST be enforced at every boundary, including cluster boundaries.

- All chat requests MUST include JWT: `Authorization: Bearer <token>`
- User isolation MUST be enforced for:
  - Tasks
  - Conversations
  - Messages
- MCP tools MUST verify task ownership using `user_id` before any operation
- No hard-coded secrets or tokens allowed; use environment variables and Kubernetes secrets
- Container images MUST NOT contain sensitive data
- Secrets MUST be injected via Kubernetes Secret resources or ConfigMaps

**Rationale**: Multi-user systems require strict isolation to prevent data leaks. JWT provides standardized, stateless authentication that scales. Kubernetes secrets provide secure credential management.

### IV. Single Source of Truth

**Rule**: All task data MUST reside in a single database with consistent access patterns.

- Tasks are stored in the `tasks` table
- Chat interface operates directly on the database via MCP tools
- No data duplication or synchronization logic allowed
- All operations (chat, API) query the same database
- Database connection strings MUST be externalized via environment variables

**Rationale**: Multiple data sources create inconsistency, confusion, and maintenance burden. A single source of truth ensures reliability across all deployment environments.

### V. Test-Driven Development

**Rule**: Tests MUST be written before implementation for new functionality, including deployment configurations.

- Write tests for MCP tools before implementing them
- Write integration tests for chat endpoint before implementing it
- Write deployment validation tests for Kubernetes manifests
- Tests MUST fail initially (Red phase)
- Implementation MUST make tests pass (Green phase)
- Refactor only after tests pass

**Rationale**: TDD ensures requirements are clear, code is testable, and regressions are caught early. It enforces discipline and quality for both application code and infrastructure.

### VI. Extensibility and Modularity

**Rule**: Architecture MUST support future phases without breaking changes, and components MUST be containerized and independently deployable.

- Components MUST be modular and independently deployable as containers
- Frontend and backend boundaries MUST remain clean with well-defined APIs
- Each service MUST have its own Dockerfile and Helm chart
- No architectural decisions that block Phase 5 (Cloud-native scaling) or Phase 6 (Microservices)
- Configuration MUST be externalized (no hard-coded hostnames, ports, or secrets)
- Services MUST communicate via documented APIs (REST, gRPC, or MCP)

**Rationale**: The Evolution of Todo project is multi-phase. Each phase must build a solid foundation for the next without requiring rewrites. Containerization enables portability and cloud deployment.

### VII. Infrastructure as Code (NON-NEGOTIABLE)

**Rule**: All deployment configurations MUST be version-controlled and declarative.

- Dockerfiles MUST define container build steps for frontend and backend
- Helm charts MUST define Kubernetes resources (Deployments, Services, ConfigMaps, Secrets)
- Kubernetes manifests MUST be generated from templates (via Helm or Kustomize)
- No manual `kubectl` commands for production deployments; use `helm install` or `helm upgrade`
- Infrastructure changes MUST be reviewed via pull requests
- Deployment configurations MUST be testable and reproducible

**Rationale**: Infrastructure as Code ensures consistency, auditability, and repeatability. Version-controlled deployment configurations enable rollback, collaboration, and disaster recovery.

### VIII. AI-Assisted DevOps (RECOMMENDED)

**Rule**: AI-powered tools SHOULD be used for container operations, Kubernetes orchestration, and diagnostics.

- Use Gordon (Docker AI Agent) for intelligent Dockerfile generation and optimization
- Use kubectl-ai for natural language Kubernetes operations
- Use kagent for cluster diagnostics and troubleshooting
- AI tools SHOULD accelerate development but MUST NOT replace understanding of underlying systems
- Generated configurations MUST be reviewed and validated before deployment

**Rationale**: AI-assisted tools accelerate development and reduce errors by providing intelligent suggestions and automating repetitive tasks. However, human oversight remains critical for production systems.

### IX. Local-First Cloud Development (NON-NEGOTIABLE)

**Rule**: All deployments MUST work on local Minikube clusters before cloud deployment.

- Development workflow MUST use Minikube for local Kubernetes testing
- Services MUST be accessible via NodePort on Minikube (frontend: 30080, backend: 30081)
- Helm charts MUST support both local and cloud environments via values files
- No cloud-specific dependencies that prevent local testing
- Developers MUST be able to run the full stack locally without cloud access

**Rationale**: Local-first development reduces costs, increases iteration speed, and ensures developers can work offline. Minikube provides a production-like Kubernetes environment for testing.

## Architecture Strategy

### Technology Stack (Phase 3 Foundation)

- **Frontend**: Next.js App Router, TailwindCSS, React
- **Backend**: FastAPI, Python 3.13
- **Database**: SQLModel + Neon PostgreSQL
- **Authentication**: Better Auth with JWT
- **Chat UI**: OpenAI ChatKit (official React component)
- **AI Agent**: OpenAI Agents SDK (official SDK for agent logic)
- **Tool Layer**: MCP (Model Context Protocol) tools built with Official MCP SDK

### Phase 4 Additions (Cloud-Native Deployment)

- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes (via Minikube locally)
- **Package Management**: Helm charts for frontend and backend
- **AI DevOps Tools**: Gordon (Docker AI), kubectl-ai, kagent
- **Service Exposure**: NodePort (local), LoadBalancer/Ingress (cloud-ready)
- **Configuration Management**: Kubernetes ConfigMaps and Secrets

### Deployment Components (Phase 4)

- **Frontend Container**: Next.js production build in Node.js Alpine image
- **Backend Container**: FastAPI + Uvicorn in Python 3.13 slim image
- **MCP Server Container**: FastMCP server in Python 3.13 slim image
- **Frontend Helm Chart**: Deployment, Service, ConfigMap for frontend
- **Backend Helm Chart**: Deployment, Service, ConfigMap, Secrets for backend
- **Database**: External PostgreSQL (Neon) accessed via connection string in Secret

### System Boundaries (Phase 4 Deployment)

**Development (3 processes - Phase 3)**:
- Frontend: `npm run dev` (port 3000)
- Backend: `uvicorn main:app --reload` (port 8000)
- MCP Server: `python server.py` (port 8001)

**Containerized Deployment (3 containers - Phase 4)**:
- Frontend Pod: Next.js container exposed via NodePort 30080
- Backend Pod: FastAPI container exposed via NodePort 30081
- MCP Server Pod: FastMCP container accessible internally (ClusterIP)

**Request Flow (Containerized)**:
1. User accesses frontend via `http://minikube-ip:30080`
2. Frontend loads ChatKit component for conversational interface
3. User sends message via ChatKit
4. Frontend calls backend chat endpoint at `http://backend-service:8000/api/{user_id}/chat`
5. Backend validates JWT and reconstructs conversation context from database
6. Backend initializes OpenAI Agent with MCP tools
7. Agent connects to MCP server at `http://mcp-service:8001` via HTTP transport
8. MCP tools execute database operations with user isolation
9. Chat endpoint persists conversation state to database
10. Response streams back to frontend via ChatKit

### Multi-Server Coordination

**Three servers must run simultaneously (Development)**:
1. Frontend (port 3000): `cd frontend && npm run dev`
2. Backend (port 8000): `cd backend && uvicorn main:app --reload`
3. MCP Server (port 8001): `cd backend/tools && python server.py`

**Three pods must run simultaneously (Kubernetes)**:
1. Frontend Pod: Managed by frontend Deployment (NodePort 30080)
2. Backend Pod: Managed by backend Deployment (NodePort 30081)
3. MCP Server Pod: Managed by mcp-server Deployment (ClusterIP 8001)

**Critical**: All three components must be running for chat functionality to work in both development and containerized environments.

## Development Workflow

### Feature Development Process (Extended for Phase 4)

1. **Specification**: Create or update feature spec in `specs/<feature>/spec.md`
2. **Planning**: Generate implementation plan in `specs/<feature>/plan.md`
3. **Tasks**: Generate task list in `specs/<feature>/tasks.md`
4. **Implementation**: Follow Red-Green-Refactor cycle
5. **Containerization**: Create/update Dockerfiles and Helm charts
6. **Local Deployment**: Deploy to Minikube and validate
7. **Validation**: Run tests, verify acceptance criteria
8. **Integration**: Verify multi-container coordination

### Quality Gates (Extended for Phase 4)

- All PRs MUST pass linting and type checking
- All tests MUST pass before merge
- No decrease in test coverage
- Manual verification that chat functionality works end-to-end (local development)
- **NEW**: Container images MUST build successfully without errors
- **NEW**: Helm charts MUST validate with `helm lint`
- **NEW**: Services MUST be accessible on Minikube via NodePort
- **NEW**: Verify statelessness: scale pods up/down and ensure functionality persists
- **NEW**: Verify multi-pod coordination: all three pods healthy and communicating

### Documentation Requirements

- ADRs (Architecture Decision Records) MUST be created for significant decisions
- PHRs (Prompt History Records) MUST be created for AI-assisted development sessions
- API contracts MUST be documented in `specs/<feature>/contracts/`
- Database schema changes MUST be documented with migration scripts
- **NEW**: Dockerfiles MUST include comments explaining multi-stage build steps
- **NEW**: Helm charts MUST include README.md with deployment instructions
- **NEW**: Kubernetes resources MUST include annotations describing purpose

## Governance

### Amendment Process

1. Propose changes via pull request to `.specify/memory/constitution.md`
2. Document rationale and impact in PR description
3. Update `CONSTITUTION_VERSION` following semantic versioning:
   - MAJOR: Backward incompatible governance/principle removals or redefinitions
   - MINOR: New principle/section added or materially expanded guidance
   - PATCH: Clarifications, wording, typo fixes, non-semantic refinements
4. Update dependent templates and documentation
5. Obtain approval from project maintainers
6. Update `LAST_AMENDED_DATE` to date of merge

### Compliance

- All specifications MUST reference this constitution
- All implementations MUST be validated against these principles
- Use `/sp.analyze` to verify cross-artifact consistency
- Constitution supersedes conflicting guidance in other documents

### Version History

**Version**: 3.0.0 | **Ratified**: 2025-12-10 | **Last Amended**: 2025-12-24

**Change Log**:
- **3.0.0** (2025-12-24): MAJOR - Phase 4 Kubernetes deployment principles
  - ADDED: Principle VII - Infrastructure as Code (Dockerfiles, Helm, K8s manifests)
  - ADDED: Principle VIII - AI-Assisted DevOps (Gordon, kubectl-ai, kagent)
  - ADDED: Principle IX - Local-First Cloud Development (Minikube workflow)
  - EXPANDED: Principle II - Stateless Server Design (added pod statelessness requirements)
  - EXPANDED: Principle VI - Extensibility and Modularity (added containerization requirements)
  - UPDATED: Architecture Strategy with Phase 4 deployment components
  - UPDATED: Development Workflow with containerization and deployment steps
  - UPDATED: Quality Gates with container build and deployment validation
  - UPDATED: Documentation Requirements with Dockerfile and Helm chart documentation
  - ADDED: Multi-Server Deployment section (development vs containerized)
  - ADDED: Phase 4 Technology Stack section
- **2.0.0** (2025-12-15): MAJOR - Redefined Phase 3 as standalone conversational AI system
  - REMOVED: Backwards Compatibility principle (Phase 3 is not extending Phase 2)
  - REMOVED: All references to "Phase 2 REST API endpoints"
  - REMOVED: All references to "React UI components" and "task CRUD UI"
  - ADDED: Conversational Interface Primary principle
  - UPDATED: Stateless Server Design to cover MCP tools
  - UPDATED: Single Source of Truth to focus on database-centric design
  - UPDATED: Architecture Strategy to detail MCP tools and Official MCP SDK
  - UPDATED: New Components section with MCP Server details
- **1.0.1** (2025-12-10): Clarified Python version requirement (3.11+ → 3.13)
- **1.0.0** (2025-12-10): Initial constitution for Phase 3 based on CONSTITUTION.md requirements
