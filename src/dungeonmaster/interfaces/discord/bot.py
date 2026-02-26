"""
Discord bot interface for DungeonMaster.

Players interact by DMing the bot or in designated server channels. Slash
commands: /start, /action, /say, /status, /notes, /register, /characters,
/switch, /unregister, /roll. Each command and each plain message is forwarded to
engine.handle_message(session_id=user_id, user_id, content, task_type, source).
Replies are sent back to the channel (truncated to 2000 chars for Discord).

When players interact via DM, a privacy-preserving notification is posted to
the Session Notes channel (if configured).
"""

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from dungeonmaster.data.state import StateStore

from dungeonmaster.core.dice_handler import DiceRollDeclaration, get_dice_handler


logger = logging.getLogger(__name__)

# Type alias for the engine handle_message callback
# Signature: async (session_id, user_id, content, task_type, source) -> reply_text
EngineHandleMessage = Callable[[str, str, str, str, str], Awaitable[str]]


class DiscordBot(commands.Bot):
    """
    Discord interface: handle DMs and designated channels, forward messages
    to engine, send replies. Posts notifications to Session Notes channel
    when players interact privately via DM.
    """

    def __init__(
        self,
        token: str,
        engine_handle_message: EngineHandleMessage,
        state_store: "StateStore | None" = None,
        dm_only: bool = False,
        guild_id: int | None = None,
        session_notes_channel_id: int | None = None,
        gameplay_channel_ids: list[int] | None = None,
        dm_user_ids: list[int] | None = None,
        command_prefix: str = "!",
        intents: discord.Intents | None = None,
    ):
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.dm_messages = True
            intents.guilds = True
            intents.members = True  # Needed for member lookup in /register
        super().__init__(command_prefix=command_prefix, intents=intents)
        self._token = token
        self._engine_handle = engine_handle_message
        self._state_store = state_store
        self._dm_only = dm_only
        self._guild_id = guild_id
        self._session_notes_channel_id = session_notes_channel_id
        self._gameplay_channel_ids: set[int] = set(gameplay_channel_ids or [])
        self._dm_user_ids: set[int] = set(dm_user_ids or [])
        self._session_notes_channel: discord.TextChannel | None = None

    async def setup_hook(self) -> None:
        """Register slash commands and sync tree."""
        tree = self.tree
        tree.add_command(self._cmd_start())
        tree.add_command(self._cmd_action())
        tree.add_command(self._cmd_say())
        tree.add_command(self._cmd_status())
        tree.add_command(self._cmd_notes())
        tree.add_command(self._cmd_register())
        tree.add_command(self._cmd_characters())
        tree.add_command(self._cmd_switch())
        tree.add_command(self._cmd_unregister())
        tree.add_command(self._cmd_roll())
        try:
            await tree.sync()
        except Exception as e:
            logger.warning("Slash command sync failed (may need time): %s", e)

    async def on_ready(self) -> None:
        """Resolve session notes channel when bot is ready."""
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id if self.user else "N/A")

        if self._session_notes_channel_id:
            channel = self.get_channel(self._session_notes_channel_id)
            if isinstance(channel, discord.TextChannel):
                self._session_notes_channel = channel
                logger.info("Session Notes channel: #%s (ID: %d)", channel.name, channel.id)
            else:
                logger.warning(
                    "Session Notes channel ID %d not found or not a text channel",
                    self._session_notes_channel_id,
                )

        if self._gameplay_channel_ids:
            logger.info("Designated gameplay channels: %s", self._gameplay_channel_ids)

    def _get_source(self, interaction_or_message: discord.Interaction | discord.Message) -> str:
        """Determine source identifier: 'dm' or 'channel:{id}'."""
        if isinstance(interaction_or_message, discord.Interaction):
            if interaction_or_message.guild is None:
                return "dm"
            return f"channel:{interaction_or_message.channel_id}"
        else:
            if isinstance(interaction_or_message.channel, discord.DMChannel):
                return "dm"
            return f"channel:{interaction_or_message.channel.id}"

    def _is_designated_channel(self, channel_id: int) -> bool:
        """Check if channel is a designated gameplay channel."""
        return channel_id in self._gameplay_channel_ids

    def _is_dm_user(self, user_id: int) -> bool:
        """Check if user has DM (admin) permissions. If no DM IDs configured, allow anyone."""
        if not self._dm_user_ids:
            return True
        return user_id in self._dm_user_ids

    async def _post_dm_notification(self, user: discord.User | discord.Member) -> None:
        """Post a privacy-preserving notification to Session Notes channel."""
        if not self._session_notes_channel:
            return

        embed = discord.Embed(
            description=f"**{user.display_name}** had a private exchange with the DungeonMaster.",
            color=discord.Color.dark_grey(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Details remain private between player and DM")

        try:
            await self._session_notes_channel.send(embed=embed)
        except discord.DiscordException as e:
            logger.warning("Failed to post DM notification: %s", e)

    async def post_session_note(self, content: str, title: str | None = None) -> None:
        """
        Post a public session note to the Session Notes channel.

        This method is called by NoteTaker when a public event should be
        shared with all players.
        """
        if not self._session_notes_channel:
            logger.warning("No session notes channel configured; cannot post public note")
            return

        embed = discord.Embed(
            title=title or "Session Note",
            description=content[:4000],  # Discord embed description limit
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )

        try:
            await self._session_notes_channel.send(embed=embed)
        except discord.DiscordException as e:
            logger.warning("Failed to post session note: %s", e)

    def _cmd_start(self) -> app_commands.Command:
        @app_commands.command(name="start", description="Start or resume your session with the DM")
        async def start(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            session_id = str(interaction.user.id)
            source = self._get_source(interaction)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                "[Player used /start to begin or resume the game.]",
                "narrative",
                source,
            )
            await interaction.followup.send(reply[:2000], ephemeral=True)
            if source == "dm":
                await self._post_dm_notification(interaction.user)
        return start

    def _cmd_action(self) -> app_commands.Command:
        @app_commands.command(name="action", description="Describe an action your character takes")
        @app_commands.describe(action="What your character does")
        async def action(interaction: discord.Interaction, action: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            source = self._get_source(interaction)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Action] {action}",
                "narrative",
                source,
            )
            await interaction.followup.send(reply[:2000])
            if source == "dm":
                await self._post_dm_notification(interaction.user)
        return action

    def _cmd_say(self) -> app_commands.Command:
        @app_commands.command(name="say", description="Have your character say something")
        @app_commands.describe(text="What your character says")
        async def say(interaction: discord.Interaction, text: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            source = self._get_source(interaction)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Says] {text}",
                "narrative",
                source,
            )
            await interaction.followup.send(reply[:2000])
            if source == "dm":
                await self._post_dm_notification(interaction.user)
        return say

    def _cmd_status(self) -> app_commands.Command:
        @app_commands.command(name="status", description="Ask for a ruling or current situation")
        @app_commands.describe(question="Your question")
        async def status(interaction: discord.Interaction, question: str) -> None:
            await interaction.response.defer()
            session_id = str(interaction.user.id)
            source = self._get_source(interaction)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                f"[Status/Ruling] {question}",
                "ruling",
                source,
            )
            await interaction.followup.send(reply[:2000])
            if source == "dm":
                await self._post_dm_notification(interaction.user)
        return status

    def _cmd_notes(self) -> app_commands.Command:
        @app_commands.command(name="notes", description="Get a summary of recent notes")
        async def notes(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            session_id = str(interaction.user.id)
            source = self._get_source(interaction)
            reply = await self._engine_handle(
                session_id,
                str(interaction.user.id),
                "[Player requested recent session notes summary.]",
                "ruling",
                source,
            )
            await interaction.followup.send(reply[:2000], ephemeral=True)
            if source == "dm":
                await self._post_dm_notification(interaction.user)
        return notes

    def _cmd_register(self) -> app_commands.Command:
        @app_commands.command(name="register", description="[DM] Register a player with a character sheet")
        @app_commands.describe(
            player="The player to register",
            character_name="Character name (must match filename without .md)"
        )
        async def register(
            interaction: discord.Interaction,
            player: discord.Member,
            character_name: str,
        ) -> None:
            await interaction.response.defer(ephemeral=True)

            if not self._is_dm_user(interaction.user.id):
                await interaction.followup.send(
                    "❌ Only the DM can register players.", ephemeral=True
                )
                return

            if not self._state_store:
                await interaction.followup.send(
                    "❌ State store not configured.", ephemeral=True
                )
                return

            character_file = self._state_store.get_character_file_path(character_name)
            if not self._state_store.character_file_exists(character_name):
                await interaction.followup.send(
                    f"❌ Character file not found: `{character_file}`\n"
                    f"Create the file in the vault's `characters/` directory first.",
                    ephemeral=True,
                )
                return

            registered_player = self._state_store.register_player(
                discord_id=str(player.id),
                display_name=player.display_name,
                character_name=character_name,
                character_file=character_file,
            )

            char_count = len(registered_player.characters)
            await interaction.followup.send(
                f"✅ Registered **{player.display_name}** as **{character_name}**\n"
                f"Character file: `{character_file}`\n"
                f"Total characters for this player: {char_count}",
                ephemeral=True,
            )
        return register

    def _cmd_characters(self) -> app_commands.Command:
        @app_commands.command(name="characters", description="List your registered characters")
        async def characters(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)

            if not self._state_store:
                await interaction.followup.send(
                    "❌ State store not configured.", ephemeral=True
                )
                return

            registry = self._state_store.load_player_registry()
            player = registry.get_player(str(interaction.user.id))

            if not player or not player.characters:
                await interaction.followup.send(
                    "You don't have any registered characters.\n"
                    "Ask the DM to register you with `/register`.",
                    ephemeral=True,
                )
                return

            lines = ["**Your Characters:**\n"]
            for char in player.characters:
                active = " ✅ *(active)*" if char.is_active else ""
                lines.append(f"• **{char.name}**{active}\n  `{char.file_path}`")

            await interaction.followup.send("\n".join(lines), ephemeral=True)
        return characters

    def _cmd_switch(self) -> app_commands.Command:
        @app_commands.command(name="switch", description="Switch to a different character")
        @app_commands.describe(character_name="Name of the character to switch to")
        async def switch(interaction: discord.Interaction, character_name: str) -> None:
            await interaction.response.defer(ephemeral=True)

            if not self._state_store:
                await interaction.followup.send(
                    "❌ State store not configured.", ephemeral=True
                )
                return

            success = self._state_store.set_active_character(
                str(interaction.user.id), character_name
            )

            if success:
                await interaction.followup.send(
                    f"✅ Switched to **{character_name}**", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Character **{character_name}** not found in your registration.\n"
                    f"Use `/characters` to see your registered characters.",
                    ephemeral=True,
                )
        return switch

    def _cmd_unregister(self) -> app_commands.Command:
        @app_commands.command(name="unregister", description="[DM] Remove a character from a player")
        @app_commands.describe(
            player="The player to modify",
            character_name="Character name to remove"
        )
        async def unregister(
            interaction: discord.Interaction,
            player: discord.Member,
            character_name: str,
        ) -> None:
            await interaction.response.defer(ephemeral=True)

            if not self._is_dm_user(interaction.user.id):
                await interaction.followup.send(
                    "❌ Only the DM can unregister characters.", ephemeral=True
                )
                return

            if not self._state_store:
                await interaction.followup.send(
                    "❌ State store not configured.", ephemeral=True
                )
                return

            success = self._state_store.unregister_character(
                str(player.id), character_name
            )

            if success:
                await interaction.followup.send(
                    f"✅ Removed **{character_name}** from **{player.display_name}**",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"❌ Character **{character_name}** not found for **{player.display_name}**",
                    ephemeral=True,
                )
        return unregister

    def _cmd_roll(self) -> app_commands.Command:
        @app_commands.command(name="roll", description="Roll dice using standard notation")
        @app_commands.describe(
            dice="Dice notation (e.g., 1d20+5, 2d6, 4d6kh3, 1d20+5 DC:14)",
            purpose="What the roll is for (optional)"
        )
        async def roll(
            interaction: discord.Interaction,
            dice: str,
            purpose: str = "manual roll",
        ) -> None:
            await interaction.response.defer()

            # Get character name if player is registered
            character_name = ""
            if self._state_store:
                registry = self._state_store.load_player_registry()
                player = registry.get_player(str(interaction.user.id))
                if player:
                    active_char = player.get_active_character()
                    if active_char:
                        character_name = active_char.name

            # Use display name as fallback
            if not character_name:
                character_name = interaction.user.display_name

            # Execute the roll
            dice_handler = get_dice_handler()
            declaration = DiceRollDeclaration(
                notation=dice,
                purpose=purpose,
                character=character_name,
            )

            report = dice_handler.execute_roll(declaration)

            if report is None:
                await interaction.followup.send(
                    f"❌ Could not parse dice notation: `{dice}`\n\n"
                    "**Supported formats:**\n"
                    "• Basic: `1d20`, `2d6`, `d8`, `d%`, `dF`\n"
                    "• Modifiers: `1d20+5`, `2d6-2`\n"
                    "• Multiple: `2d6+1d4+3`\n"
                    "• Keep/Drop: `4d6kh3`, `2d20kl1`, `4d6dl1`\n"
                    "• Exploding: `1d6!`, `1d6!>4`\n"
                    "• Reroll: `1d6r1`, `1d6r<2`\n"
                    "• Success count: `8d6>=5`\n"
                    "• DC check: `1d20+5 DC:14`"
                )
                return

            await interaction.followup.send(report.display_text)
        return roll

    async def on_message(self, message: discord.Message) -> None:
        """Handle plain text messages in DMs or designated channels."""
        if message.author.bot:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_designated = (
            message.guild is not None
            and self._is_designated_channel(message.channel.id)
        )

        # In dm_only mode, only process DMs
        if self._dm_only and not is_dm:
            return

        # If not dm_only, accept DMs or designated channels only
        if not is_dm and not is_designated:
            return

        session_id = str(message.author.id)
        source = self._get_source(message)

        try:
            reply = await self._engine_handle(
                session_id,
                str(message.author.id),
                message.content,
                "narrative",
                source,
            )
            await message.channel.send(reply[:2000])

            # Post notification to Session Notes if this was a DM
            if is_dm:
                await self._post_dm_notification(message.author)

        except Exception as e:
            logger.exception("Engine handle_message failed: %s", e)
            await message.channel.send("Something went wrong. Please try again.")

    def run_bot(self) -> None:
        """Blocking run. Use start() for async."""
        self.run(self._token, log_handler=None)
