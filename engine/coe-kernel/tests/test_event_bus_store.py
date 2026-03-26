"""Test suite for the Event Bus Store."""

import os
import tempfile
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest

from core.errors import ErrorCode, KernelError
from core.event_bus.store import EventStore
from core.types import Event, ReplayContext


@pytest.fixture(name="temp_store_path")
def temp_store_path_fixture(tmp_path: Any) -> str:
    """Provides a temporary path for the event store segments."""
    return str(tmp_path / "events")


def create_mock_event(seq: int, replay_ctx: Any = None) -> Event:
    """Helper to create a valid stored event."""
    return Event(
        event_id=uuid4(),
        sequence_number=seq,
        correlation_id=uuid4(),
        type="test.stored",
        version="1.0",
        timestamp="2024-01-01T00:00:00Z",
        origin_id=uuid4(),
        payload={"data": f"test_{seq}"},
        signature="mock",
        replay_context=replay_ctx,
    )


def test_store_appends_and_retrieves(temp_store_path: str) -> None:
    """Store must append events monotonically and retrieve by range."""
    store = EventStore(storage_path=temp_store_path, segment_size=100)

    assert store.get_current_sequence() == 0

    ev1 = create_mock_event(1)
    store.append(ev1)

    assert store.get_current_sequence() == 1

    ev2 = create_mock_event(2)
    store.append(ev2)

    assert store.get_current_sequence() == 2

    events = store.get_events(start_seq=1, end_seq=2)
    assert len(events) == 2
    assert events[0].event_id == ev1.event_id
    assert events[1].event_id == ev2.event_id


def test_store_segmentation(temp_store_path: str) -> None:
    """Store must roll files across the segment_size boundary."""
    store = EventStore(storage_path=temp_store_path, segment_size=2)

    store.append(create_mock_event(1))
    store.append(create_mock_event(2))
    store.append(create_mock_event(3))

    files = os.listdir(temp_store_path)
    segment_files = [f for f in files if f.startswith("segment_")]
    assert len(segment_files) >= 2

    events = store.get_events(start_seq=1, end_seq=3)
    assert len(events) == 3


def test_store_recovers_sequence_on_boot(temp_store_path: str) -> None:
    """Booting an EventStore against existing data must recover highest seq."""
    store1 = EventStore(storage_path=temp_store_path, segment_size=10)
    store1.append(create_mock_event(1))
    store1.append(create_mock_event(2))

    store2 = EventStore(storage_path=temp_store_path, segment_size=10)
    assert store2.get_current_sequence() == 2


def test_out_of_order_write_rejected(temp_store_path: str) -> None:
    """Appending an event with a lower or equal sequence must fail."""
    store = EventStore(storage_path=temp_store_path)
    store.append(create_mock_event(10))

    with pytest.raises(KernelError) as exc:
        store.append(create_mock_event(10))
    assert exc.value.code == ErrorCode.EVENT_VERSION_MISMATCH

    event2 = create_mock_event(11)
    store.append(event2)
    with pytest.raises(KernelError) as exc:
        store.append(event2)
    assert exc.value.code == ErrorCode.EVENT_VERSION_MISMATCH


def test_replay_context_serialization(temp_store_path: str) -> None:
    """ReplayContext must be preserved through persistence."""
    store = EventStore(storage_path=temp_store_path)
    ctx = ReplayContext(is_replay=True, replay_id=uuid4())
    ev = create_mock_event(1, replay_ctx=ctx)
    store.append(ev)

    recovered = store.get_events(1, 1)[0]
    assert recovered.replay_context is not None
    assert recovered.replay_context.is_replay is True
    assert recovered.replay_context.replay_id == ctx.replay_id


def test_replay_context_no_id_serialization(temp_store_path: str) -> None:
    """ReplayContext without ID must also work."""
    store = EventStore(storage_path=temp_store_path)
    ctx = ReplayContext(is_replay=True, replay_id=None)
    ev = create_mock_event(1, replay_ctx=ctx)
    store.append(ev)

    recovered = store.get_events(1, 1)[0]
    assert recovered.replay_context is not None
    assert recovered.replay_context.replay_id is None


def test_get_events_skips_empty_lines(temp_store_path: str) -> None:
    """Reading must ignore empty lines in segments."""
    store = EventStore(storage_path=temp_store_path)
    store.append(create_mock_event(1))

    seg_file = os.path.join(temp_store_path, "segment_000000.json")
    with open(seg_file, "a", encoding="utf-8") as f:
        f.write("\n\n")

    events = store.get_events(1, 1)
    assert len(events) == 1


def test_get_events_early_exit(temp_store_path: str) -> None:
    """Reading stops once end_seq is exceeded."""
    store = EventStore(storage_path=temp_store_path)
    store.append(create_mock_event(1))
    store.append(create_mock_event(2))
    store.append(create_mock_event(3))

    events = store.get_events(1, 2)
    assert len(events) == 2


def test_recover_corrupted_json(temp_store_path: str) -> None:
    """Recovery must survive corrupted JSON lines."""
    os.makedirs(temp_store_path, exist_ok=True)
    seg_file = os.path.join(temp_store_path, "segment_000000.json")
    with open(seg_file, "w", encoding="utf-8") as f:
        f.write("{invalid json}\n")

    store = EventStore(storage_path=temp_store_path)
    assert store.get_current_sequence() == 0


def test_store_archive_path_creation() -> None:
    """Cover 35: archive path creation"""
    with tempfile.TemporaryDirectory() as td:
        archive_dir = os.path.join(td, "archive")
        EventStore(storage_path=os.path.join(td, "store"), archive_path=archive_dir)
        assert os.path.exists(archive_dir)


def test_store_recover_bad_filename() -> None:
    """Cover 56-57: handling unparseable segment sequences"""
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(td, exist_ok=True)
        with open(os.path.join(td, "segment_bad.json"), "w", encoding="utf-8") as f:
            f.write("")
        store = EventStore(storage_path=td)
        assert store.get_current_sequence() == 0


def test_store_retention_archival() -> None:
    """Cover 165-182: rotation to archive"""
    with tempfile.TemporaryDirectory() as td:
        store_path = os.path.join(td, "store")
        archive_path = os.path.join(td, "archive")
        store = EventStore(
            storage_path=store_path,
            archive_path=archive_path,
            segment_size=1,
            max_events=1,
        )

        for i in range(1, 4):
            store.append(create_mock_event(i))

        assert len(os.listdir(archive_path)) > 0


def test_store_retention_deletion() -> None:
    """Cover 165-182: rotation sequence deletion"""
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(storage_path=td, segment_size=1, max_events=1)

        for i in range(1, 4):
            store.append(create_mock_event(i))

        assert len(os.listdir(td)) <= 2


def test_store_event_correlation() -> None:
    """Cover EventStore._correlation_index and get_correlated_events"""
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(storage_path=td, segment_size=10)

        corr_id_1 = uuid4()
        corr_id_2 = uuid4()

        e1 = create_mock_event(1)
        e1 = replace(e1, correlation_id=corr_id_1)
        e2 = create_mock_event(2)
        e2 = replace(e2, correlation_id=corr_id_2)
        e3 = create_mock_event(3)
        e3 = replace(e3, correlation_id=corr_id_1)

        store.append(e1)
        store.append(e2)
        store.append(e3)

        # Test exact match
        corr_1_events = store.get_correlated_events(corr_id_1)
        assert len(corr_1_events) == 2
        assert corr_1_events[0].sequence_number == 1
        assert corr_1_events[1].sequence_number == 3

        # Test secondary match
        corr_2_events = store.get_correlated_events(corr_id_2)
        assert len(corr_2_events) == 1
        assert corr_2_events[0].sequence_number == 2

        # Test index rebuild on boot
        store2 = EventStore(storage_path=td, segment_size=10)
        rebuilt_events = store2.get_correlated_events(corr_id_1)
        assert len(rebuilt_events) == 2


def test_store_event_correlation_empty() -> None:
    """Cover empty check in get_correlated_events"""
    with tempfile.TemporaryDirectory() as td:
        store = EventStore(storage_path=td)
        assert store.get_correlated_events(uuid4()) == []
