"""
Event Publisher Service for Phase V Event-Driven Architecture.

This service provides a Dapr Pub/Sub wrapper for publishing task lifecycle events
to the event streaming platform (Redpanda). Events are published after database
writes to ensure consistency (database-first pattern).

Topics:
- task-events: Task CRUD operations (task.created, task.updated, task.completed, task.deleted)
- reminders: Reminder lifecycle events
- task-updates: Real-time UI updates for WebSocket broadcasting

Architecture:
- Database writes occur first (single source of truth)
- Events are published asynchronously after successful writes
- Idempotency keys (event_id) prevent duplicate processing
- User isolation enforced via user_id in event payloads
"""

from dapr.clients import DaprClient
from uuid import uuid4
from datetime import datetime, UTC
from typing import Optional, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Dapr Pub/Sub event publisher for task lifecycle events.

    Usage:
        publisher = EventPublisher(dapr_client)
        await publisher.publish_task_created(task_data, user_id)
    """

    # Dapr Pub/Sub component name (from dapr-components/ configs)
    PUBSUB_NAME = "pubsub"

    # Topic names
    TOPIC_TASK_EVENTS = "task-events"
    TOPIC_REMINDERS = "reminders"
    TOPIC_TASK_UPDATES = "task-updates"

    def __init__(self, dapr_client: Optional[DaprClient] = None):
        """
        Initialize EventPublisher with Dapr client.

        Args:
            dapr_client: Optional DaprClient instance. If None, creates a new client.
        """
        self.dapr_client = dapr_client or DaprClient()

    async def publish_task_created(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        source: str = "api"
    ) -> str:
        """
        Publish task.created event to task-events topic.

        Args:
            task_data: Full task object (id, title, description, completed, priority, tags, due_date, etc.)
            user_id: User ID for isolation
            source: Event origin (api, mcp_tool, recurring_task_service)

        Returns:
            event_id: Unique event identifier (UUID)
        """
        event_id = str(uuid4())
        correlation_id = str(uuid4())

        event_payload = {
            "event_id": event_id,
            "event_type": "task.created",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "task_data": task_data,
            "previous_data": None,
            "metadata": {
                "source": source,
                "correlation_id": correlation_id
            }
        }

        try:
            self.dapr_client.publish_event(
                pubsub_name=self.PUBSUB_NAME,
                topic_name=self.TOPIC_TASK_EVENTS,
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            logger.info(f"Published task.created event: {event_id} for task {task_data.get('id')} (user: {user_id})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to publish task.created event: {e}")
            # Non-blocking: Database write succeeded, event publishing failed
            # Audit Service won't receive this event, but data is persisted
            raise

    async def publish_task_updated(
        self,
        task_data: Dict[str, Any],
        previous_data: Dict[str, Any],
        user_id: str,
        source: str = "api"
    ) -> str:
        """
        Publish task.updated event to task-events topic.

        Args:
            task_data: Current task state after update
            previous_data: Previous task state before update (only changed fields)
            user_id: User ID for isolation
            source: Event origin

        Returns:
            event_id: Unique event identifier
        """
        event_id = str(uuid4())
        correlation_id = str(uuid4())

        event_payload = {
            "event_id": event_id,
            "event_type": "task.updated",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "task_data": task_data,
            "previous_data": previous_data,
            "metadata": {
                "source": source,
                "correlation_id": correlation_id
            }
        }

        try:
            self.dapr_client.publish_event(
                pubsub_name=self.PUBSUB_NAME,
                topic_name=self.TOPIC_TASK_EVENTS,
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            logger.info(f"Published task.updated event: {event_id} for task {task_data.get('id')} (user: {user_id})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to publish task.updated event: {e}")
            raise

    async def publish_task_completed(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        source: str = "api"
    ) -> str:
        """
        Publish task.completed event to task-events topic.

        This is a critical event for recurring tasks - triggers next instance generation.

        Args:
            task_data: Task data with completed=True
            user_id: User ID for isolation
            source: Event origin

        Returns:
            event_id: Unique event identifier
        """
        event_id = str(uuid4())
        correlation_id = str(uuid4())

        event_payload = {
            "event_id": event_id,
            "event_type": "task.completed",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "task_data": task_data,
            "previous_data": {"completed": False},
            "metadata": {
                "source": source,
                "correlation_id": correlation_id
            }
        }

        try:
            self.dapr_client.publish_event(
                pubsub_name=self.PUBSUB_NAME,
                topic_name=self.TOPIC_TASK_EVENTS,
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            logger.info(f"Published task.completed event: {event_id} for task {task_data.get('id')} (user: {user_id})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to publish task.completed event: {e}")
            raise

    async def publish_task_deleted(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        source: str = "api"
    ) -> str:
        """
        Publish task.deleted event to task-events topic.

        Args:
            task_data: Task data before deletion
            user_id: User ID for isolation
            source: Event origin

        Returns:
            event_id: Unique event identifier
        """
        event_id = str(uuid4())
        correlation_id = str(uuid4())

        event_payload = {
            "event_id": event_id,
            "event_type": "task.deleted",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "task_data": task_data,
            "previous_data": None,
            "metadata": {
                "source": source,
                "correlation_id": correlation_id
            }
        }

        try:
            self.dapr_client.publish_event(
                pubsub_name=self.PUBSUB_NAME,
                topic_name=self.TOPIC_TASK_EVENTS,
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            logger.info(f"Published task.deleted event: {event_id} for task {task_data.get('id')} (user: {user_id})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to publish task.deleted event: {e}")
            raise

    async def publish_task_update_for_websocket(
        self,
        update_type: str,
        task_id: str,
        user_id: str,
        task_data: Optional[Dict[str, Any]],
        source: str = "user_action"
    ) -> str:
        """
        Publish real-time task update to task-updates topic for WebSocket broadcasting.

        Args:
            update_type: task_created, task_updated, task_completed, task_deleted, task_recurring_generated
            task_id: Task ID
            user_id: User ID for isolation
            task_data: Full task object (or None for delete)
            source: user_action, system_generated, recurring_task_service

        Returns:
            event_id: Unique event identifier
        """
        event_id = str(uuid4())

        event_payload = {
            "update_type": update_type,
            "event_id": event_id,
            "task_id": task_id,
            "user_id": user_id,
            "task_data": task_data,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
            "schema_version": "1.0.0"
        }

        try:
            self.dapr_client.publish_event(
                pubsub_name=self.PUBSUB_NAME,
                topic_name=self.TOPIC_TASK_UPDATES,
                data=json.dumps(event_payload),
                data_content_type="application/json"
            )
            logger.info(f"Published {update_type} event to WebSocket: {event_id} for task {task_id} (user: {user_id})")
            return event_id
        except Exception as e:
            logger.error(f"Failed to publish WebSocket update: {e}")
            # Non-blocking: WebSocket updates are nice-to-have, not critical
            pass

    def close(self):
        """Close Dapr client connection."""
        if self.dapr_client:
            self.dapr_client.close()
