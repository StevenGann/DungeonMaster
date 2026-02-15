"""
AI orchestrator: route by task type to narrative vs ruling provider.

Narrative (flavor text, descriptions) uses the narrative_provider (e.g. Ollama).
Ruling (rules, planning, adjudication) uses the ruling_provider (e.g. Claude).
Falls back to the other if one is missing. generate() is the single entrypoint.
"""

from typing import Any

from dungeonmaster.ai.providers.base import BaseAIProvider, GenerateResult


class AIOrchestrator:
    """
    Routes generation by task type: narrative (cheaper/faster) vs ruling (smarter).
    Can use multiple providers in parallel for narrative + ruling.
    """

    def __init__(
        self,
        narrative_provider: BaseAIProvider | None = None,
        ruling_provider: BaseAIProvider | None = None,
    ):
        self._narrative = narrative_provider
        self._ruling = ruling_provider
        # Fallback: use narrative for everything if no ruling provider
        self._default = narrative_provider or ruling_provider

    async def generate_narrative(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Use narrative model (e.g. Ollama) for flavor text, descriptions."""
        provider = self._narrative or self._default
        if not provider:
            return GenerateResult(text="", model="none", raw=None)
        model = getattr(provider, "default_model", None)
        return await provider.generate(prompt=prompt, model=model, system=system, **kwargs)

    async def generate_ruling(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        """Use ruling model (e.g. Claude) for rules, planning, decisions."""
        provider = self._ruling or self._default
        if not provider:
            return GenerateResult(text="", model="none", raw=None)
        model = getattr(provider, "default_model", None)
        return await provider.generate(prompt=prompt, model=model, system=system, **kwargs)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        task_type: str = "narrative",
        **kwargs: Any,
    ) -> GenerateResult:
        """
        Generate with the appropriate provider. task_type in ('narrative', 'ruling').
        """
        if task_type == "ruling":
            return await self.generate_ruling(prompt, system=system, **kwargs)
        return await self.generate_narrative(prompt, system=system, **kwargs)
