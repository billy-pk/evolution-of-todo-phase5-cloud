<!--
Sync Impact Report:
- Version change: 3.0.0 → 4.0.0
- Modified principles:
  * Principle II: "Stateless Server Design" → EXPANDED (now includes Dapr sidecar patterns and event-driven architecture)
  * Principle VI: "Extensibility and Modularity" → EXPANDED (added microservices and event-driven communication requirements)
  * Principle VII: "Infrastructure as Code" → EXPANDED (added Dapr components, Redpanda configurations)
  * Principle IX: "Local-First Cloud Development" → EXPANDED (added Redpanda Docker, OKE deployment targets)
- Added sections:
  * New Principle X: "Event-Driven Architecture" (Pub/Sub, loose coupling, event streaming via Redpanda)
  * New Principle XI: "Cloud Portability via Dapr" (Building blocks abstraction, vendor independence)
  * New Principle XII: "Observability and Operational Excellence" (Logging, metrics, health checks, distributed tracing)
  * Phase 5 Technology Stack section (Redpanda, Dapr, OKE, microservices)
  * Event Topics and Communication Patterns section
  * Microservices Architecture section
  * Dapr Building Blocks Requirements section
- Modified sections:
  * Architecture Strategy: Added event-driven layer and Dapr abstraction
  * Development Workflow: Added Dapr development and event-driven testing steps
  * Quality Gates: Added event streaming validation, Dapr health checks, microservices coordination tests
  * Documentation Requirements: Added Dapr component documentation, event schema definitions
- Removed sections: None (Phase 5 builds on Phase 4)
- Templates requiring updates:
  ✅ plan-template.md: No update required (generic template, constitution check adapts)
  ✅ spec-template.md: No update required (generic template)
  ✅ tasks-template.md: No update required (generic template)
- Ratification date: 2025-12-10 (original)
- Last amended: 2026-01-06 (Phase 5 event-driven, cloud-native, Dapr-based architecture)
- Breaking changes: MAJOR version bump due to new architectural paradigm (event-driven microservices)
-->

# Evolution of Todo - Phase V Constitution
## Advanced Cloud-Native, Event-Driven & Dapr-Enabled Deployment

## Core Principles

### I. Conversational Interface Primary (NON-NEGOTIABLE)

**Rule**: All task management operations MUST be accessible through conversational interface.

- Users interact with tasks via natural language chat
- AI agent interprets user intent and executes operations
- No traditional UI forms or buttons for task CRUD
- Conversational interface is the primary interaction model

**Rationale**: Phase 3 established conversational AI as the primary interface. Phase 5 preserves this core functionality while transforming the backend into event-driven microservices.

### II. Stateless Server Design (NON-NEGOTIABLE)

**Rule**: All services, pods, and Dapr sidecars MUST be fully stateless with event-driven communication.

- No in-memory session storage allowed in any service
- Chat endpoint MUST reconstruct context from the database on every request
- All services MUST be stateless and store all state in PostgreSQL or state store
- Each request MUST be independently processable with JWT
- Pods MUST be horizontally scalable without sticky sessions or affinity requirements
- Pod restart, scaling, or relocation events MUST NOT disrupt functionality
- Services MUST communicate asynchronously via events (Pub/Sub) whenever possible
- Dapr sidecars MUST be stateless and rely on external state stores

**Rationale**: Stateless design is fundamental for cloud-native microservices. Combined with event-driven patterns, it enables unlimited horizontal scaling, resilience, and Kubernetes orchestration across multiple nodes and availability zones.

### III. Security First

**Rule**: User isolation, authentication, and secrets management MUST be enforced at every boundary including event streams.

- All API requests MUST include JWT: `Authorization: Bearer <token>`
- User isolation MUST be enforced for:
  - Tasks (database and MCP tools)
  - Conversations (database)
  - Messages (database)
  - Events (user_id in event payload)
- All services MUST verify task ownership using `user_id` before operations
- No hard-coded secrets or tokens allowed
- Secrets MUST be managed via:
  - Kubernetes Secrets (local development)
  - Dapr Secret Store (production)
  - Environment variables (external injection)
- Container images MUST NOT contain sensitive data
- Event payloads MUST NOT contain sensitive credentials
- Redpanda Cloud credentials MUST be stored in Dapr Secret Store

**Rationale**: Multi-user, event-driven systems require strict isolation at every layer. JWT provides standardized authentication. Dapr Secret Store provides cloud-portable secrets management. Events must carry user context for downstream services to enforce isolation.

### IV. Single Source of Truth

**Rule**: All task data MUST reside in a single PostgreSQL database with consistent access patterns.

- Tasks are stored in the `tasks` table (Neon PostgreSQL)
- All services (Chat API, Recurring Task Service, Notification Service, Audit Service) query the same database
- No data duplication or synchronization logic allowed between services
- Event-driven updates MUST NOT create eventual consistency issues for core task data
- Database connection strings MUST be externalized via Kubernetes Secrets or Dapr State Store configuration
- State changes MUST be persisted to database first, then emitted as events

**Rationale**: A single database prevents inconsistency and race conditions. Events are notifications of changes, not the source of truth. Database-first persistence ensures reliability even if event delivery fails.

### V. Test-Driven Development

**Rule**: Tests MUST be written before implementation for new functionality, including event-driven flows.

- Write tests for MCP tools before implementing them
- Write integration tests for event producers and consumers before implementation
- Write contract tests for event schemas before producing events
- Write deployment validation tests for Kubernetes and Dapr components
- Tests MUST fail initially (Red phase)
- Implementation MUST make tests pass (Green phase)
- Refactor only after tests pass
- Event-driven flows MUST have end-to-end tests (produce event → verify consumer action)

**Rationale**: TDD ensures requirements are clear, code is testable, and regressions are caught early. Event-driven systems are complex; tests prevent integration failures and ensure event contracts are honored.

### VI. Extensibility and Modularity

**Rule**: Architecture MUST support future phases without breaking changes, and components MUST be containerized and independently deployable as microservices.

- Components MUST be modular and independently deployable as containers
- Frontend and backend boundaries MUST remain clean with well-defined APIs
- Each microservice MUST have its own Dockerfile, Helm chart, and Dapr component manifests
- No architectural decisions that block future phases
- Configuration MUST be externalized (no hard-coded hostnames, ports, or secrets)
- Services MUST communicate via documented patterns:
  - **Asynchronous**: Dapr Pub/Sub (event-driven, preferred for state changes)
  - **Synchronous**: Dapr Service Invocation or REST APIs (when immediate response required)
  - **Tool-based**: MCP protocol (for AI agent tool execution)
- Event schemas MUST be versioned and backward-compatible
- Service boundaries MUST align with business capabilities (task management, notifications, audit, etc.)
- Each microservice MUST own its data access patterns but share the single database

**Rationale**: The Evolution of Todo project is multi-phase. Each phase must build a solid foundation for the next without requiring rewrites. Microservices architecture with event-driven communication enables independent scaling, deployment, and evolution of services. Dapr abstraction ensures cloud portability.

### VII. Infrastructure as Code (NON-NEGOTIABLE)

**Rule**: All deployment configurations MUST be version-controlled and declarative, including Dapr components and event streaming infrastructure.

- Dockerfiles MUST define container build steps for all microservices
- Helm charts MUST define Kubernetes resources (Deployments, Services, ConfigMaps, Secrets)
- Dapr component YAML files MUST define building blocks (Pub/Sub, State Store, Jobs, Secrets)
- Dapr component configurations MUST be environment-specific:
  - **Local**: Redpanda Docker (single-node, no auth), PostgreSQL State Store
  - **Cloud**: Redpanda Cloud (SASL/SSL secured), same State Store with cloud credentials
- Kubernetes manifests MUST be generated from templates (via Helm or Kustomize)
- No manual `kubectl` or `dapr` commands for production deployments; use `helm install` or `helm upgrade`
- Infrastructure changes MUST be reviewed via pull requests
- Deployment configurations MUST be testable and reproducible across environments
- Event streaming configurations (Redpanda topics, retention policies) MUST be declarative

**Rationale**: Infrastructure as Code ensures consistency, auditability, and repeatability. Version-controlled Dapr components and event streaming configurations enable environment parity, rollback, and collaboration. Declarative Dapr components ensure application code remains unchanged between local and cloud deployments.

### VIII. AI-Assisted DevOps (RECOMMENDED)

**Rule**: AI-powered tools SHOULD be used for container operations, Kubernetes orchestration, and diagnostics.

- Use Gordon (Docker AI Agent) for intelligent Dockerfile generation and optimization
- Use kubectl-ai for natural language Kubernetes operations
- Use kagent for cluster diagnostics and troubleshooting
- AI tools SHOULD accelerate development but MUST NOT replace understanding of underlying systems
- Generated configurations MUST be reviewed and validated before deployment

**Rationale**: AI-assisted tools accelerate development and reduce errors by providing intelligent suggestions and automating repetitive tasks. However, human oversight remains critical for production systems.

### IX. Local-First Cloud Development (NON-NEGOTIABLE)

**Rule**: All deployments MUST work on local Minikube clusters with Redpanda Docker before cloud deployment.

- Development workflow MUST use Minikube for local Kubernetes testing
- Local event streaming MUST use Redpanda Docker (single-node, no authentication required)
- Cloud deployment MUST target Oracle Kubernetes Engine (OKE) with Redpanda Cloud (SASL/SSL secured)
- Services MUST be accessible via NodePort on Minikube (frontend: 30080, backend: 30081)
- Dapr MUST run in both environments (Minikube and OKE) with identical building blocks
- Helm charts MUST support both local and cloud environments via values files
- No cloud-specific dependencies that prevent local testing
- Developers MUST be able to run the full stack locally without cloud access
- Local and cloud environments MUST have feature parity (same microservices, same event-driven behavior)

**Rationale**: Local-first development reduces costs, increases iteration speed, and ensures developers can work offline. Minikube with Redpanda Docker provides a production-like event-driven environment for testing. Dapr abstraction ensures identical behavior between local and cloud deployments.

### X. Event-Driven Architecture (NON-NEGOTIABLE)

**Rule**: Services MUST communicate asynchronously via events for state changes, using database-first persistence pattern.

- All task state changes MUST publish events to Redpanda topics via Dapr Pub/Sub
- Event topics MUST be logically organized: `task-events` (CRUD), `reminders` (scheduling), `task-updates` (UI sync)
- Database writes MUST occur first, then events MUST be published (database-first pattern)
- Events MUST NOT be the source of truth; they are notifications of changes already persisted
- Event payloads MUST include: event_type, task_id, user_id, task_data (JSON), timestamp (ISO8601)
- Event consumers MUST be idempotent and handle duplicate events gracefully
- Event consumers MUST handle out-of-order events without corrupting state
- Services MUST remain loosely coupled; producers MUST NOT depend on specific consumers
- Event schemas MUST be defined using JSON Schema and versioned
- Failed event delivery MUST retry with exponential backoff and dead-letter topics

**Rationale**: Event-driven architecture enables loose coupling, independent scaling, and asynchronous processing. Database-first pattern ensures consistency and reliability even if event delivery fails. Redpanda provides Kafka-compatible event streaming with lower operational complexity. Events enable new services (notifications, audit, WebSocket updates) without modifying existing code.

### XI. Cloud Portability via Dapr (NON-NEGOTIABLE)

**Rule**: Application code MUST be cloud-agnostic using Dapr building blocks; ONLY Dapr component YAML MUST change between environments.

- Application code MUST call Dapr APIs (Pub/Sub, State Store, Jobs, Secrets, Service Invocation)
- Application code MUST NEVER call vendor-specific SDKs (Kafka, Redpanda, AWS, Azure, GCP)
- Dapr component YAML files MUST define environment-specific configurations (local vs cloud)
- Switching environments MUST require ONLY changing Dapr component YAML files
- Dapr sidecars MUST be co-located with every microservice as separate containers in the same pod
- Dapr building blocks MUST abstract infrastructure:
  - **Pub/Sub**: Redpanda (local Docker or Cloud)
  - **State Store**: PostgreSQL (Neon)
  - **Jobs API**: Scheduled tasks and reminders
  - **Secrets**: Kubernetes Secrets (local) or cloud provider secrets (OKE)
  - **Service Invocation**: Inter-service synchronous calls with retries and timeouts
- No vendor lock-in; switching from Redpanda to Kafka or AWS Kinesis MUST require only Dapr YAML changes

**Rationale**: Dapr provides vendor-agnostic abstraction over cloud services, enabling true portability. Application code remains unchanged when moving from local Minikube to Oracle OKE or other cloud providers. This reduces technical debt, simplifies testing, and prevents vendor lock-in.

### XII. Observability and Operational Excellence (RECOMMENDED)

**Rule**: All microservices SHOULD implement structured logging, metrics, health checks, and distributed tracing for production readiness.

- All services SHOULD emit structured JSON logs (timestamp, level, service_name, user_id, trace_id, message)
- All services SHOULD expose Prometheus-compatible metrics endpoints (/metrics)
- All services MUST implement Kubernetes health probes:
  - **Liveness**: Service is running (returns 200 OK)
  - **Readiness**: Service is ready to accept traffic (database connected, Dapr healthy)
- All services SHOULD include distributed tracing headers (trace_id, span_id) for request correlation
- Event consumers SHOULD log event processing (received, processed, failed) with event_id and user_id
- Dapr sidecars SHOULD be configured for observability (metrics, logging, tracing)
- Production deployments SHOULD aggregate logs and metrics in centralized systems (optional: Prometheus, Grafana, Loki)
- Alert thresholds SHOULD be defined for critical errors (event delivery failures, database unavailability, high latency)

**Rationale**: Observability is critical for debugging distributed microservices in production. Structured logging enables correlation across services. Health probes enable Kubernetes to automatically restart unhealthy pods. Metrics enable capacity planning and performance optimization. Distributed tracing helps diagnose latency issues across service boundaries.

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

### Phase 5 Additions (Event-Driven Microservices)

- **Event Streaming**: Redpanda (Kafka-compatible, Docker for local, Cloud for production)
- **Distributed Application Runtime**: Dapr 1.14+ with building blocks (Pub/Sub, State Store, Jobs, Secrets, Service Invocation)
- **Microservices Architecture**: 6 services (Backend API, Notification, Recurring Task, Audit, WebSocket, Frontend)
- **Event-Driven Communication**: Pub/Sub pattern via Dapr (async state changes)
- **Cloud Deployment**: Oracle Kubernetes Engine (OKE) with Redpanda Cloud
- **Observability**: Structured logging (JSON), Prometheus metrics, health probes (liveness/readiness)
- **Advanced Features**: Recurring tasks, due dates, reminders, priorities, tags, search/filter
- **Secrets Management**: Dapr Secret Store (cloud) or Kubernetes Secrets (local)

### Deployment Components (Phase 4)

- **Frontend Container**: Next.js production build in Node.js Alpine image
- **Backend Container**: FastAPI + Uvicorn in Python 3.13 slim image
- **MCP Server Container**: FastMCP server in Python 3.13 slim image
- **Frontend Helm Chart**: Deployment, Service, ConfigMap for frontend
- **Backend Helm Chart**: Deployment, Service, ConfigMap, Secrets for backend
- **Database**: External PostgreSQL (Neon) accessed via connection string in Secret

### Deployment Components (Phase 5)

- **Backend API Service**: Existing FastAPI + MCP Server, now with Dapr sidecar and event publishing
- **Notification Service**: Python microservice with Dapr sidecar, subscribes to `reminders` topic
- **Recurring Task Service**: Python microservice with Dapr sidecar, subscribes to `task-events` topic
- **Audit Logging Service**: Python microservice with Dapr sidecar, subscribes to `task-events` topic
- **WebSocket Broadcast Service**: Python/FastAPI microservice with Dapr sidecar, subscribes to `task-updates` topic
- **Frontend**: Existing Next.js application (no changes, consumes backend API)
- **Redpanda**: Event streaming platform (Docker locally, Cloud in production)
- **Dapr Runtime**: Sidecar containers co-located with each microservice
- **Dapr Components**: YAML configurations for Pub/Sub, State Store, Jobs, Secrets (environment-specific)
- **Database**: Shared Neon PostgreSQL (single source of truth for all microservices)

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

### System Boundaries (Phase 5 Event-Driven Deployment)

**Development (6+ processes - Phase 5)**:
- Frontend: `npm run dev` (port 3000)
- Backend API: `uvicorn main:app --reload` (port 8000) + Dapr sidecar
- MCP Server: `python server.py` (port 8001)
- Notification Service: `python notification_service.py` + Dapr sidecar
- Recurring Task Service: `python recurring_task_service.py` + Dapr sidecar
- Audit Service: `python audit_service.py` + Dapr sidecar
- WebSocket Service: `uvicorn websocket_service:app --reload` (port 8002) + Dapr sidecar
- Redpanda: Docker container (port 9092)

**Containerized Deployment (6 microservices - Phase 5)**:
- Frontend Pod: Next.js container (NodePort 30080)
- Backend API Pod: FastAPI + MCP Server + Dapr sidecar (NodePort 30081)
- Notification Service Pod: Python service + Dapr sidecar (ClusterIP)
- Recurring Task Service Pod: Python service + Dapr sidecar (ClusterIP)
- Audit Service Pod: Python service + Dapr sidecar (ClusterIP)
- WebSocket Service Pod: FastAPI WebSocket + Dapr sidecar (NodePort 30082)
- Redpanda: Managed service (Docker locally, Cloud in production)

**Event-Driven Request Flow (Phase 5)**:
1. User accesses frontend via `http://minikube-ip:30080`
2. User sends chat message "Create a task: Weekly team meeting, due next Monday, reminder 1 hour before"
3. Frontend calls backend chat endpoint at `http://backend-service:8000/api/{user_id}/chat`
4. Backend validates JWT, reconstructs conversation from database
5. Backend OpenAI Agent invokes MCP `add_task` tool with: title, description, due_date, reminder, recurrence="weekly", priority="normal", tags=["work"]
6. MCP tool writes task to PostgreSQL database (single source of truth)
7. MCP tool publishes event to Dapr Pub/Sub: `task-events` topic with event_type="task.created"
8. Dapr Pub/Sub forwards event to Redpanda
9. Event consumers subscribe and process asynchronously:
   - **Audit Service**: Logs task creation event to audit_log table
   - **Recurring Task Service**: Stores recurrence rule for future generation
   - **Notification Service**: Schedules reminder via Dapr Jobs API (1 hour before due date)
   - **WebSocket Service**: Broadcasts task creation to connected frontend clients for live UI updates
10. Chat response returns to frontend with task confirmation
11. When reminder time triggers, Dapr Jobs API invokes Notification Service
12. Notification Service publishes event to `reminders` topic, delivers notification to user
13. When user marks task complete via chat or UI, MCP tool writes completion to database, publishes `task.completed` event
14. Recurring Task Service receives event, generates next instance (next Monday), publishes `task.created` event for new instance

### Multi-Server Coordination

**Phase 3/4: Three servers must run simultaneously (Development)**:
1. Frontend (port 3000): `cd frontend && npm run dev`
2. Backend (port 8000): `cd backend && uvicorn main:app --reload`
3. MCP Server (port 8001): `cd backend/tools && python server.py`

**Phase 5: Six+ microservices must run simultaneously (Development)**:
1. Frontend (port 3000): `cd frontend && npm run dev`
2. Backend API (port 8000): `cd backend && dapr run --app-id backend-api --app-port 8000 -- uvicorn main:app --reload`
3. MCP Server (port 8001): `cd backend/tools && python server.py`
4. Notification Service: `cd services/notification && dapr run --app-id notification-service -- python notification_service.py`
5. Recurring Task Service: `cd services/recurring-task && dapr run --app-id recurring-task-service -- python recurring_task_service.py`
6. Audit Service: `cd services/audit && dapr run --app-id audit-service -- python audit_service.py`
7. WebSocket Service (port 8002): `cd services/websocket && dapr run --app-id websocket-service --app-port 8002 -- uvicorn websocket_service:app --reload`
8. Redpanda: `docker run -p 9092:9092 redpandadata/redpanda:latest`

**Phase 5: Six pods must run simultaneously (Kubernetes)**:
1. Frontend Pod: Managed by frontend Deployment (NodePort 30080)
2. Backend API Pod: FastAPI + MCP + Dapr sidecar (NodePort 30081)
3. Notification Service Pod: Python + Dapr sidecar (ClusterIP)
4. Recurring Task Service Pod: Python + Dapr sidecar (ClusterIP)
5. Audit Service Pod: Python + Dapr sidecar (ClusterIP)
6. WebSocket Service Pod: FastAPI + Dapr sidecar (NodePort 30082)

**Critical**: All components must be running for full functionality:
- **Phase 3/4**: Three components required for chat functionality
- **Phase 5**: Six microservices + Redpanda required for event-driven features (recurring tasks, reminders, audit, WebSocket updates)

## Development Workflow

### Feature Development Process (Extended for Phase 5)

1. **Specification**: Create or update feature spec in `specs/<feature>/spec.md`
2. **Planning**: Generate implementation plan in `specs/<feature>/plan.md`
3. **Tasks**: Generate task list in `specs/<feature>/tasks.md`
4. **Implementation**: Follow Red-Green-Refactor cycle
5. **Event Schema Design**: Define event payloads using JSON Schema in `specs/<feature>/contracts/events/`
6. **Dapr Component Configuration**: Create/update Dapr component YAML files for local and cloud environments
7. **Containerization**: Create/update Dockerfiles and Helm charts for new microservices
8. **Local Deployment**: Deploy to Minikube with Redpanda Docker and validate event flow
9. **Validation**: Run tests (unit, integration, contract, end-to-end), verify acceptance criteria
10. **Integration**: Verify multi-microservice coordination, event delivery, and idempotency

### Quality Gates (Extended for Phase 5)

- All PRs MUST pass linting and type checking
- All tests MUST pass before merge (unit, integration, contract, end-to-end)
- No decrease in test coverage
- Manual verification that chat functionality works end-to-end (local development)
- Container images MUST build successfully without errors
- Helm charts MUST validate with `helm lint`
- Services MUST be accessible on Minikube via NodePort
- Verify statelessness: scale pods up/down and ensure functionality persists
- Verify multi-pod coordination: all pods healthy and communicating
- **NEW**: Event schemas MUST validate against JSON Schema definitions
- **NEW**: Event streaming MUST work: produce event → verify consumer processes within 2 seconds
- **NEW**: Dapr components MUST be healthy: `dapr components -k` shows all components loaded
- **NEW**: Idempotency MUST be enforced: replay event → verify no duplicate processing
- **NEW**: Database-first pattern MUST be verified: database write succeeds even if event publish fails
- **NEW**: Health probes MUST pass: liveness and readiness checks return 200 OK for all microservices
- **NEW**: Microservices coordination MUST work: end-to-end test (create recurring task → mark complete → verify next instance generated)

### Documentation Requirements

- ADRs (Architecture Decision Records) MUST be created for significant decisions
- PHRs (Prompt History Records) MUST be created for AI-assisted development sessions
- API contracts MUST be documented in `specs/<feature>/contracts/`
- Database schema changes MUST be documented with migration scripts
- Dockerfiles MUST include comments explaining multi-stage build steps
- Helm charts MUST include README.md with deployment instructions
- Kubernetes resources MUST include annotations describing purpose
- **NEW**: Event schemas MUST be documented in `specs/<feature>/contracts/events/` using JSON Schema
- **NEW**: Dapr component YAML files MUST include comments explaining configuration (local vs cloud)
- **NEW**: Microservice README files MUST document: purpose, subscribed topics, published topics, Dapr dependencies, health endpoints
- **NEW**: Event flow diagrams MUST show end-to-end event propagation for complex features (e.g., recurring task generation)

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

**Version**: 4.0.0 | **Ratified**: 2025-12-10 | **Last Amended**: 2026-01-06

**Change Log**:
- **4.0.0** (2026-01-06): MAJOR - Phase 5 Event-Driven Microservices Architecture
  - ADDED: Principle X - Event-Driven Architecture (Pub/Sub, database-first pattern, Redpanda, event schemas)
  - ADDED: Principle XI - Cloud Portability via Dapr (building blocks abstraction, vendor independence)
  - ADDED: Principle XII - Observability and Operational Excellence (structured logging, metrics, health probes, tracing)
  - EXPANDED: Principle II - Stateless Server Design (added Dapr sidecars, event-driven communication, horizontal scaling)
  - EXPANDED: Principle III - Security First (added event stream security, Dapr Secret Store requirements)
  - EXPANDED: Principle IV - Single Source of Truth (added database-first event pattern, event-driven consistency)
  - EXPANDED: Principle V - Test-Driven Development (added event-driven testing, contract tests, idempotency tests)
  - EXPANDED: Principle VI - Extensibility and Modularity (added microservices communication patterns, event schema versioning)
  - EXPANDED: Principle VII - Infrastructure as Code (added Dapr component YAML, Redpanda configurations, environment-specific deployments)
  - EXPANDED: Principle IX - Local-First Cloud Development (added Redpanda Docker, OKE deployment target, Dapr in both environments)
  - UPDATED: Architecture Strategy with Phase 5 additions (Redpanda, Dapr, 6 microservices, event-driven communication)
  - UPDATED: Deployment Components with Phase 5 microservices (Backend API, Notification, Recurring Task, Audit, WebSocket, Frontend)
  - ADDED: System Boundaries (Phase 5 Event-Driven Deployment) with 14-step event-driven request flow
  - UPDATED: Multi-Server Coordination (6+ microservices for Phase 5, including Redpanda and Dapr)
  - UPDATED: Development Workflow with event schema design, Dapr component configuration, event flow validation
  - UPDATED: Quality Gates with event streaming validation, Dapr health checks, idempotency enforcement, microservices coordination tests
  - UPDATED: Documentation Requirements with event schemas, Dapr component documentation, microservice README templates, event flow diagrams
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
