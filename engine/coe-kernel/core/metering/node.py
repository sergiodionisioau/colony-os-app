"""Metering Layer implementation for resource constraint enforcement."""

import uuid
from typing import Dict, Any
from dataclasses import replace

from core.interfaces import MeteringInterface, PolicyEngineInterface, EventBusInterface
from core.types import Event
from core.event_bus.bus import compute_event_signature


class MeteringLayer(MeteringInterface):
    """Provides local resource accounting bounds."""

    def __init__(
        self,
        policy_engine: PolicyEngineInterface,
        event_bus: EventBusInterface,
    ) -> None:
        """Initialize the Metering Layer."""
        self.policy_engine = policy_engine
        self.event_bus = event_bus
        self._allocations: Dict[str, Dict[str, int]] = {}

    def _emit_budget_exceeded(self, payload: Dict[str, Any]) -> None:
        """Helper to create and publish a signed system event."""
        evt = Event.create("system.budget_exceeded", payload)
        # Compute real signature
        signature = compute_event_signature(evt)
        # Final event
        final_evt = replace(evt, signature=signature)
        self.event_bus.publish(final_evt)

    def allocate(self, identity_id: str, metric: str, amount: int) -> None:
        """Assigns an absolute token allocation for a specific identity."""
        if identity_id not in self._allocations:
            self._allocations[identity_id] = {}
        if metric not in self._allocations[identity_id]:
            self._allocations[identity_id][metric] = 0

        self._allocations[identity_id][metric] += amount

    def consume(self, identity_id: str, metric: str, amount: int) -> bool:
        """Removes allocation tokens explicitly denying if exceeding limits."""
        if (
            identity_id not in self._allocations
            or metric not in self._allocations[identity_id]
        ):
            return False

        if self._allocations[identity_id][metric] < amount:
            self._emit_budget_exceeded(
                {
                    "identity_id": identity_id,
                    "metric": metric,
                    "requested": amount,
                    "available": self._allocations[identity_id][metric],
                }
            )
            return False

        self._allocations[identity_id][metric] -= amount
        return True

    def record(self, identity_id: uuid.UUID, metric: str, value: float) -> None:
        """Records metric consumption and evaluates thresholds against policy."""
        id_str = str(identity_id)
        if id_str not in self._allocations:
            self._allocations[id_str] = {}
        if metric not in self._allocations[id_str]:
            self._allocations[id_str][metric] = 0

        new_usage = self._allocations[id_str][metric] + int(value)

        # Policy Check (Dry-run to just check limits)
        decision = self.policy_engine.evaluate(
            id_str,
            "consume_resource",
            {"metric": metric, "usage": new_usage},
            dry_run=True,
        )

        if not decision.allowed:
            self._emit_budget_exceeded(
                {
                    "identity_id": id_str,
                    "metric": metric,
                    "usage": new_usage,
                    "reason": decision.reason,
                }
            )

        self._allocations[id_str][metric] = new_usage

    def get_usage(self, identity_id: uuid.UUID) -> Dict[str, float]:
        """Provides visibility into metric usage across an identity."""
        id_str = str(identity_id)
        if id_str not in self._allocations:
            return {}
        return {k: float(v) for k, v in self._allocations[id_str].items()}
