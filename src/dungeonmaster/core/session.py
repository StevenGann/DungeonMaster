"""
Session: one player's conversation with the DM (session_id = e.g. Discord user/channel id).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    """A single exchange: user message and assistant reply."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class Session:
    """
    Per-player session: conversation history and optional metadata.
    Session ID is the player/channel identifier (e.g. Discord user ID).
    """

    session_id: str
    turns: list[Turn] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))

    def get_recent_turns(self, max_turns: int = 20) -> list[Turn]:
        """Last N turns for context window."""
        return self.turns[-max_turns:] if self.turns else []

    def to_messages(self, max_turns: int = 20) -> list[dict[str, str]]:
        """Format recent turns as [{"role": "user"|"assistant", "content": "..."}]."""
        return [
            {"role": t.role, "content": t.content}
            for t in self.get_recent_turns(max_turns)
        ]


class SessionManager:
    """In-memory session store (one campaign = one instance)."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)
