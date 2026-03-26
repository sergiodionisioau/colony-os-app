"""Business Module Entrypoint.

Multi-tenant business management with hot-swap support.
Connects to CRM, Social Media, and other modules via kernel event bus.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class Business:
    """Business entity definition."""

    id: str
    name: str
    domain: str
    industry: str
    status: str = "active"
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Module connections
    connected_modules: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)


@dataclass
class BusinessMetrics:
    """Metrics for a business."""

    business_id: str
    revenue: float = 0.0
    leads: int = 0
    conversions: int = 0
    active_agents: int = 0
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Module:
    """Business Module - manages multiple businesses with hot-swap support."""

    def __init__(self) -> None:
        """Initialize the Business Module."""
        self.businesses: Dict[str, Business] = {}
        self.metrics: Dict[str, BusinessMetrics] = {}
        self.bus = None
        self.identity_id = "business_module_root"
        self.engines: Dict[str, Any] = {}
        self._health_status = {
            "businesses_loaded": 0,
            "last_health_check": None,
            "checks": {},
        }
        # Load sample businesses immediately for demo
        self._load_sample_businesses()

    def initialize(self, bus: Any) -> None:
        """Initialize the module with the kernel event bus."""
        self.bus = bus

        # Attach Audit Ledger and Policy Engine if they exist
        if hasattr(bus, "audit_ledger"):
            self.engines["audit"] = bus.audit_ledger

        if hasattr(bus, "policy_engine"):
            self.engines["policy"] = bus.policy_engine

        # Register FSM for business lifecycle
        if hasattr(bus, "state_engine"):
            transitions = [
                {"from": "INIT", "event": "CREATE", "to": "PENDING"},
                {"from": "PENDING", "event": "ACTIVATE", "to": "ACTIVE"},
                {"from": "ACTIVE", "event": "SUSPEND", "to": "SUSPENDED"},
                {"from": "SUSPENDED", "event": "ACTIVATE", "to": "ACTIVE"},
                {"from": "ACTIVE", "event": "DELETE", "to": "DELETED"},
            ]
            bus.state_engine.register_fsm("BUSINESS_LIFECYCLE", "1.0", transitions)

        # Load sample businesses for demo
        self._load_sample_businesses()

        print(f"BUSINESS: Module initialized with {len(self.businesses)} businesses")

        # Audit
        self._audit("module.initialized", {"business_count": len(self.businesses)})

    def _load_sample_businesses(self) -> None:
        """Load sample businesses for demonstration."""
        sample_businesses = [
            Business(
                id="biz-001",
                name="Colony OS",
                domain="colonyos.ai",
                industry="Software Infra",
                config={
                    "crm_enabled": True,
                    "social_media_enabled": True,
                    "max_agents": 10,
                    "agent_framework": "CrewAI",
                },
                connected_modules=["crm", "orchestrator"],
                agents=["crewai-agent-001", "crewai-agent-002"],
            ),
            Business(
                id="biz-002",
                name="Verified OS",
                domain="verifiedos.ai",
                industry="Software Infra",
                config={
                    "crm_enabled": True,
                    "social_media_enabled": True,
                    "max_agents": 10,
                    "agent_framework": "CrewAI",
                },
                connected_modules=["crm", "orchestrator"],
                agents=["crewai-agent-003", "crewai-agent-004"],
            ),
            Business(
                id="biz-003",
                name="App OS",
                domain="appos.ai",
                industry="Software Infra",
                config={
                    "crm_enabled": True,
                    "social_media_enabled": True,
                    "max_agents": 10,
                    "agent_framework": "CrewAI",
                },
                connected_modules=["crm", "orchestrator"],
                agents=["crewai-agent-005", "crewai-agent-006"],
            ),
            Business(
                id="biz-004",
                name="Content OS",
                domain="contentos.ai",
                industry="Software Infra",
                config={
                    "crm_enabled": True,
                    "social_media_enabled": True,
                    "max_agents": 10,
                    "agent_framework": "CrewAI",
                },
                connected_modules=["crm", "orchestrator"],
                agents=["crewai-agent-007", "crewai-agent-008"],
            ),
        ]

        for biz in sample_businesses:
            self.businesses[biz.id] = biz
            self.metrics[biz.id] = BusinessMetrics(
                business_id=biz.id,
                revenue=1000.0,  # $1k revenue
                leads=50,
                conversions=5,
                active_agents=2,  # CrewAI agents
            )

    def handle_event(self, event: Any) -> None:
        """Handle kernel events."""
        if event.type == "business.created":
            self._handle_business_create(event)
        elif event.type == "business.updated":
            self._handle_business_update(event)
        elif event.type == "business.deleted":
            self._handle_business_delete(event)
        elif event.type == "business.metrics.requested":
            self._handle_metrics_request(event)
        elif event.type == "revenue.signal.detected":
            # Forward to relevant business
            self._route_signal_to_business(event)

        print(f"BUSINESS: Handled event {event.type}")

    def _handle_business_create(self, event: Any) -> None:
        """Handle business creation."""
        payload = event.payload
        business = Business(
            id=payload.get("id", str(uuid.uuid4())),
            name=payload["name"],
            domain=payload["domain"],
            industry=payload.get("industry", "Unknown"),
            config=payload.get("config", {}),
        )

        self.businesses[business.id] = business
        self.metrics[business.id] = BusinessMetrics(business_id=business.id)

        self._audit(
            "business.created", {"business_id": business.id, "name": business.name}
        )

        # Publish business ready event
        if self.bus:
            self.bus.publish(
                "business.ready", {"business_id": business.id, "status": "active"}
            )

    def _handle_business_update(self, event: Any) -> None:
        """Handle business update."""
        biz_id = event.payload.get("business_id")
        if biz_id in self.businesses:
            biz = self.businesses[biz_id]
            biz.name = event.payload.get("name", biz.name)
            biz.domain = event.payload.get("domain", biz.domain)
            biz.industry = event.payload.get("industry", biz.industry)
            biz.config.update(event.payload.get("config", {}))
            biz.updated_at = datetime.now(timezone.utc).isoformat()

            self._audit("business.updated", {"business_id": biz_id})

    def _handle_business_delete(self, event: Any) -> None:
        """Handle business deletion."""
        biz_id = event.payload.get("business_id")
        if biz_id in self.businesses:
            del self.businesses[biz_id]
            if biz_id in self.metrics:
                del self.metrics[biz_id]

            self._audit("business.deleted", {"business_id": biz_id})

    def _handle_metrics_request(self, event: Any) -> None:
        """Handle metrics request."""
        biz_id = event.payload.get("business_id")
        if biz_id and biz_id in self.metrics:
            metrics = self.metrics[biz_id]
            if self.bus:
                self.bus.publish(
                    "business.metrics.response",
                    {
                        "business_id": biz_id,
                        "metrics": {
                            "revenue": metrics.revenue,
                            "leads": metrics.leads,
                            "conversions": metrics.conversions,
                            "active_agents": metrics.active_agents,
                        },
                    },
                )

    def _route_signal_to_business(self, event: Any) -> None:
        """Route revenue signals to the appropriate business."""
        # In a real implementation, this would match signals to businesses
        # based on domain, source, or other criteria
        pass

    def _audit(self, action: str, metadata: Dict[str, Any]) -> None:
        """Log to audit ledger if available."""
        audit = self.engines.get("audit")
        if audit:
            getattr(audit, "append")(
                actor_id="BUSINESS_MODULE",
                action=action,
                status="SUCCESS",
                metadata=metadata,
            )

    # =========================================================================
    # API Methods for REST Interface
    # =========================================================================

    def list_businesses(self) -> List[Dict[str, Any]]:
        """List all businesses."""
        return [
            {
                "id": b.id,
                "name": b.name,
                "domain": b.domain,
                "industry": b.industry,
                "status": b.status,
                "connected_modules": b.connected_modules,
                "agent_count": len(b.agents),
                "created_at": b.created_at,
            }
            for b in self.businesses.values()
        ]

    def get_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific business."""
        if business_id not in self.businesses:
            return None

        b = self.businesses[business_id]
        m = self.metrics.get(business_id, BusinessMetrics(business_id=business_id))

        return {
            "id": b.id,
            "name": b.name,
            "domain": b.domain,
            "industry": b.industry,
            "status": b.status,
            "config": b.config,
            "connected_modules": b.connected_modules,
            "agents": b.agents,
            "metrics": {
                "revenue": m.revenue,
                "leads": m.leads,
                "conversions": m.conversions,
                "conversion_rate": (
                    (m.conversions / m.leads * 100) if m.leads > 0 else 0
                ),
                "active_agents": m.active_agents,
            },
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }

    def create_business(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new business."""
        business = Business(
            id=data.get("id", f"biz-{uuid.uuid4().hex[:8]}"),
            name=data["name"],
            domain=data["domain"],
            industry=data.get("industry", "Unknown"),
            config=data.get("config", {}),
            connected_modules=data.get("connected_modules", ["crm"]),
        )

        self.businesses[business.id] = business
        self.metrics[business.id] = BusinessMetrics(business_id=business.id)

        self._audit("business.created", {"business_id": business.id})

        # Publish event
        if self.bus:
            self.bus.publish(
                "business.created",
                {"id": business.id, "name": business.name, "domain": business.domain},
            )

        return self.get_business(business.id)

    def update_business(
        self, business_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a business."""
        if business_id not in self.businesses:
            return None

        biz = self.businesses[business_id]
        biz.name = data.get("name", biz.name)
        biz.domain = data.get("domain", biz.domain)
        biz.industry = data.get("industry", biz.industry)
        biz.status = data.get("status", biz.status)
        biz.config.update(data.get("config", {}))
        biz.updated_at = datetime.now(timezone.utc).isoformat()

        self._audit("business.updated", {"business_id": business_id})

        return self.get_business(business_id)

    def delete_business(self, business_id: str) -> bool:
        """Delete a business."""
        if business_id not in self.businesses:
            return False

        del self.businesses[business_id]
        if business_id in self.metrics:
            del self.metrics[business_id]

        self._audit("business.deleted", {"business_id": business_id})

        if self.bus:
            self.bus.publish("business.deleted", {"business_id": business_id})

        return True

    def get_module_stats(self) -> Dict[str, Any]:
        """Get module statistics."""
        total_revenue = sum(m.revenue for m in self.metrics.values())
        total_leads = sum(m.leads for m in self.metrics.values())
        total_conversions = sum(m.conversions for m in self.metrics.values())

        return {
            "total_businesses": len(self.businesses),
            "active_businesses": sum(
                1 for b in self.businesses.values() if b.status == "active"
            ),
            "total_revenue": total_revenue,
            "total_leads": total_leads,
            "total_conversions": total_conversions,
            "overall_conversion_rate": (
                (total_conversions / total_leads * 100) if total_leads > 0 else 0
            ),
            "industries": list(set(b.industry for b in self.businesses.values())),
            "connected_modules": list(
                set(
                    mod for b in self.businesses.values() for mod in b.connected_modules
                )
            ),
        }

    def connect_module(self, business_id: str, module_name: str) -> bool:
        """Connect a module to a business."""
        if business_id not in self.businesses:
            return False

        biz = self.businesses[business_id]
        if module_name not in biz.connected_modules:
            biz.connected_modules.append(module_name)
            biz.updated_at = datetime.now(timezone.utc).isoformat()

            self._audit(
                "business.module_connected",
                {"business_id": business_id, "module": module_name},
            )

        return True

    def disconnect_module(self, business_id: str, module_name: str) -> bool:
        """Disconnect a module from a business."""
        if business_id not in self.businesses:
            return False

        biz = self.businesses[business_id]
        if module_name in biz.connected_modules:
            biz.connected_modules.remove(module_name)
            biz.updated_at = datetime.now(timezone.utc).isoformat()

            self._audit(
                "business.module_disconnected",
                {"business_id": business_id, "module": module_name},
            )

        return True

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def healthcheck(self) -> bool:
        """Module health verification."""
        checks = {
            "bus_connected": self.bus is not None,
            "businesses_loaded": len(self.businesses) > 0,
            "audit_available": self.engines.get("audit") is not None,
            "policy_available": self.engines.get("policy") is not None,
        }

        # For standalone mode (no kernel), only require businesses_loaded
        # Full health requires kernel integration
        if self.bus is None:
            # Standalone mode - just check businesses are loaded
            health_status = checks["businesses_loaded"]
        else:
            # Kernel integrated mode - check all
            health_status = all(checks.values())

        self._health_status = {
            "businesses_loaded": len(self.businesses),
            "last_health_check": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }

        self._audit(
            "module.healthcheck",
            {"status": "healthy" if health_status else "unhealthy", "checks": checks},
        )

        return health_status

    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._audit("module.shutdown", {"businesses": len(self.businesses)})
        print(f"BUSINESS: Module shutting down ({len(self.businesses)} businesses)")
