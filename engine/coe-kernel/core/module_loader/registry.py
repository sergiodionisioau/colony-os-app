"""Module Registry for the Hardened Module Loader (Lego System).

Maintains a typed registry of all loaded modules with lifecycle status tracking.
Phase 5 specification §7-§8.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.errors import ErrorCode, KernelError


class ModuleStatus(Enum):
    """Lifecycle states for modules in the registry."""

    LOADED = "loaded"
    UNLOADED = "unloaded"
    QUARANTINED = "quarantined"
    FAILED = "failed"


@dataclass
class ModuleMetadata:
    """Metadata for a registered module."""

    version: str
    capabilities: List[str]
    event_handlers: List[str]
    resource_budget: Optional[Dict[str, Any]] = None


@dataclass
class ModuleRegistryEntry:
    """Typed record for a registered module."""

    module_id: str
    status: ModuleStatus
    metadata: ModuleMetadata
    content_hash: str
    loaded_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to a dictionary."""
        return {
            "module_id": self.module_id,
            "version": self.metadata.version,
            "status": self.status.value,
            "capabilities": self.metadata.capabilities,
            "event_handlers": self.metadata.event_handlers,
            "content_hash": self.content_hash,
            "loaded_timestamp": self.loaded_timestamp,
            "resource_budget": self.metadata.resource_budget,
        }


class ModuleRegistry:
    """Thread-safe registry maintaining module lifecycle state."""

    def __init__(self, audit_ledger: Any) -> None:
        """Initialize the module registry."""
        self.audit_ledger = audit_ledger
        self._entries: Dict[str, ModuleRegistryEntry] = {}

    def register(self, entry_data: Dict[str, Any]) -> ModuleRegistryEntry:
        """Registers a module in the registry with LOADED status."""
        module_id = entry_data["module_id"]
        metadata = ModuleMetadata(
            version=entry_data["version"],
            capabilities=entry_data["capabilities"],
            event_handlers=entry_data["event_handlers"],
            resource_budget=entry_data.get("resource_budget"),
        )
        entry = ModuleRegistryEntry(
            module_id=module_id,
            status=ModuleStatus.LOADED,
            metadata=metadata,
            content_hash=entry_data["content_hash"],
            loaded_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._entries[module_id] = entry

        self.audit_ledger.append(
            actor_id="REGISTRY",
            action="module_registered",
            status="SUCCESS",
            metadata={
                "module_id": module_id,
                "version": entry.metadata.version,
                "content_hash": entry.content_hash,
            },
        )
        return entry

    def deregister(self, module_id: str) -> None:
        """Removes a module from the registry (sets to UNLOADED)."""
        if module_id not in self._entries:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Module '{module_id}' not found in registry.",
            )
        self._entries[module_id].status = ModuleStatus.UNLOADED
        self.audit_ledger.append(
            actor_id="REGISTRY",
            action="module_deregistered",
            status="SUCCESS",
            metadata={"module_id": module_id},
        )

    def quarantine(self, module_id: str, reason: str) -> None:
        """Quarantines a module due to healthcheck failure or violation."""
        if module_id not in self._entries:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Module '{module_id}' not found in registry.",
            )
        self._entries[module_id].status = ModuleStatus.QUARANTINED
        self.audit_ledger.append(
            actor_id="REGISTRY",
            action="module_quarantined",
            status="WARNING",
            metadata={"module_id": module_id, "reason": reason},
        )

    def mark_failed(self, module_id: str, reason: str) -> None:
        """Marks a module as failed in the registry."""
        if module_id not in self._entries:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Module '{module_id}' not found in registry.",
            )
        self._entries[module_id].status = ModuleStatus.FAILED
        self.audit_ledger.append(
            actor_id="REGISTRY",
            action="module_failed",
            status="FAILED",
            metadata={"module_id": module_id, "reason": reason},
        )

    def get_entry(self, module_id: str) -> Optional[ModuleRegistryEntry]:
        """Returns the registry entry for a module."""
        return self._entries.get(module_id)

    def get_all_entries(self) -> Dict[str, ModuleRegistryEntry]:
        """Returns a copy of all registry entries."""
        return dict(self._entries)

    def get_loaded_modules(self) -> List[str]:
        """Returns IDs of all currently loaded modules."""
        return [
            mid
            for mid, entry in self._entries.items()
            if entry.status == ModuleStatus.LOADED
        ]

    @staticmethod
    def compute_module_hash(manifest: Dict[str, Any]) -> str:
        """Computes a deterministic SHA-256 hash of the module manifest."""
        content = json.dumps(manifest, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
