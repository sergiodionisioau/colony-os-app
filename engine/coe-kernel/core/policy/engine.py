"""Policy Engine implementation.

Deterministic evaluation of capabilities based on explicit rule trees.
"""

from typing import Any, Dict, List

from core.errors import ErrorCode, KernelError
from core.interfaces import IdentityServiceInterface, PolicyEngineInterface
from core.types import PolicyDecision


class PolicyEngine(PolicyEngineInterface):
    """Enforces fine-grained capability blocks across the Kernel bounds."""

    def __init__(
        self, identity_service: IdentityServiceInterface, audit_ledger: Any
    ) -> None:
        """Initialize the Policy Engine."""
        self.identity_service = identity_service
        self.audit_ledger = audit_ledger
        self.rules: List[Dict[str, Any]] = []

    def load_rules(self, raw_rules: List[Dict[str, Any]]) -> None:
        """Loads and locks down the deterministic evaluation parameters.

        Rules are sorted by:
        1. Priority (lower is higher)
        2. Action (deny before allow at same priority)
        """
        self.rules = sorted(
            raw_rules,
            key=lambda x: (
                x.get("priority", 999),
                0 if x.get("action") == "deny" else 1,
            ),
        )
        self.audit_ledger.append(
            actor_id="KERNEL",
            action="policy_rules_loaded",
            status="SUCCESS",
            metadata={"rule_count": len(self.rules)},
        )

    def _evaluate_event_auth(self, role: str, event_type: str) -> PolicyDecision:
        """Evaluates event_auth rules specifically following priority order."""
        for rule in self.rules:
            if rule.get("type") != "event_auth":
                continue
            if rule.get("conditions", {}).get("role") != role:
                continue

            action = rule.get("action", "deny")
            constraint = rule.get("constraint", {})

            # Check both 'allowed' and 'denied' keys for flexibility
            targets = (
                constraint.get("allowed_event_types")
                or constraint.get("denied_event_types")
                or []
            )

            if event_type in targets:
                if action == "deny":
                    return PolicyDecision(
                        allowed=False,
                        reason=f"Event {event_type} explicitly denied by Policy",
                    )
                return PolicyDecision(allowed=True, reason="Allowed Event Routing")

        return PolicyDecision(
            allowed=False,
            reason="Implicitly denied. No valid event_auth rule matched.",
        )

    def _evaluate_capability(self, role: str, capability: str) -> PolicyDecision:
        """Evaluates base capability rules following priority order."""
        for rule in self.rules:
            if rule.get("type") != "capability":
                continue
            if rule.get("conditions", {}).get("role") != role:
                continue

            action = rule.get("action", "deny")
            constraint = rule.get("constraint", {})

            # Check both 'allowed' and 'denied' keys for flexibility
            targets = (
                constraint.get("allowed_capabilities")
                or constraint.get("denied_capabilities")
                or []
            )

            if capability in targets:
                if action == "deny":
                    return PolicyDecision(
                        allowed=False,
                        reason=f"Capability {capability} explicitly denied by Policy",
                    )
                return PolicyDecision(allowed=True, reason="Matched Allow rule")

        return PolicyDecision(allowed=False, reason="Implicitly denied.")

    def evaluate(
        self,
        identity_id: str,
        capability: str,
        context: Dict[str, Any],
        dry_run: bool = False,
    ) -> PolicyDecision:
        """Evaluates an authorization limit deterministically against static chains."""
        try:
            identity = self.identity_service.get_identity(identity_id)
            if capability == "publish_event":
                event_type = context.get("event_type", "")
                decision = self._evaluate_event_auth(identity.role, event_type)
            else:
                decision = self._evaluate_capability(identity.role, capability)
        except KernelError as e:
            decision = PolicyDecision(allowed=False, reason=str(e.message))

        if not dry_run:
            self.audit_ledger.append(
                actor_id="KERNEL",
                action="policy_evaluation",
                status="SUCCESS" if decision.allowed else "DENIED",
                metadata={
                    "identity_id": identity_id,
                    "capability": capability,
                    "reason": decision.reason,
                },
            )
            if not decision.allowed:
                raise KernelError(code=ErrorCode.POLICY_DENIED, message=decision.reason)

        return decision
