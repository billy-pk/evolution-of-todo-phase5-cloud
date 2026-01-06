"""
Recurrence Service (Phase V - User Story 1).

This service handles all recurrence-related logic:
- Calculate next occurrence dates based on recurrence patterns
- Validate recurrence patterns and intervals
- Support daily, weekly, monthly patterns

Architecture:
- Stateless service (no state stored in service, all in database)
- Uses dateutil.relativedelta for accurate date arithmetic
- Validates patterns and intervals according to spec
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Optional


class RecurrenceService:
    """
    Service for calculating next occurrence dates for recurring tasks.
    """

    # Validation ranges
    VALID_PATTERNS = ["daily", "weekly", "monthly"]
    DAILY_INTERVAL_RANGE = (1, 365)
    WEEKLY_INTERVAL_RANGE = (1, 52)
    MONTHLY_INTERVAL_RANGE = (1, 12)

    @staticmethod
    def calculate_next_occurrence(
        current_date: datetime,
        pattern: str,
        interval: int,
        metadata: Optional[Dict] = None
    ) -> datetime:
        """
        Calculate the next occurrence date based on recurrence pattern.

        Args:
            current_date: Current/completed task due date
            pattern: "daily", "weekly", or "monthly"
            interval: Number of pattern units (e.g., 2 for bi-weekly)
            metadata: Additional pattern-specific data (weekday, day_of_month)

        Returns:
            Next occurrence datetime

        Raises:
            ValueError: If pattern is invalid or interval is out of range
        """
        # Validate pattern
        if pattern not in RecurrenceService.VALID_PATTERNS:
            raise ValueError(
                f"Invalid recurrence pattern: {pattern}. "
                f"Must be one of: {', '.join(RecurrenceService.VALID_PATTERNS)}"
            )

        # Calculate next occurrence based on pattern
        if pattern == "daily":
            return current_date + timedelta(days=interval)

        elif pattern == "weekly":
            return current_date + timedelta(weeks=interval)

        elif pattern == "monthly":
            # Use dateutil.relativedelta for accurate month arithmetic
            # Handles month-end edge cases automatically (e.g., Jan 31 + 1 month = Feb 28/29)
            return current_date + relativedelta(months=interval)

        else:
            # Should never reach here due to validation above
            raise ValueError(f"Unsupported pattern: {pattern}")

    @staticmethod
    def validate_recurrence_pattern(pattern: str, interval: int) -> bool:
        """
        Validate recurrence pattern and interval.

        Args:
            pattern: "daily", "weekly", or "monthly"
            interval: Number of pattern units

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Validate pattern
        if pattern not in RecurrenceService.VALID_PATTERNS:
            raise ValueError(
                f"Invalid pattern: {pattern}. "
                f"Must be one of: {', '.join(RecurrenceService.VALID_PATTERNS)}"
            )

        # Validate interval ranges
        if pattern == "daily":
            min_val, max_val = RecurrenceService.DAILY_INTERVAL_RANGE
            if not (min_val <= interval <= max_val):
                raise ValueError(
                    f"Daily interval must be {min_val}-{max_val}, got {interval}"
                )

        elif pattern == "weekly":
            min_val, max_val = RecurrenceService.WEEKLY_INTERVAL_RANGE
            if not (min_val <= interval <= max_val):
                raise ValueError(
                    f"Weekly interval must be {min_val}-{max_val}, got {interval}"
                )

        elif pattern == "monthly":
            min_val, max_val = RecurrenceService.MONTHLY_INTERVAL_RANGE
            if not (min_val <= interval <= max_val):
                raise ValueError(
                    f"Monthly interval must be {min_val}-{max_val}, got {interval}"
                )

        return True

    @staticmethod
    def create_recurrence_metadata(
        pattern: str,
        current_date: datetime,
        additional_data: Optional[Dict] = None
    ) -> Dict:
        """
        Create metadata dict for a recurrence pattern.

        Metadata stores pattern-specific information like:
        - Weekly: weekday name (e.g., "Monday")
        - Monthly: day_of_month (e.g., 15 for 15th of month)

        Args:
            pattern: "daily", "weekly", or "monthly"
            current_date: Reference date to extract metadata from
            additional_data: Optional dict with additional metadata

        Returns:
            Metadata dict
        """
        metadata = {}

        if pattern == "weekly":
            # Store weekday name for clarity
            metadata["weekday"] = current_date.strftime("%A")

        elif pattern == "monthly":
            # Store day of month
            metadata["day_of_month"] = current_date.day

        # Merge with additional_data if provided
        if additional_data:
            metadata.update(additional_data)

        return metadata
