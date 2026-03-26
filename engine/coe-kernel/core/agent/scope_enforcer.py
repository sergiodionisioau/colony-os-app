"""Enforcement of agent capability boundaries.

This module provides the PolicyScopeEnforcer which ensures agents only
invoke capabilities declared in their manifests.
"""

from typing import Any, Dict, List

from core.errors import ErrorCode, KernelError
from core.agent.types import PolicyScopeBinding
from core.interfaces import PolicyEngineInterface, IdentityServiceInterface
from core.types import PolicyDecision

__all__ = ["PolicyScopeEnforcer", "PolicyScopeBinding"]


class PolicyScopeEnforcer(PolicyEngineInterface):
    """Enforces capability limits at the agent role boundary, wrapping RBAC."""

    def __init__(
        self,
        base_policy: PolicyEngineInterface,
        identity_service: IdentityServiceInterface,
        bindings: List[PolicyScopeBinding],
    ) -> None:
        """Initializes with a base policy engine and role-to-capability mappings."""
        self._base_policy = base_policy
        self._identity_service = identity_service
        self._bindings: Dict[str, List[str]] = {
            b.agent_role: b.allowed_capabilities for b in bindings
        }

    def load_rules(self, raw_rules: List[Dict[str, Any]]) -> None:
        """Delegates rule loading to the wrapped base policy engine."""
        self._base_policy.load_rules(raw_rules)

    def check(self, agent_role: str, capability: str) -> None:
        """Explicitly allows or denies a capability based on the role's scope.

        Raises KernelError(AGENT_CAPABILITY_OUT_OF_SCOPE) if capability not declared.
        """
        allowed = self._bindings.get(agent_role, [])
        if "all" in allowed:
            return

        if capability not in allowed:
            raise KernelError(
                code=ErrorCode.AGENT_CAPABILITY_OUT_OF_SCOPE,
                message=(
                    f"Capability '{capability}' is outside the scope of "
                    f"role '{agent_role}'."
                ),
            )

    def evaluate(
        self,
        identity_id: str,
        capability: str,
        context: Dict[str, Any],
        dry_run: bool = False,
    ) -> PolicyDecision:
        """Wraps PolicyEngine.evaluate with an initial scope check (G3-03)."""
        try:
            # 1. Get identity to find the role
            identity = self._identity_service.get_identity(identity_id)

            # 2. Check scope
            self.check(identity.role, capability)

            # 3. Proceed to RBAC check
            return self._base_policy.evaluate(identity_id, capability, context, dry_run)

        except (KernelError, AttributeError) as exc:
            if isinstance(exc, KernelError) and exc.code == ErrorCode.POLICY_DENIED:
                # Re-raise policy denial
                raise
            if (
                isinstance(exc, KernelError)
                and exc.code == ErrorCode.AGENT_CAPABILITY_OUT_OF_SCOPE
            ):
                if not dry_run:
                    raise
                return PolicyDecision(allowed=False, reason=str(exc.message))

            # Fallback for identity not found or other errors
            return PolicyDecision(
                allowed=False, reason=f"Scope/Policy evaluation failed: {str(exc)}"
            )
