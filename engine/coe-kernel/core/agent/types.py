"""Core data structures and enums for the Agent OS.

This module defines all shared types, including task specifications, AI response
formats, and state enums used by Orchestrator and Runtime.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentTaskStatus(Enum):
    """Lifecycle states of an agent task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    EXCEEDED = "exceeded"  # max_reasoning_steps exhausted before completion


class RuntimeMode(Enum):
    """Execution modes for AI provider configurations."""

    SYSTEM = "system"  # temperature forced to 0.0
    USER = "user"  # temperature from caller config


class PatchStatus(Enum):
    """Lifecycle states of a proposed code modification."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass(frozen=True)
class AgentConstraints:
    """Bounding parameters for an agent's execution scope."""

    max_reasoning_steps: int  # hard upper bound on for-loop iterations
    max_tokens: int  # per provider call
    timeout_seconds: int  # per provider call
    deterministic_mode: bool  # if True, forces RuntimeMode.SYSTEM


@dataclass(frozen=True)
class AgentTaskSpec:
    """Explicit instruction set for an agent task."""

    task_id: uuid.UUID
    agent_id: uuid.UUID
    instruction: str
    constraints: AgentConstraints
    correlation_id: uuid.UUID
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentTaskResult:
    """Final outcome of an agent's reasoning loop."""

    task_id: uuid.UUID
    agent_id: uuid.UUID
    status: AgentTaskStatus
    steps_taken: int
    final_output: Optional[str]
    error: Optional[str]
    correlation_id: uuid.UUID


@dataclass(frozen=True)
class AIMessage:
    """Individual message in an LLM conversation history."""

    role: str  # exactly one of: "system", "user", "assistant"
    content: str


@dataclass(frozen=True)
class ProviderConfig:
    """Runtime configuration for an AI Provider call."""

    temperature: float  # 0.0–2.0; overridden to 0.0 in SYSTEM mode
    max_tokens: int
    timeout_seconds: int
    mode: RuntimeMode

    def __post_init__(self) -> None:
        if self.mode == RuntimeMode.SYSTEM:
            object.__setattr__(self, "temperature", 0.0)


@dataclass(frozen=True)
class AIResponse:
    """Structured output from an AI Provider."""

    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    provider_id: str


@dataclass(frozen=True)
class AgentDefinition:
    """Identity and capability mapping for a registered agent."""

    agent_id: str  # stable string slug e.g. "cole"
    role: str  # must exist in RBAC schema
    provider_id: str  # must match a registered AIProvider key
    capabilities: List[str]
    token_budget: int  # allocated to MeteringLayer on registration


@dataclass(frozen=True)
class Patch:
    """Represents a proposed unified diff for a module."""

    patch_id: uuid.UUID
    target_module: str  # e.g. "crm_module" — must NOT match PROTECTED_PATHS
    unified_diff: str  # non-empty string; unified diff format
    test_vector: str  # pytest command: e.g. "tests/test_crm.py -v"
    proposed_by: str  # agent identity_id (str UUID)
    status: PatchStatus = PatchStatus.PROPOSED


@dataclass(frozen=True)
class CIResult:
    """Outcome of a CI test execution for a proposed patch."""

    passed: bool
    duration_ms: int
    output: str  # captured stdout/stderr of test run


@dataclass(frozen=True)
class PolicyScopeBinding:
    """Mapping of an agent role to its permitted capabilities."""

    agent_role: str
    allowed_capabilities: List[str]
