"""
Interface abstraction for DungeonMaster.

The core engine speaks only Message (session_id, user_id, content) and returns
reply text. Interface adapters (Discord, future Web/CLI) translate
platform-specific events into Message and send the reply back to the user.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """Incoming user message from any interface."""

    session_id: str
    user_id: str
    content: str
    metadata: dict[str, Any] | None = None


@dataclass
class Response:
    """Outgoing assistant response."""

    content: str
    metadata: dict[str, Any] | None = None


class InterfaceAdapter:
    """Base for interface adapters. Subclasses start/stop and forward messages to the engine."""

    async def start(self) -> None:
        """Start the interface (e.g. connect Discord)."""
        pass

    async def stop(self) -> None:
        """Stop the interface."""
        pass
