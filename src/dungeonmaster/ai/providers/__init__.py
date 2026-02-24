"""
AI provider implementations: Ollama, Claude, and extensible base.

This module contains the concrete AI provider implementations that connect
DungeonMaster to various LLM backends.

Components:
    BaseAIProvider:
        Abstract base class defining the provider interface. All providers must
        implement the ``generate()`` method and the ``name`` property.

    GenerateResult:
        Dataclass returned by ``generate()`` containing the generated text,
        model name used, and provider-specific raw response.

    OllamaProvider:
        Local LLM provider using Ollama (https://ollama.ai). Supports both text
        generation and embeddings. Used for narrative tasks and RAG embeddings.

    ClaudeProvider:
        Anthropic Claude API provider. Used for ruling tasks where stronger
        reasoning capabilities are beneficial.

Adding New Providers:
    To add a new provider (e.g., OpenAI, Gemini):
    1. Create a new module (e.g., openai.py)
    2. Subclass BaseAIProvider
    3. Implement name property and generate() method
    4. Optionally override is_available()
    5. Export from this __init__.py

Example:
    >>> from dungeonmaster.ai.providers import OllamaProvider, ClaudeProvider
    >>> ollama = OllamaProvider(base_url="http://localhost:11434")
    >>> result = await ollama.generate("Describe a dragon", system="Be dramatic")
    >>> print(result.text)

See Also:
    - docs/ARCHITECTURE.md: AI task routing diagram
    - docs/API.md: Full provider API reference
"""

from dungeonmaster.ai.providers.base import BaseAIProvider, GenerateResult
from dungeonmaster.ai.providers.ollama import OllamaProvider
from dungeonmaster.ai.providers.claude import ClaudeProvider

__all__ = ["BaseAIProvider", "GenerateResult", "OllamaProvider", "ClaudeProvider"]
