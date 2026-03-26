"""Scoped memory adapters for Agent reasoning loops.

This module provides implementations of MemoryAdapterInterface for both
production (InMemoryAdapter) and testing (NullMemory).
"""

import uuid
from typing import Any, Dict, Optional

from core.interfaces import MemoryAdapterInterface


class NullMemory(MemoryAdapterInterface):
    """Phase 3 default: No-op memory adapter."""

    def store(self, key: str, value: Any, scope_id: uuid.UUID) -> None:
        """No-op storage."""
        _ = (key, value, scope_id)

    def retrieve(self, key: str, scope_id: uuid.UUID) -> Optional[Any]:
        """Always returns None."""
        _ = (key, scope_id)
        result: Optional[Any] = None
        return result

    def clear(self, scope_id: uuid.UUID) -> None:
        """No-op clear."""
        _ = scope_id


class InMemoryAdapter(MemoryAdapterInterface):
    """Dict-backed working memory scoped per task/correlation_id."""

    def __init__(self) -> None:
        self._storage: Dict[uuid.UUID, Dict[str, Any]] = {}

    def store(self, key: str, value: Any, scope_id: uuid.UUID) -> None:
        """Stores a value in the context of a specific scope/task."""
        if scope_id not in self._storage:
            self._storage[scope_id] = {}
        self._storage[scope_id][key] = value

    def retrieve(self, key: str, scope_id: uuid.UUID) -> Optional[Any]:
        """Retrieves a value from a specific scope context."""
        return self._storage.get(scope_id, {}).get(key)

    def clear(self, scope_id: uuid.UUID) -> None:
        """Removes all memory associated with a scope."""
        if scope_id in self._storage:
            del self._storage[scope_id]
