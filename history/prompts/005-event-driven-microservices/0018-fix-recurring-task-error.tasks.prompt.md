---
id: 0018
title: fix-recurring-task-error
stage: tasks
date: 2026-01-10
surface: agent
model: gemini-2.0-flash-exp
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.implement
labels: [fix, bug, recurrence, mcp]
links:
  spec: specs/005-event-driven-microservices/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - backend/tools/server.py
tests:
 - manual verification
---

## Prompt

/sp.implement i tried to create a recurrent task but got foloowing: It seems I need to specify a recurrence interval for the daily standup. Let me fix that for you.

It seems there's an issue with creating a task with a recurrence pattern. I'll try creating it without recurrence for now.

I've created the task "Daily standup" for you, due tomorrow at 9 AM. Unfortunately, I couldn't set it as recurring due to an issue. Let me know if there's anything else I can do for you!

## Response snapshot

Fixed the `add_task` and `update_task` tools in `backend/tools/server.py` to default `recurrence_interval` to 1 if `recurrence_pattern` is provided but `recurrence_interval` is missing. This addresses the issue where the LLM agent fails to provide the interval when asking for "daily" tasks.

Rebuilt and redeployed `mcp-server`.

## Outcome

- ✅ Impact: Recurring tasks can now be created via chat without explicitly specifying an interval (defaults to 1).
- 🧪 Tests: Confirmed logic in `server.py` handles the default.
- 📁 Files: Modified `backend/tools/server.py`.
- 🔁 Next prompts: Continue with remaining user stories or testing.
- 🧠 Reflection: The tool validation was strict but the LLM behavior was predictable (omitting implied parameters). Making the tool more robust improves the UX.

## Evaluation notes (flywheel)

- Failure modes observed: LLM failed to provide required parameter `recurrence_interval` for "daily" pattern.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A