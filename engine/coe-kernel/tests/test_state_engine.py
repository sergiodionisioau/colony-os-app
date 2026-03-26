"""Strict TDD suite for the State Engine.

Verifies finite state machine transitions and determinism.
"""

import pytest

from core.errors import ErrorCode, KernelError
from core.state_engine.engine import StateEngine
from tests.conftest import MockAuditLedger


@pytest.fixture(name="state_engine")
def state_engine_fixture(mock_audit_ledger: MockAuditLedger) -> StateEngine:
    """Fixture providing a StateEngine with common test transitions."""
    engine = StateEngine(audit_ledger=mock_audit_ledger)
    transitions = [
        {"from": "INIT", "event": "START", "to": "RUNNING"},
        {"from": "RUNNING", "event": "STOP", "to": "DONE"},
    ]
    engine.register_fsm("test_fsm", "1.0", transitions)
    return engine


def test_invalid_transition_rejected(state_engine: StateEngine) -> None:
    """Invalid transition rejected."""
    state_engine.set_active_state("user1", "INIT")
    # INIT -> INVALID_EVENT is not in the schema
    with pytest.raises(KernelError) as exc_info:
        state_engine.transition("test_fsm", "user1", "INVALID_EVENT", "admin1")

    assert exc_info.value.code == ErrorCode.STATE_TRANSITION_INVALID


def test_valid_transition_logged(
    state_engine: StateEngine, mock_audit_ledger: MockAuditLedger
) -> None:
    """Valid transition succeeded and logged."""
    new_state = state_engine.transition(
        "test_fsm", "node_1", "START", identity_id="admin_1"
    )
    assert new_state == "RUNNING"

    assert state_engine.get_active_state("test_fsm", "node_1") == "RUNNING"
    assert len(mock_audit_ledger.entries) == 1

    audit_entries = list(mock_audit_ledger.iterate("state_transition"))
    assert len(audit_entries) == 1
    assert audit_entries[0].metadata["to_state"] == "RUNNING"


def test_fsm_registration_mismatch(state_engine: StateEngine) -> None:
    """Registering same FSM with different version fails."""
    state_engine.register_fsm("fsm", "1.0", [{"from": "A", "event": "E1", "to": "B"}])
    with pytest.raises(KernelError) as exc:
        state_engine.register_fsm(
            "fsm", "2.0", [{"from": "A", "event": "E2", "to": "C"}]
        )
    assert exc.value.code == ErrorCode.STATE_VERSION_MISMATCH


def test_fsm_registration_same_version_skips(state_engine: StateEngine) -> None:
    """Registering same FSM with same version should return early."""
    # Should not raise
    state_engine.register_fsm("test_fsm", "1.0", [])


def test_transition_unknown_fsm(state_engine: StateEngine) -> None:
    """Transition on unknown FSM fails."""
    with pytest.raises(KernelError) as exc:
        state_engine.transition("unknown", "e1", "run", "a1")

    assert exc.value.code == ErrorCode.STATE_FSM_NOT_FOUND


def test_set_active_state(state_engine: StateEngine) -> None:
    """Manually setting state works."""
    state_engine.set_active_state("node_1", "FAILED")
    assert state_engine.get_active_state("test_fsm", "node_1") == "FAILED"


def test_get_active_state_default(state_engine: StateEngine) -> None:
    """Entities without transitions default to INIT."""
    assert state_engine.get_active_state("test_fsm", "unknown") == "INIT"


def test_rebuild_from_audit(
    state_engine: StateEngine, mock_audit_ledger: MockAuditLedger
) -> None:
    """Test rebuilding state from audit ledger."""
    state_engine.register_fsm(
        "test_fsm", "1.0", [{"from": "INIT", "to": "RUNNING", "event": "START"}]
    )
    mock_audit_ledger.append(
        "admin_1",
        "state_transition",
        "SUCCESS",
        {
            "fsm_name": "test_fsm",
            "entity_id": "node_2",
            "event_type": "START",
            "from_state": "INIT",
            "to_state": "RUNNING",
        },
    )
    state_engine.rebuild_from_audit()
    assert state_engine.get_active_state("test_fsm", "node_2") == "RUNNING"


# --- Aliases conforming strictly to project_plan.md requirements ---
test_version_mismatch_rejected = test_fsm_registration_mismatch
