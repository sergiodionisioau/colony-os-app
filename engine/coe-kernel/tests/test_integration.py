"""Integration test suite for the COE Kernel.

Tests the Happy Path integration of all Core subsystems.
"""

import os
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from core.main import KernelBootstrap
from core.types import Event
from core.event_bus.bus import compute_event_signature

# Test Group 8 — Integration:
# Schema registered -> Subscriber registered -> Valid event published ->
# Policy validated -> Event stored -> Audit logged -> Subscriber executed
# -> Metering incremented -> No dead-letter entry


@pytest.fixture(name="kernel")
def kernel_fixture(tmp_path: Any) -> KernelBootstrap:
    """Fixture providing a connected Kernel."""
    plugins_dir = str(tmp_path / "modules")
    config = {
        "bootstrap": {
            "mode": "genesis",
            "root_keypair_path": str(tmp_path / "root.pem"),
            "admin_identity": {"name": "admin", "role": "admin", "type": "user"},
        },
        "audit_path": str(tmp_path / "audit.log"),
        "genesis": "TEST_GENESIS",
        "rbac": {"roles": {"agent": ["publish_event"], "admin": ["*"]}},
        "secrets": {
            "data_path": str(tmp_path / "secrets.json"),
            "salt_path": str(tmp_path / "salt.bin"),
            "passphrase": "test_passphrase",
        },
        "modules": {
            "plugins_dir": plugins_dir,
            "forbidden_imports": ["os", "sys"],
        },
        "events": {"store_path": str(tmp_path / "events")},
        "policy": {
            "agent_scopes": [{"role": "agent", "capabilities": ["publish_event"]}]
        },
    }
    os.makedirs(plugins_dir, exist_ok=True)
    return KernelBootstrap(config)


def test_happy_path_integration(
    kernel: KernelBootstrap,
) -> None:
    """Runs a full lifecycle event spanning the kernel."""
    assert kernel.verify_startup() is True

    # 1. Register schema for our event type
    kernel.event_bus.schema_registry.register("test.event", ["data"], version="1.0")

    # 2. Register an Agent via Identity
    identity = kernel.identity_service.register_identity(
        "test_agent",
        "agent",
        "11111111-1111-1111-1111-111111111111",
        "agent",
        b"dummy_key",
    )

    # 3. Load Policy rules for the agent
    rules = [
        {
            "type": "event_auth",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_event_types": ["test.event"]},
            "action": "allow",
        }
    ]
    kernel.policy_engine.load_rules(rules)

    metering = kernel.get_subsystems()["metering"]
    metering.allocate(str(identity.id), "events", 10)

    # 5. Subscribe a Handler
    execution_flags = {"executed": False}

    def dummy_handler(_event_data: Event) -> None:
        execution_flags["executed"] = True

    kernel.event_bus.subscribe("test.event", dummy_handler)

    # 6. Evaluate Policy
    decision = kernel.policy_engine.evaluate(
        identity_id=str(identity.id),
        capability="publish_event",
        context={"event_type": "test.event"},
    )
    assert decision.allowed is True

    # 7. Consume Metering
    assert metering.consume(str(identity.id), "events", 1) is True

    # 8. Build signed event
    ev = Event(
        event_id=uuid4(),
        type="test.event",
        payload={"data": "test_payload"},
        origin_id=identity.id,
        timestamp=datetime.utcnow().isoformat(),
        sequence_number=0,
        correlation_id=uuid4(),
        version="1.0",
        signature="placeholder",
    )
    sig = compute_event_signature(ev)
    ev = Event(
        event_id=ev.event_id,
        type=ev.type,
        payload=ev.payload,
        origin_id=ev.origin_id,
        timestamp=ev.timestamp,
        sequence_number=0,
        correlation_id=ev.correlation_id,
        version=ev.version,
        signature=sig,
    )

    kernel.event_bus.publish(ev)

    # 9. Verifications
    assert execution_flags["executed"] is True
    dlq = kernel.event_bus.get_dlq_metrics()
    assert dlq["total_dead_letters"] == 0
    assert kernel.audit_ledger.verify_integrity() is True

    entries = list(kernel.audit_ledger.iterate("event_published"))
    assert len(entries) == 1
    assert entries[0].actor_id == str(identity.id)

    # 10. Bootstrap lifecycle coverage
    subsystems = kernel.get_subsystems()
    assert "bus" in subsystems
    assert "identity" in subsystems

    kernel.shutdown()
    shutdown_entries = list(kernel.audit_ledger.iterate("system_shutdown"))
    assert len(shutdown_entries) == 1
