"""Backpressure management for the Event Bus."""

from core.errors import ErrorCode, KernelError


class BackpressureController:
    """Manages hysteresis limits to safely shed load under stress."""

    def __init__(self, activation_depth: int, deactivation_depth: int) -> None:
        """Initialize threshold limits ensuring non-oscillating constraints."""
        if activation_depth <= deactivation_depth:
            raise KernelError(
                code=ErrorCode.EVENT_SCHEMA_INVALID,
                message=(
                    "Deactivation depth must be strictly less than " "activation depth."
                ),
            )

        self.activation_depth = activation_depth
        self.deactivation_depth = deactivation_depth
        self._is_active = False

    def is_accepting(self, current_depth: int) -> bool:
        """Determines if the system can safely route a new event."""
        if self._is_active:
            if current_depth < self.deactivation_depth:
                self._is_active = False
            else:
                return False
        else:
            if current_depth >= self.activation_depth:
                self._is_active = True
                return False

        return True

    def get_status(self) -> bool:
        """Returns the current activation state of the controller."""
        return self._is_active
