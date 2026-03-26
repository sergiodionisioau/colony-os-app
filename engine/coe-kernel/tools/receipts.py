"""Tool Receipts.

Audit trail for all tool executions.
Every tool action writes a receipt for accountability.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.schemas import PolicyDecision, ReceiptData, ToolInput, ToolOutput

# Receipt storage directory
RECEIPT_DIR = Path(
    os.environ.get(
        "COE_RECEIPT_DIR",
        "/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel/"
        "artifacts/receipts",
    )
)


def ensure_receipt_dir() -> Path:
    """Ensure receipt directory exists."""
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    return RECEIPT_DIR


def write_receipt(
    tool_input: ToolInput,
    tool_output: ToolOutput,
    policy_decision: PolicyDecision,
    started_at: str,
    artifacts: Optional[List[str]] = None,
) -> str:
    """Write a receipt for tool execution.

    Args:
        tool_input: Input envelope
        tool_output: Output envelope
        policy_decision: Policy evaluation result
        started_at: ISO timestamp when execution started
        artifacts: List of artifact paths created

    Returns:
        Path to written receipt file
    """
    ensure_receipt_dir()

    # Build receipt data
    receipt = ReceiptData(
        action_id=tool_input.action_id,
        task_id=tool_input.task_id,
        tool_name=tool_input.tool_name,
        input_summary=_sanitize_input(tool_input),
        output_summary=_sanitize_output(tool_output),
        policy_decision=policy_decision,
        started_at=started_at,
        completed_at=tool_output.timestamp,
        duration_ms=tool_output.duration_ms,
        status=tool_output.status,
        error=tool_output.error,
        artifacts=artifacts or [],
    )

    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{tool_input.task_id}_{tool_input.action_id}.json"
    receipt_path = RECEIPT_DIR / filename

    # Write receipt
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt.model_dump(), f, indent=2, default=str)

    return str(receipt_path)


def _sanitize_input(tool_input: ToolInput) -> Dict[str, Any]:
    """Sanitize input for receipt (remove sensitive data)."""
    params = tool_input.parameters.copy()

    # Redact potential secrets
    sensitive_keys = ["password", "token", "secret", "key", "api_key", "auth"]
    for key in list(params.keys()):
        if any(sk in key.lower() for sk in sensitive_keys):
            params[key] = "***REDACTED***"

    return {
        "tool_name": tool_input.tool_name,
        "action_id": tool_input.action_id,
        "task_id": tool_input.task_id,
        "parameters": params,
        "timeout_ms": tool_input.timeout_ms,
    }


def _sanitize_output(tool_output: ToolOutput) -> Dict[str, Any]:
    """Sanitize output for receipt (truncate large data)."""
    result = tool_output.result

    # Truncate large results
    if isinstance(result, str) and len(result) > 10000:
        result = result[:10000] + "... [truncated]"
    elif isinstance(result, (list, dict)) and len(str(result)) > 10000:
        result = f"[Large data: {len(str(result))} chars]"

    return {
        "status": tool_output.status.value,
        "result_preview": _preview_result(result),
        "error": tool_output.error,
        "artifact_count": len(tool_output.artifacts),
    }


def _preview_result(result: Any) -> Any:
    """Create a preview of result data."""
    if result is None:
        return None

    if isinstance(result, str):
        if len(result) > 500:
            return result[:500] + "..."
        return result

    if isinstance(result, (list, tuple)):
        if len(result) > 10:
            return f"[List with {len(result)} items]"
        return result

    if isinstance(result, dict):
        keys = list(result.keys())
        if len(keys) > 10:
            return f"[Dict with keys: {keys[:10]}...]"
        return {k: _preview_result(v) for k, v in result.items()}

    return result


def list_receipts(
    task_id: Optional[str] = None, tool_name: Optional[str] = None, limit: int = 100
) -> List[Dict[str, Any]]:
    """List receipts with optional filtering.

    Args:
        task_id: Filter by task ID
        tool_name: Filter by tool name
        limit: Maximum number of receipts to return

    Returns:
        List of receipt summaries
    """
    ensure_receipt_dir()

    receipts = []
    for receipt_file in sorted(RECEIPT_DIR.glob("*.json"), reverse=True):
        try:
            with open(receipt_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Apply filters
            if task_id and data.get("task_id") != task_id:
                continue
            if tool_name and data.get("tool_name") != tool_name:
                continue

            receipts.append(
                {
                    "path": str(receipt_file),
                    "action_id": data.get("action_id"),
                    "task_id": data.get("task_id"),
                    "tool_name": data.get("tool_name"),
                    "status": data.get("status"),
                    "started_at": data.get("started_at"),
                    "duration_ms": data.get("duration_ms"),
                }
            )

            if len(receipts) >= limit:
                break
        except (json.JSONDecodeError, IOError):
            continue

    return receipts


def get_receipt(action_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific receipt by action ID.

    Args:
        action_id: Action ID to look up

    Returns:
        Receipt data or None if not found
    """
    ensure_receipt_dir()

    for receipt_file in RECEIPT_DIR.glob("*.json"):
        try:
            with open(receipt_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("action_id") == action_id:
                return data
        except (json.JSONDecodeError, IOError):
            continue

    return None


def get_receipts_for_task(task_id: str) -> List[Dict[str, Any]]:
    """Get all receipts for a task.

    Args:
        task_id: Task ID to look up

    Returns:
        List of receipt data
    """
    ensure_receipt_dir()

    receipts = []
    for receipt_file in RECEIPT_DIR.glob("*.json"):
        try:
            with open(receipt_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("task_id") == task_id:
                receipts.append(data)
        except (json.JSONDecodeError, IOError):
            continue

    # Sort by started_at
    receipts.sort(key=lambda x: x.get("started_at", ""))
    return receipts
