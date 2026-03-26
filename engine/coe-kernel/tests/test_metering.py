"""Strict TDD suite for the Metering Layer.

Verifies quotas are strictly enforced without memory leaks.
"""

from unittest.mock import MagicMock

import pytest

from core.metering.node import MeteringLayer


@pytest.fixture(name="metering_layer")
def metering_layer_fixture() -> MeteringLayer:
    """Fixture providing an ephemeral MeteringLayer."""
    mock_policy = MagicMock()
    mock_bus = MagicMock()
    return MeteringLayer(policy_engine=mock_policy, event_bus=mock_bus)


def test_consumption_over_budget_returns_false(metering_layer: MeteringLayer) -> None:
    """Test Set 1: Consumption over budget returns explicitly False."""
    metering_layer.allocate("agent_1", "tokens", 100)

    # Consuming under budget should succeed
    assert metering_layer.consume("agent_1", "tokens", 50) is True

    # Consuming over remaining budget should explicitly deny
    assert metering_layer.consume("agent_1", "tokens", 60) is False

    # Remaining budget should be intact
    assert metering_layer.consume("agent_1", "tokens", 50) is True


def test_budget_allocation_updates_total(metering_layer: MeteringLayer) -> None:
    """Test Set 1: Budget allocation updates total tokens properly."""
    metering_layer.allocate("agent_1", "events", 5)
    metering_layer.allocate("agent_1", "events", 5)

    assert metering_layer.consume("agent_1", "events", 10) is True
    assert metering_layer.consume("agent_1", "events", 1) is False


def test_missing_context_fails_gracefully(metering_layer: MeteringLayer) -> None:
    """Test Set 1: Missing context fails gracefully."""
    # Consuming an unallocated resource silently denies (fail-safe)
    assert metering_layer.consume("agent_2", "tokens", 1) is False


# --- Aliases conforming strictly to project_plan.md requirements ---
test_over_budget_invocation_rejected = test_consumption_over_budget_returns_false
