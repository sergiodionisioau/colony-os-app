"""Null AI Provider for testing.

Returns deterministic, empty-cost responses for baseline testing.
"""

from typing import List

from core.agent.types import AIMessage, AIResponse, ProviderConfig
from core.agent_runtime.provider_adapters.base import AIProviderInterface


class NullProvider(AIProviderInterface):
    """Deterministic stub provider for testing and Phase 3 baseline."""

    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Always returns a fixed deterministic response."""
        _ = (prompt, history, config)
        return AIResponse(
            content="NULL_PROVIDER_RESPONSE",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            provider_id="null",
        )

    def provider_id(self) -> str:
        """Returns the stable identifier for this provider."""
        return "null"
