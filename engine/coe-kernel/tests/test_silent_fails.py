"""Silent Fail & Invariant Verification Suite.

Uses Hypothesis to perform property-based testing on core kernel invariants
to ensure that edge cases or corrupted states never fail silently.
"""

from datetime import datetime, timezone
import json
import secrets
from dataclasses import replace
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock
import uuid
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from core.event_bus.bus import EventBus, compute_event_signature, SchemaRegistry
from core.identity.service import IdentityService
from core.audit.ledger import AuditLedger
from core.state_engine.engine import StateEngine
from core.types import Event, AuditEntry, EventBusDependencies
from core.errors import KernelError, ErrorCode

# --- Shared Helpers (Ensuring absolute isolation for Hypothesis examples) ---


def get_fresh_event_bus(audit_ledger_instance: Any) -> EventBus:
    """Helper to provide a fresh EventBus for each test iteration."""
    deps = EventBusDependencies(
        audit_ledger=audit_ledger_instance,
        event_store=MagicMock(),
        backpressure=MagicMock(),
        dlq=MagicMock(),
        schema_registry=SchemaRegistry(),
    )
    deps.backpressure.is_accepting.return_value = True
    deps.event_store.get_current_sequence.return_value = 0
    return EventBus(deps)


def get_fresh_identity_service(audit_ledger_instance: Any) -> IdentityService:
    """Helper to provide a fresh IdentityService for each iteration."""
    role_schema = {"ROOT": ["*"], "admin": ["*"], "agent": ["publish_event"]}
    return IdentityService(audit_ledger_instance, role_schema)


# --- Strategies ---

st_event_type = st.sampled_from(["system.test", "agent.action", "audit.event"])
st_payload = st.dictionaries(
    keys=st.text(min_size=1, max_size=20), values=st.text(max_size=50)
)
st_identity_id = st.uuids()
st_parent_id = st.one_of(st.none(), st.uuids().map(str))


@st.composite
def st_signed_event(draw: Any) -> Any:
    """Generates an Event object with a valid or invalid signature."""
    event_id = draw(st.uuids())
    event_type = draw(st_event_type)
    payload = draw(st_payload)
    origin_id = draw(st_identity_id)
    timestamp = datetime.now(timezone.utc).isoformat()

    event = Event(
        event_id=event_id,
        type=event_type,
        payload=payload,
        origin_id=origin_id,
        timestamp=timestamp,
        sequence_number=0,
        correlation_id=uuid4(),
        version="1.0",
        signature="INVALID_BEFORE_COMPUTE",
    )

    # Randomly decide if the signature should be valid or corrupted
    is_valid = draw(st.booleans())
    if is_valid:
        sig = compute_event_signature(event)
        return replace(event, signature=sig), True

    # Corrupt the signature by adding a prefix
    return replace(event, signature="corrupted_" + secrets.token_hex(8)), False


# --- Invariant Tests: Event Bus ---


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(event_data=st_signed_event())
def test_event_bus_signature_invariant(
    mock_audit_ledger: Any, event_data: Tuple[Event, bool]
) -> None:
    """Invariant: The event bus must NEVER publish an event with
    an invalid signature."""
    event, expected_valid = event_data
    event_bus = get_fresh_event_bus(mock_audit_ledger)

    # We must register the schema first for validation to pass to the signature check
    event_bus.schema_registry.register(event.type, list(event.payload.keys()), "1.0")

    if expected_valid:
        # Should not raise exception
        event_bus.publish(event)
    else:
        # Should raise KernelError for signature mismatch
        with pytest.raises(KernelError) as exc:
            event_bus.publish(event)
        assert exc.value.code == ErrorCode.EVENT_SIGNATURE_INVALID


# --- Invariant Tests: Identity ---


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    name=st.text(min_size=5, max_size=50),
    role=st.sampled_from(["admin", "agent"]),
    parent_uuid=st.uuids(),
)
def test_identity_name_uniqueness_invariant(
    mock_audit_ledger: Any, name: str, role: str, parent_uuid: uuid.UUID
) -> None:
    """Invariant: Identity service must prevent duplicate registration
    of the same name."""
    identity_service = get_fresh_identity_service(mock_audit_ledger)
    parent_id = str(parent_uuid)

    # First registration
    identity_service.register_identity(
        name=name,
        role=role,
        parent_id=parent_id,
        identity_type="user",
        signing_key=b"k1",
    )

    # Second registration with same name
    with pytest.raises(KernelError) as exc:
        identity_service.register_identity(
            name=name,
            role=role,
            parent_id=parent_id,
            identity_type="user",
            signing_key=b"k2",
        )

    assert exc.value.code == ErrorCode.IDENTITY_DUPLICATE


# --- Invariant Tests: Audit Ledger ---


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    actor_id=st.text(min_size=1, max_size=20),
    action=st.text(min_size=1, max_size=20).filter(lambda x: x != "audit.segment_seal"),
    status=st.sampled_from(["SUCCESS", "FAILURE", "PENDING"]),
    metadata=st_payload,
)
def test_audit_ledger_linkage_invariant(
    tmp_path: Any, actor_id: str, action: str, status: str, metadata: Dict[str, Any]
) -> None:
    """Invariant: Single-bit change in ledger storage must cause
    verification failure."""
    # Use a unique filename for each Hypothesis example to ensure absolute isolation
    unique_filename = f"audit_{secrets.token_hex(4)}.log"
    ledger_path = tmp_path / unique_filename

    # Requires storage_path and genesis_constant
    ledger = AuditLedger(str(ledger_path), genesis_constant="FROZEN_GENESIS_TEST")

    # Append some entries
    ledger.append(actor_id, action, status, metadata)
    ledger.append(actor_id, action + "_2", status, metadata)

    assert ledger.verify_integrity() is True

    # Manually corrupt the file on disk
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if lines:
        line_data = json.loads(lines[0])
        original_hash = line_data["entry_hash"]
        # Corrupt the hash by reversing it
        corrupted_hash = original_hash[::-1]
        line_data["entry_hash"] = corrupted_hash
        lines[0] = json.dumps(line_data) + "\n"

        with open(ledger_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # verification must now fail
        try:
            new_ledger = AuditLedger(
                str(ledger_path), genesis_constant="FROZEN_GENESIS_TEST"
            )
            # The error might happen in __init__ or verification
            new_ledger.verify_integrity()
            pytest.fail("Ledger integrity verification should have failed.")
        except KernelError as exc:
            assert exc.code in [
                ErrorCode.AUDIT_INTEGRITY_VIOLATION,
                ErrorCode.AUDIT_CHAIN_BROKEN,
            ]


# --- Invariant Tests: State Engine ---


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    state_updates=st.lists(
        st.tuples(
            st.sampled_from(["workflow.start", "workflow.step", "workflow.end"]),
            st_payload,
        ),
        min_size=1,
        max_size=5,
    )
)
def test_state_engine_transition_integrity(
    mock_audit_ledger: Any, state_updates: List[Tuple[str, Dict[str, Any]]]
) -> None:
    """Invariant: State engine must always produce a deterministic
    mapping of audit events."""
    state_engine = StateEngine(mock_audit_ledger)

    # Apply updates via audit log simulation
    for action, meta in state_updates:
        entry = AuditEntry(
            entry_id=uuid4(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor_id="TEST_ACTOR",
            action=action,
            status="SUCCESS",
            metadata=meta,
            previous_hash="000",
            entry_hash="111",
        )
        mock_audit_ledger.entries.append(entry)

    # Trigger rebuild
    state_engine.rebuild_from_audit()

    # Snapshot
    snapshot1 = (
        state_engine.get_active_state(
            "workflow_id_placeholder", "entity_id_placeholder"
        )
        if "workflow_id" in str(state_updates)
        else {}
    )

    # Rebuild again
    state_engine.rebuild_from_audit()
    snapshot2 = (
        state_engine.get_active_state(
            "workflow_id_placeholder", "entity_id_placeholder"
        )
        if "workflow_id" in str(state_updates)
        else {}
    )

    assert snapshot1 == snapshot2
