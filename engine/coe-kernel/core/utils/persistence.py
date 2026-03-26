"""Shared persistence utilities for segmented logs."""

import os
from typing import List


def get_sorted_segments(storage_path: str, prefix: str) -> List[str]:
    """Returns a sorted list of segment filenames matching the prefix."""
    if not os.path.exists(storage_path):
        return []

    files = [
        f
        for f in os.listdir(storage_path)
        if f.startswith(prefix) and f.endswith(".json")
    ]
    files.sort()
    return files


def enforce_segment_retention(
    storage_path: str,
    prefix: str,
    max_events: int,
    segment_size: int,
) -> List[str]:
    """Determines which segments should be removed based on retention policy."""
    if not max_events:
        return []

    max_segments = max(1, max_events // segment_size)
    files = get_sorted_segments(storage_path, prefix)

    if len(files) > max_segments:
        return files[:-max_segments]
    return []
