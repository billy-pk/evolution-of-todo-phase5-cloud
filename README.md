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

## 📖 How The Application Works

This section provides a comprehensive guide to understanding the complete data and event flows throughout the application.

### 🔐 User Authentication Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. USER SIGNS UP/LOGS IN                                                │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend (Better Auth)                                                   │
│ - Captures user credentials                                             │
│ - Sends POST to /api/auth/sign-in or /api/auth/sign-up                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Better Auth (Next.js API Route)                                         │
│ - Validates credentials against PostgreSQL                              │
│ - Generates EdDSA-signed JWT with user_id claim                        │
│ - Stores session in database                                            │
│ - Returns JWT token + session                                           │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend Stores                                                          │
│ - Session stored in browser (httpOnly cookie)                           │
│ - JWT extracted via authClient.token()                                  │
│ - Redirects to /chat or /tasks                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- JWT tokens are EdDSA-signed (not RS256)
- JWKS endpoint: `/api/auth/jwks` for public key verification
- Token includes `user_id` claim for authorization
- Session duration: 15 minutes (configurable)

---

### 💬 Chat-Based Task Management Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. USER SENDS CHAT MESSAGE: "Create a task: Buy groceries"              │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend (/chat page with ChatKit UI)                                   │
│ - Captures message from ChatKit React component                         │
│ - Extracts JWT from session: authClient.token()                        │
│ - POST /api/{user_id}/chat                                             │
│   Headers: { Authorization: "Bearer <JWT>" }                           │
│   Body: { message: "Create...", conversation_id: "abc123" }           │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend API - JWT Middleware                                             │
│ - Validates JWT signature against JWKS endpoint                         │
│ - Extracts user_id from JWT claims                                      │
│ - Verifies path user_id matches token user_id                          │
│ - Rejects if mismatch → 401 Unauthorized                               │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend API - Chat Endpoint (routes/chatkit.py)                         │
│ - Loads conversation history from PostgreSQL (last 50 messages)         │
│ - Initializes OpenAI Agent with MCP tools connection                   │
│ - Passes message + conversation context to Agent                        │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ OpenAI Agents SDK                                                        │
│ - Analyzes user intent: "create task"                                   │
│ - Decides to call add_task tool                                         │
│ - Makes HTTP request to MCP Server                                      │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server (FastMCP on port 8001)                                       │
│ - Receives CallToolRequest for add_task                                 │
│ - Validates input: user_id, title required                             │
│ - Checks idempotency cache (60-second window)                          │
│   → If duplicate: returns cached task (prevents duplicate creation)    │
│   → If new: proceeds with creation                                      │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server - Database Write                                              │
│ - Creates Task in PostgreSQL via SQLModel                               │
│   Fields: id, user_id, title, description, completed, created_at       │
│ - Commits transaction                                                    │
│ - Caches task data (user_id, title_lower) → (task_data, timestamp)    │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server - Event Publishing (Dapr Pub/Sub)                            │
│ - Generates event_id (UUID)                                             │
│ - Constructs event payload:                                             │
│   {                                                                      │
│     event_id, event_type: "task.created",                              │
│     user_id, task_data,                                                 │
│     metadata: { source: "mcp_tool" }                                   │
│   }                                                                      │
│ - DaprClient.publish_event() to "task-events" topic                    │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Dapr Sidecar (mcp-server pod)                                           │
│ - Receives publish request on localhost:3500                            │
│ - Forwards event to Redpanda broker (host.minikube.internal:9092)      │
│ - Topic: task-events, Partition: 0                                     │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Redpanda Broker (Kafka-compatible)                                      │
│ - Stores event in task-events topic                                     │
│ - Event persisted with offset tracking                                  │
│ - Notifies subscribed consumers                                         │
└──────────────┬───────────────┬──────────────┬────────────────────────────┘
              │               │              │
              ↓               ↓              ↓
   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
   │ Audit Service│  │ Notification │  │ Recurring Task   │
   │ (Subscribes) │  │ Service      │  │ Service          │
   └──────────────┘  └──────────────┘  └──────────────────┘
```

#### Parallel Event Processing

**Audit Service Flow:**
```
Dapr Sidecar (audit-service) polls Redpanda
    ↓
Receives task.created event
    ↓
POST /events/task-events (local to audit service)
    ↓
Audit Service processes event:
  - Checks for duplicate event_id (JSONB query)
  - If duplicate: skip (idempotent)
  - If new: create AuditLog record
    ↓
PostgreSQL: INSERT into audit_log table
  - event_type: task.created
  - task_id, user_id
  - details: full event payload (JSONB)
  - timestamp
    ↓
Returns 200 OK to Dapr (event acknowledged)
```

**Notification Service Flow:**
```
Dapr Sidecar (notification-service) polls Redpanda
    ↓
Receives task.created event
    ↓
POST /events/task-events (local to notification service)
    ↓
Notification Service processes event:
  - Checks task_data for notification triggers
  - If due_date exists: schedules reminder
  - Prepares notification payload
    ↓
Currently: Logs notification (Phase 5 - email/SMS in future)
    ↓
Returns 200 OK to Dapr (event acknowledged)
```

**Recurring Task Service Flow:**
```
Dapr Sidecar (recurring-task-service) polls Redpanda
    ↓
Receives task.created or task.completed event
    ↓
POST /events/task-events (local to recurring service)
    ↓
Recurring Task Service processes event:
  - If task has recurrence_rule:
    → Creates RecurrenceRule in database
    → Schedules next instance generation
  - If task completed with recurrence_rule:
    → Generates next recurring task instance
    → Publishes new task.created event
    ↓
Returns 200 OK to Dapr (event acknowledged)
```

---

### Agent Response Flow (Continued)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server Returns to OpenAI Agent                                      │
│ - Tool result: { status: "success", data: { id, title, ... } }         │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ OpenAI Agent Generates Response                                          │
│ - Uses tool result to construct natural language response               │
│ - Example: "I've created a task 'Buy groceries' for you."              │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend Chat Endpoint                                                    │
│ - Receives agent response                                               │
│ - Saves user message to PostgreSQL (messages table)                    │
│ - Saves assistant response to PostgreSQL                                │
│ - Returns streaming response to frontend                                │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend ChatKit UI                                                      │
│ - Receives streaming response                                           │
│ - Displays assistant message in chat                                    │
│ - Message appended to conversation                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Total Flow Duration:** ~2-5 seconds
- JWT validation: <100ms
- OpenAI API call: 1-3 seconds
- Database writes: <500ms
- Event publishing: <1 second (async)
- Event processing: 2-10 seconds (async, doesn't block response)

---

### 📋 Traditional REST API Task Management Flow

Users can also manage tasks via the traditional REST API (without chat):

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER CREATES TASK VIA UI FORM                                           │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend (/tasks page)                                                   │
│ - User fills TaskForm component                                         │
│ - POST /api/{user_id}/tasks                                            │
│   Headers: { Authorization: "Bearer <JWT>" }                           │
│   Body: { title, description, priority, tags, due_date }              │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend API - JWT Middleware → Validates user_id                        │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend API - Task Endpoint (Phase 5: via event publisher)              │
│ - Creates Task in PostgreSQL                                            │
│ - get_event_publisher() retrieves global EventPublisher instance       │
│ - If publisher exists:                                                  │
│     await publisher.publish_task_created(task_data, user_id)           │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ EventPublisher (services/event_publisher.py)                            │
│ - Generates event_id                                                     │
│ - DaprClient.publish_event(pubsub_name="pubsub",                       │
│                             topic_name="task-events",                   │
│                             data=event_payload)                         │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
                    [Same event flow as Chat]
                    Dapr → Redpanda → Services
```

---

### 🔄 Task Update Flow with Real-Time WebSocket Broadcasting

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER UPDATES TASK (changes title or marks as completed)                 │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend                                                                 │
│ - PATCH /api/{user_id}/tasks/{task_id}                                 │
│   Body: { completed: true } or { title: "New title" }                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Backend API                                                              │
│ - Loads task from database                                              │
│ - Stores previous_data (before update)                                  │
│ - Updates task in PostgreSQL                                            │
│ - Publishes TWO events:                                                 │
│   1. publish_task_updated() → task-events topic                        │
│   2. publish_task_update_for_websocket() → task-updates topic          │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Event Flow Splits                                                        │
└────────┬─────────────────────────────┬───────────────────────────────────┘
         │                             │
         ↓                             ↓
┌──────────────────────┐      ┌──────────────────────────────────┐
│ task-events topic    │      │ task-updates topic               │
│ - Audit Service      │      │ - WebSocket Service              │
│ - Notification Svc   │      │                                  │
└──────────────────────┘      └────────┬─────────────────────────┘
                                       │
                                       ↓
                        ┌──────────────────────────────────────────┐
                        │ WebSocket Service                        │
                        │ - Receives task update event             │
                        │ - Filters by user_id                     │
                        │ - Broadcasts to connected WebSocket      │
                        │   clients for that user                  │
                        └────────┬─────────────────────────────────┘
                                 │
                                 ↓
                        ┌──────────────────────────────────────────┐
                        │ Frontend - WebSocket Client              │
                        │ - Connected to ws://localhost:8005/ws    │
                        │ - Receives real-time update              │
                        │ - Updates task list without page refresh │
                        │ - Shows "Task updated" notification      │
                        └──────────────────────────────────────────┘
```

**Benefits:**
- Multiple browser tabs stay in sync
- Other users see updates in real-time (future: collaborative editing)
- No polling required - event-driven updates

---

### 🔁 Recurring Task Generation Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER CREATES RECURRING TASK: "Water plants every Monday"                │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server add_task tool                                                 │
│ - Creates Task with recurrence_rule: { frequency: "weekly", ... }      │
│ - Creates RecurrenceRule record in database                             │
│ - Publishes task.created event (includes recurrence metadata)          │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Recurring Task Service receives task.created event                      │
│ - Detects recurrence_rule in task_data                                  │
│ - Calculates next occurrence date                                       │
│ - Schedules job for next instance generation                            │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓ (User completes first instance)
┌──────────────────────────────────────────────────────────────────────────┐
│ User marks task as completed → task.completed event published           │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Recurring Task Service receives task.completed event                    │
│ - Checks if task has recurrence_rule                                    │
│ - Generates next task instance:                                         │
│   → New Task with same title, description, recurrence_rule             │
│   → New due_date calculated from recurrence pattern                    │
│   → Links to parent via recurrence_id                                  │
│ - Saves new task to PostgreSQL                                          │
│ - Publishes task.created event for new instance                        │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ New task appears in user's task list                                    │
│ - Audit Service logs the generation                                     │
│ - WebSocket broadcasts update (real-time)                               │
│ - User sees new task instance without refresh                           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Recurrence Patterns Supported:**
- Daily: "every day", "daily"
- Weekly: "every Monday", "weekly on Friday"
- Monthly: "first of every month", "monthly"
- Custom intervals: "every 3 days", "every 2 weeks"

---

### 🔔 Reminder Scheduling Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER CREATES TASK WITH REMINDER: "Meeting at 3pm - remind 1 hour before"│
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ MCP Server add_task tool with reminder                                   │
│ - Creates Task with due_date                                            │
│ - Calls reminder_service.create_reminder()                              │
│   → reminder_time = due_date - 1 hour                                   │
│   → Creates Reminder record in PostgreSQL                               │
│   → Calls schedule_reminder_job() with Dapr Jobs API                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Dapr Jobs API                                                            │
│ - Schedules job for reminder_time (ISO8601 timestamp)                   │
│ - Job payload: { reminder_id, task_id, user_id, task_title }           │
│ - Target: notification-service                                          │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓ (When reminder_time arrives)
┌──────────────────────────────────────────────────────────────────────────┐
│ Dapr invokes Notification Service                                       │
│ - POST /jobs/reminder (job execution endpoint)                          │
│ - Payload contains reminder details                                     │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Notification Service processes reminder                                 │
│ - Loads task details from database                                      │
│ - Sends notification via configured channel:                            │
│   → Email (SendGrid/SMTP)                                               │
│   → SMS (Twilio)                                                        │
│   → In-app notification (WebSocket)                                     │
│ - Publishes reminder.sent event                                         │
│ - Updates Reminder status to 'sent'                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 🔍 Audit Trail Query Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ADMIN/USER QUERIES AUDIT LOGS                                           │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Frontend or API Request                                                  │
│ - GET /api/{user_id}/audit-logs?task_id={task_id}                      │
│ - Or direct database query (admin tool)                                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL Query                                                         │
│ SELECT * FROM audit_log                                                  │
│ WHERE user_id = ? AND task_id = ?                                       │
│ ORDER BY timestamp DESC                                                  │
└──────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Results Show Complete Task History                                      │
│ - task.created (who, when, details)                                     │
│ - task.updated (what changed, previous values)                          │
│ - task.completed (when marked done)                                     │
│ - task.deleted (if deleted, by whom)                                    │
│                                                                          │
│ Each entry includes:                                                     │
│ - event_id (for correlation)                                            │
│ - event_type                                                            │
│ - user_id (who performed action)                                        │
│ - task_id                                                               │
│ - details (JSONB with full context)                                     │
│ - timestamp (when it happened)                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Use Cases:**
- Compliance: Track all changes for regulatory requirements
- Debugging: Understand why a task state changed
- Analytics: Analyze user behavior patterns
- Recovery: Restore deleted tasks from audit trail

---

### 🛡️ Idempotency Protection (Duplicate Prevention)

**Problem:** OpenAI Agents SDK can invoke MCP tools multiple times for a single user request.

**Solution:** Three-layer idempotency protection:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Layer 1: MCP Tool-Level Cache (60-second window)                        │
│ Location: backend/tools/server.py                                       │
│                                                                          │
│ _task_creation_cache = { (user_id, title_lower): (task_data, timestamp)}│
│                                                                          │
│ add_task() checks:                                                       │
│   cache_key = (user_id, title.strip().lower())                         │
│   if cache_key in cache AND age < 60 seconds:                          │
│       return cached_task (DUPLICATE DETECTED)                           │
│   else:                                                                  │
│       create task → cache result → return                               │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Event-ID Deduplication (Audit Service)                         │
│ Location: services/audit-service/audit_service.py                       │
│                                                                          │
│ write_audit_log() checks:                                                │
│   SELECT * FROM audit_log                                                │
│   WHERE details->>'event_id' = ?                                        │
│                                                                          │
│   if exists:                                                             │
│       skip processing (DUPLICATE EVENT)                                  │
│   else:                                                                  │
│       create audit log                                                   │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Dapr Pub/Sub At-Least-Once Delivery Handling                   │
│ Location: All event subscribers                                         │
│                                                                          │
│ Each service processes events idempotently:                              │
│ - Returns 200 OK even if event was already processed                    │
│ - Uses event_id for deduplication                                       │
│ - Prevents duplicate side effects (emails, notifications)               │
└──────────────────────────────────────────────────────────────────────────┘
```

**Example Log Output:**
```
MCP Server: ⚠️ DUPLICATE TASK CREATION DETECTED - Returning cached task
Audit Service: ⚠️ DUPLICATE EVENT DETECTED - Idempotent skip (event_id: abc123)
```

---

### 📊 Complete Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA PERSISTENCE LAYERS                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PostgreSQL (Neon - Single Source of Truth)                            │
│  ├── tasks            - All tasks (user_id, title, description, ...)  │
│  ├── conversations    - Chat conversations                             │
│  ├── messages         - Chat messages                                  │
│  ├── audit_log        - Immutable event history                        │
│  ├── recurrence_rules - Recurring task patterns                        │
│  ├── reminders        - Scheduled reminders                            │
│  ├── users            - User accounts (Better Auth)                    │
│  └── jwks             - JWT signing keys (Better Auth)                 │
│                                                                         │
│  Redpanda (Event Streaming - Kafka Compatible)                         │
│  ├── task-events      - Task lifecycle events (CRUD)                   │
│  ├── task-updates     - Real-time UI updates                           │
│  └── reminders        - Reminder notifications                         │
│                                                                         │
│  In-Memory Caches                                                       │
│  ├── MCP task cache   - 60s idempotency window                         │
│  └── ChatKit cache    - HTTP-level idempotency                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 🎯 Key Architectural Patterns

1. **Database-First Pattern**: All writes go to PostgreSQL first, then events are published
2. **Event Sourcing**: Audit log captures every state change as immutable events
3. **CQRS Lite**: Write through API, read from audit log for history
4. **Idempotency**: Multiple layers prevent duplicate operations
5. **User Isolation**: Every query filtered by user_id from JWT
6. **Async Communication**: Services communicate via events, not direct calls
7. **Saga Pattern**: Recurring task generation is a multi-step saga coordinated by events

---

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
- Ensure Kafka/Redpanda connections are active

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