"""Unified error definitions for the COE Kernel.

This module provides the core `KernelError` class and `ErrorCode` enum mapping
predictable error states to explicit identifiers, facilitating deterministic execution
handling across all kernel components according to Phase 1 strict specification.
"""

from enum import Enum


class ErrorCode(Enum):
    """Explicitly defined error states for deterministic handling within the Kernel."""

    # Phase 3 & 4 Hardening: Ensured all codes are unique and present.

    # Identity errors (1xxx)
    IDENTITY_NOT_FOUND = "1001"
    IDENTITY_DUPLICATE = "1002"
    IDENTITY_INACTIVE = "1003"
    IDENTITY_ROLE_UNDEFINED = "1004"
    IDENTITY_ROLE_ESCALATION = "1005"
    IDENTITY_DELEGATION_EXPIRED = "1006"

    # Policy errors (2xxx)
    POLICY_DENIED = "2001"
    POLICY_BUDGET_EXCEEDED = "2002"
    POLICY_RATE_LIMITED = "2003"

    # Event errors (3xxx)
    EVENT_SCHEMA_INVALID = "3001"
    EVENT_SIGNATURE_INVALID = "3002"
    EVENT_TYPE_UNKNOWN = "3003"
    EVENT_VERSION_MISMATCH = "3004"

    # Module errors (4xxx)
    MODULE_MANIFEST_INVALID = "4001"
    MODULE_SIGNATURE_INVALID = "4002"
    MODULE_DEPENDENCY_CIRCULAR = "4003"
    MODULE_CAPABILITY_UNDECLARED = "4004"
    MODULE_EXECUTION_FAILED = "4005"
    MODULE_NOT_FOUND = "4006"

    # Vault / Secret errors (5xxx)
    VAULT_NOT_FOUND = "5001"
    VAULT_ACCESS_DENIED = "5002"
    VAULT_EXPIRED = "5003"
    SECRET_NOT_FOUND = str(5004)
    SECRET_ACCESS_DENIED = str(5005)
    SECRET_EXPIRED = str(5006)

    # State errors (6xxx)
    STATE_TRANSITION_INVALID = "6001"
    STATE_VERSION_MISMATCH = "6002"
    STATE_FSM_NOT_FOUND = "6003"

    # Audit errors (7xxx)
    AUDIT_INTEGRITY_VIOLATION = "7001"
    AUDIT_CHAIN_BROKEN = "7002"

    # Agent errors (8xxx)
    AGENT_NOT_REGISTERED = "8001"
    AGENT_TASK_POLICY_DENIED = "8002"
    AGENT_MAX_STEPS_EXCEEDED = "8003"
    AGENT_PROVIDER_TIMEOUT = "8004"
    AGENT_CAPABILITY_OUT_OF_SCOPE = "8005"

    # Improvement Engine errors (10xxx)
    PATCH_TARGET_PROTECTED = "10001"
    PATCH_CI_FAILED = "10002"
    PATCH_NOT_FOUND = "10003"
    PATCH_DIFF_EMPTY = "10004"

    # System errors (9xxx)
    KERNEL_BOOTSTRAP_FAILED = "9001"
    CONFIG_INVALID = "9002"
    BACKPRESSURE_ACTIVE = "9003"
    UNKNOWN_FAULT = "9999"


class KernelError(Exception):
    """Standardized kernel exception for explicit trapping.

    Attributes:
        code: The specific ErrorCode enum value for programmatic filtering.
        message: The human-readable string providing detail.
    """

    def __init__(self, code: ErrorCode, message: str) -> None:
        """Initialize the standard error exception.

        Args:
            code: The enumerator value mapping to the error class.
            message: The string detailing the failure.
        """
        super().__init__(f"[{code.name}] {message}")
        self.code = code
        self.message = message
