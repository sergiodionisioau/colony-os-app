"""Tool Executor for LangGraph.

Integration point between LangGraph and the Tool Execution Layer.
Maps tool requests from graph state to tool execution.
"""

from typing import Any, Dict, List, Optional

from graphs.state import AgentState
from tools.schemas import ToolInput
from tools.router import run_tool


def execute_tool_node(state: AgentState) -> AgentState:
    """LangGraph node for executing tools.

    This node checks for pending tool requests in the state
    and executes them, updating the state with results.

    Args:
        state: Current agent state

    Returns:
        Updated state with tool results
    """
    # Check if there are pending tool requests
    pending_tools = state.get("pending_tools", [])

    if not pending_tools:
        # No tools to execute
        return state

    # Execute each pending tool
    tool_results = []
    for tool_request in pending_tools:
        try:
            # Create tool input
            tool_input = ToolInput(
                tool_name=tool_request["tool_name"],
                action_id=tool_request["action_id"],
                task_id=state["task_id"],
                parameters=tool_request.get("parameters", {}),
                timeout_ms=tool_request.get("timeout_ms", 30000),
            )

            # Execute tool (async in sync context)
            import asyncio

            output = asyncio.run(run_tool(tool_input))

            tool_results.append(
                {
                    "tool_name": tool_input.tool_name,
                    "action_id": tool_input.action_id,
                    "status": output.status.value,
                    "result": output.result,
                    "error": output.error,
                    "duration_ms": output.duration_ms,
                    "artifacts": output.artifacts,
                }
            )

        except Exception as e:
            tool_results.append(
                {
                    "tool_name": tool_request.get("tool_name", "unknown"),
                    "action_id": tool_request.get("action_id", "unknown"),
                    "status": "error",
                    "result": None,
                    "error": str(e),
                    "duration_ms": 0,
                    "artifacts": [],
                }
            )

    # Update state
    state["tool_results"] = tool_results
    state["pending_tools"] = []  # Clear pending

    return state


async def execute_tool_async(state: AgentState) -> AgentState:
    """Async version of execute_tool_node.

    Args:
        state: Current agent state

    Returns:
        Updated state with tool results
    """
    # Check if there are pending tool requests
    pending_tools = state.get("pending_tools", [])

    if not pending_tools:
        # No tools to execute
        return state

    # Execute each pending tool
    tool_results = []
    for tool_request in pending_tools:
        try:
            # Create tool input
            tool_input = ToolInput(
                tool_name=tool_request["tool_name"],
                action_id=tool_request["action_id"],
                task_id=state["task_id"],
                parameters=tool_request.get("parameters", {}),
                timeout_ms=tool_request.get("timeout_ms", 30000),
            )

            # Execute tool
            output = await run_tool(tool_input)

            tool_results.append(
                {
                    "tool_name": tool_input.tool_name,
                    "action_id": tool_input.action_id,
                    "status": output.status.value,
                    "result": output.result,
                    "error": output.error,
                    "duration_ms": output.duration_ms,
                    "artifacts": output.artifacts,
                }
            )

        except Exception as e:
            tool_results.append(
                {
                    "tool_name": tool_request.get("tool_name", "unknown"),
                    "action_id": tool_request.get("action_id", "unknown"),
                    "status": "error",
                    "result": None,
                    "error": str(e),
                    "duration_ms": 0,
                    "artifacts": [],
                }
            )

    # Update state
    state["tool_results"] = tool_results
    state["pending_tools"] = []  # Clear pending

    return state


def add_tool_request(
    state: AgentState,
    tool_name: str,
    parameters: Dict[str, Any],
    action_id: Optional[str] = None,
) -> AgentState:
    """Add a tool request to the state.

    Args:
        state: Current agent state
        tool_name: Name of the tool to execute
        parameters: Tool parameters
        action_id: Optional action ID (generated if not provided)

    Returns:
        Updated state with tool request added
    """
    import uuid

    if "pending_tools" not in state:
        state["pending_tools"] = []

    tool_request = {
        "tool_name": tool_name,
        "action_id": action_id or f"action-{uuid.uuid4().hex[:8]}",
        "parameters": parameters,
        "timeout_ms": 30000,
    }

    state["pending_tools"].append(tool_request)

    return state


def get_tool_results(state: AgentState) -> List[Dict[str, Any]]:
    """Get tool results from state.

    Args:
        state: Current agent state

    Returns:
        List of tool results
    """
    return state.get("tool_results", [])


def has_pending_tools(state: AgentState) -> bool:
    """Check if there are pending tool requests.

    Args:
        state: Current agent state

    Returns:
        True if there are pending tools
    """
    return bool(state.get("pending_tools", []))


def clear_tool_results(state: AgentState) -> AgentState:
    """Clear tool results from state.

    Args:
        state: Current agent state

    Returns:
        Updated state with tool results cleared
    """
    state["tool_results"] = []
    return state


class ToolExecutor:
    """Helper class for managing tool execution in LangGraph."""

    def __init__(self):
        """Initialize tool executor."""
        self.results: List[Dict[str, Any]] = []

    def request_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request a tool execution (synchronous wrapper).

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            action_id: Optional action ID

        Returns:
            Tool result
        """
        import uuid
        import asyncio

        action_id = action_id or f"action-{uuid.uuid4().hex[:8]}"

        # Create state-like structure
        state: Dict[str, Any] = {
            "task_id": "standalone",
            "pending_tools": [
                {
                    "tool_name": tool_name,
                    "action_id": action_id,
                    "parameters": parameters,
                    "timeout_ms": 30000,
                }
            ],
        }

        # Execute
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            updated_state = loop.run_until_complete(execute_tool_async(state))
        finally:
            loop.close()

        results = updated_state.get("tool_results", [])
        self.results.extend(results)

        return results[0] if results else {"error": "No results"}

    async def request_tool_async(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request a tool execution (async).

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            action_id: Optional action ID

        Returns:
            Tool result
        """
        import uuid

        action_id = action_id or f"action-{uuid.uuid4().hex[:8]}"

        # Create state-like structure
        state: Dict[str, Any] = {
            "task_id": "standalone",
            "pending_tools": [
                {
                    "tool_name": tool_name,
                    "action_id": action_id,
                    "parameters": parameters,
                    "timeout_ms": 30000,
                }
            ],
        }

        # Execute
        updated_state = await execute_tool_async(state)

        results = updated_state.get("tool_results", [])
        self.results.extend(results)

        return results[0] if results else {"error": "No results"}

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all accumulated results.

        Returns:
            List of all tool results
        """
        return self.results.copy()

    def clear_results(self) -> None:
        """Clear accumulated results."""
        self.results = []
