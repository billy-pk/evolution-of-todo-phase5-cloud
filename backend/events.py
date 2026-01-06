"""
Global Event Publisher Access Module for Phase V.

This module provides access to the globally initialized EventPublisher instance
from main.py. This allows other modules (routes, services, MCP tools) to publish
events without creating new Dapr client instances.

Usage:
    from events import get_event_publisher

    publisher = get_event_publisher()
    if publisher:
        await publisher.publish_task_created(task_data, user_id)
"""

from typing import Optional
from services.event_publisher import EventPublisher


# This will be set by main.py during startup
_event_publisher: Optional[EventPublisher] = None


def set_event_publisher(publisher: Optional[EventPublisher]) -> None:
    """
    Set the global EventPublisher instance.
    Called by main.py during startup.

    Args:
        publisher: EventPublisher instance (or None if Dapr unavailable)
    """
    global _event_publisher
    _event_publisher = publisher


def get_event_publisher() -> Optional[EventPublisher]:
    """
    Get the global EventPublisher instance.

    Returns:
        EventPublisher instance if Dapr is available, None otherwise

    Usage:
        publisher = get_event_publisher()
        if publisher:
            await publisher.publish_task_created(task_data, user_id)
        # If publisher is None, events are disabled (Phase 3/4 compatibility mode)
    """
    return _event_publisher
