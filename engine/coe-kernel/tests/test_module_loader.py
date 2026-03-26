"""Strict TDD suite for the Module Loader.

Verifies AST restrictions and sandbox integrity in Phase 5 context.
"""

import os
from typing import Any, Tuple, cast
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader
from core.module_loader.registry import ModuleRegistry
from core.module_loader.signature import compute_module_hash
from tests.conftest import create_module_files


@pytest.fixture(name="loader_ctx")
def loader_ctx_fixture(tmp_path: Any) -> Tuple[ModuleLoader, ed25519.Ed25519PrivateKey]:
    """Fixture to provide a clean ModuleLoader and its private key."""
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )

    config = {
        "modules_path": str(modules_dir),
        "forbidden_imports": ["os", "sys"],
        "audit_ledger": MagicMock(),
        "registry": ModuleRegistry(audit_ledger=MagicMock()),
        "kernel_version": "1.0.0",
        "public_key": public_key_bytes,
    }
    return ModuleLoader(config), private_key


def _sign(module_dir: str, private_key: ed25519.Ed25519PrivateKey) -> None:
    """Helper to sign a module directory."""

    module_hash = compute_module_hash(module_dir)
    signature = private_key.sign(module_hash)
    with open(os.path.join(module_dir, "signature.sig"), "wb") as f:
        f.write(signature)


def test_missing_module_rejected(loader_ctx: Any) -> None:
    """Test rejection of non-existent module."""
    loader, _ = loader_ctx
    with pytest.raises(KernelError) as exc_info:
        loader.load("missing_module")

    assert exc_info.value.code == ErrorCode.MODULE_NOT_FOUND


def test_forbidden_imports_rejected(loader_ctx: Any) -> None:
    """Test Set 3: Forbidden imports (os, sys) are rejected via AST."""
    loader, private_key = loader_ctx
    module_name = "bad_import"
    module_dir = os.path.join(loader.modules_path, module_name)
    create_module_files(
        module_dir, module_name, {}, extra_files={"entry.py": "import os\nx=1"}
    )
    _sign(module_dir, private_key)

    with pytest.raises(KernelError) as exc:
        loader.load(module_name)
    assert "forbidden import" in str(exc.value.message).lower()


def test_circular_dependency_rejected(loader_ctx: Any) -> None:
    """Test Set 3: Circular dependencies are rejected."""
    loader, private_key = loader_ctx
    m_path = loader.modules_path

    # A -> B
    a_dir = os.path.join(m_path, "a")
    create_module_files(a_dir, "a", {"dependencies": ["b"]})
    _sign(a_dir, private_key)

    # B -> A
    b_dir = os.path.join(m_path, "b")
    create_module_files(b_dir, "b", {"dependencies": ["a"]})
    _sign(b_dir, private_key)

    with pytest.raises(KernelError) as exc:
        loader.load("a")
    assert exc.value.code == ErrorCode.MODULE_DEPENDENCY_CIRCULAR


def test_syntax_error_rejected(loader_ctx: Any) -> None:
    """Test syntax error in module code."""
    loader, private_key = loader_ctx
    module_name = "syntax"
    module_dir = os.path.join(loader.modules_path, module_name)
    create_module_files(
        module_dir, module_name, {}, extra_files={"entry.py": "if: invalid"}
    )
    _sign(module_dir, private_key)

    with pytest.raises(KernelError) as exc:
        loader.load(module_name)
    # Could be ErrorCode.MODULE_MANIFEST_INVALID during AST step
    assert "syntax error" in str(exc.value.message).lower()


def test_already_loaded_skips(loader_ctx: Any) -> None:
    """Loading an already loaded module same version should return early."""
    loader, private_key = loader_ctx
    module_name = "m1"
    module_dir = os.path.join(loader.modules_path, module_name)
    create_module_files(module_dir, module_name, {})
    _sign(module_dir, private_key)

    loader.load(module_name)
    # Re-loading same version should be a no-op
    loader.load(module_name)
    assert module_name in loader.get_loaded_modules()


def test_unload_removes_from_state(loader_ctx: Any) -> None:
    """Test Set 3: Modules can be unloaded from RAM."""
    loader, private_key = loader_ctx
    module_name = "m2"
    module_dir = os.path.join(loader.modules_path, module_name)
    create_module_files(module_dir, module_name, {})
    _sign(module_dir, private_key)

    loader.load(module_name)
    assert module_name in loader.get_loaded_modules()

    loader.unload(module_name)
    assert module_name not in loader.get_loaded_modules()
