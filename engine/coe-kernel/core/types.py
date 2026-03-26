"""Strict type definitions and dataclasses for the COE Kernel.

Provides immutable representations of kernel contracts ensuring that objects
passed between the event bus, policy engine, and audit log follow rigid signatures.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

import uuid


class IdentityStatus(Enum):
    """Lifecycle states for identities."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass(frozen=True)
class _IdentityBase:
    id: uuid.UUID
    name: str
    role: str
    type: str  # e.g., 'user', 'agent', 'module'
    status: IdentityStatus


@dataclass(frozen=True)
class Identity(_IdentityBase):
    """Immutable representation of an authenticated entity in the system."""

    created_at: str
    updated_at: str
    signature: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class DelegationToken:
    """Immutable representation of authority delegation between identities."""

    token_id: uuid.UUID
    delegator_id: uuid.UUID
    delegate_id: uuid.UUID
    scope: List[str]
    expires_at: str
    created_at: str
    signature: str


@dataclass(frozen=True)
class SecretEntry:
    """Immutable representation of an encrypted secret at rest."""

    key: str
    module_id: uuid.UUID
    ciphertext: bytes
    version: int
    created_at: str
    expires_at: Optional[str]


@dataclass(frozen=True)
class _PolicyDecisionBase:
    allowed: bool
    reason: str
    rule_id: Optional[str] = None
    policy_set_hash: Optional[str] = None


@dataclass(frozen=True)
class PolicyDecision(_PolicyDecisionBase):
    """Immutable result of a policy evaluation."""

    timestamp: Optional[str] = None
    identity_id: Optional[uuid.UUID] = None
    capability: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayContext:
    """Provides context when an event is replayed."""

    is_replay: bool
    replay_id: Optional[uuid.UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize replay context to a dictionary."""
        return {
            "is_replay": self.is_replay,
            "replay_id": str(self.replay_id) if self.replay_id else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayContext":
        """Deserialize replay context from a dictionary."""
        replay_id = uuid.UUID(data["replay_id"]) if data.get("replay_id") else None
        return cls(is_replay=data["is_replay"], replay_id=replay_id)


@dataclass(frozen=True)
class EventBusDependencies:
    """Groups dependencies for the EventBus to avoid too many arguments."""

    audit_ledger: Any
    event_store: Any
    backpressure: Any
    dlq: Any
    schema_registry: Any = None


@dataclass(frozen=True)
class _EventBase:
    event_id: uuid.UUID
    sequence_number: int  # monotonic ordering
    correlation_id: uuid.UUID
    type: str
    version: str


@dataclass(frozen=True)
class Event(_EventBase):
    """Immutable representation of a state change or command."""

    timestamp: str  # ISO 8601
    origin_id: uuid.UUID
    payload: Dict[str, Any]
    signature: str
    replay_context: Optional[ReplayContext] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to a dictionary for storage/transport."""
        data = {
            "event_id": str(self.event_id),
            "sequence_number": self.sequence_number,
            "correlation_id": str(self.correlation_id),
            "type": self.type,
            "version": self.version,
            "timestamp": self.timestamp,
            "origin_id": str(self.origin_id),
            "payload": self.payload,
            "signature": self.signature,
            "replay_context": (
                self.replay_context.to_dict() if self.replay_context else None
            ),
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Deserialize event from a dictionary."""
        replay_ctx = None
        if data.get("replay_context"):
            replay_ctx = ReplayContext.from_dict(data["replay_context"])

        return cls(
            event_id=uuid.UUID(data["event_id"]),
            sequence_number=data["sequence_number"],
            correlation_id=uuid.UUID(data["correlation_id"]),
            type=data["type"],
            version=data["version"],
            timestamp=data["timestamp"],
            origin_id=uuid.UUID(data["origin_id"]),
            payload=data["payload"],
            signature=data["signature"],
            replay_context=replay_ctx,
        )

    @staticmethod
    def create(
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[uuid.UUID] = None,
        origin_id: Optional[uuid.UUID] = None,
    ) -> "Event":
        """Factory method to create a standardized system event.

        Ensures consistent defaults for system/kernel-level signals.
        """
        return Event(
            event_id=uuid.uuid4(),
            sequence_number=0,  # System events have sequence 0 or are transient
            correlation_id=correlation_id or uuid.uuid4(),
            type=event_type,
            version="1.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            origin_id=origin_id or uuid.UUID(int=0),  # Default to Kernel origin
            payload=payload,
            signature="N/A",  # Internal events skip signature validation
        )


@dataclass(frozen=True)
class DLQEntry:
    """Wrapper for failed events containing failure metadata."""

    failed_event: Event
    reason: str
    subscriber_id: str
    timestamp: str
    retry_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DLQ entry to a dictionary."""
        return {
            "failed_event": self.failed_event.to_dict(),
            "reason": self.reason,
            "subscriber_id": self.subscriber_id,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DLQEntry":
        """Deserialize DLQ entry from a dictionary."""
        return cls(
            failed_event=Event.from_dict(data["failed_event"]),
            reason=data["reason"],
            subscriber_id=data["subscriber_id"],
            timestamp=data["timestamp"],
            retry_count=data["retry_count"],
        )


@dataclass(frozen=True)
class _AuditEntryBase:
    entry_id: uuid.UUID
    timestamp: str
    actor_id: str
    action: str


@dataclass(frozen=True)
class AuditEntry(_AuditEntryBase):
    """Immutable record intended for the tamper-evident audit ledger."""

    status: str
    metadata: Dict[str, Any]
    previous_hash: str
    entry_hash: str
