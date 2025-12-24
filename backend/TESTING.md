# Backend Testing Guide

## T089: Testing Concurrent Task Operations

### Purpose
Verify that the application handles concurrent operations (create, update, delete) from multiple browser tabs or sessions correctly without data corruption.

### Test Procedure

#### Setup
1. Start the backend server: `uvicorn backend.main:app --reload`
2. Start the frontend: `npm run dev`
3. Open two or more browser tabs/windows
4. Sign in with the same user account in all tabs

#### Test Cases

**Test 1: Concurrent Task Creation**
1. Open 3 browser tabs with the same user
2. In each tab, create a task simultaneously (within 1-2 seconds)
   - Tab 1: Create "Task A"
   - Tab 2: Create "Task B"
   - Tab 3: Create "Task C"
3. **Expected**: All 3 tasks appear in all tabs after refresh
4. **Verify**: Each task has a unique ID and correct user_id

**Test 2: Concurrent Task Updates**
1. Create a task "Original Task"
2. Open 2 tabs, both viewing the same task
3. In Tab 1: Update title to "Updated by Tab 1"
4. In Tab 2: Immediately update title to "Updated by Tab 2"
5. **Expected**: The last update wins (database uses updated_at timestamp)
6. **Verify**: Both tabs show the final state after refresh

**Test 3: Concurrent Delete Operations**
1. Create a task
2. Open 2 tabs
3. In both tabs, click delete at the same time
4. **Expected**: One tab succeeds (200/204), other gets 404 Not Found
5. **Verify**: Task is deleted and doesn't appear in task list

**Test 4: Toggle Completion Concurrently**
1. Create a task (completed=false)
2. Open 2 tabs
3. Toggle completion in both tabs simultaneously
4. **Expected**: Final state is consistent (either true or false)
5. **Verify**: updated_at timestamp reflects the last update

#### How to Verify Results
- Check browser network tab for HTTP status codes
- Verify data in database using SQL query:
  ```sql
  SELECT id, user_id, title, completed, created_at, updated_at
  FROM tasks
  ORDER BY created_at DESC;
  ```
- Check backend logs for any errors
- Verify optimistic UI updates and rollback behavior

#### Common Issues
- **Race conditions**: If two requests arrive simultaneously, database constraints and transaction isolation should handle them
- **Optimistic locking**: Frontend uses optimistic updates which may need rollback
- **Stale data**: Refresh required to see changes from other tabs (no real-time updates in Phase 2)

---

## T090: Verify Data Isolation

### Purpose
Ensure that User A cannot see or modify User B's tasks through the API or database queries.

### Test Procedure

#### Setup
1. Create two user accounts:
   - User A: `usera@example.com`
   - User B: `userb@example.com`
2. Create tasks for both users:
   - User A: Create 3-5 tasks
   - User B: Create 3-5 tasks

#### Test Cases

**Test 1: List Tasks Isolation**
1. Sign in as User A
2. Call `GET /api/{user_a_id}/tasks`
3. **Expected**: Only User A's tasks are returned
4. **Verify**: No tasks from User B appear in the response

**Test 2: Cross-User Access Attempt**
1. Sign in as User A (get JWT token)
2. Try to access User B's tasks: `GET /api/{user_b_id}/tasks`
3. **Expected**: 403 Forbidden (user_id in URL doesn't match JWT)
4. **Verify**: Backend middleware blocks the request

**Test 3: Update Another User's Task**
1. Sign in as User A
2. Get a task ID that belongs to User B
3. Try: `PUT /api/{user_b_id}/tasks/{task_id}`
4. **Expected**: 403 Forbidden
5. **Verify**: Task remains unchanged in database

**Test 4: Delete Another User's Task**
1. Sign in as User A
2. Try: `DELETE /api/{user_b_id}/tasks/{task_id}` (User B's task)
3. **Expected**: 403 Forbidden
4. **Verify**: Task still exists in database

**Test 5: Database Query Isolation**
Connect to database and verify:
```sql
-- User A should only see their tasks
SELECT COUNT(*) FROM tasks WHERE user_id = 'user_a_id';

-- User B should only see their tasks
SELECT COUNT(*) FROM tasks WHERE user_id = 'user_b_id';

-- Verify no tasks are shared
SELECT DISTINCT user_id FROM tasks;
```

#### Verification Steps

**Backend Code Verification**:
1. Check `backend/routes/tasks.py` for `verify_user_access` function
2. Verify all endpoints filter by `user_id`
3. Confirm JWT middleware extracts and validates `user_id`

**API Testing with cURL**:
```bash
# Get User A's JWT token (from browser developer tools)
USER_A_TOKEN="<jwt_token_for_user_a>"
USER_A_ID="<user_a_id>"
USER_B_ID="<user_b_id>"

# This should work (200 OK)
curl -H "Authorization: Bearer $USER_A_TOKEN" \
  http://localhost:8000/api/$USER_A_ID/tasks

# This should fail (403 Forbidden)
curl -H "Authorization: Bearer $USER_A_TOKEN" \
  http://localhost:8000/api/$USER_B_ID/tasks
```

#### Expected Security Guarantees

1. **JWT Validation**: Every request must have valid JWT
2. **User ID Matching**: URL user_id must match JWT payload user_id
3. **Query Filtering**: All database queries filter by user_id
4. **No Data Leakage**: 100% isolation between users
5. **Authorization First**: Middleware checks authorization before route handlers execute

#### Success Criteria

- ✅ User A cannot list User B's tasks
- ✅ User A cannot view User B's individual task
- ✅ User A cannot update User B's task
- ✅ User A cannot delete User B's task
- ✅ User A cannot toggle User B's task completion
- ✅ All unauthorized attempts return 403 Forbidden
- ✅ Database queries are properly filtered by user_id

---

## Additional Testing Notes

### Performance Testing
- **API Response Time**: Measure with browser DevTools Network tab
  - Target: < 500ms p95 for CRUD operations
  - Use "Disable cache" in DevTools for accurate measurements

### Database Connection Testing
- Health check endpoint: `GET /api/health`
- Should return: `{"status": "healthy", "database": "connected"}`

### Frontend Build Testing (T091)
```bash
cd frontend
npm run build
# Expected: Build completes without errors
# Check .next/build-manifest.json exists
```

### Backend Startup Testing (T092)
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
# Expected: Server starts without errors
# Navigate to http://localhost:8000/docs
# Verify Swagger UI loads with all endpoints
```

---

## Troubleshooting

### Common Issues

**Issue**: Tasks from other users appear in list
- **Cause**: Missing user_id filter in query
- **Fix**: Check `backend/routes/tasks.py` - ensure `filter(Task.user_id == user_id)`

**Issue**: 401 Unauthorized on valid requests
- **Cause**: JWT token expired or invalid
- **Fix**: Sign out and sign in again to get fresh token

**Issue**: Concurrent operations cause data corruption
- **Cause**: Missing transaction isolation
- **Fix**: Use database transactions for multi-step operations

**Issue**: Health check fails
- **Cause**: Database connection pool exhausted or network issue
- **Fix**: Check DATABASE_URL, restart backend, verify Neon connection

---

## Test Execution Checklist

- [ ] T089: Concurrent task creation (3+ tabs)
- [ ] T089: Concurrent task updates (2+ tabs)
- [ ] T089: Concurrent task deletion (2+ tabs)
- [ ] T089: Concurrent completion toggle (2+ tabs)
- [ ] T090: User A cannot list User B's tasks
- [ ] T090: User A cannot access User B's tasks with different URL user_id
- [ ] T090: User A cannot update User B's task
- [ ] T090: User A cannot delete User B's task
- [ ] T090: Database queries return only user-owned tasks
- [ ] All unauthorized access attempts return 403 Forbidden
- [ ] No data leakage between users (100% isolation)

**Result**: All tests passed ✅ / Some tests failed ❌
