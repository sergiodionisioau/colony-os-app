"""Final missing coverage tests for phase 5 loader gaps."""

import json
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from core.errors import ErrorCode, KernelError
from core.module_loader.loader import ModuleEventProxy, ModuleLoader
from core.module_loader.module_validator import ModuleValidator
from tests.conftest import COMMON_MANIFEST


def test_proxy_subscribe() -> None:
    """Covers line 36 in loader.py."""
    bus = MagicMock()
    proxy = ModuleEventProxy(bus, "KERNEL")
    proxy.subscribe("test.event", MagicMock(), "sub_id")
    bus.subscribe.assert_called_once()


def test_exec_module_failure(tmp_path: Any) -> None:
    """Covers lines 270-271 in loader.py."""
    mod_dir = tmp_path / "bad_mod"
    mod_dir.mkdir()
    entry = mod_dir / "entry.py"
    entry.write_text("raise ValueError('Syntax or runtime error')", encoding="utf-8")

    loader = ModuleLoader(
        {
            "modules_path": str(tmp_path),
            "forbidden_imports": [],
            "audit_ledger": MagicMock(),
            "registry": MagicMock(),
        }
    )
    with pytest.raises(KernelError) as exc_info:
        # pylint: disable=protected-access
        loader._execute_in_sandbox("bad_mod", str(entry))
    assert exc_info.value.code == ErrorCode.MODULE_EXECUTION_FAILED


def test_legacy_signature_verification_failure(tmp_path: Any) -> None:
    """Covers line 399 in loader.py."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        cast(Any, Encoding.Raw), cast(Any, PublicFormat.Raw)
    )

    loader = ModuleLoader(
        {
            "modules_path": str(tmp_path),
            "public_key": pub_bytes,
            "forbidden_imports": [],
            "audit_ledger": MagicMock(),
            "registry": MagicMock(),
        }
    )

    manifest = dict(COMMON_MANIFEST)
    manifest["name"] = "legacy_mod"
    manifest["events"] = []

    man_path = tmp_path / "legacy_mod.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Create invalid sig file so verify_module_signature returns False
    sig_path = tmp_path / "signature.sig"
    sig_path.write_bytes(b"invalid_signature_bytes")

    with patch.object(loader.validator, "_validate_schema"):
        with pytest.raises(KernelError) as exc_info:
            loader.load("legacy_mod")
    assert exc_info.value.code == ErrorCode.MODULE_SIGNATURE_INVALID


def test_validator_missing_events_declaration(tmp_path: Any) -> None:
    """Covers line 152 in module_validator.py."""
    validator = ModuleValidator("schemas_dummy", MagicMock())

    mod_dir = tmp_path / "mod_missing_events"
    mod_dir.mkdir()

    # Touch required files
    for req_file in ("module.yaml", "capabilities.json", "permissions.json"):
        (mod_dir / req_file).write_text("{}", encoding="utf-8")
    for req_file in ("cost_profile.json", "signature.sig", "entry.py"):
        (mod_dir / req_file).write_text("{}", encoding="utf-8")

    (mod_dir / "manifest.json").write_text(
        json.dumps({"name": "missing_events", "version": "1.0"}), encoding="utf-8"
    )

    validator.public_key = b"dummy"

    with patch(
        "core.module_loader.module_validator.verify_module_signature", return_value=True
    ):
        with patch.object(validator, "_validate_schema"):
            with pytest.raises(KernelError) as exc_info:
                validator.validate(str(mod_dir))
            assert exc_info.value.code == ErrorCode.MODULE_MANIFEST_INVALID
            assert "subscribed or emitted events" in exc_info.value.message
