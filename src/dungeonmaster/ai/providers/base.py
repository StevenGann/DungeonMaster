"""
Abstract base for AI providers. All providers implement generate() for completion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class GenerateResult:
    """Result of a single completion call."""

    text: str
    model: str
    raw: Any = None  # Provider-specific response


class BaseAIProvider(ABC):
    """Interface for LLM providers (Ollama, Claude, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'ollama', 'claude')."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """
        Generate a completion. model may be overridden per call.
        system is an optional system message / instruction.
        """
        ...

    async def is_available(self) -> bool:
        """Check if the provider can be used (e.g. Ollama reachable, API key set)."""
        return True
