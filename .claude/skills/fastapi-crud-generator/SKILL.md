---
name: fastapi-crud-generator
description: Generate complete CRUD endpoints for FastAPI with SQLModel models, including routes, schemas, database queries, user isolation, and tests. Use when creating new resources (tasks, projects, users), adding REST API endpoints, implementing database models, or building multi-tenant CRUD operations.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# FastAPI CRUD Generator Skill

## Purpose
Automatically generate complete CRUD (Create, Read, Update, Delete) operations for FastAPI applications with:
- SQLModel database models
- Pydantic request/response schemas
- FastAPI route handlers with proper validation
- Multi-tenant user isolation
- JWT authentication integration
- Comprehensive test suites
- OpenAPI documentation examples

## When to Use This Skill
- Creating a new resource type (e.g., Project, Note, Comment)
- Adding CRUD endpoints to existing FastAPI project
- Implementing multi-tenant data operations
- Building REST APIs with SQLModel ORM
- Scaffolding new features with database persistence
- Converting specifications to working CRUD code

## CRUD Pattern Architecture

```
Request → JWT Middleware → verify_user_access → Route Handler → SQLModel Query → Response
                ↓                    ↓                   ↓              ↓
           Validates JWT    Checks user_id match   Business Logic   DB Operation
```

### Key Components Generated:

1. **SQLModel Model** (`models.py`)
   - Table definition with columns
   - Field constraints and validation
   - Indexes for performance
   - Timestamps (created_at, updated_at)

2. **Pydantic Schemas** (`schemas.py`)
   - `{Model}Create` - Request for POST
   - `{Model}Update` - Request for PUT/PATCH
   - `{Model}Response` - Response format
   - `{Model}ListResponse` - List response with pagination

3. **Route Handlers** (`routes/{model}.py`)
   - POST `/{user_id}/{resources}` - Create
   - GET `/{user_id}/{resources}` - List (with filters)
   - GET `/{user_id}/{resources}/{id}` - Read one
   - PUT `/{user_id}/{resources}/{id}` - Update
   - DELETE `/{user_id}/{resources}/{id}` - Delete

4. **Test Suite** (`tests/test_{model}.py`)
   - Create tests
   - Read tests
   - Update tests
   - Delete tests
   - User isolation tests
   - Error case tests

## Workflow

### Step 1: Gather Information

Ask the user or infer from context:

**Required Information:**
1. **Model Name**: Singular, PascalCase (e.g., `Task`, `Project`, `Note`)
2. **Resource Name**: Plural, lowercase (e.g., `tasks`, `projects`, `notes`)
3. **Fields**: List of fields with types and constraints
4. **Multi-Tenant**: Does this resource belong to users? (default: yes)
5. **Additional Operations**: Any custom endpoints beyond CRUD?

**Example Prompt to User:**
```
I'll generate CRUD endpoints for you. I need some information:

1. What is the model name? (e.g., Project, Note, Comment)
2. What fields should it have?
   - Field name, type (str, int, bool, datetime), required/optional
   - Max length, min value, default value
3. Should this resource be user-specific (multi-tenant)? [yes/no]
4. Any custom operations besides CRUD? (e.g., "archive", "share")
```

### Step 2: Determine Project Structure

Check existing structure:

```bash
# Check for existing models
ls backend/models.py 2>/dev/null

# Check for existing schemas
ls backend/schemas.py 2>/dev/null

# Check for routes directory
ls -d backend/routes/ 2>/dev/null
```

**Decision Tree:**
- If `backend/models.py` exists → Add model to existing file
- If `backend/models/{model}.py` pattern exists → Create new file
- If `backend/schemas.py` exists → Add schemas to existing file
- If `backend/routes/` exists → Create `backend/routes/{resource}.py`

### Step 3: Generate SQLModel Model

Create or update `backend/models.py`:

**Template Pattern:**
```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class {ModelName}(SQLModel, table=True):
    """
    {ModelName} model for database table.
    {Description of what this model represents}
    """
    __tablename__ = "{table_name}"  # plural, lowercase

    # Primary Key (always UUID)
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique {model} identifier"
    )

    # User ID (for multi-tenant isolation)
    user_id: str = Field(
        index=True,
        max_length=255,
        description="User ID from authentication"
    )

    # Custom Fields (based on user input)
    {field_name}: {field_type} = Field(
        {constraints},
        description="{field_description}"
    )

    # Timestamps (always included)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp (UTC)"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp (UTC)"
    )
```

**Field Type Mapping:**
```python
# Common field patterns from user input
"string" → str with Field(max_length=X)
"text" → Optional[str] with Field(max_length=X)
"integer" → int with Field(ge=0) for positive
"decimal" → float
"boolean" → bool with Field(default=False)
"datetime" → datetime
"optional string" → Optional[str] = Field(default=None)
```

### Step 4: Generate Pydantic Schemas

Create or update `backend/schemas.py`:

**Template Pattern:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List

class {ModelName}Create(BaseModel):
    """Request schema for creating a new {model}"""
    {field_name}: {field_type} = Field({constraints})

    class Config:
        json_schema_extra = {
            "example": {
                "{field_name}": "{example_value}"
            }
        }

class {ModelName}Update(BaseModel):
    """Request schema for updating a {model}"""
    {field_name}: Optional[{field_type}] = Field(None, {constraints})

    class Config:
        json_schema_extra = {
            "example": {
                "{field_name}": "{example_value}"
            }
        }

class {ModelName}Response(BaseModel):
    """Response schema for {model} data"""
    id: UUID
    user_id: str
    {field_name}: {field_type}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2: ORM mode

class {ModelName}ListResponse(BaseModel):
    """Response schema for {model} list"""
    {resources}: List[{ModelName}Response]
    total: int
```

### Step 5: Generate Route Handlers

Create `backend/routes/{resource}.py`:

**Template Structure:**
```python
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlmodel import Session, select
from typing import Optional
from uuid import UUID

from db import get_session
from models import {ModelName}
from schemas import {ModelName}Create, {ModelName}Update, {ModelName}Response, {ModelName}ListResponse
from routes.tasks import verify_user_access  # Reuse from JWT auth skill

router = APIRouter(tags=["{resources}"])

# CREATE
@router.post("/{user_id}/{resources}", response_model={ModelName}Response, status_code=201)
async def create_{resource}(
    {resource}_data: {ModelName}Create,
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session)
):
    """Create a new {resource}"""
    {resource} = {ModelName}(
        user_id=user_id,
        **{resource}_data.model_dump()
    )
    session.add({resource})
    session.commit()
    session.refresh({resource})
    return {ModelName}Response.model_validate({resource})

# LIST
@router.get("/{user_id}/{resources}", response_model={ModelName}ListResponse)
async def list_{resources}(
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """List all {resources} for authenticated user"""
    query = select({ModelName}).where(
        {ModelName}.user_id == user_id
    ).order_by(
        {ModelName}.created_at.desc()
    ).offset(skip).limit(limit)

    {resources} = session.exec(query).all()
    total = len({resources})

    return {ModelName}ListResponse(
        {resources}=[{ModelName}Response.model_validate(r) for r in {resources}],
        total=total
    )

# READ
@router.get("/{user_id}/{resources}/{id}", response_model={ModelName}Response)
async def get_{resource}(
    id: UUID,
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session)
):
    """Get a single {resource} by ID"""
    {resource} = session.get({ModelName}, id)

    if not {resource}:
        raise HTTPException(status_code=404, detail="{ModelName} not found")

    if {resource}.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {ModelName}Response.model_validate({resource})

# UPDATE
@router.put("/{user_id}/{resources}/{id}", response_model={ModelName}Response)
async def update_{resource}(
    id: UUID,
    {resource}_data: {ModelName}Update,
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session)
):
    """Update a {resource}"""
    {resource} = session.get({ModelName}, id)

    if not {resource}:
        raise HTTPException(status_code=404, detail="{ModelName} not found")

    if {resource}.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    {resource}.sqlmodel_update({resource}_data.model_dump(exclude_unset=True))
    session.add({resource})
    session.commit()
    session.refresh({resource})

    return {ModelName}Response.model_validate({resource})

# DELETE
@router.delete("/{user_id}/{resources}/{id}", status_code=204)
async def delete_{resource}(
    id: UUID,
    user_id: str = Depends(verify_user_access),
    session: Session = Depends(get_session)
):
    """Delete a {resource}"""
    {resource} = session.get({ModelName}, id)

    if not {resource}:
        raise HTTPException(status_code=404, detail="{ModelName} not found")

    if {resource}.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    session.delete({resource})
    session.commit()
    return None
```

### Step 6: Update Main Application

Add router to `backend/main.py`:

```python
# Import the new router
from routes import {resources}

# Include in app with JWT middleware
app.include_router(
    {resources}.router,
    prefix="/api",
    dependencies=[Depends(JWTBearer())]
)
```

### Step 7: Generate Test Suite

Create `backend/tests/test_{resources}.py`:

**Template Structure:**
```python
import pytest
from uuid import uuid4

def test_create_{resource}(client, test_user_id):
    """Test creating a new {resource}"""
    response = client.post(
        f"/api/{test_user_id}/{resources}",
        json={
            "{field}": "{value}"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["{field}"] == "{value}"
    assert data["user_id"] == test_user_id

def test_list_{resources}(client, test_user_id):
    """Test listing {resources}"""
    response = client.get(f"/api/{test_user_id}/{resources}")
    assert response.status_code == 200
    data = response.json()
    assert "{resources}" in data
    assert "total" in data

def test_get_{resource}(client, test_user_id):
    """Test getting a single {resource}"""
    # Create first
    create_response = client.post(
        f"/api/{test_user_id}/{resources}",
        json={"{field}": "{value}"}
    )
    {resource}_id = create_response.json()["id"]

    # Get
    response = client.get(f"/api/{test_user_id}/{resources}/{{{resource}_id}}")
    assert response.status_code == 200

def test_update_{resource}(client, test_user_id):
    """Test updating a {resource}"""
    # Create first
    create_response = client.post(
        f"/api/{test_user_id}/{resources}",
        json={"{field}": "{value}"}
    )
    {resource}_id = create_response.json()["id"]

    # Update
    response = client.put(
        f"/api/{test_user_id}/{resources}/{{{resource}_id}}",
        json={"{field}": "{new_value}"}
    )
    assert response.status_code == 200
    assert response.json()["{field}"] == "{new_value}"

def test_delete_{resource}(client, test_user_id):
    """Test deleting a {resource}"""
    # Create first
    create_response = client.post(
        f"/api/{test_user_id}/{resources}",
        json={"{field}": "{value}"}
    )
    {resource}_id = create_response.json()["id"]

    # Delete
    response = client.delete(f"/api/{test_user_id}/{resources}/{{{resource}_id}}")
    assert response.status_code == 204

def test_user_isolation(client, test_user_id, another_test_user_id):
    """Test that users cannot access each other's {resources}"""
    # Create as user A
    create_response = client.post(
        f"/api/{test_user_id}/{resources}",
        json={"{field}": "{value}"}
    )
    {resource}_id = create_response.json()["id"]

    # Try to access as user B (should fail)
    response = client.get(f"/api/{another_test_user_id}/{resources}/{{{resource}_id}}")
    assert response.status_code == 403
```

### Step 8: Create Database Migration (Optional)

If using Alembic, generate migration:

```bash
cd backend
alembic revision --autogenerate -m "Add {table_name} table"
alembic upgrade head
```

### Step 9: Validation Checklist

After generation, verify:

- [ ] **Model Created**: SQLModel class in models.py
- [ ] **Schemas Created**: Create, Update, Response, ListResponse in schemas.py
- [ ] **Routes Created**: All 5 CRUD endpoints in routes/{resources}.py
- [ ] **Router Mounted**: Added to main.py with JWT middleware
- [ ] **Tests Created**: All CRUD operations tested
- [ ] **User Isolation**: verify_user_access applied to all routes
- [ ] **Ownership Check**: All mutations verify user_id match
- [ ] **Queries Filtered**: All queries filter by user_id
- [ ] **Timestamps**: created_at and updated_at included
- [ ] **OpenAPI Docs**: Examples provided in schemas

### Step 10: Testing the Implementation

**Run Tests:**
```bash
cd backend
pytest tests/test_{resources}.py -v
```

**Manual Testing with curl:**
```bash
# Create
curl -X POST http://localhost:8000/api/user123/{resources} \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{{"{field}": "{value}"}}'

# List
curl -X GET http://localhost:8000/api/user123/{resources} \
  -H "Authorization: Bearer <jwt>"

# Get one
curl -X GET http://localhost:8000/api/user123/{resources}/{id} \
  -H "Authorization: Bearer <jwt>"

# Update
curl -X PUT http://localhost:8000/api/user123/{resources}/{id} \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{{"{field}": "{new_value}"}}'

# Delete
curl -X DELETE http://localhost:8000/api/user123/{resources}/{id} \
  -H "Authorization: Bearer <jwt>"
```

## Common Use Cases

### Use Case 1: Simple CRUD Resource
```
User: "Create CRUD endpoints for a Note resource with title and content fields"

Steps:
1. Ask: What should the max length be for title and content?
2. Generate SQLModel Note with title (max 200), content (max 5000)
3. Generate schemas: NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
4. Generate routes: POST, GET (list), GET (one), PUT, DELETE
5. Add to main.py
6. Generate tests
```

### Use Case 2: Complex Resource with Relationships
```
User: "Create CRUD for Project with name, description, status, and due_date"

Steps:
1. Confirm field types and constraints
2. Generate SQLModel with status enum
3. Add custom filter in list endpoint (filter by status)
4. Generate schemas with status validation
5. Generate routes with status filter
6. Add custom endpoint: PATCH /{id}/status (change status)
7. Generate extended tests
```

### Use Case 3: Nested Resource
```
User: "Create CRUD for Comment that belongs to a Task"

Steps:
1. Ask: Should comments reference task_id as foreign key?
2. Generate SQLModel with task_id field
3. Generate routes under /{user_id}/tasks/{task_id}/comments
4. Add verification that task belongs to user
5. Filter comments by task_id
6. Generate nested tests
```

## Advanced Features

### Pagination
```python
@router.get("/{user_id}/{resources}")
async def list_{resources}(
    user_id: str = Depends(verify_user_access),
    skip: int = Query(0, ge=0, description="Skip N records"),
    limit: int = Query(100, ge=1, le=100, description="Max records"),
    session: Session = Depends(get_session)
):
    query = select({ModelName}).where(
        {ModelName}.user_id == user_id
    ).offset(skip).limit(limit)
    ...
```

### Filtering
```python
@router.get("/{user_id}/{resources}")
async def list_{resources}(
    user_id: str = Depends(verify_user_access),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    query = select({ModelName}).where({ModelName}.user_id == user_id)

    if status:
        query = query.where({ModelName}.status == status)

    if search:
        query = query.where({ModelName}.title.contains(search))

    ...
```

### Sorting
```python
@router.get("/{user_id}/{resources}")
async def list_{resources}(
    user_id: str = Depends(verify_user_access),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    session: Session = Depends(get_session)
):
    query = select({ModelName}).where({ModelName}.user_id == user_id)

    if sort_order == "asc":
        query = query.order_by(getattr({ModelName}, sort_by).asc())
    else:
        query = query.order_by(getattr({ModelName}, sort_by).desc())

    ...
```

### Soft Delete
```python
# Add to model
deleted_at: Optional[datetime] = Field(default=None)

# Override delete endpoint
@router.delete("/{user_id}/{resources}/{id}")
async def delete_{resource}(...):
    {resource}.deleted_at = datetime.utcnow()
    session.add({resource})
    session.commit()
    return None

# Filter deleted in list
query = select({ModelName}).where(
    ({ModelName}.user_id == user_id) &
    ({ModelName}.deleted_at.is_(None))
)
```

## Security Best Practices

### 1. Always Filter by user_id
```python
# CORRECT
query = select({ModelName}).where({ModelName}.user_id == user_id)

# WRONG - Security vulnerability!
query = select({ModelName})  # Returns all users' data
```

### 2. Verify Ownership on Mutations
```python
# CORRECT
{resource} = session.get({ModelName}, id)
if {resource}.user_id != user_id:
    raise HTTPException(status_code=403, detail="Access denied")

# WRONG - Allows privilege escalation
{resource}.title = new_title  # No ownership check
```

### 3. Use verify_user_access Dependency
```python
# CORRECT
async def create_{resource}(
    user_id: str = Depends(verify_user_access)  # Validates JWT
):
    ...

# WRONG - No validation
async def create_{resource}(user_id: str = Path(...)):
    ...
```

### 4. Validate Input Lengths
```python
# CORRECT
title: str = Field(min_length=1, max_length=200)

# WRONG - No limits (DoS risk)
title: str
```

## Error Handling Patterns

### 404 Not Found
```python
{resource} = session.get({ModelName}, id)
if not {resource}:
    raise HTTPException(status_code=404, detail="{ModelName} not found")
```

### 403 Forbidden
```python
if {resource}.user_id != user_id:
    raise HTTPException(status_code=403, detail="Access denied: Cannot access another user's {resource}")
```

### 422 Validation Error
```python
# Automatic from Pydantic
title: str = Field(min_length=1, max_length=200)
# If validation fails, FastAPI returns 422 automatically
```

## Summary
This skill automates complete CRUD generation for FastAPI + SQLModel projects, including:
- ✅ SQLModel database models with constraints
- ✅ Pydantic request/response schemas
- ✅ FastAPI route handlers (Create, Read, Update, Delete, List)
- ✅ Multi-tenant user isolation with verify_user_access
- ✅ Comprehensive test suites
- ✅ OpenAPI documentation examples
- ✅ Security best practices (ownership checks, query filtering)
- ✅ Pagination, filtering, sorting support

Use this skill to rapidly scaffold new resources in FastAPI projects with SQLModel ORM.
