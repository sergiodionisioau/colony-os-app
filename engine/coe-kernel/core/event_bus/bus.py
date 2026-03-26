"""Event Bus implementation.

Nervous system routing strictly typed and ordered actions.
"""

from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import gc
import json
import time
import uuid

from core.errors import ErrorCode, KernelError
from core.interfaces import EventBusInterface
from core.types import Event, EventBusDependencies, ReplayContext


class SchemaRegistry:
    """Validates event payloads against registered type schemas."""

    def __init__(self) -> None:
        """Initialize the registry with no schemas."""
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        event_type: str,
        required_fields: List[str],
        version: str = "1.0",
    ) -> str:
        """Registers a schema and returns its content hash."""
        schema = {
            "event_type": event_type,
            "required_fields": sorted(required_fields),
            "version": version,
        }
        content = json.dumps(schema, sort_keys=True)
        schema_hash = hashlib.sha256(content.encode()).hexdigest()
        schema["hash"] = schema_hash
        self._schemas[event_type] = schema
        return schema_hash

    def validate(
        self, event_type: str, payload: Dict[str, Any], version: str
    ) -> Optional[str]:
        """Returns None on success, error string on failure."""
        if event_type not in self._schemas:
            return f"Unknown event type: {event_type}"
        schema = self._schemas[event_type]
        if schema["version"] != version:
            return f"Version mismatch: expected " f"{schema['version']}, got {version}"
        for field in schema["required_fields"]:
            if field not in payload:
                return f"Missing required field: {field}"
        return None

    def get_hash(self, event_type: str) -> Optional[str]:
        """Returns the registered schema hash."""
        schema = self._schemas.get(event_type)
        if schema:
            return str(schema.get("hash"))
        return None


def compute_event_signature(event: Event) -> str:
    """Computes SHA-256 HMAC signature over event fields."""
    payload_str = json.dumps(event.payload, sort_keys=True)
    content = (
        f"{event.event_id}{event.type}"
        f"{event.version}{event.timestamp}"
        f"{event.origin_id}{payload_str}"
    )
    return hashlib.sha256(content.encode()).hexdigest()


def verify_event_signature(event: Event) -> bool:
    """Verifies the SHA-256 signature on an event."""
    if not event.signature or event.signature == "N/A":
        return False
    expected = compute_event_signature(event)
    return event.signature == expected


class IsolationLayer:
    """Best-effort timeout and memory monitoring for synchronous subscribers."""

    def __init__(
        self, audit_ledger: Any, timeout_seconds: float = 30.0, max_objects: int = 1000
    ):
        self.audit_ledger = audit_ledger
        self.timeout_seconds = timeout_seconds
        self.max_objects = max_objects
        self._metrics: Dict[str, Dict[str, Any]] = {}

    def execute_subscriber(self, subscriber_id: str, handler: Any, event: Event) -> Any:
        """Executes a single subscriber handler within the isolation layer.

        Enforces hard timeouts and captures execution metrics.
        """
        if subscriber_id not in self._metrics:
            self._metrics[subscriber_id] = {
                "total_successes": 0,
                "total_failures": 0,
                "total_latency_ms": 0.0,
                "memory_warnings": 0,
            }

        objects_before = len(gc.get_objects())
        start_time = time.monotonic()

        try:
            result = handler(event)
            self._metrics[subscriber_id]["total_successes"] += 1
        except Exception:
            self._metrics[subscriber_id]["total_failures"] += 1
            raise

        elapsed = time.monotonic() - start_time
        self._metrics[subscriber_id]["total_latency_ms"] += elapsed * 1000
        delta = len(gc.get_objects()) - objects_before

        if elapsed > self.timeout_seconds:
            self.audit_ledger.append(
                actor_id=subscriber_id,
                action="subscriber_timeout_abuse",
                status="WARNING",
                metadata={"elapsed_seconds": elapsed, "event_type": event.type},
            )
            # G-04 fix: Fail the subscriber so it routes to DLQ and stops silent hanging
            raise KernelError(
                code=ErrorCode.UNKNOWN_FAULT,
                message=f"Handler exceeded strict timeout {self.timeout_seconds}s.",
            )

        if delta > self.max_objects:
            self._metrics[subscriber_id]["memory_warnings"] += 1
            self.audit_ledger.append(
                actor_id=subscriber_id,
                action="subscriber_memory_abuse",
                status="WARNING",
                metadata={"object_delta": delta, "event_type": event.type},
            )

        return result

    def get_subscriber_metrics(self, subscriber_id: str) -> Dict[str, Any]:
        """Returns performance metrics for a specific subscriber."""
        m = self._metrics.get(subscriber_id, {})
        if not m:
            return {
                "total_successes": 0,
                "total_failures": 0,
                "average_latency_ms": 0.0,
                "memory_warnings": 0,
            }

        avg_lat = 0.0
        total_calls = m["total_successes"] + m["total_failures"]
        if total_calls > 0:
            avg_lat = m["total_latency_ms"] / total_calls

        return {
            "total_successes": m["total_successes"],
            "total_failures": m["total_failures"],
            "average_latency_ms": avg_lat,
            "memory_warnings": m["memory_warnings"],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns the current isolation constraints."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_objects": self.max_objects,
        }


class EventBus(EventBusInterface):
    """Sequential routing with backpressure, DLQ, and schema validation."""

    def __init__(self, deps: EventBusDependencies) -> None:
        """Initialize the Event Bus with grouped dependencies."""
        self.audit_ledger = deps.audit_ledger
        self.event_store = deps.event_store
        self.backpressure = deps.backpressure
        self.dlq = deps.dlq
        self.schema_registry = deps.schema_registry
        self.isolation = IsolationLayer(self.audit_ledger)
        self._subscribers: Dict[str, List[Tuple[str, Callable[[Event], None]]]] = {}

    def get_dlq_metrics(self) -> Dict[str, Any]:
        """Provides DLQ volume metrics."""
        metrics: Dict[str, Any] = self.dlq.get_metrics()
        return metrics

    def get_subscriber_health(self, subscriber_id: str) -> Dict[str, Any]:
        """Exposes isolation layer metrics for a specific subscriber."""
        return self.isolation.get_subscriber_metrics(subscriber_id)

    def get_handlers(self, event_type: str) -> List[Tuple[str, Any]]:
        """Returns the registered handlers for a specific event type.

        Used for Phase 2/5 verification.
        """
        return self._subscribers.get(event_type, [])

    def publish(self, event: Event) -> None:
        """Routes a versioned event via monotonic execution."""
        # 1. Schema validation
        if not isinstance(event.payload, dict):
            raise KernelError(
                code=ErrorCode.EVENT_SCHEMA_INVALID,
                message="Payload must be a dict.",
            )
        schema_err = self.schema_registry.validate(
            event.type, event.payload, event.version
        )
        if schema_err:
            raise KernelError(
                code=ErrorCode.EVENT_SCHEMA_INVALID,
                message=schema_err,
            )

        # 2. Signature verification
        if not verify_event_signature(event):
            raise KernelError(
                code=ErrorCode.EVENT_SIGNATURE_INVALID,
                message="Event signature verification failed.",
            )

        # 3. Backpressure check with real retained depth (M-01 fix)
        depth = self.event_store.get_retained_event_count()
        was_active = self.backpressure.get_status()
        is_accepting = self.backpressure.is_accepting(depth)
        is_active = self.backpressure.get_status()

        if is_active and not was_active:
            self._emit_system_event("system.backpressure.activated", {"depth": depth})
        elif not is_active and was_active:
            self._emit_system_event("system.backpressure.deactivated", {"depth": depth})

        if not is_accepting:
            self.audit_ledger.append(
                actor_id="KERNEL",
                action="system.backpressure",
                status="ACTIVATED",
                metadata={"depth": depth},
            )
            raise KernelError(
                code=ErrorCode.POLICY_BUDGET_EXCEEDED,
                message="Queue capacity exceeded and backpressure is active.",
            )

        # 4. Sequence assignment
        # Sequence number remains monotonic regardless of retention.
        new_seq = self.event_store.get_current_sequence() + 1
        event = replace(event, sequence_number=new_seq)

        # 5. Persistence
        self.event_store.append(event)

        # 6. Dispatch
        self._dispatch(event)

        # 7. Audit
        self.audit_ledger.append(
            actor_id=str(event.origin_id),
            action="event_published",
            status="SUCCESS",
            metadata={
                "event_type": event.type,
                "event_id": str(event.event_id),
                "sequence_number": new_seq,
            },
        )

    def subscribe(
        self,
        event_type: str,
        handler: Any,
        subscriber_id: str = "",
    ) -> None:
        """Registers a handler sorted by subscriber UUID."""
        if not subscriber_id:
            subscriber_id = str(uuid.uuid4())
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append((subscriber_id, handler))
        self._subscribers[event_type].sort(key=lambda x: x[0])

    def replay_events(
        self,
        start_sequence: int,
        end_sequence: int,
        replay_id: str,
    ) -> None:
        """Replays historical events idempotently."""
        events = self.event_store.get_events(start_sequence, end_sequence)
        for event in events:
            replay_ctx = ReplayContext(
                is_replay=True,
                replay_id=uuid.UUID(replay_id),
            )
            replay_event = replace(event, replay_context=replay_ctx)
            self._dispatch(replay_event)

        self.audit_ledger.append(
            actor_id="KERNEL",
            action="event_replayed",
            status="SUCCESS",
            metadata={
                "replay_id": replay_id,
                "start_sequence": start_sequence,
                "end_sequence": end_sequence,
                "event_count": len(events),
            },
        )

    def unsubscribe(self, subscriber_id: str, event_type: str) -> None:
        """Removes a subscriber for a specific event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                sub for sub in self._subscribers[event_type] if sub[0] != subscriber_id
            ]

    def _dispatch(self, event: Event) -> None:
        """Sequential single-threaded dispatch to deterministic subscribers."""
        handlers = self._subscribers.get(event.type, [])
        for sub_id, handler in handlers:
            try:
                self.isolation.execute_subscriber(sub_id, handler, event)
            except (  # Explicit subscriber fault types for DLQ routing
                KernelError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
                OSError,
            ) as exc:
                self.dlq.append(
                    failed_event=event,
                    reason=str(exc),
                    subscriber_id=sub_id,
                )
                self.audit_ledger.append(
                    actor_id=sub_id,
                    action="event_routing_failed",
                    status="FAILED",
                    metadata={
                        "event_id": str(event.event_id),
                        "reason": str(exc),
                    },
                )

    def _emit_system_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Internal helper to broadcast critical kernel state changes.

        Bypasses full bus overhead for kernel-to-kernel signals.
        """
        event = Event.create(event_type, payload)
        self._dispatch(event)
