"""
Discord bot: players DM the bot. Commands: /start, /action, /say, /status, /notes.
"""

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from dungeonmaster.interfaces.base import Message, Response

logger = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    """
    Discord interface: handle DMs, forward messages to engine, send replies.
    Requires engine.handle_message(session_id, user_id, content) -> str.
    """

    def __init__(
        self,
        token: str,
        engine_handle_message: Any,  # async (session_id, user_id, content, task_type?) -> str
        dm_only: bool = True,
        command_prefix: str = "!",
        intents: discord.Intents | None = None,
    ):
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.dm_messages = True
        super().__init__(command_prefix=command_prefix, intents=intents)
        self._token = token
        self._engine_handle = engine_handle_message
        self._dm_only = dm_only

    async def setup_hook(self) -> None:
        """Register slash commands and sync tree."""
        tree = self.tree
        tree.add_command(self._cmd_start())
        tree.add_command(self._cmd_action())
        tree.add_command(self._cmd_say())
        tree.add_command(self._cmd_status())
        tree.add_command(self._cmd_notes())
        try:
            await tree.sync()
        except Exception as e:
            logger.warning("Slash command sync failed (may need time): %s", e)

    def _cmd_start(self) -> app_commands.Command:
        @app_commands.command(name="start", description="Start or resume your session with the DM")
        async def start(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            session_id = str(interaction.user.id)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                "[Player used /start to begin or resume the game.]",
                task_type="narrative",
            )
            await interaction.followup.send(reply[:2000], ephemeral=True)
        return start

    def _cmd_action(self) -> app_commands.Command:
        @app_commands.command(name="action", description="Describe an action your character takes")
        @app_commands.describe(action="What your character does")
        async def action(interaction: discord.Interaction, action: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Action] {action}",
                task_type="narrative",
            )
            await interaction.followup.send(reply[:2000])
        return action

    def _cmd_say(self) -> app_commands.Command:
        @app_commands.command(name="say", description="Have your character say something")
        @app_commands.describe(text="What your character says")
        async def say(interaction: discord.Interaction, text: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Says] {text}",
                task_type="narrative",
            )
            await interaction.followup.send(reply[:2000])
        return say

    def _cmd_status(self) -> app_commands.Command:
        @app_commands.command(name="status", description="Ask for a ruling or current situation")
        @app_commands.describe(question="Your question")
        async def status(interaction: discord.Interaction, question: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Status/Ruling] {question}",
                task_type="ruling",
            )
            await interaction.followup.send(reply[:2000])
        return status

    def _cmd_notes(self) -> app_commands.Command:
        @app_commands.command(name="notes", description="Get a summary of recent notes")
        async def notes(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            session_id = str(interaction.user.id)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                "[Player requested recent session notes summary.]",
                task_type="ruling",
            )
            await interaction.followup.send(reply[:2000], ephemeral=True)
        return notes

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self._dm_only and message.guild is not None:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return
        # Plain DM text (no slash): treat as player message
        session_id = str(message.author.id)
        try:
            reply = await self._engine_handle(
                session_id,
                str(message.author.id),
                message.content,
                task_type="narrative",
            )
            await message.channel.send(reply[:2000])
        except Exception as e:
            logger.exception("Engine handle_message failed: %s", e)
            await message.channel.send("Something went wrong. Please try again.")

    def run_bot(self) -> None:
        """Blocking run. Use start() for async."""
        self.run(self._token, log_handler=None)
