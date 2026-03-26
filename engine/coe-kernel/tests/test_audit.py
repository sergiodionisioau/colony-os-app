"""Strict TDD suite for the Audit Ledger.

Verifies tamper-evident log capabilities and hash chaining.
"""

import json
import os
from typing import Any

import pytest

from core.errors import ErrorCode, KernelError
from core.audit.ledger import AuditLedger


@pytest.fixture(name="audit_ledger")
def audit_ledger_fixture(tmp_path: Any) -> AuditLedger:
    """Fixture providing an ephemeral AuditLedger."""
    storage_path = str(tmp_path / "audit.log")
    return AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")


def test_append_creates_hash_chain(audit_ledger: AuditLedger) -> None:
    """Test Set 4: Hash chain validated."""
    entry1 = audit_ledger.append("admin_1", "initialize", "SUCCESS", {})
    entry2 = audit_ledger.append("agent_1", "task_start", "SUCCESS", {})

    assert entry1.entry_hash == entry2.previous_hash


def test_tamper_detects_hash_mismatch(audit_ledger: AuditLedger) -> None:
    """Test Set 4: Tamper with log -> hash mismatch detected."""
    audit_ledger.append("admin_1", "initialize", "SUCCESS", {})
    audit_ledger.append("agent_1", "task_start", "SUCCESS", {})

    assert audit_ledger.verify_integrity() is True

    # Simulate tampering by manually writing to the backend storage
    with open(audit_ledger.storage_path, "a", encoding="utf-8") as f:
        f.write("malicious payload")

    with pytest.raises(KernelError) as exc_info:
        audit_ledger.verify_integrity()

    assert exc_info.value.code == ErrorCode.AUDIT_INTEGRITY_VIOLATION


def test_load_from_disk(tmp_path: Any) -> None:
    """Test loading existing entries from disk."""
    storage_path = str(tmp_path / "audit_load.log")
    ledger1 = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    entry = ledger1.append("admin_1", "action", "SUCCESS", {"key": "val"})

    # Create new instance pointing to same file
    ledger2 = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    assert len(list(ledger2.iterate())) == 1
    loaded_entry = list(ledger2.iterate())[0]
    assert loaded_entry.entry_id == entry.entry_id
    assert loaded_entry.entry_hash == entry.entry_hash


def test_integrity_missing_file(tmp_path: Any) -> None:
    """Test verify_integrity when file is missing but memory state exists."""
    storage_path = str(tmp_path / "missing.log")
    ledger = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    ledger.append("admin_1", "action", "SUCCESS", {})

    os.remove(storage_path)

    with pytest.raises(KernelError) as exc_info:
        ledger.verify_integrity()
    assert exc_info.value.code == ErrorCode.AUDIT_INTEGRITY_VIOLATION
    assert "Log file missing" in str(exc_info.value.message)


def test_integrity_length_mismatch(tmp_path: Any) -> None:
    """Test verify_integrity when disk count mismatch memory count."""
    storage_path = str(tmp_path / "mismatch.log")
    ledger = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    ledger.append("admin_1", "action1", "SUCCESS", {})
    ledger.append("admin_1", "action2", "SUCCESS", {})

    # Remove one line from file
    with open(storage_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(storage_path, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])

    with pytest.raises(KernelError) as exc_info:
        ledger.verify_integrity()
    assert exc_info.value.code == ErrorCode.AUDIT_INTEGRITY_VIOLATION
    assert "Log length mismatch" in str(exc_info.value.message)


def test_integrity_broken_chain(tmp_path: Any) -> None:
    """Test verify_integrity when hash chain is broken."""
    storage_path = str(tmp_path / "broken.log")
    ledger = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    ledger.append("admin_1", "action1", "SUCCESS", {})
    ledger.append("admin_1", "action2", "SUCCESS", {})

    # Modify previous_hash of second entry
    with open(storage_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    data = json.loads(lines[1])
    data["previous_hash"] = "tampered"
    lines[1] = json.dumps(data) + "\n"
    with open(storage_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    with pytest.raises(KernelError) as exc_info:
        ledger.verify_integrity()
    assert exc_info.value.code == ErrorCode.AUDIT_CHAIN_BROKEN
    assert "broken" in str(exc_info.value.message)


def test_integrity_payload_tamper(tmp_path: Any) -> None:
    """Test verify_integrity when payload is tampered."""
    storage_path = str(tmp_path / "tamper_payload.log")
    ledger = AuditLedger(storage_path=storage_path, genesis_constant="TEST_GENESIS")
    ledger.append("admin_1", "action", "SUCCESS", {"amount": 100})

    # Tamper with metadata
    with open(storage_path, "r", encoding="utf-8") as f:
        line = f.read()
    data = json.loads(line)
    data["metadata"]["amount"] = 200
    with open(storage_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

    with pytest.raises(KernelError) as exc_info:
        ledger.verify_integrity()
    assert exc_info.value.code == ErrorCode.AUDIT_INTEGRITY_VIOLATION
    assert "tampered" in str(exc_info.value.message)


def test_iterate_filter(audit_ledger: AuditLedger) -> None:
    """Test iterating with action filter."""
    audit_ledger.append("admin_1", "login", "SUCCESS", {})
    audit_ledger.append("admin_1", "logout", "SUCCESS", {})

    logins = list(audit_ledger.iterate(action="login"))
    assert len(logins) == 1
    assert logins[0].action == "login"

    all_entries = list(audit_ledger.iterate())
    assert len(all_entries) == 2


# --- Aliases conforming strictly to project_plan.md requirements ---
test_tamper_with_log_hash_mismatch_detected = test_tamper_detects_hash_mismatch
test_hash_chain_validated = test_append_creates_hash_chain
test_missing_entry_fails_integrity_check = test_integrity_length_mismatch
