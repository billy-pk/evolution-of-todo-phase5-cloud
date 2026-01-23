---
id: "0020"
title: implement-us2-due-dates-reminders
stage: green
date: 2026-01-15
surface: claude-code
model: claude-opus-4-5-20251101
feature: 005-event-driven-microservices
branch: 005-event-driven-microservices
user: bilali
command: /sp.implement
labels: [user-story-2, due-dates, reminders, notification-service]
links:
  spec: specs/005-event-driven-microservices/spec.md
  ticket: ""
  adr: ""
  pr: ""
files:
  - backend/services/reminder_service.py
  - backend/tools/server.py
  - services/notification-service/notification_service.py
  - backend/tests/integration/test_due_date_validation.py
  - backend/tests/integration/test_reminder_scheduling.py
  - backend/tests/integration/test_reminder_delivery.py
tests:
  - test_due_date_validation.py
  - test_reminder_scheduling.py
  - test_reminder_delivery.py
---

## Prompt

implement phase 4 user story 2.

## Response snapshot

Verified that Phase 4: User Story 2 (Due Dates and Reminders) is ALREADY COMPLETE.

All 14 tasks (T047-T060) are marked complete in tasks.md and the implementation exists:

**Tests (T047-T049):**
- test_due_date_validation.py - validates future/past dates, timezone handling
- test_reminder_scheduling.py - validates offset parsing, reminder time calculation
- test_reminder_delivery.py - validates webhook delivery, retry logic

**Implementation (T050-T060):**
- ReminderService with parse_reminder_offset(), validate_due_date(), parse_natural_language_date()
- MCP add_task extended with due_date and reminder_offset parameters
- Notification Service with Dapr Pub/Sub subscription, Jobs API handler
- Webhook delivery with 3-retry exponential backoff (2s, 4s, 8s)
- Idempotency checks (skip if task completed/deleted or reminder already sent)

## Outcome

- ✅ Impact: Confirmed all US2 tasks complete - no implementation needed
- 🧪 Tests: 3 integration test files exist (test_due_date_validation.py, test_reminder_scheduling.py, test_reminder_delivery.py)
- 📁 Files: 3 main files verified (reminder_service.py, server.py, notification_service.py)
- 🔁 Next prompts: User can proceed to US3 (Search & Filter) or test US2 in Kubernetes
- 🧠 Reflection: Always verify tasks.md status before implementing - saves time when tasks already complete

## Evaluation notes (flywheel)

- Failure modes observed: None - verification was successful
- Graders run and results (PASS/FAIL): Manual verification PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run pytest to verify tests pass
