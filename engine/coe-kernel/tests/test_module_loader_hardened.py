"""Hardened tests for ModuleLoader signature verification and sandbox isolation.

Phase 5 specification compliance: §3 Architecture, §6 Pipeline, §8 Sandbox.
"""

import os
import tempfile
from typing import Any, Tuple, cast
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from core.module_loader.signature import compute_module_hash

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader
from core.module_loader.registry import ModuleRegistry
from tests.conftest import create_module_files


@pytest.fixture(name="crypto_ctx")
def crypto_ctx_fixture() -> Tuple[ed25519.Ed25519PrivateKey, bytes]:
    """Provides a fresh Ed25519 keypair for module signing tests."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )
    return private_key, public_key_bytes


def _sign_dir(module_dir: str, private_key: Any) -> None:
    """Signs a module directory using the provided private key."""

    m_hash = compute_module_hash(module_dir)
    sig = private_key.sign(m_hash)
    with open(os.path.join(module_dir, "signature.sig"), "wb", encoding=None) as f:
        f.write(sig)


def test_hardened_load_success(crypto_ctx: Any) -> None:
    """Verifies that a correctly signed directory-based module loads (§3, §6)."""
    private_key, public_key_bytes = crypto_ctx

    with tempfile.TemporaryDirectory() as td:
        registry = ModuleRegistry(audit_ledger=MagicMock())
        config = {
            "modules_path": td,
            "forbidden_imports": [],
            "audit_ledger": MagicMock(),
            "registry": registry,
            "public_key": public_key_bytes,
            "kernel_version": "1.0.0",
        }
        loader = ModuleLoader(config)

        module_name = "signed_module"
        module_dir = os.path.join(td, module_name)

        create_module_files(module_dir, module_name, {})
        _sign_dir(module_dir, private_key)

        loader.load(module_name)
        entry = registry.get_entry(module_name)
        assert entry is not None


def test_sandbox_builtin_restriction(crypto_ctx: Any) -> None:
    """Verifies that modules cannot access forbidden builtins like 'eval' (§8)."""
    private_key, public_key_bytes = crypto_ctx

    with tempfile.TemporaryDirectory() as td:
        config = {
            "modules_path": td,
            "forbidden_imports": [],
            "audit_ledger": MagicMock(),
            "registry": MagicMock(),
            "public_key": public_key_bytes,
        }
        loader = ModuleLoader(config)

        module_name = "evil_module"
        module_dir = os.path.join(td, module_name)

        create_module_files(
            module_dir,
            module_name,
            {},
            extra_files={
                "entry.py": (
                    "class Module:\n    def __init__(self):\n        eval('1+1')"
                )
            },
        )
        _sign_dir(module_dir, private_key)

        with pytest.raises(KernelError) as exc:
            loader.load(module_name)
        # Should be blocked by AST (Step 5)
        assert "Forbidden instruction: eval" in str(exc.value.message)


def test_sandbox_import_restriction(crypto_ctx: Any) -> None:
    """Verifies that runtime imports are blocked via AST (§8.179)."""
    private_key, public_key_bytes = crypto_ctx

    with tempfile.TemporaryDirectory() as td:
        config = {
            "modules_path": td,
            "forbidden_imports": ["os"],  # Explicitly block os
            "audit_ledger": MagicMock(),
            "registry": MagicMock(),
            "public_key": public_key_bytes,
        }
        loader = ModuleLoader(config)

        module_name = "import_module"
        module_dir = os.path.join(td, module_name)

        create_module_files(
            module_dir, module_name, {}, extra_files={"entry.py": "import os"}
        )
        _sign_dir(module_dir, private_key)

        with pytest.raises(KernelError) as exc:
            loader.load(module_name)
        assert "Forbidden import: os" in str(exc.value.message)


def test_hardened_load_rejection_on_tamper(crypto_ctx: Any) -> None:
    """Verifies that tampering after signing causes load failure (§6.143)."""
    private_key, public_key_bytes = crypto_ctx

    with tempfile.TemporaryDirectory() as td:
        registry = ModuleRegistry(audit_ledger=MagicMock())
        config = {
            "modules_path": td,
            "forbidden_imports": [],
            "audit_ledger": MagicMock(),
            "registry": registry,
            "public_key": public_key_bytes,
        }
        loader = ModuleLoader(config)

        module_name = "tampered_module"
        module_dir = os.path.join(td, module_name)

        create_module_files(module_dir, module_name, {})
        _sign_dir(module_dir, private_key)

        # Tamper with entry.py after signing
        with open(os.path.join(module_dir, "entry.py"), "a", encoding="utf-8") as f:
            f.write("\n# Tamper")

        with pytest.raises(KernelError) as exc:
            loader.load(module_name)
        assert exc.value.code == ErrorCode.MODULE_SIGNATURE_INVALID
