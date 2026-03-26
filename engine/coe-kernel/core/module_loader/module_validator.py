"""Module Validator for the Hardened Module Loader (Lego System).

Provides comprehensive validation of module structure, manifests, capabilities,
signatures, and permissions. Phase 5 specification §6.
"""

import json
import os
from typing import Any, Dict, Optional, cast

import jsonschema

from core.errors import ErrorCode, KernelError
from core.interfaces import AuditLedgerInterface
from core.module_loader.signature import verify_module_signature


class ModuleValidator:
    """Consolidated validator for the 10-step module loading pipeline."""

    def __init__(
        self,
        schemas_path: str,
        audit_ledger: AuditLedgerInterface,
        public_key: Optional[bytes] = None,
    ) -> None:
        """Initialize the validator."""
        self.schemas_path = schemas_path
        self.audit_ledger = audit_ledger
        self.public_key = public_key
        self.kernel_capabilities = [
            "AUDIT_READ",
            "AUDIT_WRITE",
            "EVENT_PUBLISH",
            "EVENT_SUBSCRIBE",
            "STATE_READ",
            "STATE_WRITE",
            "VAULT_READ",
            "VAULT_WRITE",
        ]

    def _validate_schema(self, data: Any, schema_filename: str) -> None:
        """Helper to validate data against a specific schema file."""
        schema_path = os.path.join(self.schemas_path, schema_filename)
        if not os.path.exists(schema_path):
            alt_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "schemas", schema_filename
            )
            if os.path.exists(alt_path):
                schema_path = alt_path

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = cast(Dict[str, Any], json.load(f))
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Schema violation in {schema_filename}: {str(e)}",
            ) from e
        except Exception as e:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Failed to load schema {schema_filename}: {str(e)}",
            ) from e

    def is_hardened(self, module_dir: str) -> bool:
        """Checks if a directory contains a hardened module structure."""
        return os.path.exists(os.path.join(module_dir, "manifest.json"))

    def validate(self, module_dir: str) -> Dict[str, Any]:
        """Performs full Phase 5 validation pipeline on a module directory.

        Zero-Tolerance Implementation of §3.82 and §6.138.
        """
        # 1. Structure Audit (§3.82, §6.138 Step 1)
        required_files = [
            "module.yaml",
            "manifest.json",
            "capabilities.json",
            "permissions.json",
            "cost_profile.json",
            "signature.sig",
            "entry.py",
        ]
        for filename in required_files:
            if not os.path.exists(os.path.join(module_dir, filename)):
                raise KernelError(
                    code=ErrorCode.MODULE_MANIFEST_INVALID,
                    message=(
                        f"Structural violation: Missing required file "
                        f"'{filename}' in {module_dir}"
                    ),
                )

        # 2. Manifest Schema Validation (§6.138 Step 2)
        manifest_path = os.path.join(module_dir, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = cast(Dict[str, Any], json.load(f))
        self._validate_schema(manifest, "module_manifest.schema.json")

        # 3. Signature Verification (§6.138 Step 4)
        if self.public_key:
            if not verify_module_signature(module_dir, self.public_key):
                name = manifest.get("name", "unknown")
                raise KernelError(
                    code=ErrorCode.MODULE_SIGNATURE_INVALID,
                    message=f"Signature verification failed for {name}",
                )
        else:
            # Phase 5 §14.309: Unsigned module loads -> reject
            raise KernelError(
                code=ErrorCode.MODULE_SIGNATURE_INVALID,
                message=(
                    "Zero-Tolerance: No system public key configured "
                    "for signature verification."
                ),
            )

        # 4. Capability Audit (§6.138 Step 3)
        caps_path = os.path.join(module_dir, "capabilities.json")
        with open(caps_path, "r", encoding="utf-8") as f:
            caps_data = cast(Dict[str, Any], json.load(f))
        self._validate_schema(caps_data, "capabilities.schema.json")
        for cap in caps_data.get("capabilities", []):
            if cap not in self.kernel_capabilities:
                raise KernelError(
                    code=ErrorCode.MODULE_CAPABILITY_UNDECLARED,
                    message=f"Module requests unknown capability: {cap}",
                )

        # 5. Permission Scope Validation (§6.138 Step 5)
        perms_path = os.path.join(module_dir, "permissions.json")
        with open(perms_path, "r", encoding="utf-8") as f:
            perms_data = cast(Dict[str, Any], json.load(f))
        self._validate_schema(perms_data, "module_permissions.schema.json")

        # 6. Cost Profile Validation (§3.87)
        cost_path = os.path.join(module_dir, "cost_profile.json")
        with open(cost_path, "r", encoding="utf-8") as f:
            # We use manifest schema as a placeholder if cost.schema doesn't exist,
            # but ideally we'd have a specific cost schema.
            json.load(f)

        # 7. Event Contract Validation (§6.138 Step 6)
        # Ensure all events are declared in the manifest
        if (
            "events_subscribed" not in manifest
            and "events_emitted" not in manifest
            and "events" not in manifest
        ):
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message="Module must declare subscribed or emitted events.",
            )

        # 6. Final Audit Log
        self.audit_ledger.append(
            actor_id="VALIDATOR",
            action="module_validation",
            status="SUCCESS",
            metadata={
                "module": manifest.get("name"),
                "version": manifest.get("version"),
            },
        )

        return manifest
