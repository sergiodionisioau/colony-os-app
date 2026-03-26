"""Targeted coverage tests for module_loader/loader.py uncovered lines.

Tests cover edge-case error paths identified during audit:
- Lines 36:      ImportFrom with None module
- Lines 172-175: ImportFrom forbidden import
- Lines 194:     spec_from_file_location returns None
- Lines 239,248-249: sandbox execution failure
- Lines 274-275: corrupted manifest JSON
- Lines 377:     legacy signature verification failure
- Lines 405:     entrypoint file not found
- Lines 497,500: hot_swap finalize with old instance shutdown
- Lines 525:     hot_swap finalize new instance subscribes
- AST sandbox:   attribute-based forbidden call (ast.Attribute)
- _safe_getattr:  policy proxy blocks forbidden names
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader, _safe_getattr
from tests.conftest import create_module_files, generate_test_keys


@pytest.fixture(name="loader_cfg")
def loader_cfg_fixture(tmp_path: Any) -> Dict[str, Any]:
    """Provides a minimal ModuleLoader config."""
    return {
        "modules_path": str(tmp_path),
        "forbidden_imports": ["os", "subprocess", "socket"],
        "audit_ledger": MagicMock(),
        "registry": MagicMock(),
        "event_bus": MagicMock(),
        "kernel_version": "1.0.0",
    }


# --- AST Sandbox Hardening Tests ---


def test_analyze_ast_attribute_call_forbidden(loader_cfg: Dict[str, Any]) -> None:
    """Verifies that attribute-based forbidden calls (builtins.eval)
    are caught by the AST scanner."""
    loader = ModuleLoader(loader_cfg)
    source = 'import builtins\nbuiltins.eval("1+1")\n'
    with pytest.raises(KernelError) as exc:
        loader._analyze_ast(source)  # pylint: disable=protected-access
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID
    assert "Forbidden attribute call: eval" in str(exc.value)


def test_analyze_ast_attribute_call_compile(loader_cfg: Dict[str, Any]) -> None:
    """Verifies attribute-based compile call is blocked."""
    loader = ModuleLoader(loader_cfg)
    source = 'x.compile("code")\n'
    with pytest.raises(KernelError) as exc:
        loader._analyze_ast(source)  # pylint: disable=protected-access
    assert "compile" in str(exc.value)


def test_safe_getattr_blocks_dunder() -> None:
    """Verifies _safe_getattr blocks dunder attribute access."""
    obj = type("T", (), {"__secret": "value"})()
    with pytest.raises(AttributeError, match="Sandbox access denied"):
        _safe_getattr(obj, "__secret")


def test_safe_getattr_blocks_forbidden_names() -> None:
    """Verifies _safe_getattr blocks forbidden function names."""
    obj = type("T", (), {"eval": lambda: None})()
    with pytest.raises(AttributeError, match="Sandbox access denied"):
        _safe_getattr(obj, "eval")


def test_safe_getattr_allows_safe_access() -> None:
    """Verifies _safe_getattr allows legitimate attribute access."""
    obj = type("T", (), {"name": "hello"})()
    assert _safe_getattr(obj, "name") == "hello"


def test_safe_getattr_default_value() -> None:
    """Verifies _safe_getattr returns default when attr missing."""
    obj = type("T", (), {})()
    assert _safe_getattr(obj, "missing", "fallback") == "fallback"


# --- Coverage Gap Tests for loader.py ---


def test_analyze_ast_importfrom_no_module(loader_cfg: Dict[str, Any]) -> None:
    """Covers line 36: ImportFrom with node.module = None (relative import)."""
    loader = ModuleLoader(loader_cfg)
    # 'from . import something' has node.module = None
    source = "from . import something\n"
    # Should not raise (no module name to check against forbidden list)
    loader._analyze_ast(source)  # pylint: disable=protected-access


def test_analyze_ast_importfrom_forbidden(loader_cfg: Dict[str, Any]) -> None:
    """Covers lines 172-175: ImportFrom with forbidden module."""
    loader = ModuleLoader(loader_cfg)
    source = "from os import path\n"
    with pytest.raises(KernelError) as exc:
        loader._analyze_ast(source)  # pylint: disable=protected-access
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID
    assert "Forbidden import: os" in str(exc.value)


def test_execute_sandbox_spec_none(loader_cfg: Dict[str, Any], tmp_path: Any) -> None:
    """Covers line 194: spec_from_file_location returns None."""
    loader = ModuleLoader(loader_cfg)
    with patch(
        "core.module_loader.loader.importlib.util.spec_from_file_location",
        return_value=None,
    ):
        with pytest.raises(KernelError) as exc:
            loader._execute_in_sandbox(  # pylint: disable=protected-access
                "test_mod", str(tmp_path / "nonexistent.py")
            )
        assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID


def test_load_manifest_corrupted_json(
    loader_cfg: Dict[str, Any], tmp_path: Any
) -> None:
    """Covers lines 274-275: corrupted manifest JSON."""
    loader_cfg["modules_path"] = str(tmp_path)
    loader = ModuleLoader(loader_cfg)

    # Create a corrupted JSON manifest
    with open(tmp_path / "bad_mod.json", "w", encoding="utf-8") as f:
        f.write("{invalid json content")

    with pytest.raises(KernelError) as exc:
        loader._load_manifest("bad_mod")  # pylint: disable=protected-access
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID
    assert "Corrupted" in str(exc.value)


def test_load_signature_verification_fails(
    loader_cfg: Dict[str, Any], tmp_path: Any
) -> None:
    """Covers line 377: legacy module with signature verification failure."""
    loader_cfg["modules_path"] = str(tmp_path)
    pub_bytes, _ = generate_test_keys()

    loader_cfg["public_key"] = pub_bytes
    loader = ModuleLoader(loader_cfg)

    # Create a legacy manifest (flat JSON, not directory-based)
    manifest = {
        "name": "legacy_mod",
        "version": "1.0.0",
        "entrypoint": "main.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "legacy_mod.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(tmp_path / "main.py", "w", encoding="utf-8") as f:
        f.write("class Module:\n    pass\n")

    # No valid signature exists, so verification should fail
    with pytest.raises(KernelError) as exc:
        loader.load("legacy_mod")
    assert exc.value.code == ErrorCode.MODULE_SIGNATURE_INVALID


def test_load_entrypoint_not_found(loader_cfg: Dict[str, Any], tmp_path: Any) -> None:
    """Covers line 405: entrypoint file does not exist."""
    loader_cfg["modules_path"] = str(tmp_path)
    loader = ModuleLoader(loader_cfg)

    # Create a manifest pointing to a nonexistent entrypoint
    manifest = {
        "name": "ghost_entry",
        "version": "1.0.0",
        "entrypoint": "missing_entry.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "ghost_entry.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    with pytest.raises(KernelError) as exc:
        loader.load("ghost_entry")
    assert exc.value.code == ErrorCode.MODULE_MANIFEST_INVALID
    assert "not found" in str(exc.value)


def test_hot_swap_finalize_old_shutdown(
    loader_cfg: Dict[str, Any], tmp_path: Any
) -> None:
    """Covers lines 497, 500: old instance shutdown + bus unsubscribe during swap."""
    pub_bytes, priv_bytes = generate_test_keys()

    loader_cfg["modules_path"] = str(tmp_path)
    loader_cfg["public_key"] = pub_bytes
    loader = ModuleLoader(loader_cfg)

    # Create a fully valid hardened module for hot-swap
    mod_dir = tmp_path / "swap_mod"
    create_module_files(
        str(mod_dir),
        "swap_mod",
        {
            "version": "2.0.0",
            "events": ["test.event"],
            "events_subscribed": ["test.event"],
        },
        sign=True,
        signing_key=priv_bytes,
    )

    # Seed old state with a module that has shutdown() and events
    old_instance = MagicMock()
    old_instance.healthcheck.return_value = True
    old_instance.shutdown = MagicMock()
    loader.loaded_modules["swap_mod"] = {
        "manifest": {"version": "1.0.0", "events": ["test.event"]},
        "namespace": {},
        "instance": old_instance,
        "version": "1.0.0",
    }

    # Perform hot_swap — the _finalize_hot_swap should call shutdown on old
    loader.hot_swap("swap_mod")

    # Verify old instance shutdown was called
    old_instance.shutdown.assert_called_once()
    # Verify bus unsubscribed old events
    loader_cfg["event_bus"].unsubscribe.assert_called()


def test_hot_swap_finalize_new_subscribe(
    loader_cfg: Dict[str, Any], tmp_path: Any
) -> None:
    """Covers line 525: new instance subscribes to events after hot-swap."""
    pub_bytes, priv_bytes = generate_test_keys()

    loader_cfg["modules_path"] = str(tmp_path)
    loader_cfg["public_key"] = pub_bytes
    loader = ModuleLoader(loader_cfg)

    # Create a valid hardened module with events
    mod_dir = tmp_path / "sub_mod"
    create_module_files(
        str(mod_dir),
        "sub_mod",
        {
            "version": "1.0.0",
            "events": ["sub.event"],
            "events_subscribed": ["sub.event"],
        },
        sign=True,
        signing_key=priv_bytes,
    )

    loader.hot_swap("sub_mod")

    # Verify bus.subscribe was called for the new instance
    loader_cfg["event_bus"].subscribe.assert_called()
