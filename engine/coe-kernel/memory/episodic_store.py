"""Episodic Memory Store.

PostgreSQL-based storage for task execution history.
"""

from typing import Any, Dict, List, Optional


class EpisodicStore:
    """PostgreSQL-based episodic memory store."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize episodic store."""
        self.config = config or {}
        self.table_name = self.config.get("episodic_table", "episodic_memory")

        # In-memory storage for demo
        self._episodes: List[Dict[str, Any]] = []

    def store(self, episode: Dict[str, Any]) -> str:
        """Store an episode."""
        self._episodes.append(episode)
        return episode["id"]

    def query(self, task_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Query episodes."""
        results = self._episodes

        if task_id:
            results = [e for e in results if e.get("task_id") == task_id]

        # Sort by created_at descending
        results = sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

        return results[:limit]

    def get_by_id(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Get episode by ID."""
        for episode in self._episodes:
            if episode["id"] == episode_id:
                return episode
        return None

    def get_successful_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get successful task episodes."""
        successful = [e for e in self._episodes if e.get("success", True)]
        return successful[:limit]
