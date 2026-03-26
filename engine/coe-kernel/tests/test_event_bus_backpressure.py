"""Test suite for the Event Bus Backpressure Controller."""

import pytest

from core.event_bus.backpressure import BackpressureController
from core.errors import KernelError, ErrorCode


class TestBackpressureController:
    """TDD suite enforcing hysteresis limits for event bus load."""

    def test_startup_state_is_accepting(self) -> None:
        """The controller should start in an accepting state when under limits."""
        controller = BackpressureController(activation_depth=100, deactivation_depth=50)
        assert controller.is_accepting(current_depth=0) is True
        assert controller.is_accepting(current_depth=99) is True

    def test_activation_threshold_breach(self) -> None:
        """Hitting the exact activation threshold denies further accumulation."""
        controller = BackpressureController(activation_depth=100, deactivation_depth=50)

        # Valid at 99
        assert controller.is_accepting(current_depth=99) is True

        # Denied at 100
        assert controller.is_accepting(current_depth=100) is False
        assert controller.is_accepting(current_depth=101) is False

    def test_hysteresis_requires_full_deactivation_drop(self) -> None:
        """Once activated, backpressure remains until depth drops
        below DEACTIVATION.
        """
        controller = BackpressureController(activation_depth=100, deactivation_depth=50)

        # Trigger activation
        assert controller.is_accepting(100) is False

        # Depth lowers, but not enough to deactivate
        assert controller.is_accepting(75) is False
        assert controller.is_accepting(51) is False
        assert controller.is_accepting(50) is False

        # Depth finally drops below deactivation threshold
        assert controller.is_accepting(49) is True

        # Now we can climb back up without being blocked (until 100 is hit again)
        assert controller.is_accepting(80) is True

    def test_get_status(self) -> None:
        """The controller should return the correct activation state."""
        controller = BackpressureController(activation_depth=10, deactivation_depth=5)
        assert controller.get_status() is False
        controller.is_accepting(10)
        assert controller.get_status() is True

    def test_invalid_construction(self) -> None:
        """Deactivation depth must be strictly less than activation depth."""
        with pytest.raises(KernelError) as exc:
            BackpressureController(activation_depth=100, deactivation_depth=100)

        assert exc.value.code == ErrorCode.EVENT_SCHEMA_INVALID

        with pytest.raises(KernelError):
            BackpressureController(activation_depth=100, deactivation_depth=150)
