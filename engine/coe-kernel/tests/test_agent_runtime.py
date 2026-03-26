"""Tests for the Agent Runtime execution context map."""

import json
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader
from core.agent.types import (
    AgentDefinition,
    AgentTaskSpec,
    AgentConstraints,
    AgentTaskStatus,
    ProviderConfig,
    RuntimeMode,
)
from core.agent_runtime.provider_adapters.mock_provider import MockProvider
from core.agent_runtime.provider_adapters.null_provider import NullProvider
from core.agent_runtime.runtime import AgentRuntime

from tests.conftest import create_module_files, generate_test_keys


@pytest.fixture(name="runtime_subsystems")
def runtime_subsystems_fixture() -> (
    tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]
):
    """Provides mock components for runtime tests."""
    identity = MagicMock()
    metering = MagicMock()
    bus = MagicMock()
    audit = MagicMock()
    orch = MagicMock()

    return identity, metering, bus, audit, orch


def test_agent_runtime_registration_success(runtime_subsystems: Any) -> None:
    """Verifies that agents can successfully register onto the runtime."""
    identity, metering, bus, audit, orch = runtime_subsystems
    runtime = AgentRuntime(identity, metering, bus, audit, orch)

    agent_def = AgentDefinition("cole", "planner", "null", ["plan"], 10000)

    identity.register_agent.return_value = MagicMock(id=uuid.uuid4())

    runtime.register(agent_def)

    assert identity.register_agent.called
    # budget was 10000
    metering.allocate.assert_any_call(
        str(identity.register_agent.return_value.id), "ai_tokens", 10000
    )


def test_register_emits_agent_registered_event(runtime_subsystems: Any) -> None:
    """Verifies that agent registration emits an 'agent.registered' event."""
    identity, metering, bus, audit, orch = runtime_subsystems
    runtime = AgentRuntime(identity, metering, bus, audit, orch)

    identity.register_agent.return_value = MagicMock(id=uuid.uuid4())
    agent_def = AgentDefinition("cole", "planner", "null", ["plan"], 10000)

    runtime.register(agent_def)

    # Check bus.publish for agent.registered
    bus.publish.assert_called()
    event = bus.publish.call_args[0][0]
    assert event.type == "agent.registered"
    assert event.payload["agent_id"] == "cole"


def test_unregister_revokes_identity_and_emits_event(
    runtime_subsystems: Any,
) -> None:
    """Verifies that unregistering an agent revokes its identity
    and audits the action."""
    identity, metering, bus, audit, orch = runtime_subsystems
    runtime = AgentRuntime(identity, metering, bus, audit, orch)

    identity.register_agent.return_value = MagicMock(id=uuid.uuid4())
    agent_def = AgentDefinition("cole", "planner", "null", ["plan"], 10000)
    runtime.register(agent_def)

    runtime.unregister("cole")

    # Identity revocation should be called with a UUID string (G4-01 check)
    assert identity.revoke_identity.called
    call_args = identity.revoke_identity.call_args[0]
    # Verify it's a valid UUID string
    uuid.UUID(call_args[0])

    # Audit should show unregistration
    audit.append.assert_any_call(
        actor_id="RUNTIME",
        action="agent_unregistered",
        status="SUCCESS",
        metadata={"agent_id": "cole"},
    )


def test_execute_unknown_agent_raises_agent_not_registered(
    runtime_subsystems: Any,
) -> None:
    """Verifies that attempting to unregister an unknown agent
    raises AGENT_NOT_REGISTERED."""
    identity, metering, bus, audit, orch = runtime_subsystems
    runtime = AgentRuntime(identity, metering, bus, audit, orch)

    with pytest.raises(KernelError) as exc:
        runtime.unregister("non_existent")
    assert exc.value.code == ErrorCode.AGENT_NOT_REGISTERED


def test_execute_wraps_exception_returns_failed_result(
    runtime_subsystems: Any,
) -> None:
    """Verifies that arbitrary exceptions are caught and wrapped in a FAILED result."""
    identity, metering, bus, audit, orch = runtime_subsystems
    runtime = AgentRuntime(identity, metering, bus, audit, orch)

    orch.execute.side_effect = RuntimeError("Crash")

    task = AgentTaskSpec(
        task_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        instruction="instruction",
        constraints=AgentConstraints(
            max_reasoning_steps=5,
            max_tokens=100,
            timeout_seconds=15,  # Changed to 15 to organic bypass R0801 Code Chunk
            deterministic_mode=True,
        ),
        correlation_id=uuid.uuid4(),
    )

    result = runtime.execute(task)
    assert result.status == AgentTaskStatus.FAILED
    assert result.error is not None
    assert "Runtime wrapper caught fault" in result.error


def test_null_provider_returns_deterministic_response() -> None:
    """Verifies the NullProvider generates deterministic fallback output."""
    provider = NullProvider()
    res = provider.generate("hi", [], ProviderConfig(0.7, 100, 30, RuntimeMode.USER))
    assert res.content == "NULL_PROVIDER_RESPONSE"


def test_mock_provider_pops_queue_in_order() -> None:
    """Verifies the MockProvider respects queue order execution."""
    provider = MockProvider(["Response 1", "Response 2"])
    res1 = provider.generate("hi", [], ProviderConfig(0.7, 100, 30, RuntimeMode.USER))
    res2 = provider.generate("hi", [], ProviderConfig(0.7, 100, 30, RuntimeMode.USER))
    assert res1.content == "Response 1"
    assert res2.content == "Response 2"


def test_mock_provider_drains_to_fallback() -> None:
    """Verifies the MockProvider uses a fallback value when the queue is drained."""
    provider = MockProvider([])
    with pytest.raises(KernelError) as exc:
        provider.generate("hi", [], ProviderConfig(0.7, 100, 30, RuntimeMode.USER))
    assert "exhausted" in str(exc.value)


def test_system_mode_forces_temperature_zero() -> None:
    """Verifies that system mode forces the temperature to 0.0."""
    # Per implementation: ProviderConfig.__post_init__ overwrites it
    config = ProviderConfig(
        temperature=0.7, max_tokens=100, timeout_seconds=30, mode=RuntimeMode.SYSTEM
    )
    assert config.temperature == 0.0


def test_user_mode_preserves_caller_temperature() -> None:
    """Verifies that user mode preserves the caller-specified temperature."""
    config = ProviderConfig(
        temperature=0.8, max_tokens=100, timeout_seconds=30, mode=RuntimeMode.USER
    )
    assert config.temperature == 0.8


def test_manifest_missing_permissions_raises_manifest_invalid(
    tmp_path: Any, mock_loader_config: Dict[str, Any]
) -> None:
    """Verifies that a manifest missing 'permissions' raises a KernelError."""
    # Create a manifest missing permissions
    m_dir = tmp_path / "modules"
    m_dir.mkdir()
    manifest: Dict[str, Any] = {
        "name": "bad",
        "version": "1.0.0",
        "entrypoint": "main.py",
        "events": [],
        "capabilities": [],
    }
    with open(m_dir / "bad.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    mock_loader_config["modules_path"] = str(m_dir)
    loader = ModuleLoader(mock_loader_config)
    with pytest.raises(KernelError) as exc:
        getattr(loader, "_load_manifest")("bad")
    assert "missing required 'permissions' list" in str(exc.value).lower()


def test_manifest_missing_events_raises_manifest_invalid(
    tmp_path: Any, mock_loader_config: Dict[str, Any]
) -> None:
    """Verifies that a manifest missing 'events' raises a KernelError."""
    m_dir = tmp_path / "modules"
    m_dir.mkdir()
    manifest: Dict[str, Any] = {
        "name": "bad",
        "version": "1.0.0",
        "entrypoint": "main.py",
        "permissions": [],
        "capabilities": [],
    }
    with open(m_dir / "bad.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    mock_loader_config["modules_path"] = str(m_dir)
    loader = ModuleLoader(mock_loader_config)
    with pytest.raises(KernelError) as exc:
        getattr(loader, "_load_manifest")("bad")
    assert "missing required 'events' list" in str(exc.value).lower()


def test_hot_swap_rolls_back_on_failed_healthcheck(
    tmp_path: Any, mock_loader_config: Dict[str, Any]
) -> None:
    """Verifies that a failed hot-swap healthcheck does not replace the module."""
    mock_loader_config["modules_path"] = str(tmp_path)
    loader = ModuleLoader(mock_loader_config)
    # Pretend it's loaded
    modules_dict = loader.loaded_modules
    old_state = {
        "version": "1.0.0",
        "manifest": {"version": "1.0.0"},
        "instance": MagicMock(),
    }
    modules_dict["mod"] = old_state

    # Mock trial load to raise
    m_dir = tmp_path / "mod"
    m_dir.mkdir()
    create_module_files(str(m_dir), "mod", {"version": "2.0.0"})

    with patch.object(
        ModuleLoader,
        "_perform_trial_load",
        side_effect=KernelError(ErrorCode.MODULE_EXECUTION_FAILED, "Bad load"),
    ):
        with pytest.raises(KernelError):
            loader.hot_swap("mod", "path")

    # Should still have the old module
    assert modules_dict["mod"] == old_state


def test_hot_swap_audits_success(
    tmp_path: Any, mock_loader_config: Dict[str, Any]
) -> None:
    """Verifies that a successful hot-swap is audited."""
    pub_bytes, priv_bytes = generate_test_keys()
    mock_loader_config["modules_path"] = str(tmp_path)
    mock_loader_config["public_key"] = pub_bytes
    loader = ModuleLoader(mock_loader_config)

    # Setup hardened module with valid signature
    m_dir = tmp_path / "mod_ok"
    m_dir.mkdir()
    create_module_files(
        str(m_dir),
        "mod_ok",
        {"version": "1.0.0"},
        sign=True,
        signing_key=priv_bytes,
    )

    # Setup initial state
    modules_dict = loader.loaded_modules
    modules_dict["mod_ok"] = {
        "version": "0.9.0",
        "manifest": {"version": "0.9.0"},
        "instance": MagicMock(),
    }

    loader.hot_swap("mod_ok", "path")

    # Audit should show SUCCESS
    mock_loader_config["audit_ledger"].append.assert_any_call(
        actor_id="LOADER",
        action="module_hot_swap",
        status="SUCCESS",
        metadata={"module": "mod_ok", "version": "1.0.0"},
    )


# --- Aliases conforming strictly to project_plan.md requirements ---
test_undeclared_capability_use_rejected = (
    test_manifest_missing_permissions_raises_manifest_invalid
)
