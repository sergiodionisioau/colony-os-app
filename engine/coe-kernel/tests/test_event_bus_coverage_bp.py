"""Comprehensive coverage tests for Event Bus Backpressure logic."""

from core.event_bus.backpressure import BackpressureController


def test_backpressure_activation_boundary() -> None:
    """Verifies that backpressure activates exactly at the threshold."""
    controller = BackpressureController(activation_depth=10, deactivation_depth=5)
    assert controller.is_accepting(9) is True
    assert controller.is_accepting(10) is False


def test_backpressure_deactivation_boundary() -> None:
    """Verifies that backpressure deactivates exactly below the threshold."""
    controller = BackpressureController(activation_depth=10, deactivation_depth=5)
    controller.is_accepting(10)  # Activate
    assert controller.get_status() is True
    assert controller.is_accepting(5) is False
    assert controller.is_accepting(4) is True
    assert controller.get_status() is False
