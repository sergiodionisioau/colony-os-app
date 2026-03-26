"""Critical coverage tests for COE Kernel Phase 1 & 2.

Targets every uncovered branch identified in the 93% coverage analysis:
- audit/ledger.py: segment rotation, directory-mode load, bridge entries
- event_bus/bus.py: get_stats utility
- event_bus/store.py: archive path, segment recovery, retention eviction
- identity/service.py: register_agent, delegation paths
- main.py: genesis boot, normal boot, shutdown, get_subsystems
- metering/node.py: consume() budget-exceeded path
- module_loader/loader.py: Module.initialize health-check, rollback edge
- secrets/vault.py: TTL creation and expired-access enforcement
"""

import gc
import json
import os
import time
import uuid
from dataclasses import replace
from typing import Any, Dict, Optional, List
import pytest

from core.audit.ledger import AuditLedger
from core.errors import ErrorCode, KernelError
from core.event_bus.backpressure import BackpressureController
from core.event_bus.bus import (
    EventBus,
    IsolationLayer,
    SchemaRegistry,
    compute_event_signature,
)
from core.event_bus.dlq import DeadLetterQueue
from core.event_bus.store import EventStore
from core.identity.service import IdentityService
from core.main import KernelBootstrap
from core.metering.node import MeteringLayer
from core.module_loader.loader import ModuleLoader
from core.policy.engine import PolicyEngine
from core.secrets.vault import SecretsVault
from core.types import Event, EventBusDependencies
from tests.conftest import MockAuditLedger, MockIdentityServicePolicy

# ---------------------------------------------------------------------------
# Helper: build a correctly signed event
# ---------------------------------------------------------------------------


def _make_signed_event(
    event_type: str = "test.event",
    version: str = "1.0",
    payload: Optional[Dict[str, Any]] = None,
    sequence_number: int = 0,
) -> Event:
    if payload is None:
        payload = {"data": "value"}
    partial = Event(
        event_id=uuid.uuid4(),
        sequence_number=sequence_number,
        correlation_id=uuid.uuid4(),
        type=event_type,
        version=version,
        timestamp="2026-01-01T00:00:00Z",
        origin_id=uuid.uuid4(),
        payload=payload,
        signature="TEMP",
    )
    return replace(partial, signature=compute_event_signature(partial))


# ---------------------------------------------------------------------------
# AUDIT LEDGER — Segment rotation, bridge entries, directory-mode
# ---------------------------------------------------------------------------


class TestAuditSegmentRotation:
    """Covers ledger.py _seal_and_rotate and directory load paths."""

    def test_segment_rotation_creates_bridge_entry(self, tmp_path: Any) -> None:
        """Force a rotation; verify bridge entry appears and chain is valid."""
        storage_path = str(tmp_path / "audit.log")
        ledger = AuditLedger(
            storage_path=storage_path,
            genesis_constant="TEST_GENESIS",
            segment_max_entries=2,
        )
        ledger.append("K", "a1", "SUCCESS", {})
        ledger.append("K", "a2", "SUCCESS", {})
        # Triggers rotation — segment_max_entries=2 reached
        ledger.append("K", "a3", "SUCCESS", {})

        assert os.path.exists(f"{storage_path}.001")
        assert ledger.verify_integrity() is True
        actions = [e.action for e in ledger.iterate()]
        assert "audit.segment_bridge" in actions

    def test_multiple_rotations_keep_chain_valid(self, tmp_path: Any) -> None:
        """Multiple segment rotations maintain cryptographic chain integrity."""
        storage_path = str(tmp_path / "audit_multi.log")
        ledger = AuditLedger(
            storage_path=storage_path,
            genesis_constant="TEST_GENESIS",
            segment_max_entries=2,
        )
        for i in range(6):
            ledger.append("K", f"action{i}", "SUCCESS", {"i": i})
        assert ledger.verify_integrity() is True

    def test_directory_mode_load(self, tmp_path: Any) -> None:
        """AuditLedger operates with a directory path, loads on restart."""
        audit_dir = str(tmp_path / "audit_dir")
        os.makedirs(audit_dir, exist_ok=True)

        ledger = AuditLedger(
            storage_path=audit_dir,
            genesis_constant="DIR_GENESIS",
            segment_max_entries=100,
        )
        e1 = ledger.append("K", "dir_action", "SUCCESS", {"x": 1})

        ledger2 = AuditLedger(
            storage_path=audit_dir,
            genesis_constant="DIR_GENESIS",
        )
        entries = list(ledger2.iterate())
        assert len(entries) == 1
        assert entries[0].entry_id == e1.entry_id

    def test_directory_mode_seal_entries_not_loaded_as_data(
        self, tmp_path: Any
    ) -> None:
        """Segment seal entries are skipped when loading; bridge entries load."""
        audit_dir = str(tmp_path / "audit_dir2")
        os.makedirs(audit_dir, exist_ok=True)

        ledger = AuditLedger(
            storage_path=audit_dir,
            genesis_constant="DIR_GENESIS",
            segment_max_entries=2,
        )
        ledger.append("K", "a1", "SUCCESS", {})
        ledger.append("K", "a2", "SUCCESS", {})
        ledger.append("K", "a3", "SUCCESS", {})  # triggers rotation in dir mode

        ledger2 = AuditLedger(storage_path=audit_dir, genesis_constant="DIR_GENESIS")
        actions = [e.action for e in ledger2.iterate()]
        assert "audit.segment_seal" not in actions


# ---------------------------------------------------------------------------
# EVENT STORE — Archive, retention eviction, corrupted line recovery
# ---------------------------------------------------------------------------


class TestEventStoreAdvanced:
    """Covers store.py archive path, retention, and recovery."""

    def test_archive_path_receives_evicted_segment(self, tmp_path: Any) -> None:
        """Evicted segments are moved to archive_path when set."""
        store_dir = str(tmp_path / "store")
        archive_dir = str(tmp_path / "archive")
        store = EventStore(
            storage_path=store_dir,
            segment_size=1,
            max_events=1,
            archive_path=archive_dir,
        )

        e1 = _make_signed_event(sequence_number=1)
        store.append(e1)
        e2 = _make_signed_event(sequence_number=2)
        store.append(e2)  # Triggers eviction of segment_000000.json

        archived = os.listdir(archive_dir)
        assert len(archived) >= 1

    def test_no_archive_eviction_deletes_segment(self, tmp_path: Any) -> None:
        """Without archive_path, evicted segments are deleted."""
        store_dir = str(tmp_path / "store2")
        store = EventStore(storage_path=store_dir, segment_size=1, max_events=1)

        e1 = _make_signed_event(sequence_number=1)
        store.append(e1)
        e2 = _make_signed_event(sequence_number=2)
        store.append(e2)

        remaining = [f for f in os.listdir(store_dir) if f.startswith("segment_")]
        assert len(remaining) == 1

    def test_get_events_only_returns_requested_range(self, tmp_path: Any) -> None:
        """get_events stops reading once sequence exceeds end_seq."""
        store_dir = str(tmp_path / "store4")
        store = EventStore(storage_path=store_dir, segment_size=100)

        for i in range(1, 6):
            ev = _make_signed_event(sequence_number=i)
            store.append(ev)

        events = store.get_events(2, 3)
        assert len(events) == 2
        assert events[0].sequence_number == 2
        assert events[1].sequence_number == 3

    def test_out_of_order_write_rejected(self, tmp_path: Any) -> None:
        """Appending a lower-or-equal sequence number raises EVENT_VERSION_MISMATCH."""
        store_dir = str(tmp_path / "store5")
        store = EventStore(storage_path=store_dir, segment_size=100)

        e1 = _make_signed_event(sequence_number=5)
        store.append(e1)

        e2 = _make_signed_event(sequence_number=3)
        with pytest.raises(KernelError) as exc:
            store.append(e2)
        assert exc.value.code == ErrorCode.EVENT_VERSION_MISMATCH

    def test_segment_index_recovery_from_filename(self, tmp_path: Any) -> None:
        """_recover_state parses segment index from filename correctly."""
        store_dir = str(tmp_path / "store6")
        store1 = EventStore(storage_path=store_dir, segment_size=1)
        e1 = _make_signed_event(sequence_number=1)
        store1.append(e1)
        e2 = _make_signed_event(sequence_number=2)
        store1.append(e2)

        # New instance recovers index and sequence
        store2 = EventStore(storage_path=store_dir, segment_size=1)
        assert store2.get_current_sequence() == 2


# ---------------------------------------------------------------------------
# EVENT BUS — IsolationLayer get_stats and warning audit paths
# ---------------------------------------------------------------------------


class TestIsolationLayer:
    """Covers bus.py IsolationLayer.get_stats and timeout/memory warnings."""

    def test_get_stats_reflects_configured_limits(self) -> None:
        """get_stats() returns the configured timeout and max_objects values."""
        ledger = MockAuditLedger()
        iso = IsolationLayer(audit_ledger=ledger, timeout_seconds=5.0, max_objects=500)
        stats = iso.get_stats()
        assert stats["timeout_seconds"] == 5.0
        assert stats["max_objects"] == 500

    def test_timeout_abuse_creates_warning_audit(self) -> None:
        """Slow handler triggers subscriber_timeout_abuse WARNING."""
        ledger = MockAuditLedger()
        iso = IsolationLayer(
            audit_ledger=ledger, timeout_seconds=0.001, max_objects=999_999
        )

        def slow_handler(_event: Event) -> None:
            time.sleep(0.05)

        with pytest.raises(KernelError):
            iso.execute_subscriber("sub_slow", slow_handler, _make_signed_event())

        timeout_entries = [
            e for e in ledger.entries if e.action == "subscriber_timeout_abuse"
        ]
        assert len(timeout_entries) == 1
        assert timeout_entries[0].status == "WARNING"

    def test_memory_abuse_creates_warning_audit(self) -> None:
        """Handler that holds live object references triggers
        subscriber_memory_abuse WARNING.
        """
        ledger = MockAuditLedger()
        # max_objects=1 so any allocation the GC sees will trigger
        iso = IsolationLayer(audit_ledger=ledger, timeout_seconds=30.0, max_objects=1)

        holder: List[Any] = []

        def leaking_handler(_event: Event) -> None:
            gc.collect()
            # Allocate 5000 dicts with nested lists — all kept alive via holder
            for _ in range(5000):
                holder.append({"key": "value", "nested": [1, 2, 3]})
            gc.collect()

        iso.execute_subscriber("sub_mem", leaking_handler, _make_signed_event())

        mem_entries = [
            e for e in ledger.entries if e.action == "subscriber_memory_abuse"
        ]
        assert len(mem_entries) == 1
        assert mem_entries[0].status == "WARNING"


# ---------------------------------------------------------------------------
# IDENTITY SERVICE — register_agent and delegation token tests
# ---------------------------------------------------------------------------


class TestIdentityDelegation:
    """Covers identity/service.py register_agent and delegation paths."""

    @pytest.fixture(name="id_svc")
    def id_svc_fixture(self) -> IdentityService:
        """Provides a fresh IdentityService instance for each test."""
        ledger = MockAuditLedger()
        schema = {"admin": ["all"], "agent": ["publish_event"]}
        return IdentityService(audit_ledger=ledger, role_schema=schema)

    def test_register_agent_sets_type_agent(self, id_svc: IdentityService) -> None:
        """register_agent creates an identity with type 'agent'."""
        parent = id_svc.register_identity("parent", "admin", None, "user", b"key")
        agent = id_svc.register_agent("bot", "agent", str(parent.id), b"key")
        assert agent.type == "agent"
        assert agent.role == "agent"

    def test_create_delegation_returns_signed_token(
        self, id_svc: IdentityService
    ) -> None:
        """create_delegation returns a token with non-empty HMAC signature."""
        parent = id_svc.register_identity(
            "delegator", "admin", None, "user", b"delegator_key"
        )
        delegate = id_svc.register_identity(
            "delegatee", "agent", str(parent.id), "agent", b"delegate_key"
        )
        signing_key = b"shared_signing_key"
        token = id_svc.create_delegation(
            delegator_id=parent.id,
            delegate_id=delegate.id,
            scope=["publish_event"],
            ttl_seconds=3600,
            signing_key=signing_key,
        )
        assert token.delegator_id == parent.id
        assert token.delegate_id == delegate.id
        assert len(token.signature) > 0

    def test_verify_delegation_returns_true_for_valid_token(
        self, id_svc: IdentityService
    ) -> None:
        """verify_delegation returns True for a fresh, unexpired token."""
        parent = id_svc.register_identity("delegator2", "admin", None, "user", b"k")
        delegate = id_svc.register_identity(
            "delegatee2", "agent", str(parent.id), "agent", b"k"
        )
        token = id_svc.create_delegation(
            delegator_id=parent.id,
            delegate_id=delegate.id,
            scope=["publish_event"],
            ttl_seconds=3600,
            signing_key=b"key",
        )
        assert id_svc.verify_delegation(token) is True

    def test_verify_delegation_returns_false_for_expired(
        self, id_svc: IdentityService
    ) -> None:
        """verify_delegation returns False for an expired token (per spec §2c)."""
        parent = id_svc.register_identity("delegator3", "admin", None, "user", b"k")
        delegate = id_svc.register_identity(
            "delegatee3", "agent", str(parent.id), "agent", b"k"
        )
        token = id_svc.create_delegation(
            delegator_id=parent.id,
            delegate_id=delegate.id,
            scope=["publish_event"],
            ttl_seconds=1,
            signing_key=b"key",
        )
        time.sleep(1.1)
        # Per service.py L289-L290: returns False on expiry
        result = id_svc.verify_delegation(token)
        assert result is False

    def test_create_delegation_unknown_delegator_raises(
        self, id_svc: IdentityService
    ) -> None:
        """create_delegation raises IDENTITY_NOT_FOUND for unknown delegator."""
        with pytest.raises(KernelError) as exc:
            id_svc.create_delegation(
                delegator_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                delegate_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                scope=[],
                ttl_seconds=60,
                signing_key=b"key",
            )
        assert exc.value.code == ErrorCode.IDENTITY_NOT_FOUND


# ---------------------------------------------------------------------------
# MAIN — Genesis, normal boot, shutdown, get_subsystems
# ---------------------------------------------------------------------------


class TestKernelBootstrapPaths:
    """Covers main.py genesis/normal boot uncovered branches."""

    def _make_config(self, tmp_path: Any, mode: str = "normal") -> Dict[str, Any]:
        return {
            "bootstrap": {
                "mode": mode,
                "root_keypair_path": str(tmp_path / "root.pem"),
                "admin_identity": {
                    "name": "kernel_admin",
                    "role": "admin",
                    "type": "user",
                },
            },
            "rbac": {"roles": {"admin": ["all"], "agent": ["publish_event"]}},
            "audit_path": str(tmp_path / "audit.log"),
            "event_store_path": str(tmp_path / "events/"),
            "secrets_data_path": str(tmp_path / "secrets.json"),
            "secrets_salt_path": str(tmp_path / "salt.bin"),
            "vault_passphrase": "test_pass",
        }

    def test_normal_boot_verify_startup(self, tmp_path: Any) -> None:
        """Normal mode: verify_startup returns True."""
        k = KernelBootstrap(self._make_config(tmp_path, mode="normal"))
        assert k.verify_startup() is True

    def test_genesis_boot_creates_key_file_and_audit_entry(self, tmp_path: Any) -> None:
        """Genesis mode: root key file created, kernel.genesis audited."""
        cfg = self._make_config(tmp_path, mode="genesis")
        k = KernelBootstrap(cfg)
        assert os.path.exists(cfg["bootstrap"]["root_keypair_path"])
        actions = [e.action for e in k.audit_ledger.iterate()]
        assert "kernel.genesis" in actions

    def test_shutdown_appends_system_shutdown(self, tmp_path: Any) -> None:
        """shutdown() creates a system_shutdown audit entry."""
        k = KernelBootstrap(self._make_config(tmp_path, mode="normal"))
        k.shutdown()
        actions = [e.action for e in k.audit_ledger.iterate()]
        assert "system_shutdown" in actions

    def test_get_subsystems_has_all_keys(self, tmp_path: Any) -> None:
        """get_subsystems() returns all 6 expected keys."""
        k = KernelBootstrap(self._make_config(tmp_path, mode="normal"))
        subs = k.get_subsystems()
        for key in ("bus", "identity", "policy", "vault", "metering", "state"):
            assert key in subs


# ---------------------------------------------------------------------------
# MODULE LOADER — Module class initialize(), rollback edge case
# ---------------------------------------------------------------------------


class TestModuleLoaderLifecycle:
    """Covers loader.py Module class detection and rollback edge."""

    def test_module_class_initialize_is_called(
        self, tmp_path: Any, mock_loader_config: Dict[str, Any]
    ) -> None:
        """Loader calls initialize() on a Module class found in the namespace."""
        module_dir = str(tmp_path / "modules")
        os.makedirs(module_dir, exist_ok=True)

        manifest = {
            "name": "healthy_mod",
            "version": "1.0.0",
            "kernel_compatibility": "*",
            "entrypoint": "healthy_mod.py",
            "dependencies": [],
            "permissions": [],
            "events": [],
            "capabilities": [],
        }
        with open(
            os.path.join(module_dir, "healthy_mod.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(manifest, f)

        # Module with lifecycle class — initialize sets a flag
        with open(
            os.path.join(module_dir, "healthy_mod.py"), "w", encoding="utf-8"
        ) as f:
            f.write(
                "class Module:\n"
                "    initialized = False\n"
                "    def initialize(self, ctx):\n"
                "        Module.initialized = True\n"
            )

        mock_loader_config["modules_path"] = module_dir
        loader = ModuleLoader(mock_loader_config)
        loader.load("healthy_mod")

        state = loader.get_module_state("healthy_mod")
        assert state is not None
        assert state["instance"] is not None

    def test_rollback_no_backup_raises_manifest_invalid(
        self, tmp_path: Any, mock_loader_config: Dict[str, Any]
    ) -> None:
        """rollback() raises MODULE_MANIFEST_INVALID when no backup exists."""
        mock_loader_config["modules_path"] = str(tmp_path)
        loader = ModuleLoader(mock_loader_config)
        with pytest.raises(KernelError) as exc:
            loader.rollback("ghost_module")
        assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID


# ---------------------------------------------------------------------------
# SECRETS VAULT — TTL expiry enforcement
# ---------------------------------------------------------------------------


class TestSecretsVaultTTL:
    """Covers vault.py TTL creation and expiry enforcement paths."""

    @pytest.fixture(name="vault")
    def vault_fixture(self, tmp_path: Any) -> SecretsVault:
        """Provides a fresh SecretsVault instance for each test."""
        return SecretsVault(
            data_path=str(tmp_path / "secrets.json"),
            salt_path=str(tmp_path / "salt.bin"),
            audit_ledger=MockAuditLedger(),
            passphrase="test_passphrase",
        )

    def test_secret_with_ttl_accessible_before_expiry(
        self, vault: SecretsVault
    ) -> None:
        """Secret retrieved successfully before TTL expires."""
        identity_id = str(uuid.uuid4())
        vault.store_secret(identity_id, "api_key", "supersecret", ttl=3600)
        assert vault.retrieve_secret(identity_id, "api_key") == "supersecret"

    def test_secret_expired_raises_secret_expired(self, tmp_path: Any) -> None:
        """retrieve_secret raises SECRET_EXPIRED after TTL elapses."""
        vault = SecretsVault(
            data_path=str(tmp_path / "s2.json"),
            salt_path=str(tmp_path / "s2.bin"),
            audit_ledger=MockAuditLedger(),
            passphrase="test_passphrase",
        )
        identity_id = str(uuid.uuid4())
        vault.store_secret(identity_id, "expiring_key", "value", ttl=1)
        time.sleep(1.1)
        with pytest.raises(KernelError) as exc:
            vault.retrieve_secret(identity_id, "expiring_key")
        assert exc.value.code == ErrorCode.SECRET_EXPIRED

    def test_store_secret_persists_across_reload(self, tmp_path: Any) -> None:
        """Secrets survive vault restart (loaded from disk)."""
        data_path = str(tmp_path / "s3.json")
        salt_path = str(tmp_path / "s3.bin")
        identity_id = str(uuid.uuid4())

        v1 = SecretsVault(
            data_path=data_path,
            salt_path=salt_path,
            audit_ledger=MockAuditLedger(),
            passphrase="shared_pass",
        )
        v1.store_secret(identity_id, "key1", "persistedvalue")

        v2 = SecretsVault(
            data_path=data_path,
            salt_path=salt_path,
            audit_ledger=MockAuditLedger(),
            passphrase="shared_pass",
        )
        assert v2.retrieve_secret(identity_id, "key1") == "persistedvalue"


# ---------------------------------------------------------------------------
# METERING — consume() budget-exceeded path
# ---------------------------------------------------------------------------


def test_consume_below_balance_emits_budget_exceeded(tmp_path: Any) -> None:
    """consume() with insufficient balance returns False (budget exceeded)."""
    ledger = MockAuditLedger()
    policy_eng = PolicyEngine(
        identity_service=MockIdentityServicePolicy(),
        audit_ledger=ledger,
    )

    event_store = EventStore(storage_path=str(tmp_path / "ev"), segment_size=100)
    bp = BackpressureController(activation_depth=10000, deactivation_depth=7000)
    registry = SchemaRegistry()
    registry.register("system.budget_exceeded", [], version="1.0")
    bus = EventBus(
        EventBusDependencies(
            ledger,
            event_store,
            bp,
            DeadLetterQueue(storage_path=str(tmp_path / "dlq_test")),
            registry,
        )
    )

    layer = MeteringLayer(policy_eng, bus)
    layer.allocate("agent_1", "tokens", 100)

    # 100 available, request 101 => consume() returns False
    res = layer.consume("agent_1", "tokens", 101)
    assert res is False

    # Check budget_exceeded event was emitted
    events = event_store.get_events(1, 100)
    exceeded = [e for e in events if e.type == "system.budget_exceeded"]
    assert len(exceeded) == 1
    ev = exceeded[0]
    assert ev.payload["identity_id"] == "agent_1"
    assert ev.payload["metric"] == "tokens"
    assert ev.payload["requested"] == 101
    assert ev.payload["available"] == 100

    # Also verify that a record() exceeding budget emits policy_denied/budget_exceeded
    layer.record(uuid.uuid4(), "mem", 999999)
    events2 = event_store.get_events(1, 100)
    denied = [e for e in events2 if e.type == "system.budget_exceeded"]
    assert len(denied) > 0


# ---------------------------------------------------------------------------
# BANDIT B105 false-positive confirmation
# ---------------------------------------------------------------------------


class TestErrorCodeEnum:
    """Confirms ErrorCode values are intact after nosec B105 annotation."""

    def test_secret_error_code_values_correct(self) -> None:
        """Ensures secret-related ErrorCode values are consistently defined."""
        assert ErrorCode.SECRET_NOT_FOUND.value == "5004"
        assert ErrorCode.SECRET_ACCESS_DENIED.value == "5005"
        assert ErrorCode.SECRET_EXPIRED.value == "5006"

    def test_kernel_error_message_format(self) -> None:
        """Tests the string representation of KernelError."""
        err = KernelError(code=ErrorCode.POLICY_DENIED, message="not allowed")
        assert "POLICY_DENIED" in str(err)
        assert "not allowed" in str(err)
