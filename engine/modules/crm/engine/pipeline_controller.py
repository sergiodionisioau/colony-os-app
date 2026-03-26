"""CRM Pipeline Controller."""

import uuid
from typing import Dict, Any, List
from enum import Enum


class PipelineStatus(Enum):
    """Possible states for a revenue pipeline."""

    STAGED = "STAGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"


class PipelineController:
    """Manages the lifecycle of agentic revenue actions (FSM Hardened)."""

    def __init__(self, state_engine: Any = None) -> None:
        """Initialize the controller with optional state engine and audit ledger."""
        self.state_engine = state_engine
        self.audit: Any = None
        self.pipeline_metadata: Dict[str, Dict[str, Any]] = {}
        self.module_identity = "CRM_MODULE"

    def create_pipeline(self, decision: Dict[str, Any]) -> str:
        """Creates a new pipeline node in the StateEngine."""
        pipe_id = f"PIPE_{uuid.uuid4().hex[:8]}"

        # Store metadata locally
        self.pipeline_metadata[pipe_id] = {"decision": decision}

        # Initial transition: INIT -> STAGED
        if self.state_engine:
            self.state_engine.transition(
                "REVENUE_PIPELINE", pipe_id, "CREATE", self.module_identity
            )

        # Audit Pipeline Creation
        if self.audit:
            self.audit.append(
                actor_id=self.module_identity,
                action="pipeline.create",
                status="SUCCESS",
                metadata={"id": pipe_id, "decision": decision.get("action")},
            )

        return pipe_id

    def approve_pipeline(self, pipe_id: str) -> bool:
        """Approves a pipeline for execution via StateEngine."""
        if pipe_id not in self.pipeline_metadata:
            return False

        if self.state_engine:
            self.state_engine.transition(
                "REVENUE_PIPELINE", pipe_id, "APPROVE", self.module_identity
            )
            return True
        return False

    def get_staged_pipelines(self) -> List[Dict[str, Any]]:
        """Returns all pipelines whose active state is STAGED."""
        if not self.state_engine:
            return []

        staged = []
        for pipe_id, meta in self.pipeline_metadata.items():
            state = self.state_engine.get_active_state("REVENUE_PIPELINE", pipe_id)
            if state == "STAGED":
                staged.append({"id": pipe_id, "status": state, **meta})
        return staged
