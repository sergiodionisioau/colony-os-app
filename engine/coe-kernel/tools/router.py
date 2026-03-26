"""Tool Router.

Central router for tool execution.
Handles policy evaluation, execution, and receipt generation.
"""

import time
from datetime import datetime
from typing import Any, Dict

from tools.policies import evaluate_policy
from tools.receipts import write_receipt
from tools.registry import get_tool, tool_exists
from tools.schemas import PolicyDecision, ToolInput, ToolOutput, ToolStatus


def emit_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Emit event to event bus if available.

    Args:
        event_type: Type of event
        payload: Event payload
    """
    try:
        from orchestrator.events import emit

        emit(event_type, payload)
    except Exception:
        # Event bus not available, silently ignore
        pass


async def run_tool(tool_input: ToolInput) -> ToolOutput:
    """Execute a tool with full policy and audit handling.

    This is the main entry point for tool execution.
    It handles:
    1. Tool lookup
    2. Policy evaluation
    3. Execution
    4. Receipt generation
    5. Event emission

    Args:
        tool_input: Validated tool input envelope

    Returns:
        Tool output envelope
    """
    started_at = datetime.utcnow().isoformat()
    start_time = time.time()

    # Emit request event
    emit_event(
        "tool.requested",
        {
            "action_id": tool_input.action_id,
            "task_id": tool_input.task_id,
            "tool_name": tool_input.tool_name,
        },
    )

    # Check tool exists
    if not tool_exists(tool_input.tool_name):
        duration_ms = int((time.time() - start_time) * 1000)
        output = ToolOutput(
            tool_name=tool_input.tool_name,
            action_id=tool_input.action_id,
            task_id=tool_input.task_id,
            status=ToolStatus.ERROR,
            error=f"Tool not found: {tool_input.tool_name}",
            duration_ms=duration_ms,
        )

        # Write receipt
        write_receipt(
            tool_input=tool_input,
            tool_output=output,
            policy_decision=PolicyDecision.BLOCK,
            started_at=started_at,
        )

        emit_event(
            "tool.failed",
            {"action_id": tool_input.action_id, "reason": "tool_not_found"},
        )

        return output

    # Get tool metadata
    tool = get_tool(tool_input.tool_name)

    # Evaluate policy
    policy_check = evaluate_policy(
        tool_input.tool_name, tool_input.parameters, {"task_id": tool_input.task_id}
    )

    if policy_check.decision == PolicyDecision.BLOCK:
        duration_ms = int((time.time() - start_time) * 1000)
        output = ToolOutput(
            tool_name=tool_input.tool_name,
            action_id=tool_input.action_id,
            task_id=tool_input.task_id,
            status=ToolStatus.BLOCKED,
            error=f"Policy blocked: {policy_check.reason}",
            duration_ms=duration_ms,
        )

        # Write receipt
        write_receipt(
            tool_input=tool_input,
            tool_output=output,
            policy_decision=policy_check.decision,
            started_at=started_at,
        )

        emit_event(
            "tool.blocked",
            {
                "action_id": tool_input.action_id,
                "reason": policy_check.reason,
                "risk_score": policy_check.risk_score,
            },
        )

        return output

    # Emit allowed event
    emit_event(
        "tool.allowed",
        {"action_id": tool_input.action_id, "risk_score": policy_check.risk_score},
    )

    # Execute tool
    try:
        output = await tool.handler(
            tool_input.action_id, tool_input.task_id, tool_input.parameters
        )

        # Write receipt
        receipt_path = write_receipt(
            tool_input=tool_input,
            tool_output=output,
            policy_decision=policy_check.decision,
            started_at=started_at,
            artifacts=output.artifacts,
        )

        output.receipt_path = receipt_path

        # Emit completion event
        event_type = (
            "tool.completed" if output.status == ToolStatus.SUCCESS else "tool.failed"
        )
        emit_event(
            event_type,
            {
                "action_id": tool_input.action_id,
                "tool_name": tool_input.tool_name,
                "status": output.status.value,
                "duration_ms": output.duration_ms,
            },
        )

        return output

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        output = ToolOutput(
            tool_name=tool_input.tool_name,
            action_id=tool_input.action_id,
            task_id=tool_input.task_id,
            status=ToolStatus.ERROR,
            error=f"Execution error: {str(e)}",
            duration_ms=duration_ms,
        )

        # Write receipt
        write_receipt(
            tool_input=tool_input,
            tool_output=output,
            policy_decision=policy_check.decision,
            started_at=started_at,
        )

        emit_event(
            "tool.failed",
            {
                "action_id": tool_input.action_id,
                "reason": "execution_error",
                "error": str(e),
            },
        )

        return output


async def run_tool_from_dict(params: Dict[str, Any]) -> ToolOutput:
    """Execute a tool from a dictionary of parameters.

    Args:
        params: Dictionary containing tool_name, action_id, task_id, parameters

    Returns:
        Tool output envelope
    """
    # Validate input
    tool_input = ToolInput(**params)

    # Execute
    return await run_tool(tool_input)


def validate_tool_input(tool_name: str, parameters: Dict[str, Any]) -> tuple:
    """Validate tool input without executing.

    Args:
        tool_name: Name of the tool
        parameters: Tool parameters

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tool_exists(tool_name):
        return False, f"Tool not found: {tool_name}"

    try:
        tool = get_tool(tool_name)
        tool.input_schema(**parameters)
        return True, None
    except Exception as e:
        return False, str(e)
