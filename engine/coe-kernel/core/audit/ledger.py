"""Audit Ledger implementation.

Provides immutable, cryptographically-linked recording of all kernel mutations.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, Iterator, List, Optional
import uuid

from core.errors import ErrorCode, KernelError
from core.interfaces import AuditLedgerInterface
from core.types import AuditEntry


class AuditLedger(AuditLedgerInterface):
    """Enforces cryptographic accountability across the trust boundary."""

    def __init__(
        self,
        storage_path: str,
        genesis_constant: str,
        segment_max_entries: int = 100000,
    ) -> None:
        """Initialize the ledger and sequence from disk."""
        self.storage_path = storage_path
        self._genesis = genesis_constant
        self.segment_max_entries = segment_max_entries
        self._entries: list[AuditEntry] = []
        self._last_hash = self._hash_payload(self._genesis)
        self._current_segment_index = 0
        self._current_segment_count = 0
        self._load_from_disk()

    def _get_segment_path(self, index: int) -> str:
        """Returns the active segment path.
        Supports both a flat file or a directory structure.
        """
        if not os.path.exists(self.storage_path) or os.path.isfile(self.storage_path):
            if index == 0:
                return self.storage_path
            return f"{self.storage_path}.{index:03d}"
        return os.path.join(self.storage_path, f"audit_{index:06d}.json")

    def _hash_payload(self, payload: str) -> str:
        """Creates a deterministic SHA-256 hash."""
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _deserialize_entry(self, data: Dict[str, Any]) -> AuditEntry:
        return AuditEntry(
            entry_id=uuid.UUID(data["entry_id"]),
            timestamp=data["timestamp"],
            actor_id=data["actor_id"],
            action=data["action"],
            status=data["status"],
            metadata=data["metadata"],
            previous_hash=data["previous_hash"],
            entry_hash=data["entry_hash"],
        )

    def _load_from_disk(self) -> None:
        """Loads state from persistent storage."""
        segments = []
        if os.path.isfile(self.storage_path):
            segments.append(self.storage_path)
            idx = 1
            while os.path.isfile(f"{self.storage_path}.{idx:03d}"):
                segments.append(f"{self.storage_path}.{idx:03d}")
                idx += 1
        elif os.path.isdir(self.storage_path):
            segments = [
                os.path.join(self.storage_path, f)
                for f in os.listdir(self.storage_path)
                if f.startswith("audit_") and f.endswith(".json")
            ]
            segments.sort()

        if not segments:
            return

        for segment_idx, filepath in enumerate(segments):
            self._current_segment_index = segment_idx
            self._current_segment_count = 0
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data["action"] == "audit.segment_seal":
                            self._last_hash = data["entry_hash"]
                            continue

                        entry = self._deserialize_entry(data)
                        self._entries.append(entry)
                        self._last_hash = entry.entry_hash
                        self._current_segment_count += 1

    def _serialize_entry(self, entry: AuditEntry) -> str:
        data = {
            "entry_id": str(entry.entry_id),
            "timestamp": entry.timestamp,
            "actor_id": entry.actor_id,
            "action": entry.action,
            "status": entry.status,
            "metadata": entry.metadata,
            "previous_hash": entry.previous_hash,
            "entry_hash": entry.entry_hash,
        }
        return json.dumps(data)

    def _write_to_disk(self, entry: AuditEntry) -> None:
        """Persists a new entry sequentially."""
        filepath = self._get_segment_path(self._current_segment_index)

        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(self._serialize_entry(entry) + "\n")

        self._current_segment_count += 1

        if self._current_segment_count >= self.segment_max_entries:
            self._seal_and_rotate()

    def _seal_and_rotate(self) -> None:
        seal_hash = self._hash_payload(self._last_hash + "SEALED")
        seal_data = {
            "entry_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_id": "KERNEL",
            "action": "audit.segment_seal",
            "status": "SUCCESS",
            "metadata": {"sealed_hash": self._last_hash},
            "previous_hash": self._last_hash,
            "entry_hash": seal_hash,
        }
        filepath = self._get_segment_path(self._current_segment_index)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(seal_data) + "\n")

        self._current_segment_index += 1
        self._current_segment_count = 0
        self._last_hash = seal_hash

        # Write the bridge entry directly, bypassing the rotation check to
        # prevent infinite recursion when segment_max_entries is very small.
        bridge_id = uuid.uuid4()
        bridge_ts = datetime.now(timezone.utc).isoformat()
        bridge_meta = {"sealed_hash": seal_hash}
        bridge_meta_str = json.dumps(bridge_meta, sort_keys=True)
        bridge_payload = (
            f"{bridge_id}{bridge_ts}KERNEL"
            f"audit.segment_bridge"
            f"SUCCESS{bridge_meta_str}{self._last_hash}"
        )
        bridge_hash = self._hash_payload(bridge_payload)

        bridge_entry = AuditEntry(
            entry_id=bridge_id,
            timestamp=bridge_ts,
            actor_id="KERNEL",
            action="audit.segment_bridge",
            status="SUCCESS",
            metadata=bridge_meta,
            previous_hash=self._last_hash,
            entry_hash=bridge_hash,
        )
        self._entries.append(bridge_entry)
        self._last_hash = bridge_hash
        self._write_to_disk(bridge_entry)

    def append(
        self, actor_id: str, action: str, status: str, metadata: Dict[str, Any]
    ) -> AuditEntry:
        """Appends a new immutable record linked to the previous chain hash."""
        entry_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc).isoformat()

        meta_str = json.dumps(metadata, sort_keys=True)
        payload = (
            f"{entry_id}{timestamp}{actor_id}{action}"
            f"{status}{meta_str}{self._last_hash}"
        )
        new_hash = self._hash_payload(payload)

        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            actor_id=actor_id,
            action=action,
            status=status,
            metadata=metadata,
            previous_hash=self._last_hash,
            entry_hash=new_hash,
        )

        self._entries.append(entry)
        self._last_hash = new_hash
        self._write_to_disk(entry)

        return entry

    def _resolve_segments(self) -> List[str]:
        """Determines the list of segment file paths for integrity verification."""
        segments: List[str] = []
        if os.path.isfile(self.storage_path):
            segments.append(self.storage_path)
            idx = 1
            while os.path.isfile(f"{self.storage_path}.{idx:03d}"):
                segments.append(f"{self.storage_path}.{idx:03d}")
                idx += 1
        elif os.path.isdir(self.storage_path):
            segments = [
                os.path.join(self.storage_path, f)
                for f in os.listdir(self.storage_path)
                if f.startswith("audit_") and f.endswith(".json")
            ]
            segments.sort()
        return segments

    def _load_disk_entries(self, segments: List[str]) -> List[Dict[str, Any]]:
        """Reads and parses all entries from segment files."""
        disk_entries: List[Dict[str, Any]] = []
        for filepath in segments:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                disk_entries.append(json.loads(line))
                            except json.JSONDecodeError as exc:
                                raise KernelError(
                                    code=ErrorCode.AUDIT_INTEGRITY_VIOLATION,
                                    message=(
                                        "Corrupted non-JSON payload " "detected in log."
                                    ),
                                ) from exc
            except FileNotFoundError:
                pass
        return disk_entries

    def verify_integrity(self) -> bool:
        """Validates the cryptographic hash chain of the entire ledger
        against disk.
        """
        current_hash = self._hash_payload(self._genesis)

        segments = self._resolve_segments()
        if not segments and self._entries:
            raise KernelError(
                code=ErrorCode.AUDIT_INTEGRITY_VIOLATION, message="Log file missing."
            )

        disk_entries = self._load_disk_entries(segments)

        mem_idx = 0
        for _, data in enumerate(disk_entries):
            if data["previous_hash"] != current_hash:
                raise KernelError(
                    code=ErrorCode.AUDIT_CHAIN_BROKEN,
                    message=f"Hash chain broken at entry {data['entry_id']}",
                )

            if data["action"] == "audit.segment_seal":
                expected_hash = self._hash_payload(current_hash + "SEALED")
                if data["entry_hash"] != expected_hash:
                    raise KernelError(
                        code=ErrorCode.AUDIT_INTEGRITY_VIOLATION,
                        message=f"Seal payload tampered at entry {data['entry_id']}",
                    )
                current_hash = expected_hash
                continue

            mem_entry = self._entries[mem_idx]

            meta_str = json.dumps(data["metadata"], sort_keys=True)
            payload = (
                f"{data['entry_id']}{data['timestamp']}{data['actor_id']}"
                f"{data['action']}{data['status']}{meta_str}{current_hash}"
            )
            expected_hash = self._hash_payload(payload)

            if (
                data["entry_hash"] != expected_hash
                or mem_entry.entry_hash != expected_hash
            ):
                raise KernelError(
                    code=ErrorCode.AUDIT_INTEGRITY_VIOLATION,
                    message=f"Payload tampered at entry {data['entry_id']}",
                )

            current_hash = expected_hash
            mem_idx += 1

        if mem_idx != len(self._entries):
            raise KernelError(
                code=ErrorCode.AUDIT_INTEGRITY_VIOLATION,
                message="Log length mismatch.",
            )

        return True

    def iterate(self, action: Optional[str] = None) -> Iterator[AuditEntry]:
        """Provides an ordered iterator over the ledger entries."""
        for entry in self._entries:
            if action is None or entry.action == action:
                yield entry
