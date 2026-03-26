"""Tests for the hardened ModuleValidator.

Verifies schema validation, signature checks, and capability boundaries.
"""

import json
import os
import tempfile
from typing import Any, Tuple, cast
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from core.errors import KernelError
from core.module_loader.module_validator import ModuleValidator
from core.module_loader.signature import compute_module_hash
from tests.conftest import create_module_files, COMMON_MANIFEST


@pytest.fixture(name="validator_config")
def fixture_validator_config() -> Tuple[str, MagicMock]:
    """Fixture to setup validator with schemas."""
    schemas_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "schemas")
    )
    audit_ledger = MagicMock()
    return schemas_path, audit_ledger


def test_full_validation_pipeline_success(validator_config: Any) -> None:
    """Verifies that a perfectly structured and signed module passes (§6.138)."""
    schemas_path, audit_ledger = validator_config
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_bytes = priv_key.public_key().public_bytes(
        encoding=cast(Any, serialization.Encoding.Raw),
        format=cast(Any, serialization.PublicFormat.Raw),
    )

    validator = ModuleValidator(
        schemas_path=schemas_path,
        audit_ledger=audit_ledger,
        public_key=pub_bytes,
    )

    with tempfile.TemporaryDirectory() as td:
        # manifest already has events_subscribed/emitted and resource_budget in conftest
        create_module_files(td, "valid_module", COMMON_MANIFEST)

        # Sign
        module_hash = compute_module_hash(td)
        signature = priv_key.sign(module_hash)
        with open(os.path.join(td, "signature.sig"), "wb") as f:
            f.write(signature)

        # Run validation
        val_manifest = validator.validate(td)
        assert val_manifest["name"] == "valid_module"
        assert audit_ledger.append.called


def test_validation_failure_missing_structural_files(validator_config: Any) -> None:
    """Verifies rejection on missing any of the 7 mandatory files (§3.82)."""
    schemas_path, audit_ledger = validator_config
    validator = ModuleValidator(schemas_path=schemas_path, audit_ledger=audit_ledger)

    with tempfile.TemporaryDirectory() as td:
        # Create incomplete structure
        os.makedirs(td, exist_ok=True)
        with open(os.path.join(td, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "fail"}, f)

        with pytest.raises(KernelError) as exc:
            validator.validate(td)
        assert "Structural violation" in str(exc.value.message)


def test_validation_failure_unsigned_module(validator_config: Any) -> None:
    """Verifies rejection of unsigned modules under zero-tolerance (§14.309)."""
    schemas_path, audit_ledger = validator_config
    private_key = ed25519.Ed25519PrivateKey.generate()

    # Validator WITH public key
    validator = ModuleValidator(
        schemas_path=schemas_path,
        audit_ledger=audit_ledger,
        public_key=b"some_key_bytes",
    )

    with tempfile.TemporaryDirectory() as td:
        create_module_files(td, "unsigned", {})
        # Sign
        module_hash = compute_module_hash(td)
        signature = private_key.sign(module_hash)
        with open(os.path.join(td, "signature.sig"), "wb") as f:
            f.write(signature)

        with pytest.raises(KernelError) as exc:
            validator.validate(td)
        assert "Signature verification failed" in str(exc.value.message)


def test_validation_failure_no_system_key(validator_config: Any) -> None:
    """Verifies rejection when no system key is configured for verification."""
    schemas_path, audit_ledger = validator_config
    validator = ModuleValidator(schemas_path=schemas_path, audit_ledger=audit_ledger)

    with tempfile.TemporaryDirectory() as td:
        create_module_files(td, "no_key", {})

        with pytest.raises(KernelError) as exc:
            validator.validate(td)
        assert "Zero-Tolerance: No system public key" in str(exc.value.message)


def test_validation_failure_invalid_schema_in_manifest(validator_config: Any) -> None:
    """Verifies rejection on schema violation in manifest.json (§4)."""
    schemas_path, audit_ledger = validator_config
    validator = ModuleValidator(schemas_path=schemas_path, audit_ledger=audit_ledger)

    with tempfile.TemporaryDirectory() as td:
        # Create manifest missing required Phase 5 fields
        # (author, resource_budget, etc.)
        create_module_files(td, "invalid", {})
        with open(os.path.join(td, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "invalid", "version": "1.0.0"}, f)

        with pytest.raises(KernelError) as exc:
            validator.validate(td)
        assert "Schema violation" in str(exc.value.message)
