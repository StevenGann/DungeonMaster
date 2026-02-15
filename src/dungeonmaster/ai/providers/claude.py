"""
Claude (Anthropic) provider for rulings and planning.
"""

from typing import Any

from anthropic import AsyncAnthropic

from dungeonmaster.ai.providers.base import BaseAIProvider, GenerateResult


class ClaudeProvider(BaseAIProvider):
    """Generate completions via Anthropic Claude API."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-3-5-sonnet-20241022",
    ):
        self._client = AsyncAnthropic(api_key=api_key or None)
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "claude"

    @property
    def default_model(self) -> str:
        return self._default_model

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        model = model or self._default_model
        kwargs_use = {"max_tokens": 4096, **kwargs}
        response = await self._client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system or "",
            **kwargs_use,
        )
        text = ""
        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
        return GenerateResult(text=text, model=model, raw=response)

    async def is_available(self) -> bool:
        return bool(self._client.api_key)
