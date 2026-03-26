"""Persistent segmented Event Store for the Event Bus."""

import json
import os
import shutil
from dataclasses import dataclass
from typing import List, Optional, Dict
from uuid import UUID

from core.errors import ErrorCode, KernelError
from core.types import Event
from core.utils.persistence import get_sorted_segments, enforce_segment_retention


@dataclass
class StoreConfig:
    """Typed configuration for the Event Store."""

    storage_path: str
    segment_size: int
    max_events: Optional[int]
    archive_path: Optional[str]


class EventStore:
    """Appends strictly ordered events into segmented disk logs."""

    def __init__(
        self,
        storage_path: str,
        segment_size: int = 100000,
        max_events: Optional[int] = None,
        archive_path: Optional[str] = None,
    ) -> None:
        """Initialize the store and recover highest sequence number."""
        self.config = StoreConfig(
            storage_path=storage_path,
            segment_size=segment_size,
            max_events=max_events,
            archive_path=archive_path,
        )

        self._current_sequence = 0
        self._current_segment_index = 0
        self._current_segment_count = 0
        self._correlation_index: Dict[UUID, List[int]] = {}

        os.makedirs(self.config.storage_path, exist_ok=True)
        if self.config.archive_path:
            os.makedirs(self.config.archive_path, exist_ok=True)

        self._recover_state()
        self._rebuild_index()

    def _get_segment_path(self, index: int) -> str:
        """Returns the absolute path for a specific segment file."""
        return os.path.join(self.config.storage_path, f"segment_{index:06d}.json")

    def _recover_state(self) -> None:
        """Examines existing segments to determine the starting sequence boundary."""
        files = get_sorted_segments(self.config.storage_path, "segment_")
        if not files:
            return

        latest_file = files[-1]
        try:
            self._current_segment_index = int(latest_file.split("_")[1].split(".")[0])
        except (IndexError, ValueError):
            pass

        filepath = os.path.join(self.config.storage_path, latest_file)

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self._current_segment_count = len(lines)
            if lines:
                try:
                    data = json.loads(lines[-1])
                    self._current_sequence = data.get("sequence_number", 0)
                except json.JSONDecodeError:
                    pass

    def _rebuild_index(self) -> None:
        """Fully scans all segments on boot to rebuild the correlation index."""
        files = get_sorted_segments(self.config.storage_path, "segment_")
        for file in files:
            filepath = os.path.join(self.config.storage_path, file)
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        corr_id = UUID(data["correlation_id"])
                        seq = data.get("sequence_number", 0)
                        if corr_id not in self._correlation_index:
                            self._correlation_index[corr_id] = []
                        self._correlation_index[corr_id].append(seq)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        pass

    def get_current_sequence(self) -> int:
        """Returns the highest monotonic sequence number assigned so far."""
        return self._current_sequence

    def get_retained_event_count(self) -> int:
        """Returns the approximate number of events currently retained on disk."""
        files = get_sorted_segments(self.config.storage_path, "segment_")
        if not files:
            return 0
        return (
            max(0, len(files) - 1) * self.config.segment_size
            + self._current_segment_count
        )

    def append(self, event: Event) -> None:
        """Persists the event continuously, rotating segments when filled."""
        if event.sequence_number <= self._current_sequence:
            raise KernelError(
                code=ErrorCode.EVENT_VERSION_MISMATCH,
                message=(
                    "Out-of-order write rejected: "
                    f"seq {event.sequence_number} <= "
                    f"{self._current_sequence}"
                ),
            )

        if self._current_segment_count >= self.config.segment_size:
            self._current_segment_index += 1
            self._current_segment_count = 0

        filepath = self._get_segment_path(self._current_segment_index)

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        self._current_sequence = event.sequence_number
        self._current_segment_count += 1

        if event.correlation_id not in self._correlation_index:
            self._correlation_index[event.correlation_id] = []
        self._correlation_index[event.correlation_id].append(event.sequence_number)

        self._enforce_retention()

    def _enforce_retention(self) -> None:
        """Evicts old segments if total event capacity is exceeded."""
        files_to_remove = enforce_segment_retention(
            self.config.storage_path,
            "segment_",
            self.config.max_events or 0,
            self.config.segment_size,
        )

        # If we have more segments than allowed
        for file in files_to_remove:
            filepath = os.path.join(self.config.storage_path, file)
            if self.config.archive_path:
                archive_dest = os.path.join(self.config.archive_path, file)
                shutil.move(filepath, archive_dest)
            else:
                os.remove(filepath)

    def get_segment_path(self, index: int) -> str:
        """Returns the absolute path for a specific segment file.

        Used for Phase 2 verification.
        """
        return self._get_segment_path(index)

    def get_events(self, start_seq: int, end_seq: int) -> List[Event]:
        """Retrieves an ordered batch of events across multiple segments."""
        events = []
        files = get_sorted_segments(self.config.storage_path, "segment_")

        for file in files:
            filepath = os.path.join(self.config.storage_path, file)
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    # Pre-screen sequence number cheaply
                    try:
                        event = Event.from_dict(json.loads(line))
                    except (
                        json.JSONDecodeError,
                        ValueError,
                        KeyError,
                    ):  # G-05 fix: crash resilience for corrupted lines
                        continue

                    if start_seq <= event.sequence_number <= end_seq:
                        events.append(event)
                    elif event.sequence_number > end_seq:
                        # Since it's monotonically ordered, we can stop reading
                        return events

        return events

    def get_correlated_events(self, correlation_id: UUID) -> List[Event]:
        """Retrieves all events matching a specific correlation ID."""
        seqs = self._correlation_index.get(correlation_id, [])
        if not seqs:
            return []

        min_seq = min(seqs)
        max_seq = max(seqs)

        # Pull candidate events using the existing scan range
        events = self.get_events(min_seq, max_seq)

        # Filter for the exact correlation_id
        return [e for e in events if e.correlation_id == correlation_id]
