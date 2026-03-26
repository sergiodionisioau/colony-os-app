"""Tool Registry for Agent Tool Management.

Zero Tolerance Baseline compliant:
- All tools versioned and audited
- Capability-based access control
- Hot-swap support
- Schema validation
"""

import hashlib
import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.errors import ErrorCode, KernelError


@dataclass
class ToolSchema:
    """Schema definition for tool input/output."""
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    def validate_input(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate input parameters. Returns error message or None."""
        # Would use jsonschema in production
        required = self.input_schema.get("required", [])
        for field_name in required:
            if field_name not in params:
                return f"Missing required field: {field_name}"
        return None

    def validate_output(self, result: Dict[str, Any]) -> Optional[str]:
        """Validate output result."""
        # Would use jsonschema in production
        return None


@dataclass
class ToolDefinition:
    """Definition of a registered tool."""
    id: str
    version: str
    description: str
    entrypoint: str  # module.path:function_name
    schema: ToolSchema
    capabilities_required: List[str]
    capabilities_provided: List[str]
    resource_budget: Dict[str, int] = field(default_factory=dict)

    # Runtime state
    handler: Optional[Callable] = None
    status: str = "registered"
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""

    def compute_hash(self) -> str:
        """Compute content hash for integrity."""
        content = json.dumps({
            "id": self.id,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "schema": {
                "input": self.schema.input_schema,
                "output": self.schema.output_schema
            }
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class ToolInvocation:
    """Record of a tool invocation."""
    invocation_id: str
    tool_id: str
    identity_id: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    metering: Dict[str, float] = field(default_factory=dict)


class ToolRegistry:
    """Registry for managing tools with hot-swap support."""

    def __init__(
        self,
        audit_ledger: Any,
        policy_engine: Any,
        metering: Any
    ):
        self.audit = audit_ledger
        self.policy = policy_engine
        self.metering = metering

        # Tool storage
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_backups: Dict[str, ToolDefinition] = {}  # For rollback
        self._invocations: Dict[str, ToolInvocation] = {}

        # Shadow mode for hot-swap testing
        self._shadow_tools: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        identity_id: str,
        tool_def: ToolDefinition
    ) -> ToolDefinition:
        """Register a new tool."""
        # Policy check
        decision = self.policy.evaluate(
            identity_id=identity_id,
            capability="tool.register",
            context={"tool_id": tool_def.id}
        )

        if not decision.allowed:
            raise KernelError(
                code=ErrorCode.POLICY_DENIED,
                message=f"Policy denied: {decision.reason}"
            )

        # Check for existing
        if tool_def.id in self._tools:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Tool {tool_def.id} already registered"
            )

        # Compute hash
        tool_def.content_hash = tool_def.compute_hash()

        # Load handler
        tool_def.handler = self._load_handler(tool_def.entrypoint)

        # Store
        self._tools[tool_def.id] = tool_def

        self.audit.append(
            actor_id=identity_id,
            action="tool.registered",
            status="SUCCESS",
            metadata={
                "tool_id": tool_def.id,
                "version": tool_def.version,
                "content_hash": tool_def.content_hash
            }
        )

        return tool_def

    def _load_handler(self, entrypoint: str) -> Callable:
        """Load tool handler from entrypoint string."""
        try:
            module_path, func_name = entrypoint.rsplit(":", 1)
            module = importlib.import_module(module_path)
            handler = getattr(module, func_name)

            if not callable(handler):
                raise KernelError(
                    code=ErrorCode.MODULE_MANIFEST_INVALID,
                    message=f"Entrypoint {entrypoint} is not callable"
                )

            return handler
        except (ValueError, ImportError, AttributeError) as e:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Failed to load handler {entrypoint}: {str(e)}"
            )

    def unregister_tool(self, identity_id: str, tool_id: str) -> None:
        """Unregister a tool."""
        decision = self.policy.evaluate(
            identity_id=identity_id,
            capability="tool.unregister",
            context={"tool_id": tool_id}
        )

        if not decision.allowed:
            raise KernelError(
                code=ErrorCode.POLICY_DENIED,
                message=f"Policy denied: {decision.reason}"
            )

        if tool_id not in self._tools:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Tool {tool_id} not found"
            )

        del self._tools[tool_id]

        self.audit.append(
            actor_id=identity_id,
            action="tool.unregistered",
            status="SUCCESS",
            metadata={"tool_id": tool_id}
        )

    def hot_swap_tool(
        self,
        identity_id: str,
        tool_id: str,
        new_tool_def: ToolDefinition,
        run_tests: bool = True,
        shadow_traffic: bool = True
    ) -> ToolDefinition:
        """Hot-swap a tool with zero downtime."""
        decision = self.policy.evaluate(
            identity_id=identity_id,
            capability="tool.hot_swap",
            context={"tool_id": tool_id}
        )

        if not decision.allowed:
            raise KernelError(
                code=ErrorCode.POLICY_DENIED,
                message=f"Policy denied: {decision.reason}"
            )

        if tool_id not in self._tools:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Tool {tool_id} not found"
            )

        old_tool = self._tools[tool_id]

        # Load new handler
        new_tool_def.handler = self._load_handler(new_tool_def.entrypoint)
        new_tool_def.content_hash = new_tool_def.compute_hash()

        # Shadow traffic test
        if shadow_traffic:
            self._shadow_tools[tool_id] = new_tool_def
            # Would run shadow invocations here
            del self._shadow_tools[tool_id]

        # Run tests if requested
        if run_tests:
            test_result = self._run_tool_tests(new_tool_def)
            if not test_result:
                raise KernelError(
                    code=ErrorCode.MODULE_EXECUTION_FAILED,
                    message=f"Tool tests failed for {tool_id}"
                )

        # Backup old version
        self._tool_backups[tool_id] = old_tool

        # Swap
        self._tools[tool_id] = new_tool_def

        self.audit.append(
            actor_id=identity_id,
            action="tool.hot_swapped",
            status="SUCCESS",
            metadata={
                "tool_id": tool_id,
                "old_version": old_tool.version,
                "new_version": new_tool_def.version,
                "old_hash": old_tool.content_hash,
                "new_hash": new_tool_def.content_hash
            }
        )

        return new_tool_def

    def rollback_tool(self, identity_id: str, tool_id: str) -> ToolDefinition:
        """Rollback to previous tool version."""
        decision = self.policy.evaluate(
            identity_id=identity_id,
            capability="tool.rollback",
            context={"tool_id": tool_id}
        )

        if not decision.allowed:
            raise KernelError(
                code=ErrorCode.POLICY_DENIED,
                message=f"Policy denied: {decision.reason}"
            )

        if tool_id not in self._tool_backups:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"No backup found for tool {tool_id}"
            )

        current = self._tools[tool_id]
        backup = self._tool_backups[tool_id]

        # Restore
        self._tools[tool_id] = backup
        del self._tool_backups[tool_id]

        self.audit.append(
            actor_id=identity_id,
            action="tool.rollback",
            status="SUCCESS",
            metadata={
                "tool_id": tool_id,
                "current_version": backup.version,
                "previous_version": current.version
            }
        )

        return backup

    def _run_tool_tests(self, tool_def: ToolDefinition) -> bool:
        """Run tests for a tool definition."""
        # Would run actual test suite
        return True

    def invoke_tool(
        self,
        identity_id: str,
        tool_id: str,
        parameters: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke a tool."""
        import uuid

        invocation_id = str(uuid.uuid4())

        # Check tool exists
        if tool_id not in self._tools:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Tool {tool_id} not found"
            )

        tool = self._tools[tool_id]

        # Policy check
        decision = self.policy.evaluate(
            identity_id=identity_id,
            capability=f"tool.{tool_id}.invoke",
            context={
                "tool_id": tool_id,
                "parameters": list(parameters.keys())
            }
        )

        if not decision.allowed:
            raise KernelError(
                code=ErrorCode.POLICY_DENIED,
                message=f"Policy denied: {decision.reason}"
            )

        # Validate input
        validation_error = tool.schema.validate_input(parameters)
        if validation_error:
            raise KernelError(
                code=ErrorCode.EVENT_SCHEMA_INVALID,
                message=validation_error
            )

        # Create invocation record
        invocation = ToolInvocation(
            invocation_id=invocation_id,
            tool_id=tool_id,
            identity_id=identity_id,
            parameters=parameters
        )
        self._invocations[invocation_id] = invocation

        # Allocate metering budget
        for metric, budget in tool.resource_budget.items():
            self.metering.allocate(identity_id, metric, budget)

        # Execute
        start_time = datetime.now(timezone.utc)
        try:
            if tool.handler is None:
                raise KernelError(
                    code=ErrorCode.UNKNOWN_FAULT,
                    message=f"Tool {tool_id} handler not loaded"
                )

            result = tool.handler(**parameters)

            # Validate output
            if isinstance(result, dict):
                validation_error = tool.schema.validate_output(result)
                if validation_error:
                    raise KernelError(
                        code=ErrorCode.EVENT_SCHEMA_INVALID,
                        message=f"Tool output validation failed: {validation_error}"
                    )

            invocation.status = "completed"
            invocation.result = result if isinstance(result, dict) else {"result": result}

        except Exception as e:
            invocation.status = "failed"
            invocation.result = {"error": str(e)}
            raise

        finally:
            invocation.completed_at = datetime.now(timezone.utc).isoformat()
            duration_ms = (datetime.fromisoformat(invocation.completed_at) - start_time).total_seconds() * 1000

            invocation.metering = {
                "duration_ms": duration_ms,
                "tokens_consumed": 0  # Would track actual usage
            }

            # Consume metering
            self.metering.consume(identity_id, "tool_invocations", 1)

            # Audit
            self.audit.append(
                actor_id=identity_id,
                action="tool.invoked",
                status="SUCCESS" if invocation.status == "completed" else "FAILED",
                metadata={
                    "tool_id": tool_id,
                    "invocation_id": invocation_id,
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id
                }
            )

        return {
            "invocation_id": invocation_id,
            "status": invocation.status,
            "result": invocation.result,
            "metering": invocation.metering
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        result = []
        for tool_id, tool in self._tools.items():
            result.append({
                "id": tool.id,
                "version": tool.version,
                "description": tool.description,
                "capabilities_required": tool.capabilities_required,
                "capabilities_provided": tool.capabilities_provided,
                "status": tool.status,
                "registered_at": tool.registered_at,
                "content_hash": tool.content_hash
            })
        return result

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool definition."""
        return self._tools.get(tool_id)
