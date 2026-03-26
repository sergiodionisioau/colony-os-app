"""LangGraph State Definitions.

Strict state typing for deterministic execution.
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class AgentState(TypedDict):
    """Core agent state for LangGraph execution."""
    # Task identification
    task_id: str
    correlation_id: str

    # Input/Output
    input: str
    output: str

    # Execution state
    plan: List[str]
    current_step: int
    steps_results: List[str]

    # Status tracking
    status: str  # pending, planning, executing, completed, failed
    error: Optional[str]

    # Memory integration
    context: List[str]  # Retrieved context from memory
    memory_ids: List[str]  # IDs of stored memories

    # Metadata
    started_at: str
    completed_at: Optional[str]
    retry_count: int


class TaskRequest(TypedDict):
    """Incoming task request format."""
    task_id: str
    input: str
    context: Optional[Dict[str, Any]]
    priority: int


class TaskResult(TypedDict):
    """Task result format."""
    task_id: str
    status: str
    output: str
    plan: List[str]
    steps_taken: int
    execution_time_ms: int
    memory_ids: List[str]


def create_initial_state(task_id: str, input_text: str) -> AgentState:
    """Create initial state for new task."""
    return {
        "task_id": task_id,
        "correlation_id": task_id,  # Self-correlated
        "input": input_text,
        "output": "",
        "plan": [],
        "current_step": 0,
        "steps_results": [],
        "status": "pending",
        "error": None,
        "context": [],
        "memory_ids": [],
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "retry_count": 0,
    }
