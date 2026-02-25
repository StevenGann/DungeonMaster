"""
State management: scene JSON, character/NPC Markdown, and player registry.

SceneState is the in-memory representation of state/scene.json (location,
positions, turn_order). PlayerRegistry maps Discord user IDs to character
sheets. StateStore reads/writes scene JSON, player registry, and character/NPC
Markdown files through the vault. See docs/VAULT_AND_STATE.md for the schema.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dungeonmaster.data.vault import Vault


@dataclass
class Position:
    """Spatial position of an entity in the scene."""

    entity_id: str
    entity_type: str  # "player" | "npc" | "object"
    x: float = 0.0
    y: float = 0.0
    zone: str = ""


@dataclass
class Location:
    """Current scene location."""

    name: str = ""
    description: str = ""


@dataclass
class SceneState:
    """
    Current scene: who and what is where. Stored as JSON for VTT/frontend sync.
    """

    scene_id: str = "default"
    location: Location = field(default_factory=Location)
    positions: list[Position] = field(default_factory=list)
    turn_order: list[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "location": {
                "name": self.location.name,
                "description": self.location.description,
            },
            "positions": [asdict(p) for p in self.positions],
            "turn_order": self.turn_order,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneState":
        loc = data.get("location") or {}
        location = Location(
            name=loc.get("name", ""),
            description=loc.get("description", ""),
        )
        positions = [
            Position(
                entity_id=p.get("entity_id", ""),
                entity_type=p.get("entity_type", "npc"),
                x=float(p.get("x", 0)),
                y=float(p.get("y", 0)),
                zone=p.get("zone", ""),
            )
            for p in data.get("positions", [])
        ]
        return cls(
            scene_id=data.get("scene_id", "default"),
            location=location,
            positions=positions,
            turn_order=list(data.get("turn_order", [])),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class PlayerCharacter:
    """A character associated with a player."""

    name: str  # Human-readable name (e.g., "Gandalf")
    file_path: str  # Relative path in vault (e.g., "characters/Gandalf.md")
    is_active: bool = False  # Currently active character for this player

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerCharacter":
        return cls(
            name=data.get("name", ""),
            file_path=data.get("file_path", ""),
            is_active=data.get("is_active", False),
        )


@dataclass
class RegisteredPlayer:
    """A registered player with their character associations."""

    discord_id: str  # Discord user ID
    display_name: str  # Discord display name (cached for reference)
    characters: list[PlayerCharacter] = field(default_factory=list)
    registered_at: str = ""  # ISO timestamp

    def active_character(self) -> PlayerCharacter | None:
        """Return the currently active character, if any."""
        for char in self.characters:
            if char.is_active:
                return char
        return self.characters[0] if self.characters else None

    def get_character(self, name: str) -> PlayerCharacter | None:
        """Find a character by name (case-insensitive)."""
        name_lower = name.lower()
        for char in self.characters:
            if char.name.lower() == name_lower:
                return char
        return None

    def set_active(self, name: str) -> bool:
        """Set a character as active by name. Returns True if found."""
        char = self.get_character(name)
        if not char:
            return False
        for c in self.characters:
            c.is_active = False
        char.is_active = True
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "discord_id": self.discord_id,
            "display_name": self.display_name,
            "characters": [c.to_dict() for c in self.characters],
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisteredPlayer":
        characters = [
            PlayerCharacter.from_dict(c) for c in data.get("characters", [])
        ]
        return cls(
            discord_id=data.get("discord_id", ""),
            display_name=data.get("display_name", ""),
            characters=characters,
            registered_at=data.get("registered_at", ""),
        )


@dataclass
class PlayerRegistry:
    """Registry of all players and their character associations."""

    players: dict[str, RegisteredPlayer] = field(default_factory=dict)

    def get_player(self, discord_id: str) -> RegisteredPlayer | None:
        """Get a registered player by Discord ID."""
        return self.players.get(discord_id)

    def get_active_character_path(self, discord_id: str) -> str | None:
        """Get the active character's file path for a player."""
        player = self.get_player(discord_id)
        if player:
            char = player.active_character()
            if char:
                return char.file_path
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "players": {k: v.to_dict() for k, v in self.players.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerRegistry":
        players_data = data.get("players", {})
        players = {
            k: RegisteredPlayer.from_dict(v) for k, v in players_data.items()
        }
        return cls(players=players)


class StateStore:
    """Read/write scene state, player registry, and character/NPC Markdown from the vault."""

    def __init__(self, vault: Vault):
        self._vault = vault

    def players_path(self) -> Path:
        """Path to the player registry JSON file."""
        return self._vault.state_dir() / "players.json"

    def load_scene(self) -> SceneState:
        """Load scene.json; return default SceneState if missing or invalid."""
        path = self._vault.scene_path()
        if not path.exists():
            return SceneState()
        try:
            text = self._vault.read_text(path)
            data = json.loads(text)
            return SceneState.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return SceneState()

    def save_scene(self, scene: SceneState) -> None:
        """Write scene state to scene.json."""
        path = self._vault.scene_path()
        self._vault.write_text(path, json.dumps(scene.to_dict(), indent=2))

    def load_player_registry(self) -> PlayerRegistry:
        """Load player registry; return empty registry if missing or invalid."""
        path = self.players_path()
        if not path.exists():
            return PlayerRegistry()
        try:
            text = self._vault.read_text(path)
            data = json.loads(text)
            return PlayerRegistry.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return PlayerRegistry()

    def save_player_registry(self, registry: PlayerRegistry) -> None:
        """Save player registry to players.json."""
        path = self.players_path()
        self._vault.write_text(path, json.dumps(registry.to_dict(), indent=2))

    def register_player(
        self,
        discord_id: str,
        display_name: str,
        character_name: str,
        character_file: str,
    ) -> RegisteredPlayer:
        """
        Register a player with a character. Creates new player or adds character to existing.
        The first character registered becomes active by default.
        Returns the updated RegisteredPlayer.
        """
        registry = self.load_player_registry()
        player = registry.get_player(discord_id)

        if player is None:
            player = RegisteredPlayer(
                discord_id=discord_id,
                display_name=display_name,
                characters=[],
                registered_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
            registry.players[discord_id] = player

        existing_char = player.get_character(character_name)
        if existing_char:
            existing_char.file_path = character_file
        else:
            is_first = len(player.characters) == 0
            player.characters.append(
                PlayerCharacter(
                    name=character_name,
                    file_path=character_file,
                    is_active=is_first,
                )
            )

        player.display_name = display_name
        self.save_player_registry(registry)
        return player

    def unregister_character(self, discord_id: str, character_name: str) -> bool:
        """
        Remove a character from a player's registration.
        Returns True if found and removed, False otherwise.
        """
        registry = self.load_player_registry()
        player = registry.get_player(discord_id)
        if not player:
            return False

        char = player.get_character(character_name)
        if not char:
            return False

        was_active = char.is_active
        player.characters.remove(char)

        if was_active and player.characters:
            player.characters[0].is_active = True

        self.save_player_registry(registry)
        return True

    def set_active_character(self, discord_id: str, character_name: str) -> bool:
        """
        Switch a player's active character.
        Returns True if successful, False if player or character not found.
        """
        registry = self.load_player_registry()
        player = registry.get_player(discord_id)
        if not player:
            return False

        if not player.set_active(character_name):
            return False

        self.save_player_registry(registry)
        return True

    def get_active_character_path(self, discord_id: str) -> str | None:
        """Get the active character's file path for a player, or None if not registered."""
        registry = self.load_player_registry()
        return registry.get_active_character_path(discord_id)

    def load_character(self, player_id: str) -> str:
        """Load a player's character sheet as Markdown; empty string if missing."""
        path = self._vault.character_path(player_id)
        if not path.exists():
            return ""
        return self._vault.read_text(path)

    def load_character_by_path(self, relative_path: str) -> str:
        """Load character sheet by relative path from vault root; empty string if missing."""
        path = self._vault.root / relative_path
        if not path.exists():
            return ""
        return self._vault.read_text(path)

    def character_file_exists(self, character_name: str) -> bool:
        """Check if a character file exists in the characters directory."""
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in character_name)
        path = self._vault.characters_dir() / f"{safe_name}.md"
        return path.exists()

    def get_character_file_path(self, character_name: str) -> str:
        """Get the relative path for a character file (does not check existence)."""
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in character_name)
        return f"characters/{safe_name}.md"

    def save_character(self, player_id: str, content: str) -> None:
        """Write character sheet Markdown."""
        path = self._vault.character_path(player_id)
        self._vault.write_text(path, content)

    def load_npc(self, npc_id: str) -> str:
        """Load an NPC document as Markdown; empty string if missing."""
        path = self._vault.npc_path(npc_id)
        if not path.exists():
            return ""
        return self._vault.read_text(path)

    def save_npc(self, npc_id: str, content: str) -> None:
        """Write NPC document Markdown."""
        path = self._vault.npc_path(npc_id)
        self._vault.write_text(path, content)
