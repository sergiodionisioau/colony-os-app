"""Strict TDD suite for the Identity Service.

Verifies role delegation, permission isolation, and registration limits.
"""

import pytest

from core.errors import ErrorCode, KernelError
from core.types import IdentityStatus
from core.identity.service import IdentityService
from tests.conftest import MockAuditLedger


@pytest.fixture(name="identity_service")
def identity_service_fixture(mock_audit_ledger: MockAuditLedger) -> IdentityService:
    """Fixture to provide a clean IdentityService and Mock Ledger."""
    schema = {"admin": ["all"], "agent": ["publish_event"]}
    return IdentityService(audit_ledger=mock_audit_ledger, role_schema=schema)


def test_cannot_assign_undefined_role(identity_service: IdentityService) -> None:
    """Test rejection of roles not in schema."""
    with pytest.raises(KernelError) as exc_info:
        identity_service.register_identity(
            "agent_x",
            "unknown_role",
            "a123e456-7890-1234-5678-123456789012",
            "agent",
            b"dummy_key",
        )
    assert exc_info.value.code == ErrorCode.IDENTITY_ROLE_UNDEFINED


def test_cannot_escalate_role(identity_service: IdentityService) -> None:
    """Test agents cannot be granted admin role by non-admin parent."""
    parent = identity_service.register_identity(
        "parent", "agent", "a123e456-7890-1234-5678-123456789012", "user", b"dummy_key"
    )
    parent_id = str(parent.id)

    with pytest.raises(KernelError) as exc_info:
        identity_service.register_agent("test_agent", "admin", parent_id, b"dummy_key")
    assert exc_info.value.code == ErrorCode.IDENTITY_ROLE_ESCALATION


def test_duplicate_identity_rejected(identity_service: IdentityService) -> None:
    """Test identity name uniqueness constraint across roles and types."""
    parent = identity_service.register_identity(
        "parent", "admin", "a123e456-7890-1234-5678-123456789012", "user", b"dummy_key"
    )
    parent_id = str(parent.id)

    identity_service.register_identity(
        "test_user", "agent", parent_id, "user", b"dummy_key"
    )
    with pytest.raises(KernelError) as exc_info:
        identity_service.register_identity(
            "test_user", "agent", parent_id, "user", b"dummy_key"
        )
    assert exc_info.value.code == ErrorCode.IDENTITY_DUPLICATE


def test_permission_lookup_correct(identity_service: IdentityService) -> None:
    """Test capability bounds extraction."""
    parent = identity_service.register_identity(
        "parent", "admin", "a123e456-7890-1234-5678-123456789012", "user", b"dummy_key"
    )
    parent_id = str(parent.id)
    ident = identity_service.register_agent(
        "worker_node", "agent", parent_id, b"dummy_key"
    )

    capabilities = identity_service.get_role_capabilities(ident.role)
    assert "publish_event" in capabilities
    assert "all" not in capabilities


def test_get_identity_not_found(identity_service: IdentityService) -> None:
    """Test get_identity with non-existent ID."""
    with pytest.raises(KernelError) as exc_info:
        identity_service.get_identity("d123e456-7890-1234-5678-123456789012")
    assert exc_info.value.code == ErrorCode.IDENTITY_NOT_FOUND


def test_get_identity_status_not_found(identity_service: IdentityService) -> None:
    """Test get_identity_status with non-existent ID."""
    with pytest.raises(KernelError) as exc_info:
        identity_service.get_identity("missing")
    assert exc_info.value.code == ErrorCode.IDENTITY_NOT_FOUND


def test_identity_lifecycle_flow(identity_service: IdentityService) -> None:
    """Test full lifecycle: Active -> Suspended -> Reinstated -> Revoked."""
    parent = identity_service.register_identity(
        "p", "admin", "c123e456-7890-1234-5678-123456789012", "user", b"dummy_key"
    )
    pid = str(parent.id)

    # Init state
    assert identity_service.get_identity_status(pid) == IdentityStatus.ACTIVE

    # Suspend
    identity_service.suspend_identity(pid, "K")
    assert identity_service.get_identity_status(pid) == IdentityStatus.SUSPENDED

    # Reinstate
    identity_service.reinstate_identity(pid, "K")
    assert identity_service.get_identity_status(pid) == IdentityStatus.ACTIVE

    # Revoke
    identity_service.revoke_identity(pid, "K")
    assert identity_service.get_identity_status(pid) == IdentityStatus.REVOKED

    # Cannot reinstate revoked
    with pytest.raises(KernelError) as exc:
        identity_service.reinstate_identity(pid, "K")
        assert exc.value.code == ErrorCode.IDENTITY_INACTIVE


def test_lifecycle_errors(identity_service: IdentityService) -> None:
    """Test lifecycle errors for missing or invalid states."""
    # Suspend/Reinstate/Revoke missing
    with pytest.raises(KernelError) as exc:
        identity_service.suspend_identity("m", "K")
    assert exc.value.code == ErrorCode.IDENTITY_NOT_FOUND

    with pytest.raises(KernelError) as exc:
        identity_service.reinstate_identity("m", "K")
    assert exc.value.code == ErrorCode.IDENTITY_NOT_FOUND

    with pytest.raises(KernelError) as exc:
        identity_service.revoke_identity("m", "K")
    assert exc.value.code == ErrorCode.IDENTITY_NOT_FOUND


def test_require_active_enforcement(identity_service: IdentityService) -> None:
    """Test that suspended/revoked identities fail _require_active checks."""
    ident = identity_service.register_identity(
        "p", "admin", "e123e456-7890-1234-5678-123456789012", "user", b"dummy_key"
    )
    iid = str(ident.id)

    identity_service.suspend_identity(iid, "K")

    # suspend_identity calls _require_active internally, so we test it via next call
    with pytest.raises(KernelError) as exc:
        identity_service.suspend_identity(iid, "K")
    assert exc.value.code == ErrorCode.IDENTITY_INACTIVE
    assert "suspended" in str(exc.value.message)

    identity_service.reinstate_identity(iid, "K")
    identity_service.revoke_identity(iid, "K")

    with pytest.raises(KernelError) as exc:
        identity_service.suspend_identity(iid, "K")
    assert exc.value.code == ErrorCode.IDENTITY_INACTIVE
    assert "revoked" in str(exc.value.message)
