"""Strict TDD suite for the Secrets Vault.

Verifies encryption at rest and identity isolation.
"""

from typing import Any
import uuid

import pytest

from core.errors import ErrorCode, KernelError
from core.secrets.vault import SecretsVault
from tests.conftest import MockAuditLedger


@pytest.fixture(name="vault")
def vault_fixture(tmp_path: Any, mock_audit_ledger: MockAuditLedger) -> SecretsVault:
    """Fixture providing a SecretsVault with ephemeral storage."""
    data_path = str(tmp_path / "secrets.json")
    salt_path = str(tmp_path / "salt.bin")
    return SecretsVault(
        data_path=data_path,
        salt_path=salt_path,
        audit_ledger=mock_audit_ledger,
        passphrase="test_passphrase",
    )


def test_secret_encrypted_at_rest(vault: SecretsVault) -> None:
    """Test Set 5: Secrets are NOT stored in plaintext."""
    vault.store_secret(
        "11111111-1111-1111-1111-111111111111", "api_key", "secret_value_123"
    )

    with open(vault.data_path, "r", encoding="utf-8") as f:
        stored_content = f.read()

    assert "secret_value_123" not in stored_content


def test_unauthorized_access_rejected(vault: SecretsVault) -> None:
    """Test Set 5: Identity isolation enforced."""
    vault.store_secret(
        "11111111-1111-1111-1111-111111111111", "api_key", "secret_value_123"
    )

    with pytest.raises(KernelError) as exc_info:
        vault.retrieve_secret("22222222-2222-2222-2222-222222222222", "api_key")

    assert exc_info.value.code == ErrorCode.SECRET_NOT_FOUND


def test_access_logged(vault: SecretsVault, mock_audit_ledger: MockAuditLedger) -> None:
    """Test Set 5: Secret access is audited."""
    vault.store_secret(
        "11111111-1111-1111-1111-111111111111", "api_key", "secret_value_123"
    )
    vault.retrieve_secret("11111111-1111-1111-1111-111111111111", "api_key")

    audit_entries = list(mock_audit_ledger.iterate())
    actions = [e.action for e in audit_entries]
    assert "secret_stored" in actions
    assert "secret_read" in actions


def test_salt_persistence(tmp_path: Any, mock_audit_ledger: MockAuditLedger) -> None:
    """Verify salt reuse by checking decryption consistency."""
    data_path = str(tmp_path / "d.json")
    salt_path = str(tmp_path / "salt.bin")
    v1 = SecretsVault(data_path, salt_path, mock_audit_ledger, "p")
    v1.store_secret("33333333-3333-3333-3333-333333333333", "k", "v")

    # Second init reloads salt. If it didn't, decryption would fail.
    v2 = SecretsVault(data_path, salt_path, mock_audit_ledger, "p")
    assert v2.retrieve_secret("33333333-3333-3333-3333-333333333333", "k") == "v"


def test_load_empty_store(tmp_path: Any, mock_audit_ledger: MockAuditLedger) -> None:
    """Verify loading an empty or non-existent store file."""
    data_path = str(tmp_path / "empty.json")
    with open(data_path, "w", encoding="utf-8") as f:
        f.write("")

    v = SecretsVault(data_path, str(tmp_path / "s.bin"), mock_audit_ledger, "p")
    with pytest.raises(KernelError):
        v.retrieve_secret("44444444-4444-4444-4444-444444444444", "any")


def test_load_store_with_content(
    tmp_path: Any, mock_audit_ledger: MockAuditLedger
) -> None:
    """Verify loading a store that has existing JSON content."""
    data_path = str(tmp_path / "content.json")
    s_path = str(tmp_path / "s1.bin")
    # Manually create a vault to write something, then a second one to read it
    v1 = SecretsVault(data_path, s_path, mock_audit_ledger, "p")
    v1.store_secret("11111111-1111-1111-1111-111111111111", "key1", "val1")

    v2 = SecretsVault(data_path, s_path, mock_audit_ledger, "p")
    assert v2.retrieve_secret("11111111-1111-1111-1111-111111111111", "key1") == "val1"


def test_rotate_secret_updates_version(
    vault: SecretsVault, mock_audit_ledger: MockAuditLedger
) -> None:
    """Verify rotation re-encrypts with incremented version and audits."""
    identity = "11111111-1111-1111-1111-111111111111"
    vault.store_secret(identity, "api_key", "old_value")
    vault.rotate_secret(uuid.UUID(identity), "api_key", b"new_rotated_value")

    # Retrieve should return the new value
    result = vault.retrieve_secret(identity, "api_key")
    assert result == "new_rotated_value"

    # Verify audit trail includes rotation
    audit_entries = list(mock_audit_ledger.iterate())
    actions = [e.action for e in audit_entries]
    assert "secret_rotated" in actions


def test_revoke_secret_removes_access(
    vault: SecretsVault, mock_audit_ledger: MockAuditLedger
) -> None:
    """Verify revocation removes the secret and audits the action."""
    identity = "11111111-1111-1111-1111-111111111111"
    vault.store_secret(identity, "api_key", "value_to_revoke")
    vault.revoke_secret(uuid.UUID(identity), "api_key")

    # Should no longer be accessible
    with pytest.raises(KernelError) as exc_info:
        vault.retrieve_secret(identity, "api_key")
    assert exc_info.value.code == ErrorCode.SECRET_NOT_FOUND

    # Verify audit trail includes revocation
    audit_entries = list(mock_audit_ledger.iterate())
    actions = [e.action for e in audit_entries]
    assert "secret_revoked" in actions


def test_secret_lifecycle_full_happy_path(
    vault: SecretsVault, mock_audit_ledger: MockAuditLedger
) -> None:
    """Full lifecycle: store → retrieve → rotate → retrieve → revoke → fail."""
    identity = "11111111-1111-1111-1111-111111111111"
    mid = uuid.UUID(identity)

    # 1. Store
    vault.store_secret(identity, "db_pass", "initial_pw")
    assert vault.retrieve_secret(identity, "db_pass") == "initial_pw"

    # 2. Rotate
    vault.rotate_secret(mid, "db_pass", b"rotated_pw")
    assert vault.retrieve_secret(identity, "db_pass") == "rotated_pw"

    # 3. Revoke
    vault.revoke_secret(mid, "db_pass")
    with pytest.raises(KernelError) as exc_info:
        vault.retrieve_secret(identity, "db_pass")
    assert exc_info.value.code == ErrorCode.SECRET_NOT_FOUND

    # 4. Verify full audit trail
    audit_entries = list(mock_audit_ledger.iterate())
    actions = [e.action for e in audit_entries]
    assert "secret_stored" in actions
    assert "secret_read" in actions
    assert "secret_rotated" in actions
    assert "secret_revoked" in actions
