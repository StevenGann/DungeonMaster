"""
Note Taker: append session events to Markdown files in the vault's notes/ directory.

Each event is recorded with a timestamp and role (player/dm). Used to maintain
a session log that can be viewed or edited in Obsidian.
"""

from datetime import datetime, timezone
from pathlib import Path

from dungeonmaster.data.vault import Vault


class NoteTaker:
    """
    Writes session events (player actions, DM narrations, rulings) to vault notes/.
    Uses a single rolling note file or per-session files.
    """

    def __init__(self, vault: Vault, note_id: str | None = None):
        self._vault = vault
        self._vault.ensure_all_dirs()
        self._note_id = note_id or f"session-{datetime.utcnow().strftime('%Y%m%d')}"

    def _path(self) -> Path:
        return self._vault.note_path(self._note_id)

    def append(self, content: str) -> None:
        """Append a line or block to the current note file."""
        path = self._path()
        if path.exists():
            existing = self._vault.read_text(path)
            new_content = f"{existing.rstrip()}\n\n{content.strip()}\n"
        else:
            new_content = f"# {self._note_id}\n\n{content.strip()}\n"
        self._vault.write_text(path, new_content)

    def note_event(self, role: str, content: str) -> None:
        """Record an event (e.g. 'player' action or 'dm' narration)."""
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        block = f"**[{timestamp}] {role}:**\n{content.strip()}"
        self.append(block)
