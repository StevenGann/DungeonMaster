"""
Obsidian-compatible vault: paths and read/write for systems, notes, characters, npcs, state.

One DungeonMaster instance = one campaign; vault root holds a single vault.
"""

from pathlib import Path


class Vault:
    """
    Unified vault root for system content, campaign notes, characters, NPCs, and state.

    Directory layout:
      systems/   - rulebooks (Markdown/TXT)
      notes/     - session notes
      characters/ - player sheets (Markdown)
      npcs/      - NPC roster (Markdown)
      state/     - scene.json
      _index/    - internal (embeddings); not for Obsidian
    """

    def __init__(self, root: str | Path):
        self._root = Path(root).resolve()

    @property
    def root(self) -> Path:
        """Vault root directory."""
        return self._root

    def ensure_all_dirs(self) -> None:
        """Create vault subdirectories if they do not exist."""
        for name in ("systems", "notes", "characters", "npcs", "state", "_index"):
            (self._root / name).mkdir(parents=True, exist_ok=True)

    # Path helpers

    def systems_dir(self) -> Path:
        return self._root / "systems"

    def notes_dir(self) -> Path:
        return self._root / "notes"

    def characters_dir(self) -> Path:
        return self._root / "characters"

    def npcs_dir(self) -> Path:
        return self._root / "npcs"

    def state_dir(self) -> Path:
        return self._root / "state"

    def index_dir(self) -> Path:
        return self._root / "_index"

    def scene_path(self) -> Path:
        return self._root / "state" / "scene.json"

    def character_path(self, player_id: str) -> Path:
        """Path to a player's character sheet (Markdown)."""
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(player_id))
        return self._root / "characters" / f"{safe}.md"

    def npc_path(self, npc_id: str) -> Path:
        """Path to an NPC document (Markdown)."""
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(npc_id))
        return self._root / "npcs" / f"{safe}.md"

    def note_path(self, note_id: str) -> Path:
        """Path to a note file (e.g. session-001.md)."""
        return self._root / "notes" / f"{note_id}.md"

    # Read/write

    def read_text(self, path: Path) -> str:
        """Read file as UTF-8 text."""
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        """Write UTF-8 text; create parent dirs if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_bytes(self, path: Path) -> bytes:
        """Read file as bytes."""
        return path.read_bytes()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def list_system_files(self) -> list[Path]:
        """List Markdown and TXT files under systems/ (recursive)."""
        out: list[Path] = []
        for ext in (".md", ".txt"):
            out.extend(self.systems_dir().rglob(f"*{ext}"))
        return sorted(out)
