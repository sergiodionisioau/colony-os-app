"""Strict TDD suite for the Event Bus.

Covers Phase 2 Test Groups 1-8:
Schema, Signatures, Routing, DLQ, Replay, Backpressure, Isolation, Integration
"""

import uuid
from dataclasses import replace
import gc
import time
from typing import Any, cast

import pytest

from core.errors import ErrorCode, KernelError
from core.types import Event, EventBusDependencies
from core.event_bus.bus import (
    EventBus,
    SchemaRegistry,
    compute_event_signature,
)
from core.event_bus.store import EventStore
from core.event_bus.backpressure import BackpressureController
from core.event_bus.dlq import DeadLetterQueue
from tests.conftest import MockAuditLedger

# ─── Helpers ──────────────────────────────────────────


def _make_registry() -> SchemaRegistry:
    reg = SchemaRegistry()
    reg.register("system.test", ["data"], version="v1")
    reg.register("test.order", ["data"], version="v1")
    reg.register("test.replay", ["data"], version="v1")
    return reg


def _signed_event(
    event_type: str = "system.test",
) -> Event:
    """Helper returning a valid, signed event."""
    ev = Event(
        event_id=uuid.uuid4(),
        sequence_number=0,
        correlation_id=uuid.uuid4(),
        type=event_type,
        version="v1",
        timestamp="2024-01-01T00:00:00Z",
        origin_id=uuid.uuid4(),
        payload={"data": "test"},
        signature="placeholder",
    )
    sig = compute_event_signature(ev)
    return replace(ev, signature=sig)


# ─── Fixtures ─────────────────────────────────────────


@pytest.fixture(name="schema_registry")
def schema_registry_fix() -> SchemaRegistry:
    """Provides a SchemaRegistry with common test schemas."""
    return _make_registry()


@pytest.fixture(name="event_store")
def event_store_fix(tmp_path: Any) -> EventStore:
    """Provides a temp-path backed EventStore."""
    return EventStore(
        storage_path=str(tmp_path / "events"),
        segment_size=100,
    )


@pytest.fixture(name="dlq")
def dlq_fix(tmp_path: Any) -> DeadLetterQueue:
    """Provides a fresh DLQ instance."""
    return DeadLetterQueue(storage_path=str(tmp_path))


@pytest.fixture(name="backpressure")
def backpressure_fix() -> BackpressureController:
    """Provides a BackpressureController with test limits."""
    return BackpressureController(activation_depth=10, deactivation_depth=5)


@pytest.fixture(name="event_bus")
def event_bus_fix(
    mock_audit_ledger: MockAuditLedger,
    event_store: EventStore,
    backpressure: BackpressureController,
    dlq: DeadLetterQueue,
    schema_registry: SchemaRegistry,
) -> EventBus:
    """Provides a fully wired EventBus for Phase 2 testing."""
    deps = EventBusDependencies(
        audit_ledger=mock_audit_ledger,
        event_store=event_store,
        backpressure=backpressure,
        dlq=dlq,
        schema_registry=schema_registry,
    )
    return EventBus(deps=deps)


# ─── Group 1: Schema Validation ──────────────────────


def test_unknown_type_rejected(
    event_bus: EventBus,
) -> None:
    """Unknown event type must be rejected."""
    ev = _signed_event("unknown.type")
    with pytest.raises(KernelError) as exc:
        event_bus.publish(ev)
    assert exc.value.code == ErrorCode.EVENT_SCHEMA_INVALID


def test_non_dict_payload_rejected(
    event_bus: EventBus,
) -> None:
    """Publishing a non-dict payload must be rejected."""
    # Create an event with a string payload instead of a dict
    ev = Event(
        event_id=uuid.uuid4(),
        sequence_number=0,
        correlation_id=uuid.uuid4(),
        type="system.test",
        version="v1",
        timestamp="2024-01-01T00:00:00Z",
        origin_id=uuid.uuid4(),
        payload=cast(Any, "not a dict"),
        signature="N/A",
    )
    # Signs it
    ev = replace(ev, signature=compute_event_signature(ev))

    with pytest.raises(KernelError) as exc:
        event_bus.publish(ev)
    assert exc.value.code == ErrorCode.EVENT_SCHEMA_INVALID
    assert "Payload must be a dict" in str(exc.value.message)


def test_version_mismatch_rejected(
    event_bus: EventBus,
) -> None:
    """Version mismatch must be rejected."""
    ev = _signed_event()
    bad = replace(ev, version="v999")
    sig = compute_event_signature(bad)
    bad = replace(bad, signature=sig)
    with pytest.raises(KernelError) as exc:
        event_bus.publish(bad)
    assert exc.value.code == ErrorCode.EVENT_SCHEMA_INVALID


def test_missing_required_field_rejected(
    event_bus: EventBus,
) -> None:
    """Missing required payload field must be rejected."""
    ev = replace(_signed_event(), payload={"wrong_key": "val"})
    sig = compute_event_signature(ev)
    ev = replace(ev, signature=sig)
    with pytest.raises(KernelError) as exc:
        event_bus.publish(ev)
    assert exc.value.code == ErrorCode.EVENT_SCHEMA_INVALID


def test_schema_hash_tamper_detected(
    schema_registry: SchemaRegistry,
) -> None:
    """Tampered schema hash must be detectable."""
    original_hash = schema_registry.get_hash("system.test")
    assert original_hash is not None

    # Missing type returns None
    assert schema_registry.get_hash("non.existent") is None

    new_hash = schema_registry.register("system.test", ["data", "extra"], version="v1")
    assert new_hash != original_hash


# ─── Group 2: Signature Validation ───────────────────


def test_tampered_payload_rejected(
    event_bus: EventBus,
) -> None:
    """Tampered payload must fail signature check."""
    ev = _signed_event()
    tampered = replace(ev, payload={"data": "TAMPERED"})
    with pytest.raises(KernelError) as exc:
        event_bus.publish(tampered)
    assert exc.value.code == ErrorCode.EVENT_SIGNATURE_INVALID


def test_missing_signature_rejected(
    event_bus: EventBus,
) -> None:
    """Event with no signature must be rejected."""
    ev = Event(
        event_id=uuid.uuid4(),
        sequence_number=0,
        correlation_id=uuid.uuid4(),
        type="system.test",
        version="v1",
        timestamp="2024-01-01T00:00:00Z",
        origin_id=uuid.uuid4(),
        payload={"data": "test"},
        signature="N/A",
    )
    with pytest.raises(KernelError) as exc:
        event_bus.publish(ev)
    assert exc.value.code == ErrorCode.EVENT_SIGNATURE_INVALID


def test_tampered_signature_rejected(
    event_bus: EventBus,
) -> None:
    """Event with wrong signature must be rejected."""
    ev = _signed_event()
    bad = replace(ev, signature="deadbeef")
    with pytest.raises(KernelError) as exc:
        event_bus.publish(bad)
    assert exc.value.code == ErrorCode.EVENT_SIGNATURE_INVALID


# ─── Group 3: Deterministic Routing ──────────────────


def test_event_ordering_assignment(
    event_bus: EventBus, event_store: EventStore
) -> None:
    """Bus assigns monotonic sequence numbers."""
    ev1 = _signed_event()
    ev2 = _signed_event()
    event_bus.publish(ev1)
    event_bus.publish(ev2)
    stored = event_store.get_events(1, 2)
    assert len(stored) == 2
    assert stored[0].sequence_number == 1
    assert stored[1].sequence_number == 2


def test_dispatch_determinism(
    event_bus: EventBus,
) -> None:
    """Subscribers execute in sorted UUID order."""
    order: list[str] = []

    def h_a(_: Event) -> None:
        order.append("A")

    def h_b(_: Event) -> None:
        order.append("B")

    def h_c(_: Event) -> None:
        order.append("C")

    event_bus.subscribe("test.order", h_a, subscriber_id="sub_3")
    event_bus.subscribe("test.order", h_b, subscriber_id="sub_1")
    event_bus.subscribe("test.order", h_c, subscriber_id="sub_2")
    event_bus.publish(_signed_event("test.order"))
    assert order == ["B", "C", "A"]


# ─── Group 4: Dead Letter ────────────────────────────


def test_subscriber_isolation_dlq_routing(
    event_bus: EventBus,
) -> None:
    """Crashing subscriber → DLQ, bus survives."""

    def crash(_: Event) -> None:
        raise ValueError("Simulated crash")

    def ok(_: Event) -> None:
        pass

    event_bus.subscribe("system.test", crash, subscriber_id="crash")
    event_bus.subscribe("system.test", ok, subscriber_id="good")
    event_bus.publish(_signed_event())
    m = event_bus.get_dlq_metrics()
    assert m["total_dead_letters"] == 1
    assert m["failures_by_subscriber"]["crash"] == 1


def test_dlq_failure_reason_recorded(event_bus: EventBus, dlq: DeadLetterQueue) -> None:
    """DLQ must record the failure reason."""

    def crash(_: Event) -> None:
        raise RuntimeError("boom")

    event_bus.subscribe("system.test", crash, subscriber_id="x")
    event_bus.publish(_signed_event())
    entries = dlq.get_entries()
    assert len(entries) == 1
    assert "boom" in entries[0].reason


def test_unsubscribe(event_bus: EventBus) -> None:
    """Test unsubscribing removes the handler from the bus route."""
    calls = []

    def _handler(event: Any) -> None:
        calls.append(event)

    event_bus.subscribe("system.test", _handler, "sub_1")
    event_bus.subscribe("system.test", _handler, "sub_2")

    event_bus.publish(_signed_event("system.test"))
    assert len(calls) == 2

    event_bus.unsubscribe("sub_1", "system.test")
    event_bus.publish(_signed_event("system.test"))
    assert len(calls) == 3  # Only sub_2 was called (2 previous + 1 new)


def test_isolation_layer_memory_abuse(
    event_bus: EventBus, mock_audit_ledger: MockAuditLedger
) -> None:
    """Test isolation layer logs memory abuse warning."""
    gc.collect()  # Flush pending garbage to prevent mid-execution delta corruption

    # We drop the threshold purely for this test
    event_bus.isolation.max_objects = 10

    leaked_list: list[Any] = []

    def _leaky_handler(_event: Any) -> None:
        # Overwhelm any transient garbage collected objects with a massive allocation
        leaked_list.extend([[] for _ in range(250000)])

    event_bus.subscribe("system.test", _leaky_handler, "h_leak")
    event_bus.publish(_signed_event("system.test"))

    # Audit should contain memory abuse
    abuses = list(mock_audit_ledger.iterate("subscriber_memory_abuse"))
    assert len(abuses) == 1
    assert abuses[0].actor_id == "h_leak"


def test_isolation_layer_timeout_abuse(
    event_bus: EventBus, mock_audit_ledger: MockAuditLedger
) -> None:
    """Test isolation layer logs timeout abuse warning."""
    event_bus.isolation.timeout_seconds = 0.01  # Very low threshold

    def _slow_handler(_event: Any) -> None:
        time.sleep(0.02)

    event_bus.subscribe("system.test", _slow_handler, "h_slow")
    event_bus.publish(_signed_event("system.test"))

    abuses = list(mock_audit_ledger.iterate("subscriber_timeout_abuse"))
    assert len(abuses) == 1
    assert abuses[0].actor_id == "h_slow"


# ─── Group 5: Replay ─────────────────────────────────


def test_replay_engine_immutability(
    event_bus: EventBus,
    event_store: EventStore,
    mock_audit_ledger: MockAuditLedger,
) -> None:
    """Replay dispatches but does NOT alter store."""
    calls: list[Event] = []

    def handler(e: Event) -> None:
        calls.append(e)

    event_bus.subscribe("test.replay", handler, subscriber_id="s1")
    event_bus.publish(_signed_event("test.replay"))
    assert len(calls) == 1
    assert calls[0].replay_context is None
    assert event_store.get_current_sequence() == 1

    calls.clear()
    rid = str(uuid.uuid4())
    event_bus.replay_events(start_sequence=1, end_sequence=1, replay_id=rid)
    assert len(calls) == 1
    assert calls[0].replay_context is not None
    assert calls[0].replay_context.is_replay is True
    assert event_store.get_current_sequence() == 1

    replays = list(mock_audit_ledger.iterate("event_replayed"))
    assert len(replays) == 1


# ─── Group 6: Backpressure ───────────────────────────


def test_backpressure_rejection(
    event_bus: EventBus,
    backpressure: BackpressureController,
) -> None:
    """Publishing rejected when backpressure active."""
    backpressure.deactivation_depth = -1
    backpressure.is_accepting(10)
    with pytest.raises(KernelError) as exc:
        event_bus.publish(_signed_event())
    assert exc.value.code == ErrorCode.POLICY_BUDGET_EXCEEDED


def test_backpressure_event_emitted(
    event_bus: EventBus,
    backpressure: BackpressureController,
    mock_audit_ledger: MockAuditLedger,
) -> None:
    """system.backpressure audit entry emitted."""
    backpressure.deactivation_depth = -1
    backpressure.is_accepting(10)
    with pytest.raises(KernelError):
        event_bus.publish(_signed_event())
    bp_entries = list(mock_audit_ledger.iterate("system.backpressure"))
    assert len(bp_entries) == 1


# ─── Group 7: Isolation ──────────────────────────────


def test_crash_does_not_crash_bus(
    event_bus: EventBus,
) -> None:
    """Subscriber crash must not propagate."""

    def crash(_: Event) -> None:
        raise RuntimeError("fatal")

    event_bus.subscribe("system.test", crash, subscriber_id="c")
    event_bus.publish(_signed_event())


def test_failed_routing_audited(
    event_bus: EventBus,
    mock_audit_ledger: MockAuditLedger,
) -> None:
    """Failed routing must create audit entry."""

    def crash(_: Event) -> None:
        raise ValueError("err")

    event_bus.subscribe("system.test", crash, subscriber_id="c")
    event_bus.publish(_signed_event())
    fails = list(mock_audit_ledger.iterate("event_routing_failed"))
    assert len(fails) == 1
    assert fails[0].metadata["reason"] == "err"


def test_subscriber_unhandled_exception_dead_lettered(
    event_bus: EventBus,
) -> None:
    """G-01 Fix: Unhandled exception explicitly routes to DLQ and doesn't crash."""

    def h_fail(_: Event) -> None:
        raise OSError("Permission denied")

    event_bus.subscribe("system.test", h_fail, subscriber_id="sub_fail")
    ev = _signed_event("system.test")
    ev = replace(ev, payload={"data": "test"})
    ev = replace(ev, signature=compute_event_signature(ev))
    event_bus.publish(ev)

    metrics = event_bus.dlq.get_metrics()
    assert metrics["total_dead_letters"] == 1
    assert metrics["failures_by_subscriber"].get("sub_fail", 0) == 1


def test_get_events_with_corrupted_json_survives(
    event_store: EventStore,
) -> None:
    """G-05 Fix: EventStore.get_events skips corrupted lines silently."""
    ev1 = _signed_event("system.test")
    ev1 = replace(ev1, sequence_number=1)
    ev1 = replace(ev1, signature=compute_event_signature(ev1))
    event_store.append(ev1)

    # Corrupt the segment file manually
    segment_path = event_store.get_segment_path(0)
    with open(segment_path, "a", encoding="utf-8") as f:
        f.write("corrupted\n")

    ev2 = _signed_event("system.test")
    ev2 = replace(ev2, sequence_number=2)
    ev2 = replace(ev2, signature=compute_event_signature(ev2))
    event_store.append(ev2)

    events = event_store.get_events(1, 2)
    assert len(events) == 2
    assert events[0].sequence_number == 1
    assert events[1].sequence_number == 2


def test_replay_empty_range(
    event_bus: EventBus,
    event_store: EventStore,
) -> None:
    """Part B: Test replay over an empty range."""
    ev1 = _signed_event("system.test")
    ev1 = replace(ev1, sequence_number=1)
    ev1 = replace(ev1, signature=compute_event_signature(ev1))
    event_store.append(ev1)

    calls: list[Event] = []

    def handler(e: Event) -> None:
        calls.append(e)

    event_bus.subscribe("system.test", handler, subscriber_id="s1")
    event_bus.replay_events(
        start_sequence=5, end_sequence=10, replay_id=str(uuid.uuid4())
    )

    assert len(calls) == 0


def test_replay_multi_segment_range(
    event_bus: EventBus,
    event_store: EventStore,
) -> None:
    """Part B: Test replay over a multi-segment event range."""
    event_store.config.segment_size = 2  # Force rapid segment rotation

    for i in range(1, 6):
        ev = _signed_event("system.test")
        ev = replace(ev, sequence_number=i)
        ev = replace(ev, signature=compute_event_signature(ev))
        event_store.append(ev)

    calls: list[Event] = []

    def handler(e: Event) -> None:
        calls.append(e)

    event_bus.subscribe("system.test", handler, subscriber_id="s1")
    event_bus.replay_events(
        start_sequence=2, end_sequence=4, replay_id=str(uuid.uuid4())
    )

    assert len(calls) == 3
    assert calls[0].sequence_number == 2
    assert calls[-1].sequence_number == 4


def test_dlq_multiple_subscriber_failures_recorded(
    event_bus: EventBus,
) -> None:
    """Part B: Test multiple subscriber failures triggered by the same event."""

    def h_fail_1(_: Event) -> None:
        raise ValueError("Sub 1 boom")

    def h_fail_2(_: Event) -> None:
        raise TypeError("Sub 2 boom")

    def h_success(_: Event) -> None:
        pass

    event_bus.subscribe("system.test", h_fail_1, subscriber_id="sub_1")
    event_bus.subscribe("system.test", h_success, subscriber_id="sub_ok")
    event_bus.subscribe("system.test", h_fail_2, subscriber_id="sub_2")

    ev = _signed_event("system.test")
    ev = replace(ev, payload={"data": "test"})
    ev = replace(ev, signature=compute_event_signature(ev))
    event_bus.publish(ev)

    metrics = event_bus.dlq.get_metrics()
    assert metrics["total_dead_letters"] == 2
    assert metrics["failures_by_subscriber"].get("sub_1", 0) == 1
    assert metrics["failures_by_subscriber"].get("sub_2", 0) == 1
    assert "sub_ok" not in metrics["failures_by_subscriber"]


def test_dlq_metrics_accumulation(
    event_bus: EventBus,
) -> None:
    """Part B: Test metrics accumulation accuracy."""

    def h_fail(_: Event) -> None:
        raise ValueError("Boom")

    event_bus.subscribe("system.test", h_fail, subscriber_id="sub_fail")

    for _ in range(3):
        ev = _signed_event("system.test")
        ev = replace(ev, payload={"data": "test"})
        ev = replace(ev, signature=compute_event_signature(ev))
        event_bus.publish(ev)

    metrics = event_bus.dlq.get_metrics()
    assert metrics["total_dead_letters"] == 3
    assert metrics["failures_by_subscriber"].get("sub_fail", 0) == 3


def test_bus_isolation_get_stats(event_bus: EventBus) -> None:
    """Cover 130: get_stats."""
    stats = event_bus.isolation.get_stats()
    assert "timeout_seconds" in stats
    assert "max_objects" in stats


def test_bus_subscribe_no_uuid(event_bus: EventBus) -> None:
    """Cover 224: Unhandled error in dispatch/missing UUID generation."""

    def h(_: Event) -> None:
        pass

    event_bus.subscribe("system.test", h)
    handlers = event_bus.get_handlers("system.test")
    assert len(handlers) == 1
    assert len(handlers[0][0]) > 0
