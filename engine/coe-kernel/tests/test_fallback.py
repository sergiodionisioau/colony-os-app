"""Phase 3 Test Group 5 — Fallback: AI failure, degrade, and system resilience.

Tests the system's behavior when AI providers fail, ensuring graceful
degradation with proper event emission and continued system operation.
"""

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from core.agent.orchestrator import Orchestrator
from core.agent.types import (
    AgentConstraints,
    AgentTaskResult,
    AgentTaskSpec,
    AgentTaskStatus,
    AIMessage,
    AIResponse,
    ProviderConfig,
)
from core.agent_runtime.runtime import AgentRuntime
from tests.conftest import MockAuditLedger


class FailingProvider:
    """AI Provider that always raises to simulate total failure."""

    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Simulates an AI provider crash."""
        raise RuntimeError("Provider unavailable: connection refused")

    def provider_id(self) -> str:
        """Returns provider identifier."""
        return "failing_provider"


class TimeoutProvider:
    """AI Provider that simulates a timeout."""

    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Simulates a timeout exception."""
        raise TimeoutError("Provider timed out after 30s")

    def provider_id(self) -> str:
        """Returns provider identifier."""
        return "timeout_provider"


@pytest.fixture(name="mock_deps")
def mock_deps_fixture(mock_audit_ledger: MockAuditLedger) -> Dict[str, Any]:
    """Shared dependencies for fallback tests."""
    policy_engine = MagicMock()
    policy_engine.evaluate = MagicMock(return_value=MagicMock(allowed=True))

    event_bus = MagicMock()
    metering = MagicMock()

    return {
        "policy_engine": policy_engine,
        "event_bus": event_bus,
        "metering": metering,
        "audit_ledger": mock_audit_ledger,
    }


def _make_task() -> AgentTaskSpec:
    """Creates a standard task spec for fallback tests."""
    return AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        instruction="Summarize the quarterly report.",
        constraints=AgentConstraints(
            max_reasoning_steps=3,
            max_tokens=100,
            timeout_seconds=30,
            deterministic_mode=True,
        ),
        correlation_id=uuid.uuid4(),
    )


def test_ai_failure_triggers_degrade(mock_deps: Dict[str, Any]) -> None:
    """Phase 3 Group 5: AI failure triggers degrade — task returns FAILED status."""
    orchestrator = Orchestrator(
        policy_engine=mock_deps["policy_engine"],
        event_bus=mock_deps["event_bus"],
        metering=mock_deps["metering"],
        audit_ledger=mock_deps["audit_ledger"],
        ai_provider=FailingProvider(),
    )

    task = _make_task()
    result: AgentTaskResult = orchestrator.execute(task)

    assert result.status == AgentTaskStatus.FAILED
    assert result.error is not None
    assert "Provider unavailable" in result.error


def test_degrade_emits_event(mock_deps: Dict[str, Any]) -> None:
    """Phase 3 Group 5: Degrade emits event — event_bus.publish called with failure."""
    orchestrator = Orchestrator(
        policy_engine=mock_deps["policy_engine"],
        event_bus=mock_deps["event_bus"],
        metering=mock_deps["metering"],
        audit_ledger=mock_deps["audit_ledger"],
        ai_provider=FailingProvider(),
    )

    task = _make_task()
    orchestrator.execute(task)

    # Verify that the event bus received at least one publish call
    assert mock_deps["event_bus"].publish.called
    # Check that an agent.task_failed event was emitted
    published_events = mock_deps["event_bus"].publish.call_args_list
    event_types = [call[0][0].type for call in published_events]
    assert "agent.task_failed" in event_types


def test_system_remains_operational_after_failure(
    mock_deps: Dict[str, Any],
) -> None:
    """Phase 3 Group 5: System remains operational after AI failure."""
    orchestrator = Orchestrator(
        policy_engine=mock_deps["policy_engine"],
        event_bus=mock_deps["event_bus"],
        metering=mock_deps["metering"],
        audit_ledger=mock_deps["audit_ledger"],
        ai_provider=FailingProvider(),
    )

    # Execute multiple tasks — system should not crash
    for _ in range(5):
        task = _make_task()
        result = orchestrator.execute(task)
        assert result.status == AgentTaskStatus.FAILED

    # Verify event bus still accepts publishes (system is still alive)
    assert mock_deps["event_bus"].publish.call_count >= 5


def test_timeout_failure_returns_failed_result(
    mock_deps: Dict[str, Any],
) -> None:
    """Phase 3 Group 5: Timeout exception is caught and returns FAILED result."""
    orchestrator = Orchestrator(
        policy_engine=mock_deps["policy_engine"],
        event_bus=mock_deps["event_bus"],
        metering=mock_deps["metering"],
        audit_ledger=mock_deps["audit_ledger"],
        ai_provider=TimeoutProvider(),
    )

    task = _make_task()
    result = orchestrator.execute(task)

    assert result.status == AgentTaskStatus.FAILED
    assert result.error is not None


def test_runtime_wraps_orchestrator_failure(
    mock_deps: Dict[str, Any],
) -> None:
    """Phase 3 Group 5: AgentRuntime wraps orchestrator failure — never panics."""
    identity_service = MagicMock()
    identity = MagicMock()
    identity.id = uuid.uuid4()
    identity_service.register_agent.return_value = identity

    # Create an orchestrator that always raises
    failing_orchestrator = MagicMock()
    failing_orchestrator.execute.side_effect = RuntimeError("Orchestrator crash")

    runtime = AgentRuntime(
        identity_service=identity_service,
        metering=mock_deps["metering"],
        event_bus=mock_deps["event_bus"],
        audit_ledger=mock_deps["audit_ledger"],
        orchestrator=failing_orchestrator,
    )

    task = _make_task()
    result = runtime.execute(task)

    # Runtime should return FAILED, not raise
    assert result.status == AgentTaskStatus.FAILED
    assert "Runtime wrapper caught fault" in (result.error or "")
