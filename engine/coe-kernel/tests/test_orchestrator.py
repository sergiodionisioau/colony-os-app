"""Tests for the Orchestrator loop."""

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.errors import KernelError
from core.agent.orchestrator import Orchestrator
from core.agent.types import (
    AgentTaskSpec,
    AgentConstraints,
    AgentTaskStatus,
    AIResponse,
)
from core.agent.scope_enforcer import PolicyScopeEnforcer, PolicyScopeBinding
from core.agent.memory import NullMemory, InMemoryAdapter


@pytest.fixture(name="subsystems")
def mock_subsystems_fixture() -> tuple[
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    NullMemory,
    PolicyScopeEnforcer,
]:
    """Provides mock subsystems for the Orchestrator."""
    policy = MagicMock()
    bus = MagicMock()
    metering = MagicMock()
    audit = MagicMock()
    ai = MagicMock()
    # Ensure identity has a consistent role for scope enforcement (G3-03)
    policy.identity_service.get_identity.return_value = MagicMock(role="planner")
    memory = NullMemory()
    scope = PolicyScopeEnforcer(
        policy,
        policy.identity_service,
        [PolicyScopeBinding("planner", ["plan", "complete", "test_cap"])],
    )

    return policy, bus, metering, audit, ai, memory, scope


def test_max_steps_exceeded_returns_exceeded_status(subsystems: Any) -> None:
    """Verifies loop termination on max steps."""
    _, bus, metering, audit, ai, memory, scope = subsystems

    # AI never says COMPLETE:
    ai.generate.return_value = AIResponse("THINKING...", 0, 0, 0.0, "mock")

    orch = Orchestrator(scope, bus, metering, audit, ai, memory)

    task = AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        instruction="Do something",
        constraints=AgentConstraints(
            max_reasoning_steps=2,
            max_tokens=100,
            timeout_seconds=10,
            deterministic_mode=True,
        ),
        correlation_id=uuid.uuid4(),
    )

    result = orch.execute(task)
    assert result.status == AgentTaskStatus.EXCEEDED
    assert result.steps_taken == 2


def test_policy_deny_stops_loop_and_emits_task_failed(subsystems: Any) -> None:
    """Verifies policy denial stops the loop."""
    policy, bus, metering, audit, ai, memory, scope = subsystems

    # AI tries to call a capability
    ai.generate.return_value = AIResponse("CALL: test_cap", 10, 10, 0.0, "mock")
    # But policy says NO
    policy.evaluate.return_value = MagicMock(allowed=False, reason="Denied by RBAC")

    orch = Orchestrator(scope, bus, metering, audit, ai, memory)

    task = AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        instruction="Run test_cap",
        constraints=AgentConstraints(
            max_reasoning_steps=5,
            max_tokens=100,
            timeout_seconds=10,
            deterministic_mode=True,
        ),
        correlation_id=uuid.uuid4(),
    )

    result = orch.execute(task)
    assert result.status == AgentTaskStatus.FAILED
    assert result.error is not None
    # Can be denied by Scope or RBAC
    assert "Policy denied" in result.error or "outside the scope" in result.error

    # Verify agent.task_failed was published
    failed_events = [
        args[0]
        for args, _ in bus.publish.call_args_list
        if args[0].type == "agent.task_failed"
    ]
    assert len(failed_events) == 1


def test_all_events_share_correlation_id(subsystems: Any) -> None:
    """Verifies correlation ID is propagated to all emitted events."""
    _, bus, metering, audit, ai, memory, scope = subsystems
    corr_id = uuid.uuid4()

    ai.generate.return_value = AIResponse("COMPLETE: Done", 10, 10, 0.0, "mock")
    orch = Orchestrator(scope, bus, metering, audit, ai, memory)

    task = AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        instruction="Finish",
        constraints=AgentConstraints(
            max_reasoning_steps=5,
            max_tokens=100,
            timeout_seconds=10,
            deterministic_mode=True,
        ),
        correlation_id=corr_id,
    )

    orch.execute(task)

    for args, _ in bus.publish.call_args_list:
        event = args[0]
        assert event.correlation_id == corr_id


def test_ai_tokens_recorded_after_each_provider_call(subsystems: Any) -> None:
    """Verifies token metering after each AI provider call."""
    _, bus, metering, audit, ai, memory, scope = subsystems
    agent_id = uuid.uuid4()

    # Takes 2 steps to complete
    ai.generate.side_effect = [
        AIResponse("STILL_THINKING", 50, 50, 0.0, "mock"),
        AIResponse("COMPLETE: Done", 30, 30, 0.0, "mock"),
    ]

    orch = Orchestrator(scope, bus, metering, audit, ai, memory)

    task = AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=agent_id,
        instruction="Work",
        constraints=AgentConstraints(
            max_reasoning_steps=5,
            max_tokens=100,
            timeout_seconds=10,
            deterministic_mode=True,
        ),
        correlation_id=uuid.uuid4(),
    )

    orch.execute(task)

    # Should have recorded 4 times: (50+50) tokens, 0.0 cost,
    # then (30+30) tokens, 0.0 cost
    assert metering.record.call_count == 4
    # Check first call args
    metering.record.assert_any_call(agent_id, "ai_tokens", 100.0)
    metering.record.assert_any_call(agent_id, "ai_cost_usd", 0.0)


def test_null_memory_store_retrieve_returns_none() -> None:
    """Verifies NullMemory behaves as a black hole."""
    mem = NullMemory()
    u = uuid.uuid4()
    mem.store("key", "val", u)
    assert mem.retrieve("key", u) is None


def test_in_memory_adapter_isolates_by_scope_id() -> None:
    """Verifies InMemoryAdapter isolates data by context ID."""
    mem = InMemoryAdapter()
    u1 = uuid.uuid4()
    u2 = uuid.uuid4()

    mem.store("foo", "bar", u1)
    mem.store("foo", "baz", u2)

    assert mem.retrieve("foo", u1) == "bar"
    assert mem.retrieve("foo", u2) == "baz"

    mem.clear(u1)
    assert mem.retrieve("foo", u1) is None
    assert mem.retrieve("foo", u2) == "baz"


def test_scope_enforcer_rejects_out_of_scope_capability() -> None:
    """Verifies scope enforcer blocks undeclared capabilities."""
    mock_policy = MagicMock()
    scope = PolicyScopeEnforcer(
        mock_policy,
        mock_policy.identity_service,
        [PolicyScopeBinding("agent", ["read"])],
    )

    with pytest.raises(KernelError) as exc:
        scope.check("agent", "write")
    assert "outside the scope" in str(exc.value)


def test_scope_enforcer_allows_declared_capability() -> None:
    """Verifies scope enforcer allows declared capabilities."""
    mock_policy = MagicMock()
    scope = PolicyScopeEnforcer(
        mock_policy,
        mock_policy.identity_service,
        [PolicyScopeBinding("agent", ["read"])],
    )
    # Should NOT raise
    scope.check("agent", "read")
