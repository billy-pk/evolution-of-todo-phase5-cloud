# Security Patterns

## Table of Contents
- [User Isolation](#user-isolation)
- [Ownership Verification](#ownership-verification)
- [Input Validation](#input-validation)
- [Common Mistakes](#common-mistakes)

## User Isolation

Always filter queries by user_id:

```python
# CORRECT
query = select({ModelName}).where({ModelName}.user_id == user_id)

# WRONG - leaks all users' data
query = select({ModelName})
```

## Ownership Verification

verify_user_access dependency:
```python
def verify_user_access(request: Request, user_id: str = Path(...)) -> str:
    token_user_id = getattr(request.state, "user_id", None)
    if not token_user_id:
        raise HTTPException(401, "Authentication required")
    if token_user_id != user_id:
        raise HTTPException(403, "Access denied")
    return user_id
```

On mutations, verify resource ownership:
```python
{resource} = session.get({ModelName}, id)
if {resource}.user_id != user_id:
    raise HTTPException(403, "Access denied")
```

## Input Validation

Always set field constraints:
```python
title: str = Field(min_length=1, max_length=200)
email: str = Field(max_length=255, regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
priority: int = Field(ge=1, le=5)
```

## Common Mistakes

| Mistake | Risk | Fix |
|---------|------|-----|
| No user_id filter | Data leak | Add `.where(Model.user_id == user_id)` |
| Trust path param | Privilege escalation | Use `verify_user_access` dependency |
| No ownership check | Cross-user access | Check `resource.user_id != user_id` |
| No input length | DoS via large payloads | Set `max_length` on strings |
