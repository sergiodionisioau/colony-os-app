"""Tests for Module Lifecycle (Versioning, Rollback, Healthcheck)."""

import json
from typing import Any, Dict
import pytest

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleLoader


@pytest.fixture(name="loader_instance")
def loader_instance_fixture(mock_loader_config: Dict[str, Any]) -> ModuleLoader:
    """Fixture providing a clean ModuleLoader instance."""
    return ModuleLoader(mock_loader_config)


def test_module_versioning_and_rollback(
    loader_instance: ModuleLoader, tmp_path: Any
) -> None:
    """Test module versioning constraints and rollback functionality."""
    # 1. Setup Module v1
    manifest_v1 = {
        "name": "test_mod",
        "version": "1.0.0",
        "kernel_compatibility": "1.0.0",
        "entrypoint": "mod.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "mod_v1.json", "w", encoding="utf-8") as f:
        json.dump(manifest_v1, f)
    with open(tmp_path / "mod.py", "w", encoding="utf-8") as f:
        f.write("class Module:\n    def healthcheck(self): return 'ok'\n")

    # Use symlink or just copy to simulate update
    with open(tmp_path / "test_mod.json", "w", encoding="utf-8") as f:
        json.dump(manifest_v1, f)

    loader_instance.load("test_mod")
    state = loader_instance.get_module_state("test_mod")
    assert state is not None
    assert state["version"] == "1.0.0"

    # 2. Update to v2 (incompatible)
    manifest_v2 = {
        "name": "test_mod",
        "version": "2.0.0",
        "kernel_compatibility": "2",  # Incompatible with 1.0.0
        "entrypoint": "mod.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "test_mod.json", "w", encoding="utf-8") as f:
        json.dump(manifest_v2, f)

    # This should fail compatibility but NOT overwrite the backup
    with pytest.raises(KernelError) as exc_info:
        loader_instance.load("test_mod")
    assert exc_info.value.code == ErrorCode.MODULE_MANIFEST_INVALID

    # Still v1
    state = loader_instance.get_module_state("test_mod")
    assert state is not None
    assert state["version"] == "1.0.0"
    assert loader_instance.get_backup_state("test_mod") is None

    # 3. Update to v2 (compatible) and then rollback
    manifest_v2_compat = {
        "name": "test_mod",
        "version": "2.0.0",
        "kernel_compatibility": "1.0.0",
        "entrypoint": "mod_v2.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "mod_v2.py", "w", encoding="utf-8") as f:
        f.write("class Module:\n    def healthcheck(self): return 'v2_ok'\n")
    with open(tmp_path / "test_mod.json", "w", encoding="utf-8") as f:
        json.dump(manifest_v2_compat, f)

    loader_instance.load("test_mod")
    state = loader_instance.get_module_state("test_mod")
    assert state is not None
    assert state["version"] == "2.0.0"
    backup = loader_instance.get_backup_state("test_mod")
    assert backup is not None
    assert backup["version"] == "1.0.0"

    # 4. Rollback
    loader_instance.rollback("test_mod")
    state = loader_instance.get_module_state("test_mod")
    assert state is not None
    assert state["version"] == "1.0.0"
    assert loader_instance.get_backup_state("test_mod") is None


def test_module_healthcheck_execution(
    loader_instance: ModuleLoader, tmp_path: Any
) -> None:
    """Test that module healthcheck method is correctly identified and executed."""
    manifest = {
        "name": "health_mod",
        "version": "1.0.0",
        "kernel_compatibility": "*",
        "entrypoint": "health_mod.py",
        "permissions": [],
        "events": [],
        "capabilities": [],
    }
    with open(tmp_path / "health_mod.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(tmp_path / "health_mod.py", "w", encoding="utf-8") as f:
        f.write("class Module:\n    def healthcheck(self):\n        return 'healthy'\n")

    loader_instance.load("health_mod")
    state = loader_instance.get_module_state("health_mod")
    assert state is not None
    instance = state["instance"]
    assert instance is not None
    assert instance.healthcheck() == "healthy"
