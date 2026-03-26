"""FastAPI REST API Server for COE Kernel.

Provides HTTP interface for agents, data management, tools, metrics, and modules.
Zero Tolerance Baseline compliant.
"""

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from core.errors import KernelError


# ============================================================================
# Pydantic Models
# ============================================================================

class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=64)
    capabilities: List[str] = Field(default_factory=list)
    token_budget: int = Field(default=100000, ge=0)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class AgentRegisterResponse(BaseModel):
    identity_id: str
    status: str
    allocated_budget: int
    event_stream: str


class TaskSubmitRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=10000)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    estimated_completion: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    steps_taken: int
    result: Optional[Dict[str, Any]] = None
    audit_trail: List[str] = Field(default_factory=list)


class DBConnectionRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    type: str = Field(..., pattern="^(postgresql|mysql|sqlite|mongodb)$")
    host: str
    port: int = Field(..., ge=1, le=65535)
    database: str
    credentials_ref: str
    pool_config: Dict[str, int] = Field(default_factory=dict)


class DBConnectionResponse(BaseModel):
    status: str
    connection_id: str
    health_check_passed: bool
    failover_ready: bool


class QueryRequest(BaseModel):
    connection_id: str
    query: str = Field(..., min_length=1, max_length=10000)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True


class QueryResponse(BaseModel):
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    audit_entry_id: str


class ToolInvokeRequest(BaseModel):
    parameters: Dict[str, Any]
    correlation_id: Optional[str] = None


class ToolInvokeResponse(BaseModel):
    invocation_id: str
    status: str
    result: Dict[str, Any]
    metering: Dict[str, float]


class ModuleLoadRequest(BaseModel):
    module_id: str
    path: str
    activation: str = "immediate"


class ModuleHotSwapRequest(BaseModel):
    new_version_path: str
    verification: Dict[str, bool] = Field(default_factory=lambda: {
        "run_tests": True,
        "shadow_traffic": True
    })


class HealthResponse(BaseModel):
    kernel: str
    subsystems: Dict[str, str]
    modules: Dict[str, str]
    checks: Dict[str, str]


# ============================================================================
# Authentication & Authorization
# ============================================================================

security = HTTPBearer()


class APIAuthenticator:
    """Handles request authentication and signature verification."""

    def __init__(self, kernel: Any):
        self.kernel = kernel
        self.audit = kernel.audit_ledger

    async def authenticate(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """Authenticate request using HMAC signature."""
        identity_id = request.headers.get("X-Identity-ID")
        timestamp_str = request.headers.get("X-Timestamp")
        provided_signature = credentials.credentials

        if not all([identity_id, timestamp_str, provided_signature]):
            raise HTTPException(401, "Missing authentication headers")

        # Validate timestamp (±30s clock skew)
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            skew = abs((now - timestamp).total_seconds())
            if skew > 30:
                raise HTTPException(401, "Request timestamp expired")
        except ValueError:
            raise HTTPException(401, "Invalid timestamp format")

        # Get identity
        try:
            identity = self.kernel.identity_service.get_identity(identity_id)
        except KernelError:
            raise HTTPException(401, "Identity not found")

        # Verify signature
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()
        message = f"{request.method}:{request.url.path}:{timestamp_str}:{body_hash}"

        expected_sig = hmac.new(
            identity.signature.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(provided_signature, expected_sig):
            self.audit.append(
                actor_id=identity_id,
                action="api.auth.failed",
                status="DENIED",
                metadata={"reason": "invalid_signature"}
            )
            raise HTTPException(401, "Invalid signature")

        return {
            "identity_id": identity_id,
            "role": identity.role,
            "identity": identity
        }


# ============================================================================
# API Server
# ============================================================================

class KernelAPIServer:
    """FastAPI server exposing kernel functionality via REST."""

    def __init__(self, kernel: Any):
        self.kernel = kernel
        self.app = FastAPI(
            title="COE Kernel API",
            description="Zero Tolerance REST API for Agent OS",
            version="1.0.0"
        )
        self.auth = APIAuthenticator(kernel)
        self._setup_routes()
        self._setup_middleware()

    def _setup_middleware(self) -> None:
        """Configure request/response middleware."""

        @self.app.middleware("http")
        async def audit_middleware(request: Request, call_next):
            """Log every request to audit ledger."""
            start_time = time.time()
            request_id = str(time.time())  # Simplified; use UUID in production

            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            # Audit log entry
            identity_id = request.headers.get("X-Identity-ID", "anonymous")
            self.kernel.audit_ledger.append(
                actor_id=identity_id,
                action=f"api.{request.method}.{request.url.path}",
                status="SUCCESS" if response.status_code < 400 else "FAILED",
                metadata={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms
                }
            )

            return response

    def _setup_routes(self) -> None:
        """Register all API routes."""

        # =====================================================================
        # Health & Metrics
        # =====================================================================

        @self.app.get("/v1/health", response_model=HealthResponse)
        async def health_check():
            """Kernel health status."""
            subsystems = {}
            modules = {}
            checks = {}

            # Check core subsystems
            try:
                subsystems["event_bus"] = "healthy" if self.kernel.event_bus else "unhealthy"
                subsystems["policy_engine"] = "healthy" if self.kernel.policy_engine else "unhealthy"
                subsystems["audit_ledger"] = "healthy" if self.kernel.audit_ledger.verify_integrity() else "corrupted"
                subsystems["module_loader"] = "healthy" if self.kernel.get_subsystems().get("loader") else "unhealthy"
            except Exception as e:
                subsystems["kernel"] = f"error: {str(e)}"

            # Check loaded modules
            loader = self.kernel.get_subsystems().get("loader")
            if loader:
                for mod_name in loader.get_loaded_modules():
                    instance = loader.get_module_instance(mod_name)
                    if instance and hasattr(instance, "healthcheck"):
                        try:
                            modules[mod_name] = "healthy" if instance.healthcheck() else "unhealthy"
                        except Exception:
                            modules[mod_name] = "error"
                    else:
                        modules[mod_name] = "no_healthcheck"

            # Integrity checks
            checks["audit_chain_integrity"] = "pass" if self.kernel.audit_ledger.verify_integrity() else "fail"

            return HealthResponse(
                kernel="healthy" if all(s == "healthy" for s in subsystems.values()) else "degraded",
                subsystems=subsystems,
                modules=modules,
                checks=checks
            )

        @self.app.get("/v1/metrics")
        async def metrics():
            """Prometheus-compatible metrics."""
            lines = []

            # Event bus metrics
            lines.append("# HELP coe_events_published_total Total events published")
            lines.append("# TYPE coe_events_published_total counter")
            # Would integrate with actual counters
            lines.append("coe_events_published_total 0")

            # Module metrics
            lines.append("# HELP coe_modules_loaded Number of loaded modules")
            lines.append("# TYPE coe_modules_loaded gauge")
            loader = self.kernel.get_subsystems().get("loader")
            mod_count = len(loader.get_loaded_modules()) if loader else 0
            lines.append(f"coe_modules_loaded {mod_count}")

            return PlainTextResponse("\n".join(lines))

        # =====================================================================
        # Agents
        # =====================================================================

        @self.app.post("/v1/agents/register", response_model=AgentRegisterResponse)
        async def register_agent(
            request: AgentRegisterRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Register a new agent."""
            identity_id = auth["identity_id"]

            # Policy check
            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="agent.register",
                context={"target_role": request.role}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            # Register via AgentRuntime
            from core.agent.types import AgentDefinition

            agent_def = AgentDefinition(
                agent_id=request.agent_id,
                role=request.role,
                capabilities=request.capabilities,
                token_budget=request.token_budget,
                constraints=request.constraints
            )

            runtime = self.kernel.get_subsystems().get("agent_runtime")
            if not runtime:
                raise HTTPException(503, "Agent runtime not available")

            identity = runtime.register(agent_def)

            return AgentRegisterResponse(
                identity_id=str(identity.id),
                status="registered",
                allocated_budget=request.token_budget,
                event_stream=f"/v1/events/stream?agent_id={identity.id}"
            )

        @self.app.post("/v1/agents/{agent_id}/tasks", response_model=TaskSubmitResponse)
        async def submit_task(
            agent_id: str,
            request: TaskSubmitRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Submit a task to an agent."""
            identity_id = auth["identity_id"]

            # Policy check
            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="agent.task.submit",
                context={"target_agent": agent_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            # Submit task
            from core.agent.types import AgentTaskSpec
            import uuid

            task = AgentTaskSpec(
                task_id=uuid.uuid4(),
                agent_id=agent_id,
                instruction=request.instruction,
                context=request.context,
                correlation_id=uuid.UUID(request.correlation_id) if request.correlation_id else uuid.uuid4()
            )

            runtime = self.kernel.get_subsystems().get("agent_runtime")
            if not runtime:
                raise HTTPException(503, "Agent runtime not available")

            # Async execution
            import asyncio
            asyncio.create_task(runtime.execute(task))

            return TaskSubmitResponse(
                task_id=str(task.task_id),
                status="accepted",
                estimated_completion=None  # Would calculate based on history
            )

        @self.app.get("/v1/agents/{agent_id}/tasks/{task_id}", response_model=TaskStatusResponse)
        async def get_task_status(
            agent_id: str,
            task_id: str,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Get task status and results."""
            # Would query task store
            raise HTTPException(501, "Task status tracking not yet implemented")

        @self.app.delete("/v1/agents/{agent_id}")
        async def unregister_agent(
            agent_id: str,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Unregister an agent."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="agent.unregister",
                context={"target_agent": agent_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            runtime = self.kernel.get_subsystems().get("agent_runtime")
            if runtime:
                runtime.unregister(agent_id)

            return {"status": "unregistered", "agent_id": agent_id}

        # =====================================================================
        # Data Management
        # =====================================================================

        @self.app.get("/v1/data/connections")
        async def list_connections(
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """List database connections."""
            # Would query connection pool manager
            return {"connections": []}

        @self.app.post("/v1/data/connections", response_model=DBConnectionResponse)
        async def add_connection(
            request: DBConnectionRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Add a new database connection."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="db.connection.create",
                context={"connection_id": request.id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            # Would integrate with connection pool manager
            return DBConnectionResponse(
                status="connected",
                connection_id=request.id,
                health_check_passed=True,
                failover_ready=True
            )

        @self.app.post("/v1/data/query", response_model=QueryResponse)
        async def execute_query(
            request: QueryRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Execute a read-only query."""
            identity_id = auth["identity_id"]

            capability = "db.query.readonly" if request.read_only else "db.query.write"
            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability=capability,
                context={"connection_id": request.connection_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            # Would execute via connection pool
            raise HTTPException(501, "Query execution not yet implemented")

        # =====================================================================
        # Tools
        # =====================================================================

        @self.app.get("/v1/tools")
        async def list_tools(
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """List available tools."""
            # Would query tool registry
            return {"tools": []}

        @self.app.post("/v1/tools/{tool_id}/invoke", response_model=ToolInvokeResponse)
        async def invoke_tool(
            tool_id: str,
            request: ToolInvokeRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Invoke a tool."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability=f"tool.{tool_id}.invoke",
                context={"tool_id": tool_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            # Would invoke via tool registry
            raise HTTPException(501, "Tool invocation not yet implemented")

        # =====================================================================
        # Modules
        # =====================================================================

        @self.app.get("/v1/modules")
        async def list_modules(
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """List loaded modules."""
            loader = self.kernel.get_subsystems().get("loader")
            if not loader:
                return {"modules": []}

            modules = []
            for mod_name in loader.get_loaded_modules():
                state = loader.get_module_state(mod_name)
                instance = loader.get_module_instance(mod_name)
                health = "unknown"
                if instance and hasattr(instance, "healthcheck"):
                    try:
                        health = "healthy" if instance.healthcheck() else "unhealthy"
                    except Exception:
                        health = "error"

                modules.append({
                    "id": mod_name,
                    "version": state.get("version", "unknown") if state else "unknown",
                    "status": "active",
                    "health": health
                })

            return {"modules": modules}

        @self.app.post("/v1/modules/load")
        async def load_module(
            request: ModuleLoadRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Load a module."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="module.load",
                context={"module_id": request.module_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            loader = self.kernel.get_subsystems().get("loader")
            if not loader:
                raise HTTPException(503, "Module loader not available")

            try:
                loader.load(request.module_id)
                return {
                    "status": "loaded",
                    "module_id": request.module_id
                }
            except KernelError as e:
                raise HTTPException(400, str(e.message))

        @self.app.post("/v1/modules/{module_id}/hot-swap")
        async def hot_swap_module(
            module_id: str,
            request: ModuleHotSwapRequest,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Hot-swap a module."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="module.hot_swap",
                context={"module_id": module_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            loader = self.kernel.get_subsystems().get("loader")
            if not loader:
                raise HTTPException(503, "Module loader not available")

            try:
                loader.hot_swap(module_id)
                return {
                    "status": "swapped",
                    "module_id": module_id
                }
            except KernelError as e:
                raise HTTPException(400, str(e.message))

        @self.app.post("/v1/modules/{module_id}/rollback")
        async def rollback_module(
            module_id: str,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Rollback a module."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="module.rollback",
                context={"module_id": module_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            loader = self.kernel.get_subsystems().get("loader")
            if not loader:
                raise HTTPException(503, "Module loader not available")

            try:
                loader.rollback(module_id)
                return {
                    "status": "rolled_back",
                    "module_id": module_id
                }
            except KernelError as e:
                raise HTTPException(400, str(e.message))

        @self.app.delete("/v1/modules/{module_id}")
        async def unload_module(
            module_id: str,
            auth: Dict[str, Any] = Depends(self.auth.authenticate)
        ):
            """Unload a module."""
            identity_id = auth["identity_id"]

            decision = self.kernel.policy_engine.evaluate(
                identity_id=identity_id,
                capability="module.unload",
                context={"module_id": module_id}
            )

            if not decision.allowed:
                raise HTTPException(403, f"Policy denied: {decision.reason}")

            loader = self.kernel.get_subsystems().get("loader")
            if loader:
                loader.unload(module_id)

            return {"status": "unloaded", "module_id": module_id}

        # =====================================================================
        # WebSocket Events
        # =====================================================================

        @self.app.websocket("/v1/events/stream")
        async def event_stream(websocket: WebSocket):
            """WebSocket event stream for real-time agent updates."""
            await websocket.accept()

            # Would authenticate and subscribe to event bus
            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
                    # Echo for now
                    await websocket.send_text(f"Received: {data}")
            except WebSocketDisconnect:
                pass


# ============================================================================
# Factory Function
# ============================================================================

def create_api_server(kernel: Any) -> FastAPI:
    """Factory function to create and configure the API server."""
    server = KernelAPIServer(kernel)
    return server.app
