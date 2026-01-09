# Phase 5: Event-Driven Microservices Todo Application

A full-stack todo application with **event-driven microservices architecture** - leveraging DAPR for distributed application building and Apache Kafka for asynchronous messaging between services.

## 🌟 Overview

This is **Phase 5** of the Evolution of Todo project - a complete architectural transformation to an **event-driven microservices architecture**:

- ✅ **Event-driven design** - Services communicate via asynchronous events
- ✅ **Distributed architecture** - Multiple independent services with DAPR sidecars
- ✅ **Message streaming** - Apache Kafka for event streaming and processing
- ✅ **Scalable services** - Independent scaling of each service
- ✅ **Resilient design** - Fault tolerance and circuit breaker patterns

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User                                          │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ HTTP Requests
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│   Next.js Frontend (Port 3000)                                          │
│   - React UI Components                                                 │
│   - Better Auth (JWT)                                                   │
│   - API Integration                                                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ REST API Calls
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│   Backend API Service (Port 8000)                                       │
│   - FastAPI application                                                 │
│   - JWT middleware (JWKS validation)                                    │
│   - DAPR sidecar for service invocation                                 │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ DAPR Service Invocation / Pub/Sub Events
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────────┐
│ Audit Service   │ │ Notification     │ │ Recurring Task      │
│ (DAPR Sidecar)  │ │ Service          │ │ Service             │
│                 │ │ (DAPR Sidecar)   │ │ (DAPR Sidecar)      │
│ - Log events    │ │ - Send alerts    │ │ - Schedule tasks    │
│ - Track changes │ │ - Email/SMS      │ │ - Recurring ops     │
└─────────────────┘ └──────────────────┘ └─────────────────────┘
         ↑                    ↑                    ↑
         └────────────────────┼────────────────────┘
                              ↓
                   ┌─────────────────────────────┐
                   │ Apache Kafka Cluster        │
                   │ - Event Streaming           │
                   │ - Topic Management          │
                   │ - Message Persistence       │
                   └─────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────────┐
│ WebSocket       │ │ State Store       │ │ Secret Store        │
│ Service         │ │ (PostgreSQL)     │ │ (Encrypted)         │
│ (DAPR Sidecar)  │ │ - Tasks          │ │ - API Keys          │
│ - Real-time     │ │ - Conversations  │ │ - Database Creds    │
│ - Notifications │ │ - Messages       │ │ - Auth Secrets      │
└─────────────────┘ └──────────────────┘ └─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose**
- **Kubernetes** (Minikube, Kind, or similar)
- **DAPR CLI** installed
- **Node.js 18+** (frontend)
- **Python 3.13+** (backend services)
- **Apache Kafka** (or Redpanda)

### 1. Clone Repository
```bash
git clone <repository-url>
cd phase5-cloud
```

### 2. Initialize DAPR
```bash
# Install DAPR runtime
dapr init

# Verify installation
dapr --version
```

### 3. Setup Backend Services
```bash
# Navigate to backend
cd backend

# Install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Configure .env
cp .env.example .env
# Edit .env with your credentials

# Run migrations
python scripts/migrate.py
```

### 4. Start Services with DAPR
```bash
# Terminal 1: Start backend API with DAPR
cd backend
dapr run --app-id backend-api --app-port 8000 --dapr-http-port 3500 -- uvicorn main:app --reload --port 8000

# Terminal 2: Start audit service with DAPR
cd services/audit-service
dapr run --app-id audit-service --app-port 8002 --dapr-http-port 3501 -- python audit_service.py

# Terminal 3: Start notification service with DAPR
cd services/notification-service
dapr run --app-id notification-service --app-port 8003 --dapr-http-port 3502 -- python -m uvicorn main:app --reload --port 8003

# Terminal 4: Start recurring task service with DAPR
cd services/recurring-task-service
dapr run --app-id recurring-task-service --app-port 8004 --dapr-http-port 3503 -- python recurring_task_service.py

# Terminal 5: Start WebSocket service with DAPR
cd services/websocket-service
dapr run --app-id websocket-service --app-port 8005 --dapr-http-port 3504 -- python websocket_service.py
```

### 5. Setup Frontend
```bash
cd frontend
npm install

# Configure .env.local
cp .env.local.example .env.local
# Edit .env.local with your credentials

# Start frontend
npm run dev
```

### 6. Access Application
- **Frontend**: http://localhost:3000
- **Chat Interface**: http://localhost:3000/chat
- **Backend API Docs**: http://localhost:8000/docs
- **DAPR Dashboard**: http://localhost:8080

## 📁 Project Structure

```
phase5-cloud/
├── backend/                    # Main backend API service
│   ├── main.py                # App entry point
│   ├── routes/
│   │   └── chat.py           # Chat endpoint
│   ├── routes/
│   │   └── tasks.py          # Task endpoints
│   ├── services/
│   │   └── agent.py          # OpenAI Agent
│   ├── models.py             # SQLModel models
│   ├── middleware.py         # JWT auth
│   ├── dapr/                 # DAPR configuration
│   │   └── components/       # Component definitions
│   └── README.md
├── frontend/                  # Next.js frontend
│   ├── app/
│   │   ├── (auth)/           # Auth pages
│   │   ├── (dashboard)/
│   │   │   └── chat/         # Chat interface
│   │   └── api/auth/         # Better Auth
│   ├── components/
│   │   └── Navbar.tsx
│   ├── lib/
│   │   ├── api.ts            # API client
│   │   └── auth.ts           # Auth config
│   └── README.md
├── services/                  # Microservices
│   ├── audit-service/         # Audit logging service
│   ├── notification-service/  # Notification service
│   ├── recurring-task-service/ # Recurring task scheduler
│   └── websocket-service/     # Real-time communication
├── infrastructure/            # Infrastructure as Code
│   ├── k8s/                  # Kubernetes manifests
│   ├── helm/                 # Helm charts for each service
│   └── scripts/              # Deployment scripts
├── specs/                     # Feature specifications
│   └── 005-event-driven-microservices/
├── history/prompts/           # Development history (PHRs)
├── CLAUDE.md                  # AI development guide
└── README.md                  # This file
```

## 🔄 Event Flows

### Task Creation Event Flow
```
User creates task → Frontend → Backend API → DAPR Publish Event → Kafka Topic
→ Audit Service (logs event) → Notification Service (sends alert)
→ Recurring Task Service (checks for recurring patterns)
```

### Task Update Event Flow
```
User updates task → Frontend → Backend API → DAPR Publish Event → Kafka Topic
→ Audit Service (logs change) → WebSocket Service (broadcasts update)
→ Notification Service (sends update notification)
```

### Task Completion Event Flow
```
User completes task → Frontend → Backend API → DAPR Publish Event → Kafka Topic
→ Audit Service (logs completion) → Notification Service (confirms completion)
→ Recurring Task Service (checks for recurring tasks)
```

## 🔧 Technology Stack

### Frontend
- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **TailwindCSS**
- **Better Auth** (JWT authentication)

### Backend Services
- **Python 3.13**
- **FastAPI** (async web framework)
- **SQLModel** (ORM)
- **DAPR** (Distributed Application Runtime)
- **Apache Kafka** (Event streaming)
- **Better Auth JWKS** (JWT validation)

### Infrastructure
- **Kubernetes** (Container orchestration)
- **Helm** (Package management)
- **Docker** (Containerization)
- **DAPR Sidecars** (Microservice building blocks)

### Database & State Management
- **Neon PostgreSQL** (serverless)
- **Redis** (Caching and pub/sub)
- **SQLModel Models**: Task, Conversation, Message, AuditLog

### Messaging & Events
- **Apache Kafka** (Event streaming)
- **DAPR Pub/Sub** (Message broker abstraction)
- **Event-Driven Architecture** (Loose coupling)

## 🔒 Security

- **JWT Authentication**: All requests require valid Bearer token
- **JWKS Validation**: Backend validates tokens against Better Auth JWKS endpoint
- **User Isolation**: All database queries filtered by authenticated `user_id`
- **DAPR Security**: Service-to-service authentication
- **Secret Stores**: Encrypted storage for sensitive data
- **Network Policies**: Kubernetes network isolation

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest                    # All tests
pytest tests/test_chat.py # Chat endpoint tests
pytest --cov=.            # With coverage

# Service-specific tests
cd services/audit-service
python -m pytest

cd services/notification-service
python -m pytest
```

### Frontend Tests
```bash
cd frontend
npm test                  # All tests
npm test -- chat          # Chat component tests
```

### DAPR Component Tests
```bash
# Test DAPR service invocation
dapr invoke --app-id backend-api --method health --verb GET

# Test pub/sub functionality
dapr publish --pubsub tasks --topic task-created --data '{"taskId": "123", "userId": "456"}'
```

## 📚 Documentation

- **Frontend Setup**: [frontend/README.md](frontend/README.md)
- **Backend Setup**: [backend/README.md](backend/README.md)
- **Service Setup**: [services/*/README.md](services/)
- **Infrastructure**: [infrastructure/README.md](infrastructure/)
- **AI Development Guide**: [CLAUDE.md](CLAUDE.md)
- **Feature Specs**: [specs/005-event-driven-microservices/](specs/005-event-driven-microservices/)
- **Development History**: [history/prompts/](history/prompts/)

## 🎯 Phase 5 Principles

Per [Constitution v5.0.0](.specify/memory/constitution.md):

1. **Event-Driven Architecture**: Services communicate asynchronously via events
2. **Loose Coupling**: Services are independently deployable and scalable
3. **Distributed Resilience**: Fault tolerance and graceful degradation
4. **Observability First**: Comprehensive monitoring and tracing
5. **Developer Productivity**: DAPR simplifies distributed system complexity

## 🔄 Migration from Phase 4

Phase 5 transforms the monolithic backend into event-driven microservices:

**Removed**:
- ❌ Monolithic backend service
- ❌ Direct service-to-service calls
- ❌ Single deployment unit

**Added**:
- ✅ DAPR for distributed application building
- ✅ Event-driven communication patterns
- ✅ Independent microservices (Audit, Notification, Recurring Task, WebSocket)
- ✅ Apache Kafka for event streaming
- ✅ Kubernetes-native deployment with Helm charts

## 🛠️ Development

### Running All Services with DAPR
```bash
# Terminal 1: Backend API
cd backend && dapr run --app-id backend-api --app-port 8000 --dapr-http-port 3500 -- uvicorn main:app --reload --port 8000

# Terminal 2: Audit Service
cd services/audit-service && dapr run --app-id audit-service --app-port 8002 --dapr-http-port 3501 -- python audit_service.py

# Terminal 3: Notification Service
cd services/notification-service && dapr run --app-id notification-service --app-port 8003 --dapr-http-port 3502 -- python -m uvicorn main:app --reload --port 8003

# Terminal 4: Recurring Task Service
cd services/recurring-task-service && dapr run --app-id recurring-task-service --app-port 8004 --dapr-http-port 3503 -- python recurring_task_service.py

# Terminal 5: WebSocket Service
cd services/websocket-service && dapr run --app-id websocket-service --app-port 8005 --dapr-http-port 3504 -- python websocket_service.py

# Terminal 6: Frontend
cd frontend && npm run dev
```

### Code Quality
```bash
# Backend
cd backend
black .           # Format
ruff check .      # Lint
mypy .            # Type check

# Frontend
cd frontend
npm run lint      # ESLint
npm run format    # Prettier
```

### DAPR Management
```bash
# Check DAPR status
dapr status -k

# View DAPR dashboard
dapr dashboard

# List running DAPR apps
dapr list
```

## 🚧 Troubleshooting

**DAPR sidecar not starting?**
- Ensure DAPR runtime is installed: `dapr init`
- Check DAPR logs: `dapr logs <app-id>`
- Verify component configurations in `backend/dapr/components/`

**Services can't communicate?**
- Check DAPR service invocation: `dapr invoke --app-id <target-app> --method <method>`
- Verify pub/sub components are properly configured
- Ensure Kafka/Redis connections are active

**Kafka connectivity issues?**
- Verify Kafka cluster is running
- Check Kafka component configuration in DAPR
- Confirm topic creation and permissions

**Authentication errors?**
- Verify `BETTER_AUTH_SECRET` matches in all service `.env` files
- Check `BETTER_AUTH_JWKS_URL` is accessible from all services
- Ensure JWT token is being propagated correctly between services

## 📝 License

MIT

## 🤝 Contributing

This is an educational project demonstrating Phase 5 event-driven microservices architecture. Contributions welcome!

## 🎓 Learning Resources

- **DAPR Documentation**: https://docs.dapr.io
- **Apache Kafka**: https://kafka.apache.org
- **Kubernetes**: https://kubernetes.io
- **Helm Charts**: https://helm.sh
- **Better Auth**: https://www.better-auth.com
- **Next.js App Router**: https://nextjs.org/docs