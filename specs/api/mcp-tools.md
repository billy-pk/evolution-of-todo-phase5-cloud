# MCP Tools Specification

The MCP server exposes tools to allow the AI agent to manipulate tasks in the existing database.

---

## Tool: add_task
Purpose:
Create a new task.

Parameters:
- user_id (string, required)
- title (string, required)
- description (string, optional)

Output:
- task_id
- status ("created")
- title

---

## Tool: list_tasks
Purpose:
List tasks for a user.

Parameters:
- user_id (string, required)
- status ("all", "pending", "completed")

Output:
List of task objects.

---

## Tool: update_task
Purpose:
Modify title or description.

Parameters:
- user_id (string, required)
- task_id (int, required)
- title (string, optional)
- description (string, optional)

Output:
- task_id
- status ("updated")
- title

---

## Tool: complete_task
Purpose:
Mark task as completed.

Parameters:
- user_id (string, required)
- task_id (int, required)

Output:
- task_id
- status ("completed")
- title

---

## Tool: delete_task
Purpose:
Delete a task.

Parameters:
- user_id (string, required)
- task_id (int, required)

Output:
- task_id
- status ("deleted")
- title

---

## Security Rules
- All tools verify user ownership
- Tools must not leak data across users
