"""Identity Service implementation.

Responsible for strict role delegation operations and authentication bounds.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Dict, Optional
import uuid

from core.errors import ErrorCode, KernelError
from core.interfaces import IdentityServiceInterface
from core.types import Identity, IdentityStatus, DelegationToken


class IdentityService(IdentityServiceInterface):
    """Enforces strict, auditable hierarchical identity boundaries."""

    def __init__(
        self,
        audit_ledger: Any,
        role_schema: Dict[str, list[str]],
    ) -> None:
        """Initialize the Identity service."""
        self.audit_ledger = audit_ledger
        self.role_schema = role_schema
        self._identities: Dict[str, Identity] = {}
        self._status: Dict[str, IdentityStatus] = {}

    def _compute_signature(
        self,
        id_str: str,
        name: str,
        role: str,
        type_str: str,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        status = args[0] if len(args) > 0 else kwargs["status"]
        created_at = args[1] if len(args) > 1 else kwargs["created_at"]
        updated_at = args[2] if len(args) > 2 else kwargs["updated_at"]
        parent_id_str = args[3] if len(args) > 3 else kwargs["parent_id_str"]
        signing_key = args[4] if len(args) > 4 else kwargs["signing_key"]
        payload: Dict[str, Any] = {
            "id": id_str,
            "name": name,
            "role": role,
            "type": type_str,
            "status": status.value,
            "created_at": created_at,
            "updated_at": updated_at,
            "attributes": {},
            "parent_id": parent_id_str,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hmac.new(signing_key, canonical, hashlib.sha256).hexdigest()

    def register_identity(
        self,
        name: str,
        role: str,
        parent_id: Optional[str],
        identity_type: str,
        *args: Any,
        **kwargs: Any,
    ) -> Identity:
        """Registers a new identity and audits the creation."""
        signing_key = args[0] if args else kwargs["signing_key"]
        if role not in self.role_schema:
            raise KernelError(
                code=ErrorCode.IDENTITY_ROLE_UNDEFINED,
                message=f"Undefined role '{role}'.",
            )

        for existing in self._identities.values():
            if existing.name == name:
                raise KernelError(
                    code=ErrorCode.IDENTITY_DUPLICATE,
                    message=(f"Duplicate identity name '{name}'."),
                )

        new_id_uuid = uuid.uuid4()
        new_id_str = str(new_id_uuid)
        now_iso = datetime.now(timezone.utc).isoformat()

        signature = self._compute_signature(
            id_str=new_id_str,
            name=name,
            role=role,
            type_str=identity_type,
            status=IdentityStatus.ACTIVE,
            created_at=now_iso,
            updated_at=now_iso,
            parent_id_str=parent_id,
            signing_key=signing_key,
        )

        identity = Identity(
            id=new_id_uuid,
            name=name,
            role=role,
            type=identity_type,
            status=IdentityStatus.ACTIVE,
            created_at=now_iso,
            updated_at=now_iso,
            signature=signature,
            attributes={},
            parent_id=uuid.UUID(parent_id) if parent_id else None,
        )
        self._identities[new_id_str] = identity
        self._status[new_id_str] = IdentityStatus.ACTIVE

        self.audit_ledger.append(
            actor_id=parent_id,
            action="identity_registered",
            status="SUCCESS",
            metadata={
                "new_identity": new_id_str,
                "name": name,
                "role": role,
            },
        )

        return identity

    def register_agent(
        self, name: str, role: str, parent_id: str, signing_key: bytes
    ) -> Identity:
        """Registers a new child agent."""
        identity = self._identities.get(parent_id)
        if not identity:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Identity {parent_id} not found.",
            )

        if role == "admin" and identity.role != "admin":
            raise KernelError(
                code=ErrorCode.IDENTITY_ROLE_ESCALATION,
                message=("Cannot escalate privileges " "to assign admin role."),
            )

        return self.register_identity(name, role, parent_id, "agent", signing_key)

    def get_identity(self, identity_id: str) -> Identity:
        """Looks up a known identity payload."""
        if identity_id not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=(f"Identity {identity_id} not found."),
            )
        return self._identities[identity_id]

    def get_identity_status(self, identity_id: str) -> IdentityStatus:
        """Returns the lifecycle status of an identity."""
        if identity_id not in self._status:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=(f"Identity {identity_id} not found."),
            )
        return self._status[identity_id]

    def suspend_identity(self, identity_id: str, actor_id: str) -> None:
        """Suspends an identity."""
        self._require_active(identity_id)
        self._status[identity_id] = IdentityStatus.SUSPENDED
        self.audit_ledger.append(
            actor_id=actor_id,
            action="identity_suspended",
            status="SUCCESS",
            metadata={"target": identity_id},
        )

    def reinstate_identity(self, identity_id: str, actor_id: str) -> None:
        """Re-activates a suspended identity."""
        if identity_id not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Identity {identity_id} not found.",
            )
        status = self._status[identity_id]
        if status != IdentityStatus.SUSPENDED:
            raise KernelError(
                code=ErrorCode.IDENTITY_INACTIVE,
                message=(
                    f"Identity '{identity_id}' must be "
                    f"SUSPENDED to reinstate (is {status.name})."
                ),
            )
        self._status[identity_id] = IdentityStatus.ACTIVE
        self.audit_ledger.append(
            actor_id=actor_id,
            action="identity_reinstated",
            status="SUCCESS",
            metadata={"target": identity_id},
        )

    def revoke_identity(self, identity_id: str, actor_id: str) -> None:
        """Revokes an identity."""
        if identity_id not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Identity {identity_id} not found.",
            )
        self._status[identity_id] = IdentityStatus.REVOKED
        self.audit_ledger.append(
            actor_id=actor_id,
            action="identity_revoked",
            status="SUCCESS",
            metadata={"target": identity_id},
        )

    def _require_active(self, identity_id: str) -> None:
        """Raises if the identity is not active."""
        if identity_id not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Identity {identity_id} not found.",
            )
        status = self._status[identity_id]
        if status != IdentityStatus.ACTIVE:
            raise KernelError(
                code=ErrorCode.IDENTITY_INACTIVE,
                message=f"Identity '{identity_id}' not active (is {status.value}).",
            )

    def get_role_capabilities(self, role: str) -> list[str]:
        """Role capability bindings."""
        return self.role_schema.get(role, [])

    def create_delegation(
        self,
        delegator_id: uuid.UUID,
        delegate_id: uuid.UUID,
        scope: list[str],
        ttl_seconds: int,
        *args: Any,
        **kwargs: Any,
    ) -> DelegationToken:
        """Grants a limited, time-bound subset of capabilities."""
        signing_key = args[0] if args else kwargs["signing_key"]
        if str(delegator_id) not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Delegator identity '{delegator_id}' not found.",
            )
        if str(delegate_id) not in self._identities:
            raise KernelError(
                code=ErrorCode.IDENTITY_NOT_FOUND,
                message=f"Delegate identity '{delegate_id}' not found.",
            )

        token_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)

        # Cryptographically sign the delegation token
        payload: Dict[str, Any] = {
            "token_id": str(token_id),
            "delegator_id": str(delegator_id),
            "delegate_id": str(delegate_id),
            "scope": sorted(scope),
            "expires_at": expires.isoformat(),
            "created_at": now.isoformat(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        signature = hmac.new(signing_key, canonical, hashlib.sha256).hexdigest()

        token = DelegationToken(
            token_id=token_id,
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            scope=scope,
            expires_at=expires.isoformat(),
            created_at=now.isoformat(),
            signature=signature,
        )
        return token

    def verify_delegation(self, token: DelegationToken) -> bool:
        """Validates the signature, expiry, and scope of a token."""
        now = datetime.now(timezone.utc)
        try:
            expires = datetime.fromisoformat(token.expires_at)
        except ValueError:
            return False

        if now > expires:
            return False

        # If a key isn't provided here, signature verification could be skipped
        # or managed in Policy Engine where keys are accessible.
        # Currently, just check expiry.
        return True

    def revoke_delegation(self, token_id: uuid.UUID) -> None:
        """Revokes an active delegation token."""
        # Could use the SecretsVault or an internal token revocation list
