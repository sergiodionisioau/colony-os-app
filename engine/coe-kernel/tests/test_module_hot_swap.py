"""Tests for Module Hot Swap Pipeline (D-05).

Verifies the 7-step upgrade process including shadow-loading, event mirroring,
and atomic switching in Phase 5 context.
"""

import os
import tempfile
from typing import Optional, Any, Generator, Tuple, cast
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader
from core.module_loader.registry import ModuleRegistry
from tests.conftest import create_module_files


@pytest.fixture(name="hot_swap_config")
def fixture_hot_swap_config() -> Generator[
    Tuple[
        str, ModuleLoader, ModuleRegistry, MagicMock, ed25519.Ed25519PrivateKey, bytes
    ],
    None,
    None,
]:
    """Setup for hot swap tests."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )

    with tempfile.TemporaryDirectory() as td:
        audit_ledger = MagicMock()
        registry = ModuleRegistry(audit_ledger=audit_ledger)
        event_bus = MagicMock()

        config = {
            "modules_path": td,
            "forbidden_imports": [],
            "audit_ledger": audit_ledger,
            "registry": registry,
            "event_bus": event_bus,
            "public_key": public_key_bytes,
            "kernel_version": "1.0.0",
        }
        loader = ModuleLoader(config)

        yield td, loader, registry, event_bus, private_key, public_key_bytes


def _create_module_v2(
    td: str,
    name: str,
    version: str,
    private_key: ed25519.Ed25519PrivateKey,
    contents: Optional[str] = None,
) -> str:
    """Helper to create a Phase 5 validated module directory."""
    module_dir = os.path.join(td, name)

    manifest = {
        "version": version,
        "events_subscribed": ["test.event"],
    }

    create_module_files(
        module_dir,
        name,
        manifest,
        extra_files={
            "entry.py": contents
            or (
                "class Module:\n"
                "    def initialize(self, bus): self.bus = bus\n"
                "    def handle_event(self, ev): self.bus.publish('ok', payload={})\n"
                "    def healthcheck(self): return True"
            )
        },
        sign=True,
        signing_key=private_key.private_bytes(
            encoding=cast(Any, serialization.Encoding.Raw),
            format=cast(Any, serialization.PrivateFormat.Raw),
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )
    return module_dir


def test_hot_swap_success(hot_swap_config: Any) -> None:
    """Verifies a successful hot swap upgrade (§9)."""
    td, loader, registry, _, private_key, _ = hot_swap_config
    module_name = "test_module"

    # 1. Load initial version (0.1.0)
    _create_module_v2(td, module_name, "0.1.0", private_key)
    loader.load(module_name)
    assert registry.get_entry(module_name).metadata.version == "0.1.0"

    # 2. Upgrade to 0.2.0
    _create_module_v2(td, module_name, "0.2.0", private_key)
    loader.hot_swap(module_name)

    # 3. Verify switch
    assert registry.get_entry(module_name).metadata.version == "0.2.0"
    assert loader.get_loaded_modules() == [module_name]


def test_hot_swap_failure_healthcheck(hot_swap_config: Any) -> None:
    """Verifies hot swap rejection on healthcheck failure (§9.198)."""
    td, loader, registry, _, private_key, _ = hot_swap_config
    module_name = "fail_module"

    # 1. Load stable version
    _create_module_v2(td, module_name, "1.0.0", private_key)
    loader.load(module_name)

    # 2. Prepare broken version (healthcheck fails)
    broken_code = (
        "class Module:\n"
        "    def initialize(self, bus): pass\n"
        "    def healthcheck(self): return False"
    )
    _create_module_v2(td, module_name, "1.1.0", private_key, contents=broken_code)

    # 3. Attempt hot swap
    with pytest.raises(KernelError) as exc:
        loader.hot_swap(module_name)

    assert exc.value.code == ErrorCode.MODULE_EXECUTION_FAILED
    assert "Shadow healthcheck failed" in str(exc.value)

    # 4. Verify original remains active
    assert registry.get_entry(module_name).metadata.version == "1.0.0"


def test_hot_swap_behavior_check(hot_swap_config: Any) -> None:
    """Verifies that hot swap captures shadow events (§9.198)."""
    td, loader, _, _, private_key, _ = hot_swap_config
    module_name = "parity_module"

    # 1. Load V1
    _create_module_v2(td, module_name, "1.0.0", private_key)
    loader.load(module_name)

    # 2. Upgrade with code that emits an event during init to trigger parity log
    parity_code = (
        "class Module:\n"
        "    def initialize(self, bus): bus.publish('init_event', payload={})\n"
        "    def healthcheck(self): return True"
    )
    _create_module_v2(td, module_name, "1.1.0", private_key, contents=parity_code)

    loader.hot_swap(module_name)

    # Verify audit log contains parity check success
    logs = [
        e
        for e in loader.audit_ledger.append.call_args_list
        if e[1]["action"] == "hot_swap_parity_check"
    ]
    assert len(logs) > 0
    assert logs[0][1]["status"] == "SUCCESS"
