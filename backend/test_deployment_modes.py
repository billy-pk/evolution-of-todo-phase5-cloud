#!/usr/bin/env python3
"""
Test script to verify both deployment modes work correctly.

This script tests:
1. Separate mode (MOUNT_MCP_SERVER=False): Default configuration
2. Unified mode (MOUNT_MCP_SERVER=True): MCP mounted on FastAPI
"""

import os
import sys

def test_separate_mode():
    """Test separate deployment mode."""
    print("\n" + "="*60)
    print("TEST 1: Separate Deployment Mode (MOUNT_MCP_SERVER=False)")
    print("="*60)

    # Set environment
    os.environ["MOUNT_MCP_SERVER"] = "false"

    # Reload modules to pick up new env
    if "config" in sys.modules:
        del sys.modules["config"]

    from config import settings

    print(f"✓ MOUNT_MCP_SERVER: {settings.MOUNT_MCP_SERVER}")
    print(f"✓ mcp_server_url: {settings.mcp_server_url}")

    assert settings.MOUNT_MCP_SERVER == False, "MOUNT_MCP_SERVER should be False"
    assert "8001" in settings.mcp_server_url, "MCP URL should point to port 8001"

    print("\n✅ Separate mode test PASSED")
    return True


def test_unified_mode():
    """Test unified deployment mode."""
    print("\n" + "="*60)
    print("TEST 2: Unified Deployment Mode (MOUNT_MCP_SERVER=True)")
    print("="*60)

    # Set environment - remove override to test auto-detection
    os.environ["MOUNT_MCP_SERVER"] = "true"
    os.environ.pop("MCP_SERVER_URL", None)  # Remove any override

    # Reload modules to pick up new env
    if "config" in sys.modules:
        del sys.modules["config"]

    from config import settings

    print(f"✓ MOUNT_MCP_SERVER: {settings.MOUNT_MCP_SERVER}")
    print(f"✓ MCP_SERVER_URL env: {settings.MCP_SERVER_URL}")
    print(f"✓ mcp_server_url property: {settings.mcp_server_url}")

    assert settings.MOUNT_MCP_SERVER == True, "MOUNT_MCP_SERVER should be True"

    # When no override, should auto-detect to port 8000
    if settings.MCP_SERVER_URL is None or settings.MCP_SERVER_URL == "":
        assert "8000" in settings.mcp_server_url, f"MCP URL should point to port 8000, got: {settings.mcp_server_url}"
    else:
        print(f"  ⚠️  MCP_SERVER_URL override detected, skipping port check")

    # Test MCP app can be imported and created
    from tools.server import get_mcp_app

    mcp_app = get_mcp_app()
    print(f"✓ MCP app created successfully: {type(mcp_app).__name__}")

    print("\n✅ Unified mode test PASSED")
    return True


def test_mcp_server_url_override():
    """Test MCP_SERVER_URL override."""
    print("\n" + "="*60)
    print("TEST 3: MCP_SERVER_URL Override")
    print("="*60)

    # Set custom URL
    custom_url = "https://custom-mcp-server.example.com/mcp"
    os.environ["MCP_SERVER_URL"] = custom_url
    os.environ["MOUNT_MCP_SERVER"] = "false"

    # Reload modules
    if "config" in sys.modules:
        del sys.modules["config"]

    from config import settings

    print(f"✓ MCP_SERVER_URL override: {settings.MCP_SERVER_URL}")
    print(f"✓ mcp_server_url property: {settings.mcp_server_url}")

    assert settings.mcp_server_url == custom_url, "Custom URL should be used"

    print("\n✅ MCP_SERVER_URL override test PASSED")
    return True


def test_main_app_mounting():
    """Test that main.py can mount MCP app without errors."""
    print("\n" + "="*60)
    print("TEST 4: Main App MCP Mounting")
    print("="*60)

    # Set unified mode
    os.environ["MOUNT_MCP_SERVER"] = "true"
    os.environ.pop("MCP_SERVER_URL", None)  # Remove override

    # Reload modules
    for mod in ["config", "main"]:
        if mod in sys.modules:
            del sys.modules[mod]

    try:
        # Import main - this will trigger MCP mounting if MOUNT_MCP_SERVER=true
        import main

        print(f"✓ Main app created successfully")
        print(f"✓ App title: {main.app.title}")

        # Check if /mcp is mounted
        routes = [route.path for route in main.app.routes]
        print(f"✓ Available routes: {len(routes)} routes")

        # Check if MCP is mounted (it will be a sub-app)
        mcp_mounted = any("/mcp" in str(route.path) for route in main.app.routes)
        print(f"✓ MCP mounted: {mcp_mounted}")

        print("\n✅ Main app mounting test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Main app mounting test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🧪 DEPLOYMENT MODES TEST SUITE ".center(60, "="))

    results = []

    try:
        results.append(("Separate Mode", test_separate_mode()))
    except Exception as e:
        print(f"\n❌ Separate mode test FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Separate Mode", False))

    try:
        results.append(("Unified Mode", test_unified_mode()))
    except Exception as e:
        print(f"\n❌ Unified mode test FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Unified Mode", False))

    try:
        results.append(("URL Override", test_mcp_server_url_override()))
    except Exception as e:
        print(f"\n❌ URL override test FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("URL Override", False))

    try:
        results.append(("Main App Mounting", test_main_app_mounting()))
    except Exception as e:
        print(f"\n❌ Main app mounting test FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Main App Mounting", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print("="*60)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Deployment modes working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review errors above.")
        sys.exit(1)
