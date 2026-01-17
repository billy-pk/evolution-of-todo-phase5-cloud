---
name: fastapi-crud-generator
description: Generate complete CRUD endpoints for FastAPI with SQLModel models. Use when creating new resources (tasks, projects, notes), adding REST API endpoints, implementing database models with user isolation, or scaffolding multi-tenant CRUD operations. Triggers include requests like "create CRUD for X", "add a new resource", "scaffold endpoints", or "implement database model".
---

# FastAPI CRUD Generator

Generate CRUD operations with SQLModel models, Pydantic schemas, route handlers, and tests.

## Workflow

### 1. Gather Requirements

Ask (or infer from context):
- **Model name**: Singular, PascalCase (e.g., `Project`)
- **Resource name**: Plural, lowercase (e.g., `projects`)
- **Fields**: Name, type, constraints
- **Multi-tenant**: User-scoped? (default: yes)

### 2. Check Project Structure

```bash
ls backend/models.py backend/schemas.py backend/routes/ 2>/dev/null
```

Add to existing files or create new ones based on project conventions.

### 3. Generate Components

Use templates from `templates/` directory:

| Component | Template | Output |
|-----------|----------|--------|
| Model | `templates/model.py.template` | `models.py` or `models/{resource}.py` |
| Schemas | `templates/schemas.py.template` | `schemas.py` |
| Routes | `templates/routes.py.template` | `routes/{resource}.py` |
| Tests | `templates/test_crud.py.template` | `tests/test_{resource}.py` |

### 4. Mount Router

Add to `main.py`:
```python
from routes import {resources}
app.include_router({resources}.router, prefix="/api", dependencies=[Depends(JWTBearer())])
```

### 5. Validate

- [ ] All queries filter by `user_id`
- [ ] Mutations verify ownership
- [ ] `verify_user_access` dependency on all routes
- [ ] Tests cover CRUD + user isolation

## Quick Reference

### Field Types

```python
str          # Field(max_length=200)
Optional[str] # Field(default=None, max_length=500)
int          # Field(ge=0, le=100)
bool         # Field(default=False)
datetime     # Field(default_factory=datetime.utcnow)
UUID         # Field(default_factory=uuid4)
Literal["a","b"] # Enum-like fixed choices
```

### Route Pattern

```
POST   /{user_id}/{resources}      # Create
GET    /{user_id}/{resources}      # List
GET    /{user_id}/{resources}/{id} # Read
PUT    /{user_id}/{resources}/{id} # Update
DELETE /{user_id}/{resources}/{id} # Delete
```

### Core Security

```python
# Every route must use verify_user_access
user_id: str = Depends(verify_user_access)

# Every query must filter by user_id
query = select(Model).where(Model.user_id == user_id)

# Every mutation must verify ownership
if resource.user_id != user_id:
    raise HTTPException(403, "Access denied")
```

## Advanced Features

See `references/` for detailed patterns:
- **[advanced-patterns.md](references/advanced-patterns.md)**: Pagination, filtering, sorting, soft delete, nested resources
- **[security-patterns.md](references/security-patterns.md)**: User isolation, ownership verification, common mistakes

## Templates

The `templates/` directory contains ready-to-use templates:
- `model.py.template` - SQLModel with field examples
- `schemas.py.template` - Pydantic Create/Update/Response schemas
- `routes.py.template` - Full CRUD endpoints with verify_user_access
- `test_crud.py.template` - Pytest test suite

Replace placeholders: `{ModelName}`, `{resource}`, `{resources}`, `{table_name}`
