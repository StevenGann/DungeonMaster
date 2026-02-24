"""
Core engine: session management, message routing, and note-taking.

This module contains the central components that orchestrate DungeonMaster gameplay:

Components:
    Engine:
        The main message-handling entrypoint. Processes player messages through
        the full pipeline: session history, RAG context retrieval, scene/character
        loading, AI generation, scene updates, and note logging.

    Session:
        Per-player conversation session holding the message history (turns).
        Used to maintain context across multiple exchanges with the AI.

    SessionManager:
        In-memory store for all active sessions. One campaign uses one manager.
        Sessions are created on first message and persist for the process lifetime.

    Turn:
        A single conversation exchange with role ("user" or "assistant") and content.
        Sessions contain a list of turns representing the conversation history.

    NoteTaker:
        Appends session events (player actions, DM narrations) to Markdown files
        in the vault's notes/ directory. Creates rolling or per-session log files.

Example:
    >>> from dungeonmaster.core import Engine, SessionManager
    >>> session_manager = SessionManager()
    >>> session = session_manager.get_or_create("player_123")
    >>> session.add_turn("user", "I attack the goblin!")

See Also:
    - docs/ARCHITECTURE.md: Message flow sequence diagram
    - docs/API.md: Full API reference
"""

from dungeonmaster.core.engine import Engine
from dungeonmaster.core.session import Session, SessionManager, Turn
from dungeonmaster.core.note_taker import NoteTaker

__all__ = ["Engine", "Session", "SessionManager", "Turn", "NoteTaker"]
