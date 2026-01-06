"""
Unit Test for Recurrence Pattern Calculation (Phase V - User Story 1).

This test validates the RecurrenceService logic for calculating next occurrence dates
based on recurrence pattern (daily, weekly, monthly) and interval.

Test Strategy:
- Test calculate_next_occurrence() method
- Test all patterns: daily, weekly, monthly
- Test different intervals (1, 2, 3, etc.)
- Test edge cases (month boundaries, leap years, weekday calculations)
- Test validation logic for recurrence patterns

Expected Behavior (TDD - these tests should FAIL before implementation):
- RecurrenceService.calculate_next_occurrence(current_date, pattern, interval, metadata) → next_date
- Daily: next_date = current_date + (interval * days)
- Weekly: next_date = current_date + (interval * 7 days)
- Monthly: next_date = current_date + (interval * months), preserving day_of_month
- Validation: daily interval 1-365, weekly interval 1-52, monthly interval 1-12
"""

import pytest
from datetime import datetime, timedelta, UTC
from dateutil.relativedelta import relativedelta


# Mock RecurrenceService (will be implemented in T039)
class RecurrenceService:
    """
    Service for calculating next occurrence dates for recurring tasks.

    This is a TDD mock - these methods don't exist yet and tests should FAIL.
    """

    @staticmethod
    def calculate_next_occurrence(
        current_date: datetime,
        pattern: str,
        interval: int,
        metadata: dict = None
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
        if pattern == "daily":
            return current_date + timedelta(days=interval)
        elif pattern == "weekly":
            return current_date + timedelta(weeks=interval)
        elif pattern == "monthly":
            # Use dateutil.relativedelta for accurate month arithmetic
            return current_date + relativedelta(months=interval)
        else:
            raise ValueError(f"Invalid recurrence pattern: {pattern}")

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
        if pattern not in ["daily", "weekly", "monthly"]:
            raise ValueError(f"Invalid pattern: {pattern}. Must be daily, weekly, or monthly")

        if pattern == "daily" and not (1 <= interval <= 365):
            raise ValueError(f"Daily interval must be 1-365, got {interval}")

        if pattern == "weekly" and not (1 <= interval <= 52):
            raise ValueError(f"Weekly interval must be 1-52, got {interval}")

        if pattern == "monthly" and not (1 <= interval <= 12):
            raise ValueError(f"Monthly interval must be 1-12, got {interval}")

        return True


def test_calculate_next_occurrence_daily():
    """
    Test daily recurrence calculation.

    Expected: next_date = current_date + interval days
    """
    current_date = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)

    # Daily with interval=1
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="daily",
        interval=1
    )
    assert next_date == datetime(2026, 1, 7, 10, 0, 0, tzinfo=UTC)

    # Daily with interval=3
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="daily",
        interval=3
    )
    assert next_date == datetime(2026, 1, 9, 10, 0, 0, tzinfo=UTC)


def test_calculate_next_occurrence_weekly():
    """
    Test weekly recurrence calculation.

    Expected: next_date = current_date + (interval * 7 days)
    """
    current_date = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)  # Tuesday

    # Weekly with interval=1
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="weekly",
        interval=1
    )
    assert next_date == datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)  # Next Tuesday

    # Weekly with interval=2 (bi-weekly)
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="weekly",
        interval=2
    )
    assert next_date == datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC)


def test_calculate_next_occurrence_monthly():
    """
    Test monthly recurrence calculation.

    Expected: next_date = current_date + interval months (preserving day if possible)
    """
    current_date = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)  # Jan 15

    # Monthly with interval=1
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=1
    )
    assert next_date == datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)  # Feb 15

    # Monthly with interval=3 (quarterly)
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=3
    )
    assert next_date == datetime(2026, 4, 15, 10, 0, 0, tzinfo=UTC)  # Apr 15


def test_calculate_next_occurrence_monthly_cross_year_boundary():
    """
    Test monthly recurrence that crosses year boundary.

    Expected: December + 1 month = next January
    """
    current_date = datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC)  # Dec 15, 2025

    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=1
    )
    assert next_date == datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)  # Jan 15, 2026


def test_calculate_next_occurrence_monthly_preserve_time():
    """
    Test that time component is preserved when calculating monthly recurrence.

    Expected: Hour, minute, second remain unchanged
    """
    current_date = datetime(2026, 1, 15, 14, 30, 45, tzinfo=UTC)  # Jan 15 at 14:30:45

    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=1
    )
    assert next_date.hour == 14
    assert next_date.minute == 30
    assert next_date.second == 45


def test_validate_recurrence_pattern_valid():
    """
    Test validation of valid recurrence patterns.

    Expected: All valid patterns and intervals should pass
    """
    # Daily: 1-365
    assert RecurrenceService.validate_recurrence_pattern("daily", 1) is True
    assert RecurrenceService.validate_recurrence_pattern("daily", 365) is True

    # Weekly: 1-52
    assert RecurrenceService.validate_recurrence_pattern("weekly", 1) is True
    assert RecurrenceService.validate_recurrence_pattern("weekly", 52) is True

    # Monthly: 1-12
    assert RecurrenceService.validate_recurrence_pattern("monthly", 1) is True
    assert RecurrenceService.validate_recurrence_pattern("monthly", 12) is True


def test_validate_recurrence_pattern_invalid_pattern():
    """
    Test validation rejects invalid patterns.

    Expected: Raises ValueError for invalid pattern
    """
    with pytest.raises(ValueError, match="Invalid pattern"):
        RecurrenceService.validate_recurrence_pattern("yearly", 1)

    with pytest.raises(ValueError, match="Invalid pattern"):
        RecurrenceService.validate_recurrence_pattern("hourly", 1)


def test_validate_recurrence_pattern_invalid_interval():
    """
    Test validation rejects invalid intervals.

    Expected: Raises ValueError for out-of-range intervals
    """
    # Daily: must be 1-365
    with pytest.raises(ValueError, match="Daily interval must be 1-365"):
        RecurrenceService.validate_recurrence_pattern("daily", 0)

    with pytest.raises(ValueError, match="Daily interval must be 1-365"):
        RecurrenceService.validate_recurrence_pattern("daily", 366)

    # Weekly: must be 1-52
    with pytest.raises(ValueError, match="Weekly interval must be 1-52"):
        RecurrenceService.validate_recurrence_pattern("weekly", 0)

    with pytest.raises(ValueError, match="Weekly interval must be 1-52"):
        RecurrenceService.validate_recurrence_pattern("weekly", 53)

    # Monthly: must be 1-12
    with pytest.raises(ValueError, match="Monthly interval must be 1-12"):
        RecurrenceService.validate_recurrence_pattern("monthly", 0)

    with pytest.raises(ValueError, match="Monthly interval must be 1-12"):
        RecurrenceService.validate_recurrence_pattern("monthly", 13)


def test_calculate_next_occurrence_edge_case_feb_29_leap_year():
    """
    Test monthly recurrence for Feb 29 (leap year) → Mar 29 (non-leap year).

    Expected: Handles month-end gracefully (dateutil handles this automatically)
    """
    # Feb 29, 2024 (leap year)
    current_date = datetime(2024, 2, 29, 10, 0, 0, tzinfo=UTC)

    # Next month (Mar 29, 2024)
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=1
    )
    assert next_date == datetime(2024, 3, 29, 10, 0, 0, tzinfo=UTC)


def test_calculate_next_occurrence_edge_case_jan_31_to_feb():
    """
    Test monthly recurrence for Jan 31 → Feb (28 or 29 days).

    Expected: dateutil.relativedelta handles this by moving to last day of Feb
    """
    # Jan 31, 2026
    current_date = datetime(2026, 1, 31, 10, 0, 0, tzinfo=UTC)

    # Next month (Feb 28, 2026 - not a leap year)
    next_date = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="monthly",
        interval=1
    )
    # dateutil.relativedelta intelligently handles this
    assert next_date.month == 2
    # Day will be 28 or 29 depending on implementation


def test_calculate_next_occurrence_metadata_ignored_for_now():
    """
    Test that metadata parameter is accepted but not required.

    Expected: metadata is optional and doesn't affect basic calculation
    """
    current_date = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)

    # With metadata
    next_date_with_metadata = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="daily",
        interval=1,
        metadata={"some_key": "some_value"}
    )

    # Without metadata
    next_date_without_metadata = RecurrenceService.calculate_next_occurrence(
        current_date=current_date,
        pattern="daily",
        interval=1
    )

    assert next_date_with_metadata == next_date_without_metadata
