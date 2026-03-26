"""Tests for Metering Enforcement Loop."""

import uuid
from unittest.mock import MagicMock

import pytest

from core.metering.node import MeteringLayer


@pytest.fixture(name="policy_mock")
def mock_policy_fixture() -> MagicMock:
    """Provides a mocked policy engine."""
    return MagicMock()


@pytest.fixture(name="bus_mock")
def mock_bus_fixture() -> MagicMock:
    """Provides a mocked event bus."""
    return MagicMock()


@pytest.fixture(name="metering_layer")
def metering_fixture(policy_mock: MagicMock, bus_mock: MagicMock) -> MeteringLayer:
    """Provides the underlying metering layer."""
    return MeteringLayer(policy_engine=policy_mock, event_bus=bus_mock)


def test_consume_emits_event_on_failure(
    metering_layer: MeteringLayer, bus_mock: MagicMock
) -> None:
    """Verifies system emits budget_exceeded upon consume denying tokens."""
    metering_layer.allocate("agent_1", "tokens", 10)

    # Exceed budget
    result = metering_layer.consume("agent_1", "tokens", 20)

    assert result is False
    bus_mock.publish.assert_called_once()
    event = bus_mock.publish.call_args[0][0]
    assert event.type == "system.budget_exceeded"
    assert event.payload["metric"] == "tokens"
    assert event.payload["requested"] == 20


def test_record_checks_policy_and_emits_event(
    metering_layer: MeteringLayer, policy_mock: MagicMock, bus_mock: MagicMock
) -> None:
    """Verifies metering tracks cost appropriately, utilizing policy bounds."""
    agent_id = uuid.uuid4()
    policy_mock.evaluate.return_value.allowed = False
    policy_mock.evaluate.return_value.reason = "Quota exceeded"

    metering_layer.record(agent_id, "api_calls", 1.0)

    policy_mock.evaluate.assert_called_once_with(
        str(agent_id),
        "consume_resource",
        {"metric": "api_calls", "usage": 1},
        dry_run=True,
    )
    bus_mock.publish.assert_called_once()
    event = bus_mock.publish.call_args[0][0]
    assert event.type == "system.budget_exceeded"
    assert event.payload["reason"] == "Quota exceeded"
