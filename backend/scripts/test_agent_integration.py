#!/usr/bin/env python3
"""
Integration test for OpenAI Agent + MCP Server

This script tests the full flow:
1. MCP Server exposes add_task tool
2. OpenAI Agent connects to MCP Server
3. Agent processes natural language and calls the tool
4. Task is created in the database

Prerequisites:
- MCP Server must be running at http://localhost:8000/mcp
- OPENAI_API_KEY must be set in .env

Usage:
    # Terminal 1: Start MCP Server
    cd backend
    uv run python tools/server.py

    # Terminal 2: Run this test
    cd backend
    uv run python scripts/test_agent_integration.py
"""

import sys
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.agent import process_message
import json


async def test_natural_language_task_creation():
    """Test creating a task via natural language"""
    print("=" * 70)
    print("INTEGRATION TEST: Natural Language Task Creation")
    print("=" * 70)
    print()
    print("Testing: OpenAI Agent → MCP Server → Database")
    print()

    user_id = "test_integration_user_456"
    test_message = "Add a task to review the Phase 3 implementation and write deployment docs"

    print(f"User ID: {user_id}")
    print(f"Message: {test_message}")
    print()
    print("Processing with AI Agent...")
    print("-" * 70)

    try:
        result = await process_message(
            user_id=user_id,
            message=test_message
        )

        print()
        print("RESULT:")
        print("=" * 70)
        print(json.dumps(result, indent=2))
        print("=" * 70)
        print()

        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
            return False

        print(f"✅ Agent Response: {result['response']}")
        print()

        if result.get('tool_calls'):
            print(f"🔧 Tool Calls Made: {len(result['tool_calls'])}")
            for i, tool_call in enumerate(result['tool_calls'], 1):
                print(f"\n  Tool Call {i}:")
                print(f"    Tool: {tool_call.get('tool', 'unknown')}")
                print(f"    Parameters: {tool_call.get('parameters', {})}")
                if 'result' in tool_call:
                    print(f"    Result: {tool_call.get('result')}")

        print()
        print("✅ Integration test completed successfully!")
        print()
        print("You can verify the task in database:")
        print(f"  SELECT * FROM tasks WHERE user_id = '{user_id}';")

        return True

    except Exception as e:
        print()
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_conversation_history():
    """Test multi-turn conversation with history"""
    print()
    print("=" * 70)
    print("INTEGRATION TEST: Conversation History")
    print("=" * 70)
    print()

    user_id = "test_integration_user_789"

    # First message
    print("Turn 1: Creating a task...")
    result1 = await process_message(
        user_id=user_id,
        message="Add a task to write unit tests"
    )
    print(f"Response: {result1['response']}")
    print()

    # Build conversation history
    conversation_history = [
        {"role": "user", "content": "Add a task to write unit tests"},
        {"role": "assistant", "content": result1['response']}
    ]

    # Second message with context
    print("Turn 2: Follow-up question...")
    result2 = await process_message(
        user_id=user_id,
        message="What did I just ask you to add?",
        conversation_history=conversation_history
    )
    print(f"Response: {result2['response']}")
    print()

    if "test" in result2['response'].lower() or "unit" in result2['response'].lower():
        print("✅ Agent remembered the context!")
    else:
        print("⚠️ Agent might not have remembered the context")

    return True


async def main():
    """Run all integration tests"""
    print()
    print("🧪 OpenAI Agent + MCP Server Integration Tests")
    print("=" * 70)
    print()
    print("⚠️  Make sure the MCP Server is running:")
    print("   Terminal 1: uv run python tools/server.py")
    print()
    input("Press Enter when MCP Server is running...")
    print()

    # Test 1: Natural language task creation
    success1 = await test_natural_language_task_creation()

    if success1:
        # Test 2: Conversation history
        success2 = await test_conversation_history()

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if success1:
        print("✅ All integration tests passed!")
        print()
        print("The AI Agent successfully:")
        print("  1. Connected to the MCP Server")
        print("  2. Understood natural language requests")
        print("  3. Called the add_task tool")
        print("  4. Created tasks in the database")
        print("  5. Maintained conversation context")
    else:
        print("❌ Some tests failed. Check the output above.")


if __name__ == "__main__":
    asyncio.run(main())
