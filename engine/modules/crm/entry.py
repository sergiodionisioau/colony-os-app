"""Autonomous Revenue OS Entrypoint.

Bootstraps the Decision Engine, R-KG, and Agent Orchestrator.
"""

from typing import Any, cast
from .registry.knowledge_graph import KnowledgeGraph
from .engine.decision_engine import DecisionEngine
from .engine.pipeline_controller import PipelineController
from .registry.schemas import Signal
from .agents.orchestrator import AgentOrchestrator


class Module:
    """The CRM Module instance."""

    def __init__(self) -> None:
        """Initialize the CRM logic layers."""
        self.graph = KnowledgeGraph()
        self.pipeline = PipelineController()
        self.orchestrator = AgentOrchestrator()
        self.engines = {
            "decision": DecisionEngine(self.graph),
            "policy": None,
            "audit": None,
        }
        self.bus = None
        self.identity_id = "crm_module_root"

    def initialize(self, bus: Any) -> None:
        """Initialize the module with the kernel event bus and state engine."""
        self.bus = bus

        # 1. Register FSM if state engine exists
        if hasattr(bus, "state_engine"):
            transitions = [
                {"from": "INIT", "event": "CREATE", "to": "STAGED"},
                {"from": "STAGED", "event": "APPROVE", "to": "APPROVED"},
                {"from": "STAGED", "event": "REJECT", "to": "REJECTED"},
                {"from": "APPROVED", "event": "EXECUTE", "to": "EXECUTING"},
                {"from": "EXECUTING", "event": "COMPLETE", "to": "COMPLETED"},
            ]
            bus.state_engine.register_fsm("REVENUE_PIPELINE", "1.0", transitions)
            self.pipeline.state_engine = bus.state_engine

        # 2. Attach Audit Ledger and Policy Engine if they exist
        if hasattr(bus, "audit_ledger"):
            self.engines["audit"] = bus.audit_ledger
            self.pipeline.audit = bus.audit_ledger

        if hasattr(bus, "policy_engine"):
            self.engines["policy"] = bus.policy_engine
            self.orchestrator.policy_engine = bus.policy_engine

        print("CRM: Autonomous Revenue OS Initialized (FSM-Hardened)")

    def handle_event(self, event: Any) -> None:
        """Entrypoint for kernel events."""
        if event.type == "revenue.signal.detected":
            self._stage_1_ingress(event)
        elif event.type == "revenue.signal.recorded":
            self._stage_2_logic(event)
        elif event.type == "revenue.outcome.closed":
            self._handle_outcome(event)

        print(f"CRM: Handled event {event.type}")

    def _stage_1_ingress(self, event: Any) -> None:
        """Stage 1: Capture and Record (Non-blocking)."""
        signal = Signal(
            uid=event.payload.get("sig_id", "SIG_UNK"),
            type=event.payload.get("type", "UNKNOWN"),
            source=event.payload.get("source", "UNKNOWN"),
            confidence=event.payload.get("confidence", 0.5),
            timestamp=event.timestamp,
            payload=event.payload,
        )
        self.graph.add_signal(signal)

        # Audit Signal Ingestion
        audit = self.engines.get("audit")
        if audit:
            # Use getattr or cast for dynamic engines
            getattr(audit, "append")(
                actor_id="CRM_MODULE",
                action="signal.ingest",
                status="SUCCESS",
                metadata={"uid": signal.uid, "type": signal.type},
            )

        # Publish internal event for Stage 2
        if self.bus:
            self.bus.publish("revenue.signal.recorded", payload=event.payload)

    def _stage_2_logic(self, event: Any) -> None:
        """Stage 2: Score and Pipeline Generation."""
        entity_uid = event.payload.get("entity_uid")
        if not entity_uid:
            return

        # Re-fetch from graph to ensure consistency (Deterministic)
        signals = self.graph.get_signal_history(entity_uid)
        if not signals:
            return

        # Sort signals by timestamp to guarantee deterministic scoring
        signals.sort(key=lambda x: x.timestamp)
        latest_signal = signals[-1]

        # Zero Tolerance: Verify capability before execution
        policy = self.engines.get("policy")
        if policy:
            decision_auth = getattr(policy, "evaluate")(
                identity_id=self.identity_id,
                capability="DECISION_LOOP_EXECUTION",
                context={"entity_uid": entity_uid},
            )
            if decision_auth.outcome != "ALLOW":
                print(f"CRM: Policy DENIED decision loop for {entity_uid}")
                return

        decision_engine = cast(DecisionEngine, self.engines["decision"])
        decision = decision_engine.generate_decision(latest_signal)

        if decision["action"] != "NONE":
            # Integrate Agent Layer for Strategy Proposal
            context = {"entity_uid": entity_uid, "decision": decision}
            strategy = self.orchestrator.run_cycle(context)
            decision["strategy"] = strategy

            pipe_id = self.pipeline.create_pipeline(decision)
            print(f"CRM: Created pipeline {pipe_id} with strategy: {strategy}")

    def _handle_outcome(self, event: Any) -> None:
        """Handles terminal pipeline states."""
        pipe_id = event.payload.get("pipeline_id")
        outcome = event.payload.get("outcome")
        print(f"CRM: Pipeline {pipe_id} closed with outcome {outcome}")

    def healthcheck(self) -> bool:
        """Module health verification with dependency checks."""
        checks = [
            self.bus is not None,
            self.graph is not None,
            self.engines.get("decision") is not None,
            self.pipeline is not None,
            self.orchestrator is not None,
        ]
        health_status = all(checks)

        # Audit health check result
        audit = self.engines.get("audit")
        if audit:
            getattr(audit, "append")(
                actor_id="CRM_MODULE",
                action="module.healthcheck",
                status="SUCCESS" if health_status else "FAILED",
                metadata={
                    "checks_passed": sum(checks),
                    "checks_total": len(checks),
                    "failures": [i for i, c in enumerate(checks) if not c]
                }
            )

        return health_status

    def shutdown(self) -> None:
        """Graceful shutdown logic."""
        print("CRM: Module shutting down")
