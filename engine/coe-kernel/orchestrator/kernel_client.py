"""Kernel Integration Layer.

Connects LangGraph orchestrator to COE Kernel via REST API.
"""

import requests
from typing import Any, Dict, Optional


class KernelClient:
    """Client for COE Kernel REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", identity: str = "orchestrator"):
        """Initialize kernel client."""
        self.base_url = base_url
        self.identity = identity
        self.headers = {
            "Content-Type": "application/json",
            "X-Identity-ID": identity
        }

    def health_check(self) -> Dict[str, Any]:
        """Check kernel health."""
        response = requests.get(f"{self.base_url}/v1/health", headers=self.headers)
        return response.json()

    def register_agent(self, agent_id: str, role: str, capabilities: list) -> Dict[str, Any]:
        """Register an agent with the kernel."""
        data = {
            "agent_id": agent_id,
            "role": role,
            "capabilities": capabilities,
            "token_budget": 100000
        }
        response = requests.post(
            f"{self.base_url}/v1/agents/register",
            headers=self.headers,
            json=data
        )
        return response.json()

    def submit_task(self, agent_id: str, instruction: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Submit a task to an agent."""
        data = {
            "instruction": instruction,
            "context": context or {}
        }
        response = requests.post(
            f"{self.base_url}/v1/agents/{agent_id}/tasks",
            headers=self.headers,
            json=data
        )
        return response.json()

    def list_modules(self) -> Dict[str, Any]:
        """List loaded modules."""
        response = requests.get(f"{self.base_url}/v1/modules", headers=self.headers)
        return response.json()

    def load_module(self, module_id: str) -> Dict[str, Any]:
        """Load a module."""
        data = {"module_id": module_id, "path": f"modules/{module_id}", "activation": "immediate"}
        response = requests.post(
            f"{self.base_url}/v1/modules/load",
            headers=self.headers,
            json=data
        )
        return response.json()

    def hot_swap_module(self, module_id: str, new_path: str) -> Dict[str, Any]:
        """Hot-swap a module."""
        data = {
            "new_version_path": new_path,
            "verification": {"run_tests": True, "shadow_traffic": True}
        }
        response = requests.post(
            f"{self.base_url}/v1/modules/{module_id}/hot-swap",
            headers=self.headers,
            json=data
        )
        return response.json()

    def list_businesses(self) -> Dict[str, Any]:
        """List all businesses."""
        response = requests.get(f"{self.base_url}/v1/businesses", headers=self.headers)
        return response.json()

    def get_business(self, business_id: str) -> Dict[str, Any]:
        """Get specific business."""
        response = requests.get(f"{self.base_url}/v1/businesses/{business_id}", headers=self.headers)
        return response.json()
