"""Base interface for AI Provider adapters.

This module defines the contract that all LLM provider adapters must follow.
"""

import abc
from typing import List

from core.agent.types import AIMessage, AIResponse, ProviderConfig


class AIProviderInterface(abc.ABC):
    """Stateless LLM adapter. MUST NOT store state between calls."""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Calls the provider. History is passed explicitly on every call."""

    @abc.abstractmethod
    def provider_id(self) -> str:
        """Stable identifier string for this provider e.g. 'openai_gpt4'."""
