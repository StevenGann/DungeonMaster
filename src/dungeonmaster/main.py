"""
DungeonMaster application entrypoint.

Loads config (YAML + env), builds the vault, RAG store, state store, AI
orchestrator, and engine; optionally runs initial RAG ingest; starts the
file watcher and the Discord bot. One process = one campaign.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure src is on path when run as module
if __name__ == "__main__":
    src = Path(__file__).resolve().parent
    if str(src) not in sys.path:
        sys.path.insert(0, str(src.parent))

from dungeonmaster.config import load_config
from dungeonmaster.data.vault import Vault
from dungeonmaster.data.state import StateStore
from dungeonmaster.data.watcher import VaultWatcher
from dungeonmaster.ai.rag import RAGStore
from dungeonmaster.ai.providers.ollama import OllamaProvider
from dungeonmaster.ai.providers.claude import ClaudeProvider
from dungeonmaster.ai.orchestrator import AIOrchestrator
from dungeonmaster.core.engine import Engine
from dungeonmaster.core.session import SessionManager
from dungeonmaster.core.note_taker import NoteTaker
from dungeonmaster.interfaces.discord import DiscordBot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dungeonmaster")


def _build_engine(config: dict):
    """Build vault, RAG, state, orchestrator, engine from config."""
    vault_path = config.get("vault", {}).get("path", "data")
    vault = Vault(Path(vault_path).resolve())
    vault.ensure_all_dirs()

    # Ollama
    ollama_cfg = config.get("ai", {}).get("ollama", {})
    ollama = OllamaProvider(
        base_url=ollama_cfg.get("base_url", "http://localhost:11434"),
        default_model=ollama_cfg.get("narrative_model", "llama3.2"),
        embedding_model=ollama_cfg.get("embedding_model", "nomic-embed-text"),
    )

    async def embed_fn(texts: list[str]):
        return await ollama.embed(texts)

    rag_cfg = config.get("rag", {})
    rag = RAGStore(
        vault=vault,
        embed_fn=embed_fn,
        chunk_size=rag_cfg.get("chunk_size", 512),
        chunk_overlap=rag_cfg.get("chunk_overlap", 64),
        top_k=rag_cfg.get("top_k", 5),
    )

    # Claude (optional)
    claude_cfg = config.get("ai", {}).get("claude", {})
    api_key = claude_cfg.get("api_key", "") or ""
    ruling_provider = None
    if api_key:
        ruling_provider = ClaudeProvider(
            api_key=api_key,
            default_model=claude_cfg.get("ruling_model", "claude-3-5-sonnet-20241022"),
        )

    orchestrator = AIOrchestrator(
        narrative_provider=ollama,
        ruling_provider=ruling_provider,
    )
    state_store = StateStore(vault)
    session_manager = SessionManager()
    note_taker = NoteTaker(vault)

    engine = Engine(
        orchestrator=orchestrator,
        rag=rag,
        state_store=state_store,
        session_manager=session_manager,
        note_taker=note_taker,
    )
    return engine, rag, vault


async def run_async(config: dict) -> None:
    """Build and run: optional initial RAG ingest, start Discord bot."""
    engine, rag, vault = _build_engine(config)

    # Optional: ingest system docs on startup
    try:
        n = await rag.ingest_all()
        logger.info("RAG ingest: %d chunks indexed", n)
    except Exception as e:
        logger.warning("RAG initial ingest failed: %s", e)

    discord_cfg = config.get("discord", {})
    token = discord_cfg.get("token", "").strip()
    if not token:
        logger.error("No Discord token (DISCORD_BOT_TOKEN or config discord.token). Exiting.")
        return

    loop = asyncio.get_running_loop()

    # Optional file watcher: on system change, re-ingest that path (from watcher thread)
    def on_system_change(path: str) -> None:
        async def reingest() -> None:
            try:
                rag.delete_by_source(path)
                await rag.ingest_path(Path(path))
                logger.info("Re-ingested: %s", path)
            except Exception as e:
                logger.warning("Re-ingest failed for %s: %s", path, e)

        asyncio.run_coroutine_threadsafe(reingest(), loop)

    watcher = VaultWatcher(vault, on_system_change=on_system_change)
    watcher.start()

    bot = DiscordBot(
        token=token,
        engine_handle_message=engine.handle_message,
        dm_only=discord_cfg.get("dm_only", True),
    )

    async def run_bot():
        async with bot:
            await bot.start(token)

    try:
        await run_bot()
    finally:
        watcher.stop()


def main() -> None:
    config = load_config()
    try:
        asyncio.run(run_async(config))
    except KeyboardInterrupt:
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
