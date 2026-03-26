"""Enhanced COE Kernel bootstrapper with REST API and new subsystems.

Initializes and wires the core components plus:
- REST API Server (FastAPI)
- Database Connection Pool Manager
- Tool Registry
"""

import os
import secrets
from typing import Any, Dict

import yaml
from jsonschema import validate, ValidationError

from core.errors import ErrorCode, KernelError
from core.schema import CONFIG_SCHEMA
from core.audit.ledger import AuditLedger
from core.event_bus.bus import EventBus, SchemaRegistry
from core.event_bus.store import EventStore
from core.event_bus.backpressure import BackpressureController
from core.event_bus.dlq import DeadLetterQueue
from core.identity.service import IdentityService
from core.metering.node import MeteringLayer
from core.module_loader.loader import ModuleLoader
from core.module_loader.registry import ModuleRegistry
from core.policy.engine import PolicyEngine
from core.agent.scope_enforcer import PolicyScopeEnforcer
from core.agent.types import PolicyScopeBinding
from core.interfaces import PolicyEngineInterface
from core.secrets.vault import SecretsVault
from core.state_engine.engine import StateEngine
from core.types import EventBusDependencies

# New components
from core.api.server import create_api_server
from core.api.extensions import create_business_router, create_ui_router
from core.persistence.connection_pool import ConnectionPoolManager
from core.tools.registry import ToolRegistry


class KernelBootstrap:
    """Enhanced kernel with REST API and data management."""

    KERNEL_VERSION = "1.1.0"  # Bumped for new features

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize all subsystems sequentially."""
        self._validate_config(config)
        self.config = config

        # 1. Audit Ledger MUST be first
        audit_cfg = config.get("audit", {})
        self.audit_ledger = AuditLedger(
            storage_path=audit_cfg.get("storage_path")
            or config.get("audit_path", "audit.log"),
            genesis_constant=audit_cfg.get("genesis_constant")
            or config.get("genesis", "SYSTEM_START"),
        )

        # 2. Event Bus
        self.event_bus = self._init_event_bus(config)

        # 3. Identity
        rbac_cfg = config.get("rbac", {})
        self.identity_service = IdentityService(
            audit_ledger=self.audit_ledger,
            role_schema=rbac_cfg.get("roles") or config.get("role_schema", {}),
        )

        # 4. Policy Engine
        self.policy_engine = self._init_policy_engine(config)

        # 5. Secrets Vault
        secrets_vault = self._init_secrets_vault(config)

        # 6. Module Loader
        self.registry = ModuleRegistry(audit_ledger=self.audit_ledger)
        module_loader = self._init_module_loader(config)

        # 7. Metering
        metering_layer = MeteringLayer(
            policy_engine=self.policy_engine, event_bus=self.event_bus
        )

        # 8. State Engine
        state_engine = StateEngine(audit_ledger=self.audit_ledger)

        # 9. Connection Pool Manager (NEW)
        connection_pool = self._init_connection_pool(secrets_vault, metering_layer)

        # 10. Tool Registry (NEW)
        tool_registry = ToolRegistry(
            audit_ledger=self.audit_ledger,
            policy_engine=self.policy_engine,
            metering=metering_layer
        )

        # Group secondary subsystems
        self._subsystems: Dict[str, Any] = {
            "vault": secrets_vault,
            "loader": module_loader,
            "metering": metering_layer,
            "state": state_engine,
            "config": config,
            "connection_pool": connection_pool,
            "tool_registry": tool_registry,
        }

        self._register_event_schemas()
        self._run_bootstrap_sequence()

        # 11. REST API Server (NEW) - initialized after bootstrap
        self.api_server = None
        if config.get("api", {}).get("enabled", True):
            self.api_server = create_api_server(self)

    def _init_event_bus(self, config: Dict[str, Any]) -> EventBus:
        """Isolated Event Bus initialization."""
        event_cfg = config.get("events", {})
        event_store = EventStore(
            storage_path=event_cfg.get("store_path")
            or config.get("event_store_path", "events/"),
            segment_size=event_cfg.get("segment_size")
            or config.get("event_segment_size", 100000),
        )
        backpressure = BackpressureController(
            activation_depth=event_cfg.get("backpressure_activation_depth")
            or config.get("event_backpressure_activation", 10000),
            deactivation_depth=event_cfg.get("backpressure_deactivation_depth")
            or config.get("event_backpressure_deactivation", 7000),
        )
        dlq = DeadLetterQueue(
            storage_path=config.get("event_storage_path", "./data/events")
        )

        deps = EventBusDependencies(
            audit_ledger=self.audit_ledger,
            event_store=event_store,
            backpressure=backpressure,
            dlq=dlq,
            schema_registry=SchemaRegistry(),
        )
        return EventBus(deps=deps)

    def _init_policy_engine(self, config: Dict[str, Any]) -> PolicyEngineInterface:
        """Isolated Policy Engine initialization."""
        base_policy = PolicyEngine(
            identity_service=self.identity_service,
            audit_ledger=self.audit_ledger,
        )

        # Load rules from file if specified
        rules_path = config.get("policy", {}).get("rules_path")
        if rules_path and os.path.exists(rules_path):
            import json
            with open(rules_path, "r") as f:
                rules = json.load(f)
            base_policy.load_rules(rules)

        scope_cfg = config.get("policy", {}).get("agent_scopes", [])
        bindings = [
            PolicyScopeBinding(
                agent_role=s["role"], allowed_capabilities=s["capabilities"]
            )
            for s in scope_cfg
        ]
        return PolicyScopeEnforcer(
            base_policy=base_policy,
            identity_service=self.identity_service,
            bindings=bindings,
        )

    def _init_secrets_vault(self, config: Dict[str, Any]) -> SecretsVault:
        """Isolated Secrets Vault initialization."""
        secrets_cfg = config.get("secrets", {})
        return SecretsVault(
            data_path=secrets_cfg.get("data_path")
            or config.get("secrets_data_path", "secrets.json"),
            salt_path=secrets_cfg.get("salt_path")
            or config.get("secrets_salt_path", "salt.bin"),
            audit_ledger=self.audit_ledger,
            passphrase=(
                secrets_cfg.get("passphrase")
                or os.environ.get(secrets_cfg.get("passphrase_env_var", ""))
                or config.get("vault_passphrase", "default_passphrase")
            ),
        )

    def _init_module_loader(self, config: Dict[str, Any]) -> ModuleLoader:
        """Isolated Module Loader initialization."""
        mod_cfg = config.get("modules", {})
        return ModuleLoader(
            {
                "modules_path": mod_cfg.get("plugins_dir")
                or config.get("modules_path", "modules/"),
                "forbidden_imports": mod_cfg.get("forbidden_imports")
                or config.get(
                    "forbidden_imports",
                    [
                        "os",
                        "sys",
                        "subprocess",
                        "shutil",
                        "socket",
                        "http",
                        "urllib",
                        "ctypes",
                        "importlib",
                        "multiprocessing",
                        "signal",
                    ],
                ),
                "audit_ledger": self.audit_ledger,
                "registry": self.registry,
                "event_bus": self.event_bus,
                "kernel_version": self.KERNEL_VERSION,
            }
        )

    def _init_connection_pool(
        self,
        secrets_vault: SecretsVault,
        metering: MeteringLayer
    ) -> ConnectionPoolManager:
        """Initialize connection pool manager."""
        return ConnectionPoolManager(
            audit_ledger=self.audit_ledger,
            secrets_vault=secrets_vault,
            policy_engine=self.policy_engine
        )

    def _register_event_schemas(self) -> None:
        """Populates the SchemaRegistry with event definitions."""
        registry = self.event_bus.schema_registry

        # Agent Lifecycle
        registry.register("agent.registered", ["agent_id", "role", "capabilities"])
        registry.register("agent.unregistered", ["agent_id"])

        # Agent Tasking
        registry.register(
            "agent.task_submitted",
            ["task_id", "agent_id", "instruction", "constraints", "correlation_id"],
        )
        registry.register(
            "agent.task_completed",
            ["task_id", "steps_taken", "output", "correlation_id"],
        )
        registry.register(
            "agent.task_failed",
            ["task_id", "reason", "step_at_failure", "correlation_id"],
        )

        # Improvement Engine
        registry.register(
            "improvement.patch_proposed", ["patch_id", "target_module", "proposed_by"]
        )
        registry.register("improvement.patch_approved", ["patch_id", "approver_id"])
        registry.register(
            "improvement.patch_applied", ["patch_id", "module_name", "new_version"]
        )
        registry.register("improvement.patch_rejected", ["patch_id", "reason"])

        # API Events (NEW)
        registry.register(
            "api.request.received",
            ["endpoint", "method", "identity_id", "request_id"]
        )
        registry.register(
            "api.request.completed",
            ["request_id", "status_code", "duration_ms"]
        )

        # DB Events (NEW)
        registry.register(
            "db.connection.created",
            ["connection_id", "type", "host"]
        )
        registry.register(
            "db.query.executed",
            ["connection_id", "row_count", "duration_ms"]
        )

        # Tool Events (NEW)
        registry.register(
            "tool.registered",
            ["tool_id", "version", "content_hash"]
        )
        registry.register(
            "tool.invoked",
            ["tool_id", "invocation_id", "duration_ms"]
        )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Enforces JSON schema validation."""
        try:
            validate(instance=config, schema=CONFIG_SCHEMA)
        except ValidationError as e:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message=f"Configuration schema validation failed: {e.message}",
            ) from e

    def _run_bootstrap_sequence(self) -> None:
        """Executes the strict genesis or normal boot process."""
        bootstrap_cfg = self._subsystems["config"].get("bootstrap", {})
        mode = bootstrap_cfg.get("mode", "normal")
        root_key_path = bootstrap_cfg.get("root_keypair_path", "kernel_root.pem")

        if mode == "genesis":
            # Generate deterministic root key
            root_key = secrets.token_bytes(32)
            os.makedirs(os.path.dirname(os.path.abspath(root_key_path)), exist_ok=True)
            with open(root_key_path, "wb") as f:
                f.write(root_key)

            self.audit_ledger.append(
                actor_id="KERNEL",
                action="kernel.genesis",
                status="SUCCESS",
                metadata={"message": "Genesis sequence initiated."},
            )

            admin_cfg = bootstrap_cfg.get("admin_identity", {})
            self.identity_service.register_identity(
                name=admin_cfg.get("name", "kernel_admin"),
                role=admin_cfg.get("role", "kernel_root"),
                parent_id=None,
                identity_type=admin_cfg.get("type", "user"),
                signing_key=root_key,
            )

            # Switch to normal
            try:
                with open("config.yaml", "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if "bootstrap" not in data:
                    data["bootstrap"] = {}
                data["bootstrap"]["mode"] = "normal"
                with open("config.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(data, f)
            except FileNotFoundError:
                pass

            self.audit_ledger.append(
                actor_id="KERNEL",
                action="kernel.mode_switch",
                status="SUCCESS",
                metadata={"mode": "normal"},
            )

        elif mode == "normal":
            self.verify_startup()
            self._subsystems["state"].rebuild_from_audit()

    def verify_startup(self) -> bool:
        """Executes initialization sequence checks."""
        return self.audit_ledger.verify_integrity()

    def shutdown(self) -> None:
        """Safely tears down the kernel."""
        # Stop connection pool
        import asyncio
        pool = self._subsystems.get("connection_pool")
        if pool:
            asyncio.run(pool.stop())

        self.audit_ledger.append(
            actor_id="KERNEL",
            action="system_shutdown",
            status="SUCCESS",
            metadata={},
        )

    def get_subsystems(self) -> Dict[str, Any]:
        """Provides access to the initialized core subsystems."""
        return {
            "bus": self.event_bus,
            "identity": self.identity_service,
            "policy": self.policy_engine,
            "vault": self._subsystems["vault"],
            "metering": self._subsystems["metering"],
            "state": self._subsystems["state"],
            "loader": self._subsystems["loader"],
            "connection_pool": self._subsystems["connection_pool"],
            "tool_registry": self._subsystems["tool_registry"],
        }

    def run_api(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run the REST API server."""
        if not self.api_server:
            raise KernelError(
                code=ErrorCode.CONFIG_INVALID,
                message="API server not initialized"
            )

        # Add business and UI routers
        business_router = create_business_router(self)
        ui_router = create_ui_router(self)
        self.api_server.include_router(business_router)
        self.api_server.include_router(ui_router)

        import uvicorn
        uvicorn.run(self.api_server, host=host, port=port)


# Backwards compatibility
__all__ = ["KernelBootstrap"]
