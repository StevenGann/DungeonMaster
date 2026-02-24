"""
DungeonMaster: AI-powered Dungeon Master for TTRPGs.

DungeonMaster is a modular, AI-powered Dungeon Master application for tabletop
role-playing games (D&D, Pathfinder, homebrew systems, etc.). One process runs
a single campaign, with players interacting via private messages (e.g., Discord DMs).

Key Features:
    - **System-agnostic**: Rules come from ingested documents (RAG), not hardcoded logic.
    - **Modular AI**: Supports Ollama (local) and Claude (API) providers.
    - **Obsidian-compatible**: All content lives in a Markdown vault you can edit.
    - **Interface-agnostic**: Discord bot included; other UIs can be added.

Modules:
    - ``dungeonmaster.ai``: AI providers, orchestrator, and RAG store.
    - ``dungeonmaster.core``: Engine, session management, and note-taking.
    - ``dungeonmaster.data``: Vault, state store, and file watcher.
    - ``dungeonmaster.interfaces``: User interfaces (Discord bot).
    - ``dungeonmaster.config``: Configuration loading.
    - ``dungeonmaster.main``: Application entrypoint.

Quick Start:
    1. Install: ``pip install -e ".[dev]"``
    2. Configure: Set ``DISCORD_BOT_TOKEN`` (and optionally ``ANTHROPIC_API_KEY``)
    3. Run: ``python -m dungeonmaster.main``

See Also:
    - docs/ARCHITECTURE.md: System design and message flow
    - docs/VAULT_AND_STATE.md: Data layout and schemas
    - docs/API.md: Python API reference
    - docs/CONFIGURATION.md: Configuration options
"""

__version__ = "0.1.0"
__author__ = "DungeonMaster Contributors"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
