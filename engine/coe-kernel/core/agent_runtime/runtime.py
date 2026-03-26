"""Agent Runtime management.

This module provides the AgentRuntime which handles registration,
unregistration, and task dispatch for all agents in the COE.
"""

from dataclasses import replace
from typing import Any, Dict

from core.errors import ErrorCode, KernelError
from core.event_bus.bus import compute_event_signature
from core.interfaces import AgentRuntimeInterface
from core.agent.types import (
    AgentDefinition,
    AgentTaskSpec,
    AgentTaskResult,
    AgentTaskStatus,
)
from core.types import Event


class AgentRuntime(AgentRuntimeInterface):
    """Lifecycle manager for agent registration and task dispatch."""

    def __init__(
        self,
        identity_service: Any,
        metering: Any,
        event_bus: Any,
        audit_ledger: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._identity_service = identity_service
        self._metering = metering
        self._event_bus = event_bus
        self._audit_ledger = audit_ledger
        self._orchestrator = args[0] if len(args) > 0 else kwargs.get("orchestrator")
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register(self, agent_def: AgentDefinition) -> Any:
        """Registers a new agent identity and allocates its budget."""
        # Create identity via IdentityService
        identity = self._identity_service.register_agent(
            name=agent_def.agent_id,
            role=agent_def.role,
            parent_id="KERNEL",  # Agents registered at runtime are children of Kernel
            # In real impl, would be passed or generated
            signing_key=b"AGENT_KEY_STUB",
        )

        # Allocate budget in MeteringLayer
        self._metering.allocate(str(identity.id), "ai_tokens", agent_def.token_budget)

        # Store in local registry with its UUID (G4-01)
        self._registry[agent_def.agent_id] = {
            "definition": agent_def,
            "identity_id": identity.id,
        }

        # Emit event
        payload = {
            "agent_id": agent_def.agent_id,
            "role": agent_def.role,
            "capabilities": agent_def.capabilities,
        }

        event = Event.create("agent.registered", payload, origin_id=identity.id)
        # Self-correlated registration (G4-01)
        event = replace(event, correlation_id=event.event_id)

        sig = compute_event_signature(event)
        event = replace(event, signature=sig)
        self._event_bus.publish(event)

        self._audit_ledger.append(
            actor_id="RUNTIME",
            action="agent_registered",
            status="SUCCESS",
            metadata={"agent_id": agent_def.agent_id, "identity_id": str(identity.id)},
        )

        return identity

    def unregister(self, agent_id: str) -> None:
        """Revokes an agent identity and removes it from the registry."""
        if agent_id not in self._registry:
            raise KernelError(
                code=ErrorCode.AGENT_NOT_REGISTERED,
                message=f"Agent '{agent_id}' is not registered.",
            )

        # In this baseline, we revoke the identity using its UUID (G4-01 fix)
        try:
            reg_entry = self._registry[agent_id]
            identity_id = reg_entry["identity_id"]
            self._identity_service.revoke_identity(str(identity_id), actor_id="RUNTIME")
        except KernelError:
            # If identity not found, we still proceed with audit
            pass

        # Emit agent.unregistered event
        event = Event.create("agent.unregistered", {"agent_id": agent_id})
        # Self-correlated (G4-01)
        event = replace(event, correlation_id=event.event_id)

        sig = compute_event_signature(event)
        event = replace(event, signature=sig)
        self._event_bus.publish(event)

        self._audit_ledger.append(
            actor_id="RUNTIME",
            action="agent_unregistered",
            status="SUCCESS",
            metadata={"agent_id": agent_id},
        )
        del self._registry[agent_id]

    def execute(self, task: AgentTaskSpec) -> AgentTaskResult:
        """Delegates task execution to the orchestrator with exception wrapping."""
        try:
            if self._orchestrator is None:
                raise RuntimeError("Orchestrator is not configured.")
            result: AgentTaskResult = self._orchestrator.execute(task)
            return result
        except (KernelError, RuntimeError, ValueError) as e:
            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                status=AgentTaskStatus.FAILED,
                steps_taken=0,
                final_output=None,
                error=f"Runtime wrapper caught fault: {str(e)}",
                correlation_id=task.correlation_id,
            )
