"""
State management: scene JSON (VTT sync) and character/NPC Markdown load/save.
"""

import json
from dataclasses import asdict, dataclass, field
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


class StateStore:
    """Read/write scene state and character/NPC Markdown from the vault."""

    def __init__(self, vault: Vault):
        self._vault = vault

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

    def load_character(self, player_id: str) -> str:
        """Load a player's character sheet as Markdown; empty string if missing."""
        path = self._vault.character_path(player_id)
        if not path.exists():
            return ""
        return self._vault.read_text(path)

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
