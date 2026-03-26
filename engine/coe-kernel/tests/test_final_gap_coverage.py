"""Targeted gap coverage for remaining uncovered lines in COE Kernel."""

import json
import os
import uuid
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519 as ed_lib
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from core.agent.memory import NullMemory
from core.agent.orchestrator import Orchestrator
from core.agent.scope_enforcer import PolicyScopeEnforcer, PolicyScopeBinding
from core.agent.types import (
    AgentTaskSpec,
    AgentConstraints,
    AgentTaskStatus,
    AIResponse,
)
from core.audit.ledger import AuditLedger
from core.errors import KernelError, ErrorCode
from core.event_bus.bus import EventBus
from core.event_bus.dlq import DeadLetterQueue
from core.event_bus.store import EventStore
from core.improvement_engine.engine import ImprovementEngine
from core.metering.node import MeteringLayer
from core.module_loader.module_validator import ModuleValidator
from core.module_loader.signature import compute_module_hash
from core.types import DLQEntry
from tests.conftest import MockAuditLedger, create_test_event, create_module_files

# Real schema path for validator
SCHEMA_PATH = "c:/Users/sergi/colony/backend/col/engine/coe-kernel/schemas"


def test_dlq_recovery_faults(tmp_path: Any) -> None:
    """Cover DLQ recovery error paths (lines 66-67, 78, 86-87)."""
    dp = str(tmp_path / "dlq_faults")
    dlq_dir = os.path.join(dp, "dlq")
    os.makedirs(dlq_dir, exist_ok=True)

    # Invalid index in filename (triggers 66-67)
    with open(
        os.path.join(dlq_dir, "dlq_segment_BAD.json"), "w", encoding="utf-8"
    ) as f:
        f.write("{}\n")

    # Empty line (triggers 78)
    with open(
        os.path.join(dlq_dir, "dlq_segment_000001.json"), "w", encoding="utf-8"
    ) as f:
        f.write("\n")

    # Valid entry for recovery metrics (81-83)
    ev = create_test_event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    entry = DLQEntry(ev, "r", "s1", "2026-01-01", 0)
    with open(
        os.path.join(dlq_dir, "dlq_segment_000002.json"), "w", encoding="utf-8"
    ) as f:
        f.write(json.dumps(entry.to_dict()) + "\n")

    dlq = DeadLetterQueue(dp)
    assert dlq.get_metrics()["total_dead_letters"] == 1


def test_dlq_retention_deletion_gap(tmp_path: Any) -> None:
    """Cover DLQ retention deletion (lines 98-99)."""
    dp = str(tmp_path / "dlq_retention_del")
    dlq = DeadLetterQueue(dp, segment_size=1, max_events=1)

    ev = create_test_event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    dlq.append(ev, "r1", "s1")  # segment 0
    dlq.append(ev, "r2", "s1")  # segment 1
    dlq.append(ev, "r3", "s1")  # segment 2, deletes 0

    assert not os.path.exists(os.path.join(dp, "dlq", "dlq_segment_000000.json"))


def test_bus_isolation_metrics_gap() -> None:
    """Cover IsolationLayer.get_subscriber_metrics average latency (lines 159-164)."""
    bus_deps = MagicMock()
    bus_deps.schema_registry.validate.return_value = None
    bus = EventBus(bus_deps)

    # Empty metrics branch (line 152)
    assert bus.get_subscriber_health("ghost")["average_latency_ms"] == 0.0

    handler = MagicMock()
    bus.subscribe("t", handler, "s1")
    ev = create_test_event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    with patch("core.event_bus.bus.verify_event_signature", return_value=True):
        bus.publish(ev)

    metrics = bus.get_subscriber_health("s1")
    assert metrics["average_latency_ms"] >= 0


def test_bus_system_events_gap() -> None:
    """Cover backpressure activation/deactivation system events (239, 241, 354-365)."""
    deps = MagicMock()
    deps.event_store.get_retained_event_count.side_effect = [1000, 0]
    deps.backpressure.get_status.side_effect = [False, True, True, False]
    deps.backpressure.is_accepting.return_value = True
    deps.schema_registry.validate.return_value = None

    bus = EventBus(deps)
    ev = create_test_event(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    with patch("core.event_bus.bus.verify_event_signature", return_value=True):
        # Trigger activation
        bus.publish(ev)
        # Trigger deactivation
        bus.publish(ev)


def test_orchestrator_gaps() -> None:
    """Cover Orchestrator error paths and active tasks (144-147, 215)."""
    # pylint: disable=protected-access
    orch = Orchestrator(MagicMock(), MagicMock(), MagicMock(), MockAuditLedger())
    orch._ai_provider = MagicMock()
    orch._ai_provider.generate.return_value = AIResponse(
        content="CALL: cap {bad",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.1,
        provider_id="mock",
    )

    task = AgentTaskSpec(
        uuid.uuid4(), uuid.uuid4(), "i", AgentConstraints(5, 5, 5, False), uuid.uuid4()
    )
    res = orch.execute(task)
    assert res.status == AgentTaskStatus.FAILED

    # Active tasks coverage (215)
    orch._active_tasks[uuid.uuid4()] = task
    assert len(orch.get_active_tasks()) >= 1


def test_orchestrator_kernel_error_gap() -> None:
    """Cover Orchestrator KernelError catch (lines 155-156)."""
    # pylint: disable=protected-access
    orch = Orchestrator(MagicMock(), MagicMock(), MagicMock(), MockAuditLedger())
    orch._ai_provider = MagicMock()
    orch._ai_provider.generate.side_effect = KernelError(ErrorCode.UNKNOWN_FAULT, "KE")

    task = AgentTaskSpec(
        uuid.uuid4(), uuid.uuid4(), "i", AgentConstraints(5, 5, 5, False), uuid.uuid4()
    )
    res = orch.execute(task)
    assert res.status == AgentTaskStatus.FAILED


def test_scope_enforcer_gaps() -> None:
    """Cover ScopeEnforcer wildcard and errors (44, 76, 86)."""
    base = MagicMock()
    ids = MagicMock()
    ids.get_identity.return_value = MagicMock(role="admin")

    # Wildcard coverage (44)
    se = PolicyScopeEnforcer(base, ids, [PolicyScopeBinding("admin", ["all"])])
    se.check("admin", "any")  # Should pass

    # Policy denied re-raise (76)
    base.evaluate.side_effect = KernelError(ErrorCode.POLICY_DENIED, "Denied")
    with pytest.raises(KernelError):
        se.evaluate("u1", "c1", {})

    # Fallback error (86)
    ids.get_identity.side_effect = AttributeError("System fault")
    res = se.evaluate("u1", "c1", {})
    assert not res.allowed


def test_audit_ledger_gaps(tmp_path: Any) -> None:
    """Cover AuditLedger multi-segment and dir loading (70-71, 216-221, 242)."""
    ld = str(tmp_path / "audit_dir")
    os.makedirs(ld, exist_ok=True)
    ledger = AuditLedger(ld, "G")
    g_hash = getattr(ledger, "_hash_payload")("G")

    e_id = str(uuid.uuid4())
    meta_str = json.dumps({}, sort_keys=True)
    payload = f"{e_id}2026-01-01atestS{meta_str}{g_hash}"
    e_hash = getattr(ledger, "_hash_payload")(payload)

    v_entry = {
        "entry_id": e_id,
        "timestamp": "2026-01-01",
        "actor_id": "a",
        "action": "test",
        "status": "S",
        "metadata": {},
        "previous_hash": g_hash,
        "entry_hash": e_hash,
    }

    # Multi-file segment loading (70-71)
    lp = str(tmp_path / "audit_multi.log")
    with open(lp, "w", encoding="utf-8") as f:
        f.write(json.dumps(v_entry) + "\n")
    with open(lp + ".001", "w", encoding="utf-8") as f:
        f.write(json.dumps(v_entry) + "\n")
    AuditLedger(lp, "G")

    # Dir loading coverage (216-221)
    with open(os.path.join(ld, "audit_000000.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(v_entry) + "\n")
    getattr(ledger, "_entries").append(getattr(ledger, "_deserialize_entry")(v_entry))
    ledger.verify_integrity()

    # FNF in loading (242)
    ledger2 = AuditLedger(str(tmp_path / "ghost_audit"), "G")
    # We MUST use patch on the ledger2 instance specifically or globally
    with patch("builtins.open", side_effect=FileNotFoundError):
        # pylint: disable=protected-access
        res = getattr(ledger2, "_load_disk_entries")(["any.json"])
        assert not res


def test_store_empty_line_gap(tmp_path: Any) -> None:
    """Cover EventStore index rebuild with empty line (line 91)."""
    sp = str(tmp_path / "store_gap")
    os.makedirs(sp, exist_ok=True)
    with open(os.path.join(sp, "segment_000000.json"), "w", encoding="utf-8") as f:
        f.write("\n")  # Empty line
    EventStore(sp, 10, 100)


def test_engine_gaps(tmp_path: Any) -> None:
    """Cover ImprovementEngine 98, 121, 173-175, 189, 248, 259."""
    # pylint: disable=protected-access
    engine = ImprovementEngine(MagicMock(), MagicMock(), MagicMock(), MockAuditLedger())

    # 98: Patch not found
    with pytest.raises(KernelError) as exc:
        engine.approve_patch(uuid.uuid4(), "a")
    assert exc.value.code == ErrorCode.PATCH_NOT_FOUND

    # 189: Reject unknown patch
    engine.reject_patch(uuid.uuid4(), "r")

    # 121: CI Gate not configured
    p_id = uuid.uuid4()
    p = MagicMock(patch_id=p_id, target_module="m", unified_diff="--- a\n+++ b\n")
    engine._patches[p_id] = p
    with pytest.raises(RuntimeError):
        engine.approve_patch(p_id, str(uuid.uuid4()))

    # 248: IOError in _apply_diff if file exists but open fails
    with pytest.raises(IOError):
        getattr(engine, "_apply_diff")("ghost_file_99.py", "diff")

    # 173-175: Hot-swap fault
    engine._ci_gate = MagicMock()
    engine._ci_gate.run_tests.return_value = MagicMock(passed=True)
    with patch.object(engine, "_apply_diff", side_effect=Exception("fault")):
        with pytest.raises(Exception):
            engine.approve_patch(p_id, str(uuid.uuid4()))

    # 259: Unified diff pass
    tp = str(tmp_path / "target.py")
    with open(tp, "w", encoding="utf-8") as f:
        f.write("orig\n")
    getattr(engine, "_apply_diff")(tp, "--- a\n")


def test_metering_node_usage_gap() -> None:
    """Cover get_usage for untracked ID (line 111)."""
    m = MeteringLayer(MagicMock(), MagicMock())
    assert m.get_usage(uuid.uuid4()) == {}


def test_null_memory_clear_gap() -> None:
    """Cover NullMemory.clear (line 28)."""
    mem = NullMemory()
    mem.clear(uuid.uuid4())


def test_validator_capability_undeclared_gap(tmp_path: Any) -> None:
    """Cover module_validator capability check (lines 102-103).

    Must create all 7 structural files so the validator reaches the
    capability audit phase (Step 4) instead of failing at structure (Step 1).
    """
    # Generate a real signing keypair
    private_key = ed_lib.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        cast(Any, Encoding.Raw), cast(Any, PublicFormat.Raw)
    )

    md = tmp_path / "mod_gap"
    create_module_files(
        str(md),
        "mod_gap",
        {
            "version": "1.0.0",
            "entrypoint": "entry.py",
            "events_subscribed": [],
            "events_emitted": [],
        },
    )

    # Override capabilities.json with a capability that passes the schema
    # enum but is NOT in ModuleValidator.kernel_capabilities.
    # Schema allows: AUDIT_READ, AUDIT_WRITE, EVENT_PUBLISH, EVENT_SUBSCRIBE,
    #   STORAGE_READ, STORAGE_WRITE, IDENTITY_QUERY
    # kernel_capabilities contains: AUDIT_READ, AUDIT_WRITE, EVENT_PUBLISH,
    #   EVENT_SUBSCRIBE, STATE_READ, STATE_WRITE, VAULT_READ, VAULT_WRITE
    # So STORAGE_READ passes schema but triggers MODULE_CAPABILITY_UNDECLARED.
    with open(md / "capabilities.json", "w", encoding="utf-8") as f:
        json.dump({"module_id": "mod_gap", "capabilities": ["STORAGE_READ"]}, f)
    # Re-sign the module after overriding capabilities.json
    m_hash = compute_module_hash(str(md))
    sig = private_key.sign(m_hash)
    with open(md / "signature.sig", "wb") as f:
        f.write(sig)

    v = ModuleValidator(SCHEMA_PATH, MagicMock(), public_key=public_key_bytes)

    with pytest.raises(KernelError) as exc:
        v.validate(str(md))
    assert exc.value.code == ErrorCode.MODULE_CAPABILITY_UNDECLARED


def test_validator_schema_fallback_gap() -> None:
    """Cover ModuleValidator schema fallback (line 50)."""
    v = ModuleValidator("/non/existent/path", MagicMock())
    getattr(v, "_validate_schema")(
        {"module_id": "a", "capabilities": ["AUDIT_READ"]}, "capabilities.schema.json"
    )
