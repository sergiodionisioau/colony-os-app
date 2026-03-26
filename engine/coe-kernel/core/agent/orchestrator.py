"""Agent Orchestrator implementation.

This module provides the Orchestrator which manages the finite reasoning loop
for agents, integrating metering, policy enforcement, and event propagation.
"""

import dataclasses
import json
import uuid
from typing import Any, Dict, List, Optional

from core.errors import KernelError
from core.event_bus.bus import compute_event_signature
from core.interfaces import AgentOrchestratorInterface, PolicyEngineInterface
from core.agent.types import (
    AgentTaskSpec,
    AgentTaskResult,
    AgentTaskStatus,
    AIMessage,
    ProviderConfig,
    AIResponse,
    RuntimeMode,
)
from core.types import Event


class Orchestrator(AgentOrchestratorInterface):
    """Finite-step execution controller for agent task processing."""

    def __init__(
        self,
        policy_engine: PolicyEngineInterface,
        event_bus: Any,
        metering: Any,
        audit_ledger: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._policy_engine = policy_engine
        self._event_bus = event_bus
        self._metering = metering
        self._audit_ledger = audit_ledger
        self._ai_provider = args[0] if len(args) > 0 else kwargs.get("ai_provider")
        self._memory_adapter = (
            args[1] if len(args) > 1 else kwargs.get("memory_adapter")
        )
        self._active_tasks: Dict[uuid.UUID, AgentTaskSpec] = {}

    def _build_provider_config(self, task: AgentTaskSpec) -> ProviderConfig:
        """Creates a provider config from task constraints."""
        mode = (
            RuntimeMode.SYSTEM
            if task.constraints.deterministic_mode
            else RuntimeMode.USER
        )
        return ProviderConfig(
            temperature=0.7,
            max_tokens=task.constraints.max_tokens,
            timeout_seconds=task.constraints.timeout_seconds,
            mode=mode,
        )

    def _process_capability_call(
        self, task: AgentTaskSpec, content: str, history: List[AIMessage]
    ) -> Optional[str]:
        """Processes a CALL: directive. Returns error string or None on success."""
        parts = content[5:].strip().split(None, 1)
        capability = parts[0]
        args = json.loads(parts[1]) if len(parts) > 1 else {}

        decision = self._policy_engine.evaluate(
            str(task.agent_id), capability, context=args
        )
        if not decision.allowed:
            return f"Policy denied capability '{capability}': {decision.reason}"

        event = self._create_event(task, f"agent.action.{capability}", args)
        self._event_bus.publish(event)
        history.append(
            AIMessage(role="system", content=f"Action '{capability}' published.")
        )
        return None

    def execute(self, task: AgentTaskSpec) -> AgentTaskResult:
        """Runs the agent reasoning loop for a finite number of steps."""
        self._active_tasks[task.task_id] = task
        self._audit_ledger.append(
            actor_id=str(task.agent_id),
            action="agent.task_started",
            status="SUCCESS",
            metadata={
                "task_id": str(task.task_id),
                "correlation_id": str(task.correlation_id),
            },
        )

        history: List[AIMessage] = []
        final_output: Optional[str] = None
        error: Optional[str] = None
        status = AgentTaskStatus.COMPLETED
        steps_taken = 0
        config = self._build_provider_config(task)

        try:
            for step in range(task.constraints.max_reasoning_steps):
                steps_taken = step + 1
                prompt = task.instruction if not history else "Continue."

                if self._ai_provider is None:
                    raise RuntimeError("AIProvider is not configured.")
                response: AIResponse = self._ai_provider.generate(
                    prompt=prompt,
                    history=history,
                    config=config,
                )

                self._metering.record(
                    task.agent_id,
                    "ai_tokens",
                    float(response.tokens_in + response.tokens_out),
                )
                self._metering.record(
                    task.agent_id,
                    "ai_cost_usd",
                    float(response.cost_usd),
                )

                history.append(AIMessage(role="assistant", content=response.content))

                if response.content.startswith("COMPLETE:"):
                    final_output = response.content[9:].strip()
                    break

                if response.content.startswith("CALL:"):
                    try:
                        cap_error = self._process_capability_call(
                            task, response.content, history
                        )
                        if cap_error:
                            error = cap_error
                            status = AgentTaskStatus.FAILED
                            break
                    except (json.JSONDecodeError, IndexError) as exc:
                        error = f"Failed to parse agent action: {str(exc)}"
                        status = AgentTaskStatus.FAILED
                        break

            else:
                if not final_output and status != AgentTaskStatus.FAILED:
                    status = AgentTaskStatus.EXCEEDED
                    error = "Reasoning steps exhausted without completion."

        except KernelError as exc:
            error = str(exc)
            status = AgentTaskStatus.FAILED
        except (RuntimeError, ValueError, TypeError, TimeoutError, OSError) as exc:
            error = f"Unexpected orchestrator fault: {str(exc)}"
            status = AgentTaskStatus.FAILED

        result = AgentTaskResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            status=status,
            steps_taken=steps_taken,
            final_output=final_output,
            error=error,
            correlation_id=task.correlation_id,
        )
        return self._finalize_task(task, result)

    def _finalize_task(
        self,
        task: AgentTaskSpec,
        result: AgentTaskResult,
    ) -> AgentTaskResult:
        """Emits completion/failure events, audits, and cleans up active tasks."""
        if result.status == AgentTaskStatus.COMPLETED:
            self._event_bus.publish(
                self._create_event(
                    task,
                    "agent.task_completed",
                    {
                        "task_id": str(task.task_id),
                        "steps_taken": result.steps_taken,
                        "output": result.final_output,
                    },
                )
            )
        else:
            self._event_bus.publish(
                self._create_event(
                    task,
                    "agent.task_failed",
                    {
                        "task_id": str(task.task_id),
                        "reason": result.error or "Unknown",
                        "step_at_failure": result.steps_taken,
                    },
                )
            )

        self._audit_ledger.append(
            actor_id=str(task.agent_id),
            action="agent.task_finished",
            status=result.status.value.upper(),
            metadata={"task_id": str(task.task_id), "steps_taken": result.steps_taken},
        )

        del self._active_tasks[task.task_id]
        return result

    def get_active_tasks(self) -> List[uuid.UUID]:
        """Returns the list of currently active task IDs."""
        return list(self._active_tasks.keys())

    def _create_event(
        self, task: AgentTaskSpec, event_type: str, payload: Dict[str, Any]
    ) -> Event:
        """Helper to create a signed event with the task's correlation_id."""
        event = Event.create(
            event_type,
            payload,
            correlation_id=task.correlation_id,
            origin_id=task.agent_id,
        )
        # Signature computation requires the object, then we replace it
        sig = compute_event_signature(event)
        return dataclasses.replace(event, signature=sig)
