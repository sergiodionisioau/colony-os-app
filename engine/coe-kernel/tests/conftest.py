"""Pytest fixtures and common mocks for the COE Kernel test suite.

Maintains strict separation by providing deterministic mock implementations
for cross-component dependencies natively used by multiple testing suites.
"""

import json
import os
import uuid
from typing import Any, Dict, Iterator, Optional, cast
from unittest.mock import MagicMock

import pytest

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)

from core.errors import ErrorCode, KernelError
from core.interfaces import AuditLedgerInterface, IdentityServiceInterface
from core.module_loader.signature import compute_module_hash
from core.types import AuditEntry, Identity, IdentityStatus, Event


def generate_test_keys() -> tuple[bytes, bytes]:
    """Generates standard ed25519 keypair bytes for testing signatures."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        cast(Any, Encoding.Raw), cast(Any, PublicFormat.Raw)
    )
    priv_bytes = priv.private_bytes(
        cast(Any, Encoding.Raw), cast(Any, PrivateFormat.Raw), cast(Any, NoEncryption())
    )
    return pub_bytes, priv_bytes


COMMON_MANIFEST: Dict[str, Any] = {
    "version": "1.0.0",
    "entrypoint": "entry.py",
    "author": "verified_vendor",
    "description": "Test Module",
    "permissions": [],
    "events_subscribed": [],
    "events_emitted": [],
    "capabilities": [],
    "resource_budget": {
        "max_cpu": 0.5,
        "max_memory": 128,
        "max_events_per_minute": 100,
        "max_token_cost": 0.1,
    },
}


class MockAuditLedger(AuditLedgerInterface):
    """Mock ledger for testing components isolated from actual I/O.

    Deterministically captures entries without cryptographic chaining.
    """

    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def append(
        self, actor_id: str, action: str, status: str, metadata: Dict[str, Any]
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=uuid.uuid4(),
            timestamp="now",
            actor_id=actor_id,
            action=action,
            status=status,
            metadata=metadata,
            previous_hash="000",
            entry_hash="111",
        )
        self.entries.append(entry)
        return entry

    def verify_integrity(self) -> bool:
        return True

    def iterate(self, action: Optional[str] = None) -> Iterator[AuditEntry]:
        for entry in self.entries:
            if action is None or entry.action == action:
                yield entry


@pytest.fixture(name="mock_audit_ledger")
def mock_audit_ledger_fixture() -> MockAuditLedger:
    """Provides a fresh MockAuditLedger instance for each test."""
    return MockAuditLedger()


class MockIdentityServicePolicy(IdentityServiceInterface):
    """Mock identity service for policy evaluation tests."""

    def get_identity(self, identity_id: str) -> Identity:
        """Returns complex identity objects for hardcoded IDs."""
        if identity_id == "agent_1":
            return Identity(
                id=uuid.uuid4(),
                name="a1",
                role="agent",
                type="agent",
                status=IdentityStatus.ACTIVE,
                created_at="now",
                updated_at="now",
                signature="dummy",
            )
        if identity_id == "admin_1":
            return Identity(
                id=uuid.uuid4(),
                name="adm1",
                role="admin",
                type="user",
                status=IdentityStatus.ACTIVE,
                created_at="now",
                updated_at="now",
                signature="dummy",
            )

        raise KernelError(code=ErrorCode.IDENTITY_NOT_FOUND, message="Not found")

    def register_identity(
        self,
        name: str,
        role: str,
        parent_id: Optional[str],
        identity_type: str,
        *args: Any,
        **kwargs: Any,
    ) -> Identity:
        """Stub."""
        _ = (args, kwargs)
        return Identity(
            id=uuid.uuid4(),
            name=name,
            role=role,
            type=identity_type,
            status=IdentityStatus.ACTIVE,
            created_at="now",
            updated_at="now",
            signature="dummy",
            parent_id=uuid.UUID(parent_id) if parent_id else None,
        )

    def register_agent(
        self, name: str, role: str, parent_id: str, signing_key: bytes
    ) -> Identity:
        return self.register_identity(name, role, parent_id, "agent", signing_key)

    def get_identity_status(self, identity_id: str) -> Any:
        """Return None for mock status lookup."""
        _ = identity_id
        result: Any = None
        return result

    def suspend_identity(self, identity_id: str, actor_id: str) -> None:
        """No-op mock for identity suspension."""
        _ = (identity_id, actor_id)

    def reinstate_identity(self, identity_id: str, actor_id: str) -> None:
        """No-op mock for identity reinstatement."""
        _ = (identity_id, actor_id)

    def revoke_identity(self, identity_id: str, actor_id: str) -> None:
        """No-op mock for identity revocation."""
        _ = (identity_id, actor_id)

    def get_role_capabilities(self, role: str) -> list[str]:
        """Return empty capabilities for mock."""
        _ = role
        return []

    def create_delegation(self, *args: Any, **kwargs: Any) -> Any:
        _ = (args, kwargs)

    def verify_delegation(self, *args: Any, **kwargs: Any) -> bool:
        _ = (args, kwargs)
        return True

    def revoke_delegation(self, *args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)


def create_module_files(
    module_dir: str,
    module_name: str,
    manifest: Dict[str, Any],
    extra_files: Optional[Dict[str, Any]] = None,
    sign: bool = False,
    signing_key: Optional[bytes] = None,
) -> None:
    """Helper to create all mandatory files for a Phase 5 module (§3.82)."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    full_manifest = COMMON_MANIFEST.copy()
    full_manifest.update(manifest)
    full_manifest["name"] = module_name

    module_files: Dict[str, Any] = {
        "module.yaml": f"name: {module_name}\nversion: 1.0.0",
        "manifest.json": full_manifest,
        "capabilities.json": {"module_id": module_name, "capabilities": []},
        "permissions.json": {"module_id": module_name, "permissions": []},
        "cost_profile.json": {"module_id": module_name, "cost_per_event": 0.001},
        "entry.py": (
            "class Module:\n    def initialize(self, bus): pass\n"
            "    def handle_event(self, event): pass"
        ),
    }
    if extra_files:
        module_files.update(extra_files)

    os.makedirs(module_dir, exist_ok=True)
    for name, content in module_files.items():
        path = os.path.join(module_dir, name)
        if name.endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # 4. Digital Signature (§6.143)
    if sign and signing_key:
        m_hash = compute_module_hash(module_dir)
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(signing_key)
        sig = priv_key.sign(m_hash)
        with open(os.path.join(module_dir, "signature.sig"), "wb") as f:
            f.write(sig)
    else:
        # Create empty signature if not signing but file is mandatory
        # for structure check
        with open(os.path.join(module_dir, "signature.sig"), "wb") as f:
            f.write(b"dummy_signature")


@pytest.fixture(name="mock_loader_config")
def mock_loader_config_fixture(tmp_path: Any) -> Dict[str, Any]:
    """Provides a standard mock configuration for ModuleLoader."""
    return {
        "modules_path": str(tmp_path),
        "forbidden_imports": [],
        "audit_ledger": MagicMock(),
        "registry": MagicMock(),
        "event_bus": MagicMock(),
        "kernel_version": "1.0.0",
    }


def create_test_event(
    event_id: uuid.UUID,
    correlation_id: uuid.UUID,
    origin_id: uuid.UUID,
    kind: str = "t",
) -> Event:
    """Helper to create a standard event for testing to avoid duplication."""
    return Event(
        event_id=event_id,
        sequence_number=1,
        correlation_id=correlation_id,
        type=kind,
        version="1",
        timestamp="now",
        origin_id=origin_id,
        payload={"f": 1},
        signature="sig",
    )
