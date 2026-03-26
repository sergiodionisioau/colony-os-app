"""State Engine implementation.

Tracks deterministic finite state machines strictly.
"""

from typing import Any, Dict, List

from core.errors import ErrorCode, KernelError
from core.interfaces import StateEngineInterface


class StateEngine(StateEngineInterface):
    """FSM engine enforcing path rules natively and logging bounds."""

    def __init__(self, audit_ledger: Any) -> None:
        """Initialize the State Engine."""
        self.audit_ledger = audit_ledger
        self._fsms: Dict[str, Any] = {}
        self._active_states: Dict[str, str] = {}

    def register_fsm(
        self, name: str, version: str, transitions: List[Dict[str, Any]]
    ) -> None:
        """Registers strict path rules for a workflow."""
        if name in self._fsms:
            if self._fsms[name]["version"] != version:
                raise KernelError(
                    code=ErrorCode.STATE_VERSION_MISMATCH,
                    message=(
                        f"FSM '{name}' version mismatch: expected "
                        f"{self._fsms[name]['version']}, got {version}"
                    ),
                )
            # Already registered with the same version
            return

        self._fsms[name] = {"version": version, "transitions": transitions}

    def transition(
        self, fsm_name: str, entity_id: str, event_type: str, identity_id: str
    ) -> str:
        """Applies an explicit mutation verifying pathing rules,
        returning new state.
        """
        if fsm_name not in self._fsms:
            raise KernelError(
                code=ErrorCode.STATE_FSM_NOT_FOUND,
                message=f"FSM '{fsm_name}' not found.",
            )

        current_state = self._active_states.get(entity_id, "INIT")
        fsm = self._fsms[fsm_name]

        # Find valid transition
        target_state = None
        for transition in fsm["transitions"]:
            if (
                transition.get("from") == current_state
                and transition.get("event") == event_type
            ):
                target_state = transition.get("to")
                break

        if target_state is None:
            raise KernelError(
                code=ErrorCode.STATE_TRANSITION_INVALID,
                message=(
                    f"Invalid transition for {entity_id} in {fsm_name} "
                    f"from {current_state} via {event_type}."
                ),
            )

        self._active_states[entity_id] = target_state

        self.audit_ledger.append(
            actor_id=identity_id,
            action="state_transition",
            status="SUCCESS",
            metadata={
                "fsm_name": fsm_name,
                "entity_id": entity_id,
                "event_type": event_type,
                "from_state": current_state,
                "to_state": target_state,
            },
        )
        return str(target_state)

    def set_active_state(self, entity_id: str, state: str) -> None:
        """Manually overrides the active state for an entity."""
        self._active_states[entity_id] = state

    def get_active_state(self, fsm_name: str, entity_id: str) -> str:
        """Returns the current active state for an entity in an FSM."""
        # For phase 1, we still fall back to INIT if unknown
        return self._active_states.get(entity_id, "INIT")

    def rebuild_from_audit(self) -> None:
        """Replays all state_transition audit entries to reconstruct state."""
        for entry in self.audit_ledger.iterate(action="state_transition"):
            fsm_name = entry.metadata.get("fsm_name")
            entity_id = entry.metadata.get("entity_id")
            to_state = entry.metadata.get("to_state")
            if fsm_name and entity_id and to_state:
                # We simply set it explicitly as we reconstruct
                self._active_states[entity_id] = to_state
