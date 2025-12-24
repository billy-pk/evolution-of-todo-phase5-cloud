# Quickstart: Verify Legacy Endpoint Removal

**Feature**: 003-remove-legacy-endpoints
**Purpose**: Verification steps to confirm legacy code removal was successful and chat interface continues working

## Prerequisites

- Implementation complete (all files deleted/modified per plan.md)
- Backend server running on port 8000
- Frontend server running on port 3000
- Valid user account with authentication token
- Database contains at least one test task

## Verification Checklist

### ✅ Phase 1: File Deletion Verification

Confirm all legacy files have been removed:

```bash
# Navigate to project root
cd /home/bilali/vibe-coding-projects/evolution-of-todo/phase3-ai-chatbot

# Verify backend files deleted
test ! -f backend/routes/tasks.py && echo "✅ tasks.py deleted" || echo "❌ tasks.py still exists"

# Verify frontend files deleted
test ! -f frontend/app/\(dashboard\)/tasks/page.tsx && echo "✅ tasks/page.tsx deleted" || echo "❌ tasks page still exists"
test ! -f frontend/components/TaskForm.tsx && echo "✅ TaskForm deleted" || echo "❌ TaskForm still exists"
test ! -f frontend/components/TaskList.tsx && echo "✅ TaskList deleted" || echo "❌ TaskList still exists"
test ! -f frontend/components/TaskItem.tsx && echo "✅ TaskItem deleted" || echo "❌ TaskItem still exists"
```

**Expected**: All echo "✅ [file] deleted"

### ✅ Phase 2: Import Cleanup Verification

Verify imports have been removed:

```bash
# Check main.py doesn't import tasks
grep -n "from routes import tasks" backend/main.py
# Expected: No output (grep should find nothing)

grep -n "tasks.router" backend/main.py
# Expected: No output

# Check api.ts doesn't have task methods
grep -n "createTask\|listTasks\|updateTask\|deleteTask\|toggleComplete" frontend/lib/api.ts
# Expected: No output (all task methods removed)
```

**Expected**: All grep commands return no results

### ✅ Phase 3: Build Verification

Confirm both backend and frontend build successfully:

```bash
# Backend: Check for Python import errors
cd backend
python -c "import main; print('✅ Backend imports successful')"
# Expected: ✅ Backend imports successful

# Frontend: Build for production
cd ../frontend
npm run build
# Expected: Build completes with no errors
# Look for: "✓ Compiled successfully" or similar
```

**Expected**: Both commands succeed with no import or build errors

### ✅ Phase 4: Backend Endpoint Verification

Test that legacy REST endpoints return 404:

```bash
# Test GET /api/{user_id}/tasks (should be 404)
curl -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/test-user-id/tasks
# Expected: HTTP Status: 404

# Test POST /api/{user_id}/tasks (should be 404)
curl -X POST -w "\nHTTP Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"Test"}' \
  http://localhost:8000/api/test-user-id/tasks
# Expected: HTTP Status: 404

# Test PUT /api/{user_id}/tasks/{task_id} (should be 404)
curl -X PUT -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/test-user-id/tasks/some-task-id
# Expected: HTTP Status: 404

# Test DELETE /api/{user_id}/tasks/{task_id} (should be 404)
curl -X DELETE -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/test-user-id/tasks/some-task-id
# Expected: HTTP Status: 404
```

**Expected**: All legacy endpoints return HTTP 404 Not Found

### ✅ Phase 5: Chat Endpoint Verification

Verify chat endpoint still works (requires valid JWT token):

```bash
# Get JWT token from Better Auth
# Replace <YOUR_TOKEN> with actual token from frontend session

# Test chat endpoint
curl -X POST http://localhost:8000/api/<user-id>/chat \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "list my tasks",
    "conversation_id": null
  }' | jq

# Expected: 200 OK with JSON response containing task list
```

**Expected**: Chat endpoint responds successfully with task data

### ✅ Phase 6: Frontend Route Verification

Test frontend routes:

```bash
# Start frontend dev server
cd frontend
npm run dev

# In browser:
# 1. Navigate to http://localhost:3000/tasks
#    Expected: 404 Not Found page

# 2. Navigate to http://localhost:3000/chat
#    Expected: Chat interface loads successfully

# 3. Navigate to http://localhost:3000/signin
#    Expected: Sign in page loads (auth still works)
```

**Expected**:
- /tasks returns 404
- /chat loads successfully
- /signin loads successfully

### ✅ Phase 7: Chat Interface Functional Testing

Manual testing of chat interface CRUD operations:

1. **Sign in** to the application at http://localhost:3000/signin

2. **Navigate to Chat** at http://localhost:3000/chat

3. **Test CREATE**:
   - Type: "add a task to buy groceries"
   - Expected: ✅ Task created confirmation message
   - Time: <30 seconds

4. **Test READ (List)**:
   - Type: "list my tasks"
   - Expected: ✅ Shows task "buy groceries" in response
   - Time: <30 seconds

5. **Test READ (Filter)**:
   - Type: "show my pending tasks"
   - Expected: ✅ Shows only uncompleted tasks
   - Time: <30 seconds

6. **Test UPDATE**:
   - Type: "update 'buy groceries' to 'buy groceries and milk'"
   - Expected: ✅ Task title updated confirmation
   - Time: <30 seconds

7. **Test COMPLETE**:
   - Type: "mark 'buy groceries and milk' as complete"
   - Expected: ✅ Task marked complete confirmation
   - Time: <30 seconds

8. **Test DELETE**:
   - Type: "delete the task 'buy groceries and milk'"
   - Expected: ✅ Task deleted confirmation
   - Time: <30 seconds

**Expected**: All CRUD operations work within 30 seconds each

### ✅ Phase 8: Data Integrity Verification

Verify no data loss occurred:

```bash
# Connect to database and count tasks
# Replace $DATABASE_URL with actual connection string
psql $DATABASE_URL -c "SELECT COUNT(*) as task_count FROM tasks;"

# Compare with count taken before removal
# Expected: Same count or higher (if new tasks added during testing)
```

**Expected**: Task count unchanged (no data loss)

### ✅ Phase 9: Code Quality Verification

Verify code reduction and quality improvements:

```bash
# Check lines of code removed
cd /home/bilali/vibe-coding-projects/evolution-of-todo/phase3-ai-chatbot
git diff --stat 002-chatkit-refactor...003-remove-legacy-endpoints

# Expected output similar to:
# backend/main.py                          | 7 deletions
# backend/routes/tasks.py                  | 271 deletions
# frontend/app/(dashboard)/tasks/page.tsx  | 310 deletions
# frontend/components/TaskForm.tsx         | ~100 deletions
# frontend/components/TaskList.tsx         | ~80 deletions
# frontend/components/TaskItem.tsx         | ~120 deletions
# frontend/lib/api.ts                      | ~150 deletions
# Total: ~1000+ lines removed
```

**Expected**: At least 500 lines of code removed (spec SC-004)

### ✅ Phase 10: Security Verification

Confirm security improvements:

```bash
# Count remaining API endpoints
grep -r "@router\." backend/routes/ | wc -l

# Before removal: ~10+ endpoints (tasks + chat + chatkit + auth)
# After removal: ~6 endpoints (chat + chatkit + auth)

# Verify JWT middleware still protects remaining endpoints
curl -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/test-user/chat
# Expected: HTTP Status: 401 Unauthorized (missing JWT)
```

**Expected**:
- Fewer total endpoints (reduced attack surface)
- Authentication still enforced on protected routes

## Success Criteria Validation

Mark each criterion as complete:

- [ ] **SC-001**: Zero legacy REST task endpoints accessible ✅ (Phase 4)
- [ ] **SC-002**: Zero frontend task UI components in codebase ✅ (Phase 1)
- [ ] **SC-003**: Chat provides 100% functional parity ✅ (Phase 7)
- [ ] **SC-004**: Codebase reduced by 500+ lines ✅ (Phase 9)
- [ ] **SC-005**: Build succeeds with no errors ✅ (Phase 3)
- [ ] **SC-006**: Task CRUD operations < 30 seconds via chat ✅ (Phase 7)
- [ ] **SC-007**: Zero data loss ✅ (Phase 8)

## Troubleshooting

### Issue: Frontend build fails with import errors

**Symptom**: `npm run build` fails with "Cannot find module 'TaskForm'"

**Solution**:
1. Search codebase for remaining imports: `grep -r "TaskForm\|TaskList\|TaskItem" frontend/`
2. Remove any remaining import statements
3. Rebuild: `npm run build`

### Issue: Backend fails to start

**Symptom**: `uvicorn main:app` fails with "cannot import name 'tasks'"

**Solution**:
1. Check backend/main.py for remaining tasks imports
2. Remove lines 95-101 (tasks import and router inclusion)
3. Restart: `uvicorn main:app --reload`

### Issue: Chat interface shows errors

**Symptom**: Chat page loads but shows error when sending messages

**Solution**:
1. Verify MCP server is running: `cd backend/tools && python server.py`
2. Check backend logs for MCP connection errors
3. Verify environment variable `MCP_SERVER_URL=http://localhost:8001`
4. Restart both backend and MCP server

### Issue: /tasks route still accessible

**Symptom**: Navigating to /tasks shows old page instead of 404

**Solution**:
1. Verify file deletion: `ls frontend/app/\(dashboard\)/tasks/`
2. Clear Next.js build cache: `rm -rf frontend/.next`
3. Rebuild: `cd frontend && npm run build`
4. Restart dev server: `npm run dev`

## Rollback Procedure

If verification fails and rollback is needed:

```bash
# Restore deleted files from previous branch
git checkout 002-chatkit-refactor -- backend/routes/tasks.py
git checkout 002-chatkit-refactor -- frontend/app/\(dashboard\)/tasks/
git checkout 002-chatkit-refactor -- frontend/components/Task*.tsx

# Restore main.py tasks import
git checkout 002-chatkit-refactor -- backend/main.py

# Restore api.ts task methods
git checkout 002-chatkit-refactor -- frontend/lib/api.ts

# Restart servers
cd backend && uvicorn main:app --reload &
cd frontend && npm run dev &
```

## Deployment Checklist

Before deploying to production:

- [ ] All verification phases pass locally
- [ ] Git commit created with clear message
- [ ] Branch pushed to remote
- [ ] Pull request created with verification results
- [ ] Code review completed
- [ ] CI/CD pipeline passes (if applicable)
- [ ] Staging environment tested
- [ ] Production deployment plan reviewed
- [ ] Rollback plan documented and tested

## Post-Deployment Monitoring

After deploying to production:

1. **Monitor 404 errors**: Check if users are hitting removed endpoints
2. **Monitor chat endpoint**: Verify increased usage of /api/{user_id}/chat
3. **Monitor error rates**: Ensure no spike in application errors
4. **Monitor performance**: Confirm expected performance improvements
5. **User feedback**: Collect feedback on chat-only interface

## Notes

- This is a **one-way migration** - legacy endpoints will not be restored
- Users must transition to chat interface for all task management
- Keep this quickstart guide for future reference when onboarding new developers
- Document any issues encountered during verification for process improvement
