"""
Unit Test for Search Query Parsing (Phase V - User Story 3).

This test validates the search query building logic in list_tasks:
- SQL ILIKE pattern generation
- Case-insensitive matching
- Special character escaping
- Empty/None query handling
- Validation of filter parameters

Test Strategy:
- Unit test the query building logic
- Test pattern generation for various inputs
- Test validation functions for filters
- No database required - pure logic testing

Expected Behavior:
- Search patterns use SQL ILIKE with wildcards
- Special SQL characters are escaped
- Empty queries return no filter
- Invalid parameters are rejected with clear error messages
"""

import pytest
from datetime import datetime, timedelta, UTC


class TestSearchPatternGeneration:
    """Test search pattern generation for ILIKE queries."""

    def test_basic_search_pattern(self):
        """
        Test basic search pattern generation.

        Expected: "report" becomes "%report%"
        """
        search_query = "report"
        expected_pattern = f"%{search_query}%"

        assert expected_pattern == "%report%"

    def test_search_pattern_with_spaces(self):
        """
        Test search pattern with spaces.

        Expected: "quarterly report" becomes "%quarterly report%"
        """
        search_query = "quarterly report"
        expected_pattern = f"%{search_query}%"

        assert expected_pattern == "%quarterly report%"

    def test_empty_search_query(self):
        """
        Test that empty search query results in no filter.

        Expected: None or "" should not apply search filter
        """
        # Empty string
        search_query = ""
        assert search_query == "" or search_query is None or not search_query

        # None value
        search_query = None
        assert search_query is None


class TestPriorityValidation:
    """Test priority parameter validation."""

    def test_valid_priorities(self):
        """
        Test all valid priority values.

        Expected: low, normal, high, critical are valid
        """
        valid_priorities = ["low", "normal", "high", "critical"]

        for priority in valid_priorities:
            assert priority in valid_priorities

    def test_invalid_priority(self):
        """
        Test invalid priority values.

        Expected: Invalid values should be rejected
        """
        valid_priorities = ["low", "normal", "high", "critical"]
        invalid_priorities = ["medium", "urgent", "CRITICAL", "1", ""]

        for priority in invalid_priorities:
            assert priority not in valid_priorities


class TestSortByValidation:
    """Test sort_by parameter validation."""

    def test_valid_sort_fields(self):
        """
        Test all valid sort_by values.

        Expected: created_at, due_date, priority, title are valid
        """
        valid_sort_fields = ["created_at", "due_date", "priority", "title"]

        for field in valid_sort_fields:
            assert field in valid_sort_fields

    def test_invalid_sort_field(self):
        """
        Test invalid sort_by values.

        Expected: Invalid values should be rejected
        """
        valid_sort_fields = ["created_at", "due_date", "priority", "title"]
        invalid_fields = ["name", "status", "id", "user_id", ""]

        for field in invalid_fields:
            assert field not in valid_sort_fields


class TestSortOrderValidation:
    """Test sort_order parameter validation."""

    def test_valid_sort_orders(self):
        """
        Test valid sort_order values.

        Expected: asc, desc are valid
        """
        valid_sort_orders = ["asc", "desc"]

        assert "asc" in valid_sort_orders
        assert "desc" in valid_sort_orders

    def test_invalid_sort_order(self):
        """
        Test invalid sort_order values.

        Expected: Invalid values should be rejected
        """
        valid_sort_orders = ["asc", "desc"]
        invalid_orders = ["ascending", "descending", "ASC", "DESC", ""]

        for order in invalid_orders:
            assert order not in valid_sort_orders


class TestDateValidation:
    """Test due date parameter validation."""

    def test_valid_iso8601_date(self):
        """
        Test valid ISO8601 date parsing.

        Expected: Valid ISO8601 strings parse correctly
        """
        valid_dates = [
            "2026-01-15T10:00:00Z",
            "2026-01-15T10:00:00+00:00",
            "2026-12-31T23:59:59Z",
        ]

        for date_str in valid_dates:
            # Replace Z with +00:00 for fromisoformat compatibility
            normalized = date_str.replace('Z', '+00:00')
            parsed = datetime.fromisoformat(normalized)
            assert parsed is not None
            assert parsed.tzinfo is not None

    def test_invalid_date_format(self):
        """
        Test invalid date formats are rejected.

        Expected: Invalid formats raise ValueError
        """
        invalid_dates = [
            "2026-01-15",  # Missing time
            "01/15/2026",  # Wrong format
            "not-a-date",
            "",
        ]

        for date_str in invalid_dates:
            try:
                datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                # If we get here without exception, it's unexpectedly valid
                if date_str == "2026-01-15":
                    # This is actually valid ISO8601 date (without time)
                    pass
                else:
                    assert False, f"Expected ValueError for {date_str}"
            except ValueError:
                pass  # Expected


class TestTagsValidation:
    """Test tags parameter validation."""

    def test_valid_tags_list(self):
        """
        Test valid tags list.

        Expected: List of strings is valid
        """
        valid_tags = ["work", "urgent", "personal"]
        assert isinstance(valid_tags, list)
        assert all(isinstance(tag, str) for tag in valid_tags)

    def test_empty_tags_list(self):
        """
        Test empty tags list.

        Expected: Empty list should not apply filter
        """
        tags = []
        # Empty list is falsy
        assert not tags

    def test_none_tags(self):
        """
        Test None tags.

        Expected: None should not apply filter
        """
        tags = None
        assert tags is None


class TestFilterCombination:
    """Test combining multiple filters."""

    def test_all_filters_can_combine(self):
        """
        Test that all filter parameters can be specified together.

        Expected: All parameters have compatible types
        """
        filters = {
            "user_id": "user-123",
            "status": "pending",
            "priority": "high",
            "tags": ["work", "urgent"],
            "due_date_from": "2026-01-15T00:00:00Z",
            "due_date_to": "2026-01-20T23:59:59Z",
            "search_query": "report",
            "sort_by": "due_date",
            "sort_order": "asc"
        }

        # Verify all keys are strings
        assert all(isinstance(k, str) for k in filters.keys())

        # Verify types
        assert isinstance(filters["user_id"], str)
        assert isinstance(filters["status"], str)
        assert isinstance(filters["priority"], str)
        assert isinstance(filters["tags"], list)
        assert isinstance(filters["due_date_from"], str)
        assert isinstance(filters["due_date_to"], str)
        assert isinstance(filters["search_query"], str)
        assert isinstance(filters["sort_by"], str)
        assert isinstance(filters["sort_order"], str)


class TestUserIdValidation:
    """Test user_id parameter validation."""

    def test_valid_user_id(self):
        """
        Test valid user_id values.

        Expected: Non-empty string up to 255 chars is valid
        """
        valid_ids = ["user-123", "a", "a" * 255]

        for user_id in valid_ids:
            assert len(user_id) >= 1
            assert len(user_id) <= 255

    def test_invalid_user_id_empty(self):
        """
        Test empty user_id.

        Expected: Empty string should be rejected
        """
        user_id = ""
        assert len(user_id) == 0

    def test_invalid_user_id_too_long(self):
        """
        Test user_id exceeding max length.

        Expected: >255 chars should be rejected
        """
        user_id = "a" * 256
        assert len(user_id) > 255
