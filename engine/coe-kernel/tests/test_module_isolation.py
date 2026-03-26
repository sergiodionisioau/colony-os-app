"""Tests for Module Isolation (Step 8).

Verifies that modules are restricted from accessing forbidden imports,
sensitive builtins (exec, eval, open), and global namespaces.
"""

import json
import os
import tempfile
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest

from core.errors import KernelError
from core.module_loader.loader import ModuleLoader
from core.module_loader.registry import ModuleRegistry


@pytest.fixture(name="isolation_config")
def fixture_isolation_setup() -> Generator[tuple[str, ModuleLoader], None, None]:
    """Setup for isolation tests."""
    with tempfile.TemporaryDirectory() as td:
        audit_ledger = MagicMock()
        registry = ModuleRegistry(audit_ledger=audit_ledger)
        config = {
            "modules_path": td,
            "forbidden_imports": ["os", "sys", "importlib"],
            "audit_ledger": audit_ledger,
            "registry": registry,
        }
        loader = ModuleLoader(config)
        yield td, loader


def test_module_isolation_breach_denied(isolation_config: Any) -> None:
    """Verifies that a module cannot access restricted builtins or namespaces."""
    td, loader = isolation_config

    module_name = "malicious_module"
    # Create a legacy module that tries to access 'os' via builtins
    with open(os.path.join(td, f"{module_name}.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "name": module_name,
                "version": "1.0.0",
                "entrypoint": f"{module_name}.py",
                "permissions": [],
                "events": [],
                "capabilities": [],
            },
            f,
        )

    malicious_code = """
class Module:
    def initialize(self, bus):
        import os  # Should be blocked by AST
"""
    with open(os.path.join(td, f"{module_name}.py"), "w", encoding="utf-8") as f:
        f.write(malicious_code)

    with pytest.raises(KernelError) as exc:
        loader.load(module_name)
    assert "Forbidden import" in str(exc.value)


def test_module_cannot_access_global_globals(isolation_config: Any) -> None:
    """Verifies that globals() is restricted."""
    td, loader = isolation_config
    module_name = "globals_tester"

    with open(os.path.join(td, f"{module_name}.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "name": module_name,
                "version": "1.0.0",
                "entrypoint": f"{module_name}.py",
                "permissions": [],
                "events": [],
                "capabilities": [],
            },
            f,
        )

    code = """
class Module:
    def initialize(self, bus):
        x = globals()  # Should be restricted builtin
"""
    with open(os.path.join(td, f"{module_name}.py"), "w", encoding="utf-8") as f:
        f.write(code)

    with pytest.raises(KernelError) as exc:
        loader.load(module_name)
    assert "Forbidden instruction" in str(exc.value)
    assert "globals" in str(exc.value).lower()
