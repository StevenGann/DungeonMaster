"""
Abstract base for LLM providers (Ollama, Claude, etc.).

Each provider implements generate(prompt, model?, system?, **kwargs) and
optionally is_available(). The orchestrator calls generate with a task_type
to select narrative vs ruling model.
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
