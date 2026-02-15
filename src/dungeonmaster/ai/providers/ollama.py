"""
Ollama provider for local models (narrative, embeddings).
"""

from typing import Any

from ollama import AsyncClient

from dungeonmaster.ai.providers.base import BaseAIProvider, GenerateResult


class OllamaProvider(BaseAIProvider):
    """Generate completions and embeddings via a local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ):
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._embedding_model = embedding_model
        self._client = AsyncClient(host=self._base_url)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def embedding_model(self) -> str:
        return self._embedding_model

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> GenerateResult:
        model = model or self._default_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat(model=model, messages=messages, **kwargs)
        text = response.get("message", {}).get("content", "") or ""
        return GenerateResult(text=text, model=model, raw=response)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for each text. Uses embedding_model."""
        if not texts:
            return []
        out = []
        for text in texts:
            r = await self._client.embeddings(model=self._embedding_model, prompt=text)
            vec = r.get("embedding", [])
            out.append(vec)
        return out

    async def is_available(self) -> bool:
        try:
            await self._client.list()
            return True
        except Exception:
            return False
