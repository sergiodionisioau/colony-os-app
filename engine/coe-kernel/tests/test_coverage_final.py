"""Comprehensive coverage targeted tests for core kernel components."""

import json
import os
import uuid
from typing import Any, Dict, cast
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from core.agent.types import Patch
from core.errors import ErrorCode, KernelError
from core.improvement_engine.ci_gate import LocalCIGate
from core.module_loader.loader import ModuleLoader, _ShadowBus, ModuleEventProxy
from core.module_loader.module_validator import ModuleValidator
from core.module_loader.registry import ModuleRegistry, ModuleStatus
from core.module_loader.signature import compute_module_hash, verify_module_signature
from core.types import DLQEntry
from core.utils.persistence import enforce_segment_retention, get_sorted_segments
from tests.conftest import create_module_files, create_test_event


@pytest.fixture(name="config")
def fixture_mock_loader_config(tmp_path: Any) -> Dict[str, Any]:
    """Fixture to provide a mock ModuleLoader configuration with signing keys."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )
    return {
        "modules_path": str(tmp_path),
        "forbidden_imports": [],
        "audit_ledger": MagicMock(),
        "registry": ModuleRegistry(audit_ledger=MagicMock()),
        "event_bus": MagicMock(),
        "public_key": public_key_bytes,
        "private_key": private_key,  # Store for tests to sign
    }


def _sign(module_dir: str, private_key: ed25519.Ed25519PrivateKey) -> None:
    """Helper to sign a module directory."""

    module_hash = compute_module_hash(module_dir)
    signature = private_key.sign(module_hash)
    with open(os.path.join(module_dir, "signature.sig"), "wb") as f:
        f.write(signature)


def test_dlq_comprehensive() -> None:
    """Cover DLQEntry from_dict and all fields."""
    ev_id = uuid.uuid4()
    cor_id = uuid.uuid4()
    org_id = uuid.uuid4()
    e = create_test_event(ev_id, cor_id, org_id)
    entry = DLQEntry(e, "r", "sub", "2026-01-01", 3)
    d = entry.to_dict()
    assert d["retry_count"] == 3

    entry2 = DLQEntry.from_dict(d)
    assert entry2.retry_count == 3
    assert entry2.reason == "r"
    assert entry2.failed_event.type == "t"


def test_persistence_gaps(tmp_path: Any) -> None:
    """Cover persistence utilities error paths."""

    # Bad path
    assert get_sorted_segments(str(tmp_path / "ghost"), "p") == []
    # Retention with 0 events
    assert enforce_segment_retention("p", "p", 0, 100) == []
    # Retention within limit
    res = enforce_segment_retention(str(tmp_path), "p", 10, 5)
    assert res == []


def test_ci_gate_exhaustive() -> None:
    """Cover LocalCIGate success and failure paths."""
    gate = LocalCIGate()
    p = Patch(
        patch_id=uuid.uuid4(),
        target_module="m",
        unified_diff="---",
        test_vector="pytest tests/t.py",
        proposed_by="agent",
    )
    # Success
    with patch("pytest.main", return_value=0):
        res = gate.run_tests(p)
        assert res.passed is True
    # Exception
    with patch("pytest.main", side_effect=RuntimeError("boom")):
        res = gate.run_tests(p)
        assert res.passed is False
        assert "boom" in res.output


def test_loader_circular_detection(config: Any) -> None:
    """Cover circular dependency detection."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path

    # A -> B
    a_dir = os.path.join(m_path, "a")
    create_module_files(a_dir, "a", {"dependencies": ["b"]})
    _sign(a_dir, config["private_key"])

    # B -> A
    b_dir = os.path.join(m_path, "b")
    create_module_files(b_dir, "b", {"dependencies": ["a"]})
    _sign(b_dir, config["private_key"])

    with pytest.raises(KernelError) as exc:
        loader.load("a")
    assert exc.value.code == ErrorCode.MODULE_DEPENDENCY_CIRCULAR


def test_loader_manifest_validation_gaps(config: Any) -> None:
    """Cover _load_manifest error paths and signature failures."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path

    # Missing required field in manifest (but structural files exist)
    bad_dir = os.path.join(m_path, "bad_manifest")
    create_module_files(bad_dir, "bad_manifest", {"version": "1"})
    # Re-sign after manual manifest modification
    with open(os.path.join(bad_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1"}, f)
    _sign(bad_dir, config["private_key"])

    with pytest.raises(KernelError) as exc:
        loader.load("bad_manifest")
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID

    # Signature failure
    loader.public_key = b"key"
    s_dir = os.path.join(loader.modules_path, "s")
    create_module_files(s_dir, "s", {})
    with patch("core.module_loader.loader.verify_module_signature", return_value=False):
        with pytest.raises(KernelError) as exc:
            loader.load("s")
        assert exc.value.code == ErrorCode.MODULE_SIGNATURE_INVALID


def test_loader_activation_failure(config: Any) -> None:
    """Cover Exception catch in module activation."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path
    fail_dir = os.path.join(m_path, "fail_module")
    create_module_files(
        fail_dir,
        "fail_module",
        {},
        extra_files={
            "entry.py": (
                "class Module:\n"
                "    def __init__(self):\n"
                "        raise RuntimeError('crash')"
            )
        },
    )
    _sign(fail_dir, config["private_key"])

    with pytest.raises(KernelError) as exc:
        loader.load("fail_module")
    assert exc.value.code == ErrorCode.MODULE_EXECUTION_FAILED


def test_loader_getters_and_properties_success(config: Any) -> None:
    """Cover ModuleLoader properties and SUCCESS path for get_module_instance."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path
    # Load a module to hit line 511
    ok_dir = os.path.join(m_path, "ok")
    create_module_files(ok_dir, "ok", {"version": "1.0.0"})
    _sign(ok_dir, config["private_key"])
    loader.load("ok")

    assert loader.get_module_instance("ok") is not None  # Hits 511
    assert loader.audit_ledger is not None
    assert loader.registry is not None
    assert loader.event_bus is not None
    assert isinstance(loader.loaded_modules, dict)
    assert loader.get_module_instance("none") is None
    assert loader.get_module_state("none") is None
    assert loader.get_backup_state("none") is None


def test_loader_hot_swap_missing_manifest(config: Any, tmp_path: Any) -> None:
    """Cover hot_swap ErrorCode.MODULE_MANIFEST_INVALID (line 427)."""
    loader = ModuleLoader(config)
    os.makedirs(tmp_path / "no_manifest_dir", exist_ok=True)
    with pytest.raises(KernelError) as exc:
        loader.hot_swap("no_manifest_dir")
    assert "Hot swap requires a hardened" in exc.value.message


def test_loader_trial_load_no_module_class(config: Any) -> None:
    """Cover _perform_trial_load ErrorCode.MODULE_MANIFEST_INVALID."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path
    module_dir = os.path.join(m_path, "no_class")
    create_module_files(module_dir, "no_class", {}, extra_files={"entry.py": "x = 1"})
    _sign(module_dir, config["private_key"])

    with pytest.raises(KernelError) as exc:
        method = getattr(loader, "_perform_trial_load")
        method("no_class", str(module_dir), None)
    assert "No 'Module' class found" in exc.value.message


def test_loader_rollback_with_events(config: Any) -> None:
    """Cover rollback with events subscription (lines 487-488)."""
    loader = ModuleLoader(config)
    module_name = "rb_evt"
    # Setup state manually for rollback mock
    manifest = {"name": module_name, "version": "1.0.0", "events": ["E1"]}
    backup = {
        "version": "1.0.0",
        "manifest": manifest,
        "instance": MagicMock(),
        "namespace": {},
    }
    state = loader.state
    state["backups"][module_name] = backup
    loader.rollback(module_name)
    core = loader.core
    assert core["bus"].subscribe.called


SCHEMA_PATH = "c:/Users/sergi/colony/backend/col/engine/coe-kernel/schemas"


def test_validator_exhaustive(tmp_path: Any) -> None:
    """Cover ModuleValidator edge cases (schema alt path, exceptions)."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )
    v = ModuleValidator(SCHEMA_PATH, MagicMock(), public_key=public_key_bytes)

    # is_hardened coverage
    empty_dir = os.path.join(tmp_path, "empty_mod")
    os.makedirs(empty_dir, exist_ok=True)
    assert v.is_hardened(empty_dir) is False

    # alt_path coverage (loader.py:46)
    # We mock os.path.exists to trigger the alt_path logic
    with patch(
        "os.path.exists",
        side_effect=lambda p: "alt" in p or "schemas" in p or "manifest" in p,
    ):
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value={"type": "object"}):
                with patch("jsonschema.validate", return_value=None):
                    method = getattr(v, "_validate_schema")
                    method({"a": 1}, "test.json")

    # Schema exception (loader.py:61)
    with patch("builtins.open", side_effect=RuntimeError("io error")):
        method = getattr(v, "_validate_schema")
        with pytest.raises(KernelError) as exc:
            method({}, "error.json")
        assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID

    # Unknown capability
    v.kernel_capabilities = ["EXISTING"]
    bad_caps_dir = os.path.join(tmp_path, "bad_caps")
    create_module_files(bad_caps_dir, "b", {})
    # Sign it so we reach capability check
    _sign(bad_caps_dir, private_key)

    # Override capabilities.json
    with open(
        os.path.join(bad_caps_dir, "capabilities.json"), "w", encoding="utf-8"
    ) as f:
        json.dump({"module_id": "b", "capabilities": ["AUDIT_READ"]}, f)
    # Re-sign
    _sign(bad_caps_dir, private_key)

    with pytest.raises(KernelError) as exc:
        v.validate(bad_caps_dir)
    assert exc.value.code == ErrorCode.MODULE_CAPABILITY_UNDECLARED


def test_signature_exception() -> None:
    """Cover Exception catch in verify_module_signature (signature.py:66)."""

    # Trigger exception via malformed key bytes
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", MagicMock()):
            with pytest.raises(KernelError) as exc:
                verify_module_signature("mod", b"too_short")
            assert exc.value.code == ErrorCode.UNKNOWN_FAULT


def test_registry_full_lifecycle(mock_audit_ledger: Any) -> None:
    """Cover all status transitions and error paths in ModuleRegistry."""
    reg = ModuleRegistry(mock_audit_ledger)
    data = {
        "module_id": "m",
        "version": "1",
        "capabilities": [],
        "event_handlers": [],
        "content_hash": "h",
    }
    reg.register(data)

    # Transitions
    reg.quarantine("m", "q")
    entry = reg.get_entry("m")
    assert entry is not None
    assert entry.status == ModuleStatus.QUARANTINED
    reg.mark_failed("m", "f")
    entry = reg.get_entry("m")
    assert entry is not None
    assert entry.status == ModuleStatus.FAILED
    reg.deregister("m")
    entry = reg.get_entry("m")
    assert entry is not None
    assert entry.status == ModuleStatus.UNLOADED

    # Error paths (missing module)
    for method_name in ["quarantine", "mark_failed"]:
        method = getattr(reg, method_name)
        with pytest.raises(KernelError) as exc:
            method("ghost", "reason")
        assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID

    # Deregister (1 arg)
    with pytest.raises(KernelError):
        reg.deregister("ghost")

    # Helpers
    assert len(reg.get_all_entries()) == 1
    assert reg.get_loaded_modules() == []
    assert reg.compute_module_hash({"a": 1}) is not None


def test_shadow_bus_full() -> None:
    """Cover _ShadowBus publish, subscribe, unsubscribe, cleanup."""
    bus = MagicMock()
    shadow = _ShadowBus(bus)
    # publish line 35
    shadow.publish("event_type", {"data": 1})
    assert shadow.emitted_events[0]["type"] == "event_type"
    assert shadow.emitted_events[0]["payload"]["data"] == 1

    shadow.subscribe("evt", MagicMock(), "sub")
    # Unsubscribe manual
    shadow.unsubscribe("sub", "evt")
    shadow.unsubscribe("sub", "evt")  # Coverage: double unsubscribe

    # Cleanup
    shadow.subscribe("evt2", MagicMock(), "sub2")
    shadow.cleanup()
    assert bus.unsubscribe.call_count == 3


def test_module_event_proxy_publish() -> None:
    """Cover ModuleEventProxy.publish (lines 42-55)."""
    bus = MagicMock()
    proxy = ModuleEventProxy(bus, "m1")

    # Needs Event import from core.types
    proxy.publish("test.event", {"payload": "data"})
    assert bus.publish.called
    event = bus.publish.call_args[0][0]
    assert event.type == "test.event"
    assert event.payload == {"payload": "data"}


def test_loader_compatibility_failure(config: Any) -> None:
    """Cover _check_compatibility failure (lines 304-307)."""
    config["kernel_version"] = "2.0.0"
    loader = ModuleLoader(config)
    with pytest.raises(KernelError) as exc:
        loader.check_compatibility("m", "1.0.0", "1.x")
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID
    assert "incompatible" in str(exc.value.message)


def test_loader_activation_no_module_class(config: Any) -> None:
    """Cover _activate_instance no Module class fail."""
    loader = ModuleLoader(config)
    # namespace with no Module class
    namespace = {"x": 1}
    instance = loader.activate_instance("m", namespace, {}, None)
    assert instance is None


def test_loader_hot_swap_health_fail(config: Any) -> None:
    """Cover hot_swap shadow_health check failure (line 474)."""
    loader = ModuleLoader(config)
    m_path = loader.modules_path

    # Setup V1
    v1_dir = os.path.join(m_path, "h_fail")
    create_module_files(v1_dir, "h_fail", {"version": "1.0.0"})
    _sign(v1_dir, config["private_key"])
    loader.load("h_fail")

    # Overwrite V1 with V2 (healthcheck fails)
    create_module_files(
        v1_dir,
        "h_fail",
        {"version": "1.1.0"},
        extra_files={
            "entry.py": "class Module:\n    def healthcheck(self): return False"
        },
    )
    _sign(v1_dir, config["private_key"])

    with pytest.raises(KernelError) as exc:
        loader.hot_swap("h_fail")
    assert "Shadow healthcheck failed" in str(exc.value.message)


def test_loader_rollback_errors(config: Any) -> None:
    """Cover rollback error paths (lines 517, 525)."""
    loader = ModuleLoader(config)
    # Missing module
    with pytest.raises(KernelError) as exc:
        loader.rollback("ghost")
    assert "No backup found" in str(exc.value.message)

    # Missing backup
    loader.state["loaded"]["m"] = {"version": "1"}
    with pytest.raises(KernelError) as exc:
        loader.rollback("m")
    assert "No backup found" in str(exc.value.message)


def test_validator_signature_missing_sys_key(tmp_path: Any) -> None:
    """Cover ModuleValidator.validate missing system key (line 146)."""
    v = ModuleValidator(SCHEMA_PATH, MagicMock(), public_key=None)
    mod_dir = os.path.join(tmp_path, "no_sys_key")
    create_module_files(mod_dir, "no_sys_key", {})
    with pytest.raises(KernelError) as exc:
        v.validate(mod_dir)
    assert "No system public key" in str(exc.value.message)
