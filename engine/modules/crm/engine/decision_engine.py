"""CRM Decision Engine."""

from typing import Dict, Any
from ..registry.knowledge_graph import KnowledgeGraph
from ..registry.schemas import Signal


class DecisionEngine:
    """Processes R-KG data to generate actionable revenue decisions."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def score_intent(self, entity_uid: str) -> float:
        """Computes an intent score for an entity based on signals."""
        entity = self.graph.entities.get(entity_uid)
        if not entity:
            return 0.0

        # Weighted heuristic: Different signal types have different impact
        type_weights = {
            "FUNDING": 2.0,
            "HIRING": 1.5,
            "WEB_VISIT": 0.5,
            "CONTENT_CONSUMPTION": 0.8,
            "WEB_INTERACTION": 0.7,
        }

        signals = self.graph.get_signal_history(entity_uid)
        if not signals:
            return 0.0

        weighted_score = sum(
            s.confidence * type_weights.get(s.type, 1.0) for s in signals
        )
        # Normalize: target score of 3.5 roughly equals high intent
        return min(weighted_score / 5.0, 1.0)

    def generate_decision(self, signal: Signal) -> Dict[str, Any]:
        """Generates a DecisionObject from a signal."""
        entity_uid = signal.payload.get("entity_uid")
        if not entity_uid:
            return {"action": "NONE", "reason": "No entity associated with signal"}

        intent_score = self.score_intent(entity_uid)

        if intent_score > 0.7:
            return {
                "action": "PROPOSER_OUTREACH",
                "entity_uid": entity_uid,
                "confidence": intent_score,
                "priority": "HIGH",
                "reason": f"High intent detected ({intent_score:.2f}) from signal {signal.type}",
            }

        return {
            "action": "STAGE_MONITOR",
            "entity_uid": entity_uid,
            "confidence": intent_score,
            "priority": "LOW",
            "reason": "Signal detected but intent below threshold",
        }
