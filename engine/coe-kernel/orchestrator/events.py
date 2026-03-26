"""Event Bus Adapter for LangGraph Integration.

Connects LangGraph to the COE Kernel event bus via Redis.
"""

import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timezone

import redis


class EventBusAdapter:
    """Adapter for COE Kernel event bus."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize event bus connection."""
        self.config = config or {}
        self.stream = self.config.get("stream", "coe_events")
        self.group = self.config.get("consumer_group", "orchestrator")

        # Redis connection
        self._redis = redis.Redis(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 6379),
            decode_responses=True
        )

        # Ensure consumer group exists
        self._create_consumer_group()

    def _create_consumer_group(self) -> None:
        """Create consumer group if not exists."""
        try:
            self._redis.xgroup_create(self.stream, self.group, id="0-0", mkstream=True)
        except redis.ResponseError as e:
            if "already exists" not in str(e):
                raise

    def emit(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Emit event to the bus."""
        event_data = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": json.dumps(payload),
            "source": "orchestrator"
        }

        message_id = self._redis.xadd(self.stream, event_data)
        return message_id

    def listen(self, block_ms: int = 5000, count: int = 10) -> list:
        """Listen for events from the bus."""
        try:
            events = self._redis.xreadgroup(
                self.group,
                "worker-1",
                {self.stream: ">"},
                count=count,
                block=block_ms
            )
            return events
        except redis.RedisError as e:
            print(f"Redis error: {e}")
            return []

    def ack(self, message_id: str) -> None:
        """Acknowledge message processing."""
        self._redis.xack(self.stream, self.group, message_id)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to specific event type."""
        # For pattern-based subscription, use separate thread
        pass


def emit(event_type: str, payload: Dict[str, Any]) -> str:
    """Global emit function."""
    bus = EventBusAdapter()
    return bus.emit(event_type, payload)


def listen() -> list:
    """Global listen function."""
    bus = EventBusAdapter()
    return bus.listen()
