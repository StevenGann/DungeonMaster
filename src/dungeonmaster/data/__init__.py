"""
Data layer: vault, state management, and file watcher.

This module provides the data persistence infrastructure for DungeonMaster:

Components:
    Vault:
        Abstraction over the Obsidian-compatible vault directory. Provides path
        helpers and read/write methods for all vault content: systems (rulebooks),
        notes, characters, NPCs, scene state, and the internal index.

    StateStore:
        Read/write interface for scene state (JSON) and character/NPC documents
        (Markdown). Loads scene.json and character sheets for context injection.

    SceneState:
        Dataclass representing the current scene: location, entity positions,
        turn order, and timestamp. Serializable to/from JSON for VTT sync.

    Position:
        Spatial position of an entity (player, NPC, object) in the scene.

    Location:
        Current scene location with name and description.

    VaultWatcher:
        File system watcher using watchdog. Monitors systems/, characters/, and
        npcs/ for changes and triggers callbacks (e.g., RAG re-ingestion).

Example:
    >>> from dungeonmaster.data import Vault, StateStore, SceneState
    >>> vault = Vault("/path/to/campaign")
    >>> vault.ensure_all_dirs()
    >>> state_store = StateStore(vault)
    >>> scene = state_store.load_scene()
    >>> print(scene.location.name)

See Also:
    - docs/VAULT_AND_STATE.md: Directory layout and JSON schema
    - docs/ARCHITECTURE.md: Data flow diagram
    - docs/API.md: Full API reference
"""

from dungeonmaster.data.vault import Vault
from dungeonmaster.data.state import Location, Position, SceneState, StateStore
from dungeonmaster.data.watcher import VaultWatcher

__all__ = [
    "Vault",
    "Location",
    "Position",
    "SceneState",
    "StateStore",
    "VaultWatcher",
]
