# Data Model: Phase V Event-Driven Microservices Architecture

**Feature**: Phase V Event-Driven Microservices Architecture
**Branch**: `005-event-driven-microservices`
**Date**: 2026-01-06
**Status**: Design Complete

## Overview

This document defines the extended database schema for Phase V, including modifications to the existing `tasks` table and four new tables: `recurrence_rules`, `reminders`, `audit_log`. All tables maintain user isolation via `user_id` column for multi-tenant security.

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│      tasks          │
│─────────────────────│
│ id (PK)             │
│ user_id             │◄─────┐
│ title               │      │
│ description         │      │
│ completed           │      │
│ priority (NEW)      │      │
│ tags (NEW)          │      │
│ due_date (NEW)      │      │
│ recurrence_id (FK)  │──┐   │
│ created_at          │  │   │
│ updated_at          │  │   │
└─────────────────────┘  │   │
                          │   │
                          ▼   │
┌─────────────────────────┐  │
│  recurrence_rules (NEW) │  │
│─────────────────────────│  │
│ id (PK)                 │◄─┘
│ task_id (FK)            │
│ user_id                 │
│ pattern                 │
│ interval                │
│ metadata (JSONB)        │
│ created_at              │
└─────────────────────────┘

┌─────────────────────┐
│  reminders (NEW)    │
│─────────────────────│
│ id (PK)             │
│ task_id (FK)        │──────┐
│ user_id             │      │
│ reminder_time       │      │
│ status              │      │
│ delivery_method     │      │
│ retry_count         │      │
│ created_at          │      │
│ sent_at             │      │
└─────────────────────┘      │
                              │
                              ▼
                      ┌─────────────────────┐
                      │      tasks          │
                      └─────────────────────┘

┌─────────────────────┐
│  audit_log (NEW)    │
│─────────────────────│
│ id (PK)             │
│ event_type          │
│ user_id             │
│ task_id (nullable)  │
│ details (JSONB)     │
│ timestamp           │
└─────────────────────┘
```

---

## Table Definitions

### 1. tasks (Extended)

**Description**: Core task entity with Phase V enhancements (priority, tags, due dates, recurring tasks).

**Modifications**:
- Added 4 new columns: `priority`, `tags`, `due_date`, `recurrence_id`
- All new columns are nullable for backward compatibility
- Existing Phase 3/4 tasks continue working without changes

**SQL DDL**:
```sql
-- Existing table structure (Phase 3/4)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phase V additions (migration)
ALTER TABLE tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal';
ALTER TABLE tasks ADD COLUMN tags TEXT[];
ALTER TABLE tasks ADD COLUMN due_date TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN recurrence_id UUID;

-- Add foreign key constraint
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_recurrence_id
    FOREIGN KEY (recurrence_id) REFERENCES recurrence_rules(id)
    ON DELETE SET NULL;

-- Add indexes for performance
CREATE INDEX ix_tasks_user_id ON tasks(user_id);  -- Existing
CREATE INDEX ix_tasks_due_date ON tasks(due_date);
CREATE INDEX ix_tasks_priority ON tasks(priority);
CREATE INDEX ix_tasks_tags ON tasks USING GIN(tags);  -- Array index
CREATE INDEX ix_tasks_completed ON tasks(completed);
```

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, nullable=False, index=True)
    title: str = Field(max_length=500, nullable=False)
    description: Optional[str] = Field(default=None)
    completed: bool = Field(default=False, index=True)
    priority: str = Field(default="normal", max_length=20, index=True)  # NEW
    tags: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))  # NEW
    due_date: Optional[datetime] = Field(default=None, index=True)  # NEW
    recurrence_id: Optional[UUID] = Field(default=None, foreign_key="recurrence_rules.id")  # NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "title": "Weekly team meeting",
                "description": "Discuss project progress",
                "completed": False,
                "priority": "high",
                "tags": ["work", "meetings"],
                "due_date": "2026-01-13T10:00:00Z",
                "recurrence_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
```

**Field Constraints**:
- `priority`: Enum values: `low`, `normal`, `high`, `critical` (validated at application layer)
- `tags`: PostgreSQL array of strings; max 10 tags per task
- `due_date`: ISO8601 datetime with timezone; must be in future (validated at creation)
- `recurrence_id`: FK to `recurrence_rules.id`; SET NULL on parent deletion

**Business Rules**:
1. Completed tasks cannot have `due_date` modified (except by recurring task generation)
2. Tasks with `recurrence_id` are instances of recurring tasks
3. Tags are case-insensitive for search/filter (normalized at application layer)
4. Priority defaults to `normal` for backward compatibility

---

### 2. recurrence_rules (New)

**Description**: Defines how a task repeats. One recurrence rule can generate multiple task instances.

**SQL DDL**:
```sql
CREATE TABLE recurrence_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,  -- Original template task
    user_id VARCHAR(255) NOT NULL,
    pattern VARCHAR(50) NOT NULL,  -- daily, weekly, monthly, custom
    interval INTEGER DEFAULT 1,  -- Every N days/weeks/months
    metadata JSONB,  -- Preserve task attributes (priority, tags, description)
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_recurrence_rules_task_id FOREIGN KEY (task_id)
        REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX ix_recurrence_rules_user_id ON recurrence_rules(user_id);
CREATE INDEX ix_recurrence_rules_task_id ON recurrence_rules(task_id);
CREATE INDEX ix_recurrence_rules_pattern ON recurrence_rules(pattern);
```

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class RecurrenceRule(SQLModel, table=True):
    __tablename__ = "recurrence_rules"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.id", nullable=False)
    user_id: str = Field(max_length=255, nullable=False, index=True)
    pattern: str = Field(max_length=50, nullable=False, index=True)  # daily, weekly, monthly, custom
    interval: int = Field(default=1)  # Every N periods
    metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "pattern": "weekly",
                "interval": 1,
                "metadata": {
                    "title": "Weekly team meeting",
                    "description": "Discuss project progress",
                    "priority": "high",
                    "tags": ["work", "meetings"]
                }
            }
        }
```

**Field Constraints**:
- `pattern`: Enum values: `daily`, `weekly`, `monthly`
- `interval`: Must be positive integer (1-365 for daily, 1-52 for weekly, 1-12 for monthly)
- `metadata`: JSON object preserving task attributes to copy to next instance

**Business Rules**:
1. When task with `recurrence_id` is completed → Recurring Task Service generates next instance
2. Next instance inherits: `title`, `description`, `priority`, `tags` from `metadata`
3. Next instance gets: new `id`, new `due_date` (calculated), `completed=false`, same `recurrence_id`
4. Deleting original template task cascades to recurrence rule (stops future generation)

---

### 3. reminders (New)

**Description**: Scheduled notifications for tasks with due dates. Managed by Dapr Jobs API.

**SQL DDL**:
```sql
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    reminder_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed
    delivery_method VARCHAR(50) DEFAULT 'webhook',  -- webhook, email (future)
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,

    CONSTRAINT fk_reminders_task_id FOREIGN KEY (task_id)
        REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX ix_reminders_user_id ON reminders(user_id);
CREATE INDEX ix_reminders_task_id ON reminders(task_id);
CREATE INDEX ix_reminders_reminder_time ON reminders(reminder_time);
CREATE INDEX ix_reminders_status ON reminders(status);
```

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class Reminder(SQLModel, table=True):
    __tablename__ = "reminders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.id", nullable=False)
    user_id: str = Field(max_length=255, nullable=False, index=True)
    reminder_time: datetime = Field(nullable=False, index=True)
    status: str = Field(default="pending", max_length=20, index=True)  # pending, sent, failed
    delivery_method: str = Field(default="webhook", max_length=50)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-123",
                "reminder_time": "2026-01-13T09:00:00Z",
                "status": "pending",
                "delivery_method": "webhook",
                "retry_count": 0
            }
        }
```

**Field Constraints**:
- `status`: Enum values: `pending`, `sent`, `failed`
- `delivery_method`: Enum values: `webhook`, `email` (email for future implementation)
- `reminder_time`: Must be before or equal to task `due_date`
- `retry_count`: Max 3 retries before marking as `failed`

**Business Rules**:
1. Dapr Jobs API schedules job at `reminder_time`
2. Notification Service delivers reminder at scheduled time
3. If delivery fails → increment `retry_count`, retry with exponential backoff (5s, 30s, 2m)
4. After 3 failed retries → status = `failed` (logged to audit_log)
5. If task completed before reminder → skip delivery (check database state)
6. If task deleted → reminder also deleted (CASCADE)

---

### 4. audit_log (New)

**Description**: Immutable audit trail of all task operations for compliance and debugging.

**SQL DDL**:
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,  -- task.created, task.updated, task.completed, task.deleted
    user_id VARCHAR(255) NOT NULL,
    task_id UUID,  -- Nullable (some events may not reference a task)
    details JSONB,  -- Event payload (task_data, changes)
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_audit_log_user_id ON audit_log(user_id);
CREATE INDEX ix_audit_log_task_id ON audit_log(task_id);
CREATE INDEX ix_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX ix_audit_log_event_type ON audit_log(event_type);
```

**SQLModel Definition**:
```python
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_type: str = Field(max_length=50, nullable=False, index=True)
    user_id: str = Field(max_length=255, nullable=False, index=True)
    task_id: Optional[UUID] = Field(default=None, index=True)
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "task.created",
                "user_id": "user-123",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {
                    "title": "New task",
                    "priority": "high",
                    "tags": ["work"]
                },
                "timestamp": "2026-01-06T10:00:00Z"
            }
        }
```

**Field Constraints**:
- `event_type`: Matches event schema `event_type` enum (task.created, task.updated, task.completed, task.deleted, reminder.triggered, etc.)
- `details`: JSON object containing full event payload
- `timestamp`: Immutable (set once at creation)

**Business Rules**:
1. Audit Service subscribes to `task-events` topic → writes all events to audit_log
2. Entries are **immutable** (no updates or deletes allowed)
3. Used for compliance tracking, debugging, and analytics
4. Query by `user_id` for user-specific audit trail
5. Retention policy: Keep 90 days (configurable)

---

## Database Migration Strategy

### Migration 001: Add Advanced Features

**File**: `backend/migrations/001_add_advanced_features.py`

**Execution Order**:
1. Create new tables: `recurrence_rules`, `reminders`, `audit_log`
2. Add new columns to `tasks` table: `priority`, `tags`, `due_date`, `recurrence_id`
3. Create indexes for performance
4. Add foreign key constraints

**Backward Compatibility**:
- ✅ All new columns are nullable or have defaults
- ✅ Existing tasks continue working without changes
- ✅ Old clients (Phase 3/4) ignore new columns
- ✅ New clients (Phase 5) use new columns for enhanced features

**Rollback Plan**:
```sql
-- Rollback migration (if needed)
ALTER TABLE tasks DROP CONSTRAINT fk_tasks_recurrence_id;
ALTER TABLE tasks DROP COLUMN recurrence_id;
ALTER TABLE tasks DROP COLUMN due_date;
ALTER TABLE tasks DROP COLUMN tags;
ALTER TABLE tasks DROP COLUMN priority;

DROP TABLE reminders;
DROP TABLE recurrence_rules;
DROP TABLE audit_log;
```

---

## Query Patterns

### Common Queries

**1. Get all tasks for user with filters**:
```sql
SELECT * FROM tasks
WHERE user_id = 'user-123'
  AND completed = false
  AND priority = 'high'
  AND 'work' = ANY(tags)
  AND due_date > NOW()
  AND due_date < NOW() + INTERVAL '7 days'
ORDER BY due_date ASC
LIMIT 50;
```

**2. Get recurring tasks that need next instance**:
```sql
SELECT t.*, rr.*
FROM tasks t
JOIN recurrence_rules rr ON t.recurrence_id = rr.id
WHERE t.user_id = 'user-123'
  AND t.completed = true
  AND NOT EXISTS (
      SELECT 1 FROM tasks t2
      WHERE t2.recurrence_id = rr.id
        AND t2.completed = false
  );
```

**3. Get pending reminders to schedule**:
```sql
SELECT * FROM reminders
WHERE status = 'pending'
  AND reminder_time <= NOW() + INTERVAL '5 minutes'
  AND reminder_time > NOW()
ORDER BY reminder_time ASC;
```

**4. Get user audit trail**:
```sql
SELECT * FROM audit_log
WHERE user_id = 'user-123'
ORDER BY timestamp DESC
LIMIT 100;
```

---

## Performance Considerations

### Index Strategy

| Table | Index | Type | Cardinality | Purpose |
|-------|-------|------|-------------|---------|
| tasks | user_id | B-tree | High | User isolation (every query filters by user_id) |
| tasks | due_date | B-tree | Medium | Range queries ("due this week") |
| tasks | priority | B-tree | Low | Filter by priority (4 values) |
| tasks | tags | GIN | High | Array containment queries ("has tag X") |
| tasks | completed | B-tree | Low | Filter pending/completed (2 values) |
| recurrence_rules | user_id | B-tree | High | User isolation |
| recurrence_rules | task_id | B-tree | Medium | FK lookups |
| reminders | user_id | B-tree | High | User isolation |
| reminders | reminder_time | B-tree | High | Scheduled job queries |
| reminders | status | B-tree | Low | Filter pending reminders (3 values) |
| audit_log | user_id | B-tree | High | User audit trail |
| audit_log | timestamp | B-tree (DESC) | High | Recent events queries |

### Expected Query Performance

| Query | Expected Latency | Optimization |
|-------|-----------------|--------------|
| List user tasks (50 tasks) | <50ms | Indexed by user_id, completed |
| Filter by priority + tags | <100ms | Composite index or GIN index |
| Search by title/description | <500ms | Full-text search (future: PostgreSQL tsvector) |
| Get recurring tasks to generate | <100ms | Indexed by recurrence_id, completed |
| Get pending reminders | <50ms | Indexed by status, reminder_time |
| User audit trail (last 100) | <100ms | Indexed by user_id, timestamp DESC |

---

## Data Integrity Constraints

### Foreign Key Relationships

1. `tasks.recurrence_id → recurrence_rules.id` (SET NULL on delete)
2. `recurrence_rules.task_id → tasks.id` (CASCADE on delete)
3. `reminders.task_id → tasks.id` (CASCADE on delete)

### Validation Rules (Application Layer)

1. **Priority**: Must be one of: `low`, `normal`, `high`, `critical`
2. **Tags**: Max 10 tags per task; each tag max 50 characters
3. **Due Date**: Must be in future (unless explicitly allowed by user)
4. **Recurrence Pattern**: Must be one of: `daily`, `weekly`, `monthly`
5. **Recurrence Interval**: 1-365 for daily, 1-52 for weekly, 1-12 for monthly

---

## Test Data Setup

### Seed Data for Testing

```python
# Seed script: backend/seeds/phase5_test_data.py
from backend.models import Task, RecurrenceRule, Reminder, AuditLog
from backend.db import engine
from sqlmodel import Session
from datetime import datetime, timedelta

def seed_phase5_data():
    with Session(engine) as session:
        # User 1: Regular tasks with priority and tags
        task1 = Task(
            user_id="test-user-1",
            title="Submit quarterly report",
            description="Q4 2025 financial report",
            completed=False,
            priority="high",
            tags=["work", "urgent"],
            due_date=datetime.utcnow() + timedelta(days=3)
        )
        session.add(task1)

        # User 1: Recurring task (weekly team meeting)
        task2 = Task(
            user_id="test-user-1",
            title="Weekly team meeting",
            description="Discuss project progress",
            completed=False,
            priority="normal",
            tags=["work", "meetings"],
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        session.add(task2)
        session.commit()

        # Create recurrence rule for task2
        recurrence = RecurrenceRule(
            task_id=task2.id,
            user_id="test-user-1",
            pattern="weekly",
            interval=1,
            metadata={
                "title": "Weekly team meeting",
                "description": "Discuss project progress",
                "priority": "normal",
                "tags": ["work", "meetings"]
            }
        )
        session.add(recurrence)

        # Update task2 with recurrence_id
        task2.recurrence_id = recurrence.id
        session.commit()

        # Create reminder for task1
        reminder = Reminder(
            task_id=task1.id,
            user_id="test-user-1",
            reminder_time=datetime.utcnow() + timedelta(days=2, hours=22),
            status="pending",
            delivery_method="webhook"
        )
        session.add(reminder)

        # Create audit log entry
        audit = AuditLog(
            event_type="task.created",
            user_id="test-user-1",
            task_id=task1.id,
            details={
                "title": task1.title,
                "priority": task1.priority,
                "tags": task1.tags
            }
        )
        session.add(audit)

        session.commit()
        print("✅ Phase 5 test data seeded successfully")
```

---

## Summary

**Tables**:
- ✅ `tasks` (extended with 4 new columns)
- ✅ `recurrence_rules` (new)
- ✅ `reminders` (new)
- ✅ `audit_log` (new)

**Indexes**: 15 indexes across all tables for optimal query performance

**Foreign Keys**: 3 relationships maintaining referential integrity

**Migration Strategy**: Zero-downtime deployment with nullable columns

**Backward Compatibility**: Existing Phase 3/4 tasks continue working without changes

---

**Status**: ✅ COMPLETE
**Next**: Generate event schemas and Dapr component YAMLs
