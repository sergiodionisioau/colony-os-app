"""LLM Adapter for LangGraph Integration.

Provides deterministic LLM binding with zero temperature.
Swappable: OpenAI -> Ollama -> vLLM
"""

import os
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class LLMAdapter:
    """Deterministic LLM adapter with structured output support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLM with configuration."""
        self.config = config or {}
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize the LLM client."""
        provider = self.config.get("provider", "openai")

        if provider == "openai":
            self._llm = ChatOpenAI(
                model=self.config.get("model", "gpt-4.1-mini"),
                temperature=self.config.get("temperature", 0),  # Zero for determinism
                max_tokens=self.config.get("max_tokens", 4096),
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Invoke LLM with prompt."""
        messages = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        response = self._llm.invoke(messages)
        return response.content

    def invoke_structured(self, prompt: str, schema: Dict[str, Any],
                          system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Invoke LLM with structured JSON output."""
        structured_llm = self._llm.with_structured_output(schema)

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        return structured_llm.invoke(messages)

    def get_llm(self) -> ChatOpenAI:
        """Get raw LLM instance."""
        return self._llm


def get_llm(config: Optional[Dict[str, Any]] = None) -> LLMAdapter:
    """Factory function to get LLM adapter."""
    return LLMAdapter(config)
