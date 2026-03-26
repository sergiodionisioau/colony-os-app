#!/usr/bin/env python3
"""
Colony OS - Model Router
Routes tasks to appropriate models based on availability, complexity, and cost.
"""

from enum import Enum
from typing import Dict, Any
import json
from datetime import datetime


class Model(Enum):
    """Available models in priority order"""
    KIMI_CLOUD = "ollama/kimi-k2.5:cloud"      # Primary - 262k ctx
    QWEN_LOCAL = "ollama/qwen2.5:3b"            # Fallback - 128k ctx
    DEEPSEEK_R1 = "ollama/deepseek-r1:1.5b"     # Reasoning - 128k ctx
    DEEPSEEK_AGENT = "ollama/deepseek-agent:latest"  # General - 128k ctx


class TaskComplexity(Enum):
    TRIVIAL = 1      # Quick responses, summaries
    SIMPLE = 2       # Standard queries
    MODERATE = 3     # Multi-step tasks
    COMPLEX = 4      # Deep analysis, code review
    EPIC = 5         # Architecture, planning


class ModelRouter:
    """Intelligent model selection with fallback support"""

    # Model capabilities and constraints
    MODEL_CONFIG = {
        Model.KIMI_CLOUD: {
            "context_window": 262144,
            "max_tokens": 8192,
            "supports_reasoning": False,
            "cost_per_1k": 0.0,  # Your local/cloud pricing
            "rate_limit": None,  # Set to requests/min if known
            "is_cloud": True,
            "is_local": False,
        },
        Model.QWEN_LOCAL: {
            "context_window": 128000,
            "max_tokens": 8192,
            "supports_reasoning": False,
            "cost_per_1k": 0.0,  # Free - local
            "rate_limit": None,  # Unlimited
            "is_cloud": False,
            "is_local": True,
        },
        Model.DEEPSEEK_R1: {
            "context_window": 128000,
            "max_tokens": 8192,
            "supports_reasoning": True,
            "cost_per_1k": 0.0,  # Free - local
            "rate_limit": None,
            "is_cloud": False,
            "is_local": True,
        },
        Model.DEEPSEEK_AGENT: {
            "context_window": 128000,
            "max_tokens": 8192,
            "supports_reasoning": False,
            "cost_per_1k": 0.0,
            "rate_limit": None,
            "is_cloud": False,
            "is_local": True,
        }
    }

    def __init__(self):
        self.rate_limit_status = {
            Model.KIMI_CLOUD: {"available": True, "retry_after": None},
            Model.QWEN_LOCAL: {"available": True, "retry_after": None},
            Model.DEEPSEEK_R1: {"available": True, "retry_after": None},
            Model.DEEPSEEK_AGENT: {"available": True, "retry_after": None},
        }
        self.usage_stats = {model: {"calls": 0, "tokens": 0} for model in Model}

    def route(self, task_description: str, complexity: TaskComplexity = None,
              requires_reasoning: bool = False, preferred_model: Model = None) -> Model:
        """
        Route task to best available model.

        Args:
            task_description: What needs to be done
            complexity: Task complexity level (auto-detected if None)
            requires_reasoning: If chain-of-thought needed
            preferred_model: User override (if available)

        Returns:
            Selected Model enum
        """

        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self._estimate_complexity(task_description)

        # Check user preference first
        if preferred_model and self._is_available(preferred_model):
            return preferred_model

        # Reasoning tasks -> DeepSeek R1
        if requires_reasoning and self._is_available(Model.DEEPSEEK_R1):
            return Model.DEEPSEEK_R1

        # Epic/Complex tasks -> Kimi (if available)
        if complexity in [TaskComplexity.EPIC, TaskComplexity.COMPLEX]:
            if self._is_available(Model.KIMI_CLOUD):
                return Model.KIMI_CLOUD
            # Fallback to DeepSeek Agent for complex tasks
            if self._is_available(Model.DEEPSEEK_AGENT):
                return Model.DEEPSEEK_AGENT

        # Moderate tasks -> Try Kimi, fallback to Qwen
        if complexity == TaskComplexity.MODERATE:
            if self._is_available(Model.KIMI_CLOUD):
                return Model.KIMI_CLOUD
            if self._is_available(Model.QWEN_LOCAL):
                return Model.QWEN_LOCAL

        # Simple/Trivial -> Qwen (fast, free, local)
        if complexity in [TaskComplexity.SIMPLE, TaskComplexity.TRIVIAL]:
            if self._is_available(Model.QWEN_LOCAL):
                return Model.QWEN_LOCAL
            if self._is_available(Model.KIMI_CLOUD):
                return Model.KIMI_CLOUD

        # Ultimate fallback
        for model in [Model.QWEN_LOCAL, Model.DEEPSEEK_AGENT, Model.KIMI_CLOUD]:
            if self._is_available(model):
                return model

        # Last resort
        return Model.QWEN_LOCAL

    def _is_available(self, model: Model) -> bool:
        """Check if model is currently available (not rate limited)"""
        status = self.rate_limit_status[model]
        if not status["available"] and status["retry_after"]:
            if datetime.now() > status["retry_after"]:
                status["available"] = True
                status["retry_after"] = None
        return status["available"]

    def _estimate_complexity(self, description: str) -> TaskComplexity:
        """Rough heuristic for task complexity"""
        desc_lower = description.lower()

        # Keywords indicating complexity
        epic_indicators = ["architecture", "design system", "refactor entire", "plan", "strategy"]
        complex_indicators = ["review", "analyze", "debug", "implement feature", "integrate"]
        trivial_indicators = ["fix typo", "summarize", "quick", "short", "one line"]

        if any(kw in desc_lower for kw in epic_indicators):
            return TaskComplexity.EPIC
        if any(kw in desc_lower for kw in complex_indicators):
            return TaskComplexity.COMPLEX
        if any(kw in desc_lower for kw in trivial_indicators):
            return TaskComplexity.TRIVIAL
        if len(description) < 100:
            return TaskComplexity.SIMPLE

        return TaskComplexity.MODERATE

    def mark_rate_limited(self, model: Model, retry_after_seconds: int = 60):
        """Mark model as rate limited"""
        self.rate_limit_status[model] = {
            "available": False,
            "retry_after": datetime.now().timestamp() + retry_after_seconds
        }

    def record_usage(self, model: Model, tokens_used: int):
        """Track model usage"""
        self.usage_stats[model]["calls"] += 1
        self.usage_stats[model]["tokens"] += tokens_used

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "rate_limits": {m.value: self.rate_limit_status[m] for m in Model},
            "usage": {m.value: self.usage_stats[m] for m in Model},
            "timestamp": datetime.now().isoformat()
        }

    def get_recommendation(self, task_description: str) -> Dict[str, Any]:
        """Get full routing recommendation with explanation"""
        complexity = self._estimate_complexity(task_description)
        selected = self.route(task_description, complexity)

        # Build explanation
        reasons = []
        if selected == Model.DEEPSEEK_R1:
            reasons.append("Selected for reasoning capabilities")
        elif selected == Model.QWEN_LOCAL:
            if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
                reasons.append("Fast local execution for simple task")
            else:
                reasons.append("Fallback to local model (Kimi may be rate limited)")
        elif selected == Model.KIMI_CLOUD:
            reasons.append("Primary model with large context window")

        return {
            "task": task_description[:100] + "..." if len(task_description) > 100 else task_description,
            "estimated_complexity": complexity.name,
            "selected_model": selected.value,
            "is_local": self.MODEL_CONFIG[selected]["is_local"],
            "reasons": reasons,
            "alternatives": [m.value for m in Model if m != selected and self._is_available(m)]
        }


# Singleton instance
router = ModelRouter()

if __name__ == "__main__":
    # Test examples
    test_tasks = [
        "Fix typo in README",
        "Summarize the last conversation",
        "Review this PR for bugs",
        "Design the architecture for a new feature",
        "Explain why this code is failing",
        "Write a complex data pipeline",
    ]

    print("=" * 70)
    print("COLONY OS - Model Router Test")
    print("=" * 70)

    for task in test_tasks:
        rec = router.get_recommendation(task)
        print(f"\nTask: {rec['task']}")
        print(f"  Complexity: {rec['estimated_complexity']}")
        print(f"  Selected: {rec['selected_model']}")
        print(f"  Local: {rec['is_local']}")
        print(f"  Why: {', '.join(rec['reasons'])}")
        print(f"  Fallbacks: {', '.join(rec['alternatives'])}")

    print("\n" + "=" * 70)
    print(json.dumps(router.get_stats(), indent=2))
