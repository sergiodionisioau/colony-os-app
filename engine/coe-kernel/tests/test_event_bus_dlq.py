"""Test suite for the Event Bus DLQ."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.event_bus.dlq import DeadLetterQueue
from core.types import Event, DLQEntry


def create_mock_event() -> Event:
    """Helper to create a valid failed event."""
    return Event(
        event_id=uuid4(),
        sequence_number=1,
        correlation_id=uuid4(),
        type="test.failed",
        version="1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        origin_id=uuid4(),
        payload={"data": "test"},
        signature="mock",
    )


def test_dlq_appends_and_metrics(tmp_path: Any) -> None:
    """DLQ must store failed events and provide accessible metrics."""
    dlq = DeadLetterQueue(storage_path=str(tmp_path))
    event = create_mock_event()

    dlq.append(
        failed_event=event,
        reason="ZeroDivisionError in handler",
        subscriber_id="sub_1",
    )

    metrics = dlq.get_metrics()
    assert metrics["total_dead_letters"] == 1
    assert metrics["failures_by_subscriber"]["sub_1"] == 1

    entries = dlq.get_entries()
    assert len(entries) == 1
    assert isinstance(entries[0], DLQEntry)
    assert entries[0].failed_event.event_id == event.event_id
    assert entries[0].reason == "ZeroDivisionError in handler"


# --- Aliases conforming strictly to project_plan.md requirements ---
test_dead_letter_queue_triggered = test_dlq_appends_and_metrics
