"""
Discord bot interface for DungeonMaster.

This module provides the Discord integration, allowing players to interact with
the AI Dungeon Master via Discord direct messages (DMs).

Components:
    DiscordBot:
        A discord.py Bot subclass that handles DM messages and slash commands.
        Forwards player messages to the engine and sends replies back.

Slash Commands:
    - /start: Start or resume a session with the DM
    - /action <action>: Describe a character action (narrative)
    - /say <text>: Have your character speak (narrative)
    - /status <question>: Ask for a ruling or situation (ruling)
    - /notes: Get a summary of recent session notes (ruling)

Configuration:
    Set the following in your config or environment:
    - DISCORD_BOT_TOKEN: Your Discord bot token
    - discord.dm_only: If true (default), only respond to DMs

Setup:
    1. Create a Discord application at https://discord.com/developers/applications
    2. Add a bot user and copy the token
    3. Enable Message Content Intent and Direct Messages intents
    4. Invite the bot to your server with appropriate permissions
    5. Set the token in secrets.json or DISCORD_BOT_TOKEN env var

Example:
    >>> from dungeonmaster.interfaces.discord import DiscordBot
    >>> bot = DiscordBot(
    ...     token="your-token",
    ...     engine_handle_message=engine.handle_message,
    ...     dm_only=True,
    ... )
    >>> await bot.start(bot._token)

See Also:
    - docs/CONFIGURATION.md: Discord setup instructions
    - docs/API.md: DiscordBot API reference
"""

from dungeonmaster.interfaces.discord.bot import DiscordBot

__all__ = ["DiscordBot"]
