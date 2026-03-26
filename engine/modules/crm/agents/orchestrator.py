"""Agent Orchestrator for CRM."""

# pylint: disable=too-few-public-methods

from typing import Dict, Any, cast
from .prospecting import ProspectingAgent
from .deal_strategy import DealStrategyAgent


class AgentOrchestrator:
    """Autonomous CRM Agent Orchestrator."""

    def __init__(self) -> None:
        """Initialize agents and policy link."""
        # Policies would normally be loaded from an encrypted signed store
        self.policy_engine: Any = None
        self.module_identity = "crm_module_root"
        self.agents = {
            "prospector": ProspectingAgent(capability_policy={"web": True}),
            "strategist": DealStrategyAgent(capability_policy={"graph_read": True}),
        }

    def get_status(self) -> str:
        """Returns the health status of the orchestrator."""
        return "HEALTHY"

    def run_cycle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a multi-agent processing cycle (Policy Hardened)."""
        results: Dict[str, Any] = {}
        decision = context.get("decision", {})

        # 1. Coordinate Prospecting if needed
        if decision.get("action") == "NONE" or "harvester" in results:
            # Explicit Capability Check
            if self.policy_engine:
                auth = self.policy_engine.evaluate(
                    self.module_identity, "SIGNAL_HARVESTING", context
                )
                if auth.outcome != "ALLOW":
                    return results

                p_agent = cast(ProspectingAgent, self.agents["prospector"])
                if "web" in p_agent.policy:
                    results["prospecting"] = p_agent.harvest_signal(context)

        # 2. Coordinate Strategy for High-Intent decisions
        elif decision.get("action") == "PROPOSER_OUTREACH":
            # Explicit Capability Check
            if self.policy_engine:
                auth = self.policy_engine.evaluate(
                    self.module_identity, "REVENUE_GRAPH_UPDATE", context
                )
                if auth.outcome != "ALLOW":
                    return results

                s_agent = cast(DealStrategyAgent, self.agents["strategist"])
                if "graph_read" in s_agent.policy:
                    results["strategy"] = s_agent.propose_strategy(context)

        return results
