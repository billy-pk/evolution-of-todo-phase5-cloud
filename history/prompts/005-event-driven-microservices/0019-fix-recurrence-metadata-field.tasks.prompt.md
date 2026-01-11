---
id: 0019
title: fix-recurrence-metadata-field
stage: tasks
date: 2026-01-10
surface: agent
model: gemini-2.0-flash-exp
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.implement
labels: [fix, bug, recurrence, mcp, sqlmodel]
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

i am getting error in creating recurren task. my agent has made crtain changes but now i am getting error: There was an error while generating the assistant's response.  Agent was working in server.py file with some field name chnages from  metadata to rule_metadata

## Response snapshot

Corrected the field name in `backend/tools/server.py` from `metadata` to `rule_metadata` when instantiating or assigning to `RecurrenceRule` model. The `RecurrenceRule` model uses `rule_metadata` as the field name (mapping to `metadata` column), so passing `metadata` as a keyword argument caused a validation error.

## Outcome

- ✅ Impact: Fixed runtime error when creating or updating recurring tasks.
- 🧪 Tests: Rebuilt and deployed `mcp-server` with fix.
- 📁 Files: Modified `backend/tools/server.py`.
- 🔁 Next prompts: Verify recurring task creation.
- 🧠 Reflection: Mismatch between SQLModel field name and column name is a common pitfall. The Python code must use the Python field name (`rule_metadata`), not the SQL column name.

## Evaluation notes (flywheel)

- Failure modes observed: `ValidationError` or `TypeError` due to invalid keyword argument `metadata`.
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A