"""
Note Taker: append session events to Markdown files in the vault's notes/ directory.

Each event is recorded with a timestamp and role (player/dm). Used to maintain
a session log that can be viewed or edited in Obsidian.

Supports an optional public note callback for posting events to a Discord
channel (Session Notes) in addition to the vault files.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from dungeonmaster.data.vault import Vault


# Type alias for the public note callback (posts to Discord Session Notes channel)
PublicNoteCallback = Callable[[str, str | None], Awaitable[None]]


class NoteTaker:
    """
    Writes session events (player actions, DM narrations, rulings) to vault notes/.
    Uses a single rolling note file or per-session files.

    Optionally supports a public note callback for posting events to a Discord
    channel (Session Notes) when events should be shared with all players.
    """

    def __init__(
        self,
        vault: Vault,
        note_id: str | None = None,
        public_note_callback: PublicNoteCallback | None = None,
    ):
        self._vault = vault
        self._vault.ensure_all_dirs()
        self._note_id = note_id or f"session-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        self._public_note_callback = public_note_callback

    def set_public_note_callback(self, callback: PublicNoteCallback | None) -> None:
        """Set or update the public note callback (for Discord Session Notes)."""
        self._public_note_callback = callback

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

    async def note_public_event(self, content: str, title: str | None = None) -> None:
        """
        Record an event publicly (Discord channel) AND privately (vault).

        Use this for announcements and events that should be visible to all
        players in the Session Notes channel.
        """
        self.note_event("announcement", content)

        if self._public_note_callback:
            await self._public_note_callback(content, title)
