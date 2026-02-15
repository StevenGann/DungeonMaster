"""
File watcher: monitor systems/, characters/, npcs/ for changes; trigger re-ingest or refresh.

Callbacks are synchronous; the application can schedule async re-ingest from
on_system_change (e.g. via an asyncio queue consumed by a background task).
"""

import logging
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from dungeonmaster.data.vault import Vault

logger = logging.getLogger(__name__)


class VaultWatcherHandler(FileSystemEventHandler):
    """Emit events for system file changes (re-ingest) and character/NPC changes (refresh)."""

    def __init__(
        self,
        vault: Vault,
        on_system_change: Callable[[str], None] | None = None,
        on_character_or_npc_change: Callable[[str], None] | None = None,
    ):
        self._vault = vault
        self._on_system_change = on_system_change
        self._on_character_or_npc_change = on_character_or_npc_change
        self._systems_root = str(vault.systems_dir())
        self._characters_root = str(vault.characters_dir())
        self._npcs_root = str(vault.npcs_dir())

    def _is_system_file(self, path: str) -> bool:
        p = Path(path)
        if p.suffix.lower() not in (".md", ".txt"):
            return False
        return path.startswith(self._systems_root)

    def _is_character_or_npc(self, path: str) -> bool:
        p = Path(path)
        if p.suffix.lower() != ".md":
            return False
        return path.startswith(self._characters_root) or path.startswith(self._npcs_root)

    def dispatch(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = str(Path(event.src_path).resolve())
        if self._on_system_change and self._is_system_file(path):
            try:
                self._on_system_change(path)
            except Exception as e:
                logger.warning("System change callback failed: %s", e)
        elif self._on_character_or_npc_change and self._is_character_or_npc(path):
            try:
                self._on_character_or_npc_change(path)
            except Exception as e:
                logger.warning("Character/NPC change callback failed: %s", e)


class VaultWatcher:
    """
    Watch vault systems/, characters/, npcs/. Callbacks are sync; app can schedule
    async re-ingest from on_system_change (e.g. via asyncio queue).
    """

    def __init__(
        self,
        vault: Vault,
        on_system_change: Callable[[str], None] | None = None,
        on_character_or_npc_change: Callable[[str], None] | None = None,
    ):
        self._vault = vault
        self._handler = VaultWatcherHandler(
            vault,
            on_system_change=on_system_change,
            on_character_or_npc_change=on_character_or_npc_change,
        )
        self._observer: Observer | None = None

    def start(self) -> None:
        """Start watching. Creates dirs if missing."""
        self._vault.ensure_all_dirs()
        self._observer = Observer()
        for path in (
            self._vault.systems_dir(),
            self._vault.characters_dir(),
            self._vault.npcs_dir(),
        ):
            if path.exists():
                self._observer.schedule(
                    self._handler,
                    str(path),
                    recursive=True,
                )
        self._observer.start()
        logger.info("Vault watcher started")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("Vault watcher stopped")
