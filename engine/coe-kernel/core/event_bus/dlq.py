"""Dead Letter Queue for handling subscriber execution casualties."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.types import DLQEntry, Event
from core.utils.persistence import get_sorted_segments, enforce_segment_retention


@dataclass
class DLQConfig:
    """Typed configuration for the Dead Letter Queue."""

    storage_path: str
    segment_size: int
    max_events: Optional[int]


class DeadLetterQueue:
    """Isolates subscriber failures preserving the origin event payload safely to disk.

    Safe serialization to disk ensures durability and recovery after kernel restarts.
    """

    def __init__(
        self,
        storage_path: str,
        segment_size: int = 10000,
        max_events: Optional[int] = None,
    ) -> None:
        """Initialize persistent DLQ and recover state."""
        self.logger = logging.getLogger(__name__)
        self.config = DLQConfig(
            storage_path=os.path.join(storage_path, "dlq"),
            segment_size=segment_size,
            max_events=max_events,
        )

        self._entries: List[DLQEntry] = []
        self._metrics_by_subscriber: Dict[str, int] = {}

        self._current_segment_index = 0
        self._current_segment_count = 0

        os.makedirs(self.config.storage_path, exist_ok=True)
        self._recover_state()

    def _get_segment_path(self, index: int) -> str:
        """Returns the absolute path for a specific segment file."""
        return os.path.join(self.config.storage_path, f"dlq_segment_{index:06d}.json")

    def _recover_state(self) -> None:
        """Examines existing fragments and builds in-memory DLQ state."""
        files = get_sorted_segments(self.config.storage_path, "dlq_segment_")
        if not files:
            return

        # Determine latest segment
        latest_file = files[-1]
        try:
            self._current_segment_index = int(latest_file.split("_")[2].split(".")[0])
        except (IndexError, ValueError):
            pass

        # Load all entries into memory
        for file in files:
            filepath = os.path.join(self.config.storage_path, file)
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if file == latest_file:
                    self._current_segment_count = len(lines)
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        entry = DLQEntry.from_dict(json.loads(line))
                        self._entries.append(entry)
                        sub_id = entry.subscriber_id
                        self._metrics_by_subscriber[sub_id] = (
                            self._metrics_by_subscriber.get(sub_id, 0) + 1
                        )
                    except (json.JSONDecodeError, OSError, ValueError, KeyError) as exc:
                        self.logger.error("Failed to deserialize DLQ entry: %s", exc)

    def _enforce_retention(self) -> None:
        """Evicts old segments if total DLQ capacity is exceeded."""
        files_to_remove = enforce_segment_retention(
            self.config.storage_path,
            "dlq_segment_",
            self.config.max_events or 0,
            self.config.segment_size,
        )
        for file in files_to_remove:
            filepath = os.path.join(self.config.storage_path, file)
            os.remove(filepath)

    def append(self, failed_event: Event, reason: str, subscriber_id: str) -> None:
        """Records a subscriber exception to disk and memory."""
        entry = DLQEntry(
            failed_event=failed_event,
            reason=reason,
            subscriber_id=subscriber_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            retry_count=0,
        )

        # Persist to disk
        if self._current_segment_count >= self.config.segment_size:
            self._current_segment_index += 1
            self._current_segment_count = 0
            self._enforce_retention()

        filepath = self._get_segment_path(self._current_segment_index)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        self._current_segment_count += 1

        # Update memory state
        self._entries.append(entry)
        if subscriber_id not in self._metrics_by_subscriber:
            self._metrics_by_subscriber[subscriber_id] = 0
        self._metrics_by_subscriber[subscriber_id] += 1

    def get_entries(self) -> List[DLQEntry]:
        """Provides direct access to failed events."""
        return list(self._entries)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns summarized failure constraints for systemic health monitoring."""
        return {
            "total_dead_letters": len(self._entries),
            "failures_by_subscriber": dict(self._metrics_by_subscriber),
        }
