"""Mock AI Provider for deterministic testing.

This module provides a queue-based mock provider that returns pre-defined
responses for testing agent reasoning loops without external API calls.
"""

from typing import List

from core.errors import ErrorCode, KernelError
from core.agent.types import AIMessage, AIResponse, ProviderConfig
from core.agent_runtime.provider_adapters.base import AIProviderInterface


class MockProvider(AIProviderInterface):
    """Queue-based mock provider for deterministic tests."""

    def __init__(self, responses: List[str]) -> None:
        self._queue = responses

    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Pops a response from the queue. Raises if empty."""
        _ = (prompt, history, config)
        if not self._queue:
            raise KernelError(
                code=ErrorCode.UNKNOWN_FAULT,
                message="MockProvider response queue exhausted.",
            )

        content = self._queue.pop(0)
        return AIResponse(
            content=content,
            tokens_in=10,  # Synthetic values
            tokens_out=20,
            cost_usd=0.001,
            provider_id="mock",
        )

    def provider_id(self) -> str:
        """Returns the stable identifier for this mock provider."""
        return "mock"
