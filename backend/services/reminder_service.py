"""
ReminderService - Schedule and manage task reminders via Dapr Jobs API.

This service handles:
1. Parsing natural language reminder offsets ("1 hour before", "30 minutes before")
2. Calculating trigger times based on due dates and offsets
3. Scheduling reminders via Dapr Jobs API
4. Validating due dates (reject past dates unless explicitly allowed)
5. Natural language date parsing with dateparser library

Architecture:
- Stateless service (no in-memory state)
- Persists reminders to PostgreSQL database
- Schedules jobs via Dapr Jobs API for reliable delivery
- Notification Service receives job triggers and delivers reminders
- Idempotent: Safe to call multiple times with same parameters

Dependencies:
- dateutil.relativedelta for date arithmetic
- dateparser for natural language date parsing
- Dapr client for Jobs API scheduling
- SQLModel for database operations
"""

import re
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta
import dateparser


class ReminderService:
    """
    Service for parsing reminder offsets, validating due dates, and scheduling reminders.

    Supports natural language date parsing and reminder offset formats.
    All times are handled in UTC for consistency.
    """

    # Valid reminder offset patterns
    OFFSET_PATTERNS = {
        "minutes": r"(\d+)\s*minutes?\s+before",
        "hours": r"(\d+)\s*hours?\s+before",
        "days": r"(\d+)\s*days?\s+before",
    }

    @staticmethod
    def parse_reminder_offset(offset_str: str) -> Optional[timedelta]:
        """
        Parse natural language reminder offset into timedelta.

        Args:
            offset_str: Natural language offset (e.g., "1 hour before", "30 minutes before")

        Returns:
            timedelta representing the offset, or None if invalid format

        Examples:
            >>> parse_reminder_offset("1 hour before")
            timedelta(hours=1)
            >>> parse_reminder_offset("30 minutes before")
            timedelta(minutes=30)
            >>> parse_reminder_offset("2 days before")
            timedelta(days=2)
        """
        if not offset_str:
            return None

        offset_lower = offset_str.lower().strip()

        # Try minutes pattern
        match = re.search(ReminderService.OFFSET_PATTERNS["minutes"], offset_lower)
        if match:
            minutes = int(match.group(1))
            return timedelta(minutes=minutes)

        # Try hours pattern
        match = re.search(ReminderService.OFFSET_PATTERNS["hours"], offset_lower)
        if match:
            hours = int(match.group(1))
            return timedelta(hours=hours)

        # Try days pattern
        match = re.search(ReminderService.OFFSET_PATTERNS["days"], offset_lower)
        if match:
            days = int(match.group(1))
            return timedelta(days=days)

        return None

    @staticmethod
    def calculate_reminder_time(
        due_date: datetime,
        offset: timedelta
    ) -> datetime:
        """
        Calculate reminder trigger time by subtracting offset from due date.

        Args:
            due_date: Task due date (timezone-aware datetime)
            offset: Time before due date to trigger reminder

        Returns:
            datetime when reminder should trigger (timezone-aware)

        Examples:
            >>> due = datetime(2026, 1, 10, 15, 0, 0, tzinfo=UTC)
            >>> offset = timedelta(hours=1)
            >>> calculate_reminder_time(due, offset)
            datetime(2026, 1, 10, 14, 0, 0, tzinfo=UTC)
        """
        reminder_time = due_date - offset
        return reminder_time

    @staticmethod
    def validate_due_date(
        due_date: datetime,
        allow_past: bool = False,
        reference_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that due date is in the future (unless explicitly allowed).

        Args:
            due_date: Task due date to validate
            allow_past: If True, allow past dates (default False)
            reference_time: Reference time for comparison (default: now in UTC)

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])

        Examples:
            >>> future_date = datetime.now(UTC) + timedelta(days=1)
            >>> validate_due_date(future_date)
            (True, None)

            >>> past_date = datetime.now(UTC) - timedelta(days=1)
            >>> validate_due_date(past_date)
            (False, "Due date must be in the future")

            >>> validate_due_date(past_date, allow_past=True)
            (True, None)
        """
        if reference_time is None:
            reference_time = datetime.now(UTC)

        # Ensure both datetimes are timezone-aware for comparison
        if due_date.tzinfo is None:
            return False, "Due date must be timezone-aware (ISO8601 with timezone)"

        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=UTC)

        # Check if due date is in the past
        if due_date < reference_time and not allow_past:
            return False, "Due date must be in the future"

        return True, None

    @staticmethod
    def parse_natural_language_date(
        date_str: str,
        timezone: str = "UTC",
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Parse natural language date strings into datetime objects.

        Uses dateparser library for robust parsing of formats like:
        - "tomorrow at 5pm"
        - "next Friday at 3:30pm"
        - "in 2 days"
        - "January 15th at noon"
        - ISO8601 strings (passthrough)

        Args:
            date_str: Natural language date string
            timezone: Target timezone (default UTC)
            reference_time: Reference time for relative dates (default: now)

        Returns:
            datetime object (timezone-aware) or None if parsing fails

        Examples:
            >>> parse_natural_language_date("tomorrow at 5pm")
            datetime(2026, 1, 8, 17, 0, 0, tzinfo=UTC)

            >>> parse_natural_language_date("2026-01-10T15:00:00Z")
            datetime(2026, 1, 10, 15, 0, 0, tzinfo=UTC)
        """
        if not date_str:
            return None

        # Try parsing with dateparser
        settings = {
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future"  # Prefer future dates for relative parsing
        }

        if reference_time:
            settings["RELATIVE_BASE"] = reference_time

        parsed_date = dateparser.parse(date_str, settings=settings)

        return parsed_date

    @staticmethod
    def validate_reminder_offset(
        offset_str: str,
        due_date: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that reminder offset is valid and results in future reminder time.

        Args:
            offset_str: Natural language offset (e.g., "1 hour before")
            due_date: Task due date

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])

        Examples:
            >>> future_due = datetime.now(UTC) + timedelta(days=1)
            >>> validate_reminder_offset("1 hour before", future_due)
            (True, None)

            >>> validate_reminder_offset("invalid format", future_due)
            (False, "Invalid reminder offset format")
        """
        # Parse offset
        offset = ReminderService.parse_reminder_offset(offset_str)
        if offset is None:
            return False, "Invalid reminder offset format. Use format like '1 hour before', '30 minutes before', or '1 day before'"

        # Calculate reminder time
        reminder_time = ReminderService.calculate_reminder_time(due_date, offset)

        # Check if reminder time is in the future
        now = datetime.now(UTC)
        if reminder_time < now:
            return False, f"Reminder time ({reminder_time.isoformat()}) is in the past. Due date might be too soon or offset too large."

        return True, None

    @staticmethod
    def create_reminder_metadata(
        task_id: str,
        user_id: str,
        task_title: str,
        due_date: datetime,
        reminder_offset: str
    ) -> Dict[str, Any]:
        """
        Create metadata dictionary for Dapr Jobs API payload.

        Args:
            task_id: Task UUID
            user_id: User ID for isolation
            task_title: Task title for notification content
            due_date: Task due date
            reminder_offset: Natural language offset

        Returns:
            Dict containing all reminder context for Notification Service

        Example:
            {
                "task_id": "uuid...",
                "user_id": "user123",
                "task_title": "Review presentation",
                "due_date": "2026-01-10T15:00:00Z",
                "reminder_offset": "1 hour before",
                "reminder_time": "2026-01-10T14:00:00Z"
            }
        """
        offset = ReminderService.parse_reminder_offset(reminder_offset)
        reminder_time = ReminderService.calculate_reminder_time(due_date, offset) if offset else due_date

        return {
            "task_id": task_id,
            "user_id": user_id,
            "task_title": task_title,
            "due_date": due_date.isoformat(),
            "reminder_offset": reminder_offset,
            "reminder_time": reminder_time.isoformat()
        }
