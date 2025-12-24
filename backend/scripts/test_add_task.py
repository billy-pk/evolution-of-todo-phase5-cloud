#!/usr/bin/env python3
"""
Manual test script for add_task MCP tool

This script directly calls the add_task function to verify it works
with the real PostgreSQL database.

Usage:
    cd backend
    uv run python scripts/test_add_task.py
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tools.server import add_task
import json


def test_add_task_simple():
    """Test adding a simple task"""
    print("=" * 60)
    print("TEST 1: Add task with title only")
    print("=" * 60)

    result = add_task(
        user_id="test_user_manual_123",
        title="Test task from manual script"
    )

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        print("\n✅ SUCCESS: Task created")
        return result["data"]["task_id"]
    else:
        print("\n❌ FAILED: Task creation failed")
        return None


def test_add_task_with_description():
    """Test adding a task with description"""
    print("\n" + "=" * 60)
    print("TEST 2: Add task with title and description")
    print("=" * 60)

    result = add_task(
        user_id="test_user_manual_123",
        title="Write deployment documentation",
        description="Document how to deploy the MCP server to production"
    )

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        print("\n✅ SUCCESS: Task with description created")
        return result["data"]["task_id"]
    else:
        print("\n❌ FAILED: Task creation failed")
        return None


def test_add_task_validation():
    """Test validation - should fail with empty title"""
    print("\n" + "=" * 60)
    print("TEST 3: Validation test (should fail with empty title)")
    print("=" * 60)

    result = add_task(
        user_id="test_user_manual_123",
        title=""
    )

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    if result["status"] == "error":
        print("\n✅ SUCCESS: Validation working correctly (rejected empty title)")
    else:
        print("\n❌ FAILED: Validation should have rejected empty title")


def main():
    """Run all tests"""
    print("\n🧪 Manual Test Suite for add_task MCP Tool")
    print("=" * 60)
    print("\nThis will add test tasks to your database.")
    print("User ID used: test_user_manual_123")
    print("\n")

    try:
        # Test 1: Simple task
        task_id_1 = test_add_task_simple()

        # Test 2: Task with description
        task_id_2 = test_add_task_with_description()

        # Test 3: Validation
        test_add_task_validation()

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        if task_id_1 and task_id_2:
            print(f"\n✅ All tests completed successfully!")
            print(f"\nCreated tasks:")
            print(f"  - Task 1 ID: {task_id_1}")
            print(f"  - Task 2 ID: {task_id_2}")
            print(f"\nYou can verify these in your database:")
            print(f"  SELECT * FROM tasks WHERE user_id = 'test_user_manual_123';")
        else:
            print("\n⚠️  Some tests failed. Check the output above.")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
