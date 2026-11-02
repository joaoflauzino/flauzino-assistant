"""Data contracts shared by the agent core modules."""

from dataclasses import dataclass


@dataclass(slots=True)
class TokenUsage:
    """Aggregated token counts reported by an LLM provider."""

    prompt: int = 0
    completion: int = 0
