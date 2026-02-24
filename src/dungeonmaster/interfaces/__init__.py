"""
User interface layer: adapters for different platforms.

This module contains interface adapters that connect DungeonMaster to external
platforms. Each adapter translates platform-specific events into a common Message
format and sends AI responses back to users.

Components:
    Message:
        Incoming user message dataclass with session_id, user_id, content, and
        optional metadata. Used to pass messages from any interface to the engine.

    Response:
        Outgoing assistant response dataclass with content and optional metadata.

    InterfaceAdapter:
        Base class for interface adapters. Defines start() and stop() methods.
        Concrete implementations (like DiscordBot) inherit from this.

Submodules:
    dungeonmaster.interfaces.discord:
        Discord bot implementation using discord.py. Handles DMs and slash commands.

Future Interfaces:
    - Web UI (REST/WebSocket API)
    - CLI (terminal interface for testing)
    - Slack, Telegram, or other chat platforms

Example:
    >>> from dungeonmaster.interfaces import Message, Response
    >>> msg = Message(session_id="123", user_id="player1", content="I attack!")
    >>> response = Response(content="The goblin dodges your swing.")

See Also:
    - docs/ARCHITECTURE.md: Interface layer in system diagram
    - docs/API.md: Full API reference
"""

from dungeonmaster.interfaces.base import InterfaceAdapter, Message, Response

__all__ = ["InterfaceAdapter", "Message", "Response"]
