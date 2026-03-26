"""End-to-End Demonstration of the Autonomous Revenue OS."""

import sys
import os
from typing import Any, Dict
from modules.crm.entry import Module


# Mocking the kernel environment
class MockEvent:
    """Mock event object representing a kernel event."""

    def __init__(self, event_type: str, payload: Dict[str, Any]):
        self.type = event_type
        self.payload = payload
        self.timestamp = "2026-03-13T16:50:00Z"

    @property
    def data(self):
        """Mock data property for event payload."""
        return self.payload


class MockBus:
    """Mock kernel event bus with state, audit, and policy engines."""

    def __init__(self):
        self.state_engine = MockStateEngine()
        self.audit_ledger = MockAuditLedger()
        self.policy_engine = MockPolicyEngine()
        self.subscribers = {}
        self.module = None

    def subscribe(self, event_type, handler, subscriber_id):
        """Mock subscription."""
        _ = subscriber_id
        self.subscribers[event_type] = handler

    def publish(self, event_type, payload=None):
        """Mock synchronous publish (triggers registered handler)."""
        print(f"[Bus] Published: {event_type}")
        if event_type in self.subscribers:
            # Simulate Event Bus routing to registered handler
            event = MockEvent(event_type, payload or {})
            handler = self.subscribers[event_type]
            handler(event)


class MockStateEngine:
    """Mock FSM engine."""

    def __init__(self):
        self.states = {}

    def register_fsm(self, name, version, transitions):
        """Mock registration."""
        _ = (name, version, transitions)

    def transition(self, fsm_name, obj_id, event, actor_id):
        """Mock transition logic."""
        _ = (fsm_name, actor_id)
        if event == "CREATE":
            self.states[obj_id] = "STAGED"
        elif event == "APPROVE":
            self.states[obj_id] = "APPROVED"

    def get_active_state(self, fsm_name, obj_id):
        """Mock state lookup."""
        _ = fsm_name
        return self.states.get(obj_id, "INIT")


class MockAuditLedger:
    """Mock audit ledger."""

    def append(self, actor_id, action, status, metadata=None):
        """Mock audit append."""
        _ = metadata
        print(f"[Audit] {actor_id} -> {action} [{status}]")


class MockPolicyEngine:
    """Mock policy engine."""

    def evaluate(self, identity_id, capability, context=None):
        """Mock policy evaluation."""
        _ = (identity_id, capability, context)

        class Result:
            """Mock evaluation result."""

            outcome = "ALLOW"

        return Result()


def run_demo():
    """Executes the end-to-end CRM demonstration cycle."""
    print("=== Phase 6: Autonomous Revenue OS E2E Demo ===")

    # 1. Initialize Module with Mock Bus
    bus = MockBus()
    crm = Module()
    bus.module = crm  # Link for sync publish logic
    crm.initialize(bus)

    # 1.1 Subscribe handle_event to recorded signals (simulating Kernel/ModuleLoader action)
    bus.subscribe("revenue.signal.recorded", crm.handle_event, "CRM_MODULE")

    # 2. Inject Hardware signal (via Event Bus)
    funding_signal = MockEvent(
        event_type="revenue.signal.detected",
        payload={
            "sig_id": "SIG_101",
            "type": "FUNDING_ROUND",
            "source": "Crunchbase",
            "confidence": 0.98,
            "entity_uid": "ent_9901",
            "amount": "50M",
        },
    )

    print("\n[Step 1] Injecting Funding Signal...")
    crm.handle_event(funding_signal)

    # 3. Verify Pipeline Creation
    staged = crm.pipeline.get_staged_pipelines()
    if staged:
        pipe = staged[0]
        print("\n[Step 2] Pipeline Successfully Created!")
        print(f"Pipeline ID: {pipe['id']}")
        print(f"Current State: {pipe['status']}")
    else:
        print("\n[Error] No pipeline created.")
        sys.exit(1)

    # 4. Simulate HITL Approval
    print("\n[Step 3] Simulating HITL Approval...")
    crm.pipeline.approve_pipeline(pipe["id"])
    new_state = crm.pipeline.state_engine.get_active_state(
        "REVENUE_PIPELINE", pipe["id"]
    )
    print(f"Final Pipeline State: {new_state}")

    print("\n=== Demo Completed Successfully ===")


if __name__ == "__main__":
    # Add root to sys.path
    sys.path.append(os.getcwd())
    run_demo()
