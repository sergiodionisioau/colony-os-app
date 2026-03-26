"""Strict TDD suite for the Policy Engine.

Verifies capability checks and event authorization rules.
"""

from typing import Any, List, Dict
import pytest

from core.policy.engine import PolicyEngine
from core.errors import KernelError, ErrorCode
from tests.conftest import MockAuditLedger, MockIdentityServicePolicy


@pytest.fixture(name="policy_engine")
def policy_engine_fixture(mock_audit_ledger: MockAuditLedger) -> PolicyEngine:
    """Fixture providing a PolicyEngine with a mock IdentityService."""
    identity_service = MockIdentityServicePolicy()
    return PolicyEngine(
        identity_service=identity_service, audit_ledger=mock_audit_ledger
    )


def test_unauthorized_capability_call_rejected(policy_engine: PolicyEngine) -> None:
    """Test Set 2: Unauthorized capability rejected."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "allow",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["read_only"]},
        }
    ]
    policy_engine.load_rules(rules)

    # identity_id "agent_1" is hardcoded in MockIdentityServicePolicy
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate("agent_1", "write_secrets", {})
    assert exc_info.value.code == ErrorCode.POLICY_DENIED


def test_invalid_event_rejected(policy_engine: PolicyEngine) -> None:
    """Test Set 2: Invalid event rejected."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "event_auth",
            "action": "allow",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_event_types": ["system.test"]},
        }
    ]
    policy_engine.load_rules(rules)

    decision = policy_engine.evaluate(
        "agent_1", "publish_event", {"event_type": "restricted.action"}, dry_run=True
    )
    assert decision.allowed is False

    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate(
            "agent_1", "publish_event", {"event_type": "restricted.action"}
        )
    assert exc_info.value.code == ErrorCode.POLICY_DENIED


def test_authorized_scenario_allowed(policy_engine: PolicyEngine) -> None:
    """Test Set 2: Authorized scenario allowed."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "event_auth",
            "action": "allow",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_event_types": ["system.test"]},
        },
        {
            "type": "capability",
            "action": "allow",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["read_only"]},
        },
    ]
    policy_engine.load_rules(rules)

    # Check event auth
    decision_ev = policy_engine.evaluate(
        "agent_1", "publish_event", {"event_type": "system.test"}
    )
    assert decision_ev.allowed is True

    # Check base capability
    decision_cap = policy_engine.evaluate("agent_1", "read_only", {})
    assert decision_cap.allowed is True


def test_evaluate_identity_not_found(policy_engine: PolicyEngine) -> None:
    """Test evaluate when identity lookup fails."""
    # MockIdentityServicePolicy raises KernelError for unknown IDs
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate("unknown", "any", {})
    assert exc_info.value.code == ErrorCode.POLICY_DENIED
    assert "not found" in exc_info.value.message.lower()


def test_implicit_denial(policy_engine: PolicyEngine) -> None:
    """Test implicit denial when no rules match."""
    policy_engine.load_rules([])
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate("agent_1", "any", {})
    assert exc_info.value.code == ErrorCode.POLICY_DENIED
    assert "implicitly denied" in exc_info.value.message.lower()


def test_event_auth_role_mismatch(policy_engine: PolicyEngine) -> None:
    """Test event_auth rule with different role."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "event_auth",
            "action": "allow",
            "conditions": {"role": "admin"},
            "constraint": {"allowed_event_types": ["system.test"]},
        }
    ]
    policy_engine.load_rules(rules)
    # agent_1 has role 'agent'
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate(
            "agent_1", "publish_event", {"event_type": "system.test"}
        )
    assert exc_info.value.code == ErrorCode.POLICY_DENIED


def test_capability_role_mismatch(policy_engine: PolicyEngine) -> None:
    """Test capability rule with different role."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "allow",
            "conditions": {"role": "admin"},
            "constraint": {"allowed_capabilities": ["read"]},
        }
    ]
    policy_engine.load_rules(rules)
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate("agent_1", "read", {})
    assert exc_info.value.code == ErrorCode.POLICY_DENIED


def test_event_auth_wrong_type_skip(policy_engine: PolicyEngine) -> None:
    """Test that event_auth logic skips non-event_auth rules."""
    rules: List[Dict[str, Any]] = [
        {"type": "capability", "action": "allow", "conditions": {"role": "agent"}}
    ]
    policy_engine.load_rules(rules)
    with pytest.raises(KernelError) as exc_info:
        policy_engine.evaluate("agent_1", "publish_event", {"event_type": "any"})
    assert exc_info.value.code == ErrorCode.POLICY_DENIED


def test_dry_run_denied(policy_engine: PolicyEngine) -> None:
    """Test that dry_run suppresses exceptions when denied."""
    rules: List[Dict[str, Any]] = []
    policy_engine.load_rules(rules)

    # Should not raise KernelError
    decision = policy_engine.evaluate("agent_1", "any", {}, dry_run=True)
    assert decision.allowed is False
    assert "implicitly denied" in decision.reason.lower()


def test_dry_run_allowed(policy_engine: PolicyEngine) -> None:
    """Test that dry_run behaves identically to allowed evaluating without throwing."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "allow",
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["read_only"]},
        }
    ]
    policy_engine.load_rules(rules)

    # Should not raise KernelError
    decision = policy_engine.evaluate("agent_1", "read_only", {}, dry_run=True)
    assert decision.allowed is True


def test_priority_ordering_allow_over_deny(policy_engine: PolicyEngine) -> None:
    """Test that higher priority allow overrides lower priority deny."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "deny",
            "priority": 20,
            "conditions": {"role": "agent"},
            "constraint": {"denied_capabilities": ["restricted"]},
        },
        {
            "type": "capability",
            "action": "allow",
            "priority": 10,
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["restricted"]},
        },
    ]
    policy_engine.load_rules(rules)
    decision = policy_engine.evaluate("agent_1", "restricted", {}, dry_run=True)
    assert decision.allowed is True


def test_priority_ordering_deny_over_allow(policy_engine: PolicyEngine) -> None:
    """Test that higher priority deny overrides lower priority allow."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "deny",
            "priority": 10,
            "conditions": {"role": "agent"},
            "constraint": {"denied_capabilities": ["restricted"]},
        },
        {
            "type": "capability",
            "action": "allow",
            "priority": 20,
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["restricted"]},
        },
    ]
    policy_engine.load_rules(rules)
    decision = policy_engine.evaluate("agent_1", "restricted", {}, dry_run=True)
    assert decision.allowed is False


def test_first_deny_wins_same_prio(policy_engine: PolicyEngine) -> None:
    """Test that deny wins over allow at the same priority level."""
    rules: List[Dict[str, Any]] = [
        {
            "type": "capability",
            "action": "allow",
            "priority": 10,
            "conditions": {"role": "agent"},
            "constraint": {"allowed_capabilities": ["restricted"]},
        },
        {
            "type": "capability",
            "action": "deny",
            "priority": 10,
            "conditions": {"role": "agent"},
            "constraint": {"denied_capabilities": ["restricted"]},
        },
    ]
    policy_engine.load_rules(rules)
    decision = policy_engine.evaluate("agent_1", "restricted", {}, dry_run=True)
    assert decision.allowed is False
