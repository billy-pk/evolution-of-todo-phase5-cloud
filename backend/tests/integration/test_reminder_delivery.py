"""
Integration Test for Reminder Delivery (Phase V - User Story 2).

This test validates that reminders are delivered correctly via the Notification Service:
- Reminder jobs are processed by Dapr Jobs API
- Notifications are delivered via webhook with correct payload
- Reminder status is updated (pending → sent/failed)
- Idempotency checks prevent duplicate deliveries
- Retry logic handles webhook failures with exponential backoff
- Reminders are skipped if task is completed or deleted

Test Strategy:
- Create tasks and reminders in database
- Simulate Dapr Jobs API calling notification service endpoint
- Mock webhook delivery to test success and failure scenarios
- Verify database state changes (status updates, sent_at timestamps)
- Test edge cases (task deleted, task completed, already sent)
- Validate retry logic and backoff timing

Expected Behavior (TDD - these tests should FAIL before implementation):
- Notification Service processes reminder delivery via /api/jobs/reminder
- Successful delivery updates status to 'sent' and sets sent_at timestamp
- Failed delivery after retries updates status to 'failed' and increments retry_count
- Idempotency: Already sent reminders are skipped
- Completed tasks skip reminder delivery (idempotency check)
- Deleted tasks fail reminder delivery gracefully
"""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session, select
from db import engine
from models import Task, Reminder
import httpx


@pytest.fixture
def db_session():
    """Fixture to provide a clean database session for each test."""
    with Session(engine) as session:
        yield session
        # Cleanup after test
        session.rollback()


@pytest.fixture
def test_user_id():
    """Fixture for test user ID."""
    return f"test-user-{uuid4()}"


@pytest.fixture
def sample_task(db_session: Session, test_user_id: str):
    """Fixture to create a sample task with future due date."""
    due_date = datetime.now(UTC) + timedelta(hours=2)
    task = Task(
        user_id=test_user_id,
        title="Submit quarterly report",
        description="Q4 2025 financial report",
        completed=False,
        priority="high",
        tags=["work", "urgent"],
        due_date=due_date
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def sample_reminder(db_session: Session, sample_task: Task, test_user_id: str):
    """Fixture to create a sample pending reminder."""
    reminder_time = datetime.now(UTC) + timedelta(hours=1)
    reminder = Reminder(
        task_id=sample_task.id,
        user_id=test_user_id,
        reminder_time=reminder_time,
        status="pending",
        delivery_method="webhook",
        retry_count=0
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.refresh(reminder)
    return reminder


@pytest.mark.asyncio
async def test_reminder_delivery_success(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test successful reminder delivery updates status to 'sent'.

    Expected:
    - Webhook is called with correct payload
    - Reminder status is updated to 'sent'
    - sent_at timestamp is set
    - retry_count remains 0 (first attempt succeeds)
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mock successful webhook response
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Process reminder delivery
        result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

        # Assertions on result
        assert result["status"] == "success", f"Expected success, got: {result}"
        assert "delivered successfully" in result["message"].lower()

        # Verify webhook was called
        assert mock_post.called, "Webhook should have been called"
        call_args = mock_post.call_args
        webhook_payload = call_args.kwargs["json"]
        assert webhook_payload["reminder_id"] == str(sample_reminder.id)
        assert webhook_payload["task_id"] == str(sample_task.id)
        assert webhook_payload["user_id"] == sample_task.user_id
        assert webhook_payload["task_title"] == sample_task.title

        # Refresh reminder from database
        db_session.refresh(sample_reminder)

        # Verify database state
        assert sample_reminder.status == "sent", f"Status should be 'sent', got {sample_reminder.status}"
        assert sample_reminder.sent_at is not None, "sent_at should be set"
        assert sample_reminder.retry_count == 0, "retry_count should be 0 (first attempt succeeded)"


@pytest.mark.asyncio
async def test_reminder_delivery_idempotency_already_sent(db_session: Session, sample_reminder: Reminder):
    """
    Test that already sent reminders are skipped (idempotency).

    Expected:
    - process_reminder_delivery returns success without calling webhook
    - Reminder status remains 'sent'
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mark reminder as already sent
    sample_reminder.status = "sent"
    sample_reminder.sent_at = datetime.now(UTC)
    db_session.commit()

    # Mock webhook (should NOT be called)
    with patch('httpx.AsyncClient.post') as mock_post:
        # Process reminder delivery
        result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

        # Assertions
        assert result["status"] == "success", "Should return success (idempotent)"
        assert "already sent" in result["message"].lower()

        # Verify webhook was NOT called
        assert not mock_post.called, "Webhook should NOT be called for already sent reminder"


@pytest.mark.asyncio
async def test_reminder_delivery_skip_completed_task(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that reminders are skipped if task is already completed.

    Expected:
    - process_reminder_delivery skips delivery
    - Reminder status is updated to 'sent' (task completed, no need to remind)
    - Webhook is NOT called
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mark task as completed
    sample_task.completed = True
    db_session.commit()

    # Mock webhook (should NOT be called)
    with patch('httpx.AsyncClient.post') as mock_post:
        # Process reminder delivery
        result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

        # Assertions
        assert result["status"] == "success", "Should return success (task completed)"
        assert "completed" in result["message"].lower()

        # Verify webhook was NOT called
        assert not mock_post.called, "Webhook should NOT be called for completed task"

        # Refresh reminder from database
        db_session.refresh(sample_reminder)

        # Verify status updated to 'sent' (completed = no need to remind)
        assert sample_reminder.status == "sent", f"Status should be 'sent', got {sample_reminder.status}"
        assert sample_reminder.sent_at is not None, "sent_at should be set"


@pytest.mark.asyncio
async def test_reminder_delivery_task_deleted(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that reminders fail gracefully if task is deleted.

    Expected:
    - process_reminder_delivery returns error
    - Reminder status is updated to 'failed'
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Delete task
    db_session.delete(sample_task)
    db_session.commit()

    # Process reminder delivery
    result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

    # Assertions
    assert result["status"] == "error", "Should return error (task deleted)"
    assert "not found" in result["message"].lower() or "deleted" in result["message"].lower()

    # Refresh reminder from database
    db_session.refresh(sample_reminder)

    # Verify status updated to 'failed'
    assert sample_reminder.status == "failed", f"Status should be 'failed', got {sample_reminder.status}"


@pytest.mark.asyncio
async def test_reminder_delivery_webhook_failure_retries(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that webhook failures trigger retry logic with exponential backoff.

    Expected:
    - Webhook is called multiple times (max 4 attempts: 1 initial + 3 retries)
    - After all retries fail, status is updated to 'failed'
    - retry_count is incremented to 4
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mock webhook failure (all attempts fail)
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 503  # Service Unavailable
        mock_response.text = "Service Unavailable"
        mock_post.return_value = mock_response

        # Mock time.sleep to avoid waiting during test
        with patch('time.sleep') as mock_sleep:
            # Process reminder delivery
            result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

            # Assertions
            assert result["status"] == "error", "Should return error after all retries fail"
            assert "failed" in result["message"].lower()

            # Verify webhook was called 4 times (1 initial + 3 retries)
            assert mock_post.call_count == 4, f"Webhook should be called 4 times, got {mock_post.call_count}"

            # Verify exponential backoff sleep calls
            # Expected: sleep(2), sleep(4), sleep(8)
            assert mock_sleep.call_count == 3, f"Should sleep 3 times, got {mock_sleep.call_count}"
            sleep_durations = [call.args[0] for call in mock_sleep.call_args_list]
            assert sleep_durations == [2, 4, 8], f"Expected backoff [2, 4, 8], got {sleep_durations}"

            # Refresh reminder from database
            db_session.refresh(sample_reminder)

            # Verify database state
            assert sample_reminder.status == "failed", f"Status should be 'failed', got {sample_reminder.status}"
            assert sample_reminder.retry_count == 4, f"retry_count should be 4, got {sample_reminder.retry_count}"


@pytest.mark.asyncio
async def test_reminder_delivery_webhook_timeout(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that webhook timeouts trigger retry logic.

    Expected:
    - httpx.TimeoutException triggers retry
    - After retries, status is 'failed'
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mock webhook timeout
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        # Mock time.sleep to avoid waiting
        with patch('time.sleep') as mock_sleep:
            # Process reminder delivery
            result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

            # Assertions
            assert result["status"] == "error", "Should return error after timeouts"

            # Verify webhook was called 4 times
            assert mock_post.call_count == 4, f"Webhook should be called 4 times, got {mock_post.call_count}"

            # Refresh reminder from database
            db_session.refresh(sample_reminder)

            # Verify status is 'failed'
            assert sample_reminder.status == "failed", f"Status should be 'failed', got {sample_reminder.status}"


@pytest.mark.asyncio
async def test_reminder_delivery_webhook_payload_structure(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that webhook payload contains all required fields.

    Expected:
    - Payload includes: reminder_id, task_id, user_id, task_title, task_description, due_date, reminder_time, message
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mock successful webhook
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Process reminder delivery
        await process_reminder_delivery(reminder_id=str(sample_reminder.id))

        # Get webhook payload
        call_args = mock_post.call_args
        webhook_payload = call_args.kwargs["json"]

        # Verify required fields
        required_fields = ["reminder_id", "task_id", "user_id", "task_title", "task_description", "due_date", "reminder_time", "message"]
        for field in required_fields:
            assert field in webhook_payload, f"Webhook payload missing required field: {field}"

        # Verify field types and values
        assert webhook_payload["reminder_id"] == str(sample_reminder.id)
        assert webhook_payload["task_id"] == str(sample_task.id)
        assert webhook_payload["user_id"] == sample_task.user_id
        assert webhook_payload["task_title"] == sample_task.title
        assert webhook_payload["task_description"] == sample_task.description
        assert sample_task.title in webhook_payload["message"], "Message should include task title"


@pytest.mark.asyncio
async def test_reminder_delivery_partial_success_on_retry(db_session: Session, sample_reminder: Reminder, sample_task: Task):
    """
    Test that delivery succeeds on second attempt (first fails, second succeeds).

    Expected:
    - First attempt fails (503)
    - Second attempt succeeds (200)
    - Status is 'sent', retry_count is 1
    """
    # Import notification service functions
    from services.notification_service.notification_service import process_reminder_delivery

    # Mock webhook: first call fails, second succeeds
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_fail = MagicMock()
        mock_fail.status_code = 503
        mock_success = MagicMock()
        mock_success.status_code = 200

        mock_post.side_effect = [mock_fail, mock_success]  # First fails, second succeeds

        # Mock time.sleep
        with patch('time.sleep'):
            # Process reminder delivery
            result = await process_reminder_delivery(reminder_id=str(sample_reminder.id))

            # Assertions
            assert result["status"] == "success", "Should succeed on retry"

            # Verify webhook was called 2 times
            assert mock_post.call_count == 2, f"Webhook should be called 2 times, got {mock_post.call_count}"

            # Refresh reminder from database
            db_session.refresh(sample_reminder)

            # Verify status is 'sent' and retry_count is 1
            assert sample_reminder.status == "sent", f"Status should be 'sent', got {sample_reminder.status}"
            assert sample_reminder.retry_count == 1, f"retry_count should be 1, got {sample_reminder.retry_count}"


def test_integration_query_reminders_needing_delivery(db_session: Session, test_user_id: str):
    """
    Integration test: Query pending reminders that are due for delivery.

    Expected: Can query reminders where status='pending' and reminder_time <= now
    """
    # Create task
    task = Task(
        user_id=test_user_id,
        title="Test task",
        completed=False,
        due_date=datetime.now(UTC) + timedelta(hours=1)
    )
    db_session.add(task)
    db_session.commit()

    # Create reminders at different times
    now = datetime.now(UTC)

    # Reminder due now (should be delivered)
    reminder_due = Reminder(
        task_id=task.id,
        user_id=test_user_id,
        reminder_time=now - timedelta(minutes=1),  # 1 minute ago
        status="pending"
    )

    # Reminder due later (should NOT be delivered yet)
    reminder_future = Reminder(
        task_id=task.id,
        user_id=test_user_id,
        reminder_time=now + timedelta(hours=1),
        status="pending"
    )

    # Reminder already sent (should NOT be re-delivered)
    reminder_sent = Reminder(
        task_id=task.id,
        user_id=test_user_id,
        reminder_time=now - timedelta(hours=2),
        status="sent",
        sent_at=now - timedelta(hours=2)
    )

    db_session.add_all([reminder_due, reminder_future, reminder_sent])
    db_session.commit()

    # Query reminders needing delivery (pending AND due)
    stmt = select(Reminder).where(
        Reminder.status == "pending",
        Reminder.reminder_time <= now
    ).order_by(Reminder.reminder_time)

    reminders_to_deliver = db_session.exec(stmt).all()

    # Assertions
    assert len(reminders_to_deliver) == 1, f"Should have 1 reminder to deliver, got {len(reminders_to_deliver)}"
    assert reminders_to_deliver[0].id == reminder_due.id, "Should return the reminder due now"
