"""Tests for Discord channel routing and Session Notes notifications."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dungeonmaster.interfaces.discord.bot import DiscordBot


@pytest.fixture
def mock_engine_handle():
    """Mock engine.handle_message that returns a simple reply."""
    async def handle(session_id, user_id, content, task_type, source):
        return f"Reply to {content[:20]}..."
    return handle


@pytest.fixture
def bot_with_channels(mock_engine_handle):
    """Create a DiscordBot with channel configuration."""
    return DiscordBot(
        token="test-token",
        engine_handle_message=mock_engine_handle,
        dm_only=False,
        guild_id=123456789,
        session_notes_channel_id=987654321,
        gameplay_channel_ids=[111111111, 222222222],
    )


@pytest.fixture
def bot_dm_only(mock_engine_handle):
    """Create a DiscordBot in DM-only mode."""
    return DiscordBot(
        token="test-token",
        engine_handle_message=mock_engine_handle,
        dm_only=True,
    )


class TestChannelRouting:
    """Tests for _is_designated_channel and _get_source."""

    def test_is_designated_channel_true(self, bot_with_channels):
        assert bot_with_channels._is_designated_channel(111111111) is True
        assert bot_with_channels._is_designated_channel(222222222) is True

    def test_is_designated_channel_false(self, bot_with_channels):
        assert bot_with_channels._is_designated_channel(999999999) is False

    def test_is_designated_channel_empty(self, bot_dm_only):
        assert bot_dm_only._is_designated_channel(111111111) is False

    def test_get_source_dm_message(self, bot_with_channels):
        import discord
        mock_message = MagicMock(spec=discord.Message)
        mock_dm_channel = MagicMock(spec=discord.DMChannel)
        mock_message.channel = mock_dm_channel
        source = bot_with_channels._get_source(mock_message)
        assert source == "dm"

    def test_get_source_guild_channel_message(self, bot_with_channels):
        import discord
        mock_message = MagicMock(spec=discord.Message)
        mock_text_channel = MagicMock(spec=discord.TextChannel)
        mock_text_channel.id = 111111111
        mock_message.channel = mock_text_channel
        source = bot_with_channels._get_source(mock_message)
        assert source == "channel:111111111"

    def test_get_source_dm_interaction(self, bot_with_channels):
        import discord
        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_interaction.guild = None
        mock_interaction.channel_id = 123
        source = bot_with_channels._get_source(mock_interaction)
        assert source == "dm"

    def test_get_source_guild_interaction(self, bot_with_channels):
        import discord
        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_interaction.guild = MagicMock()
        mock_interaction.channel_id = 111111111
        source = bot_with_channels._get_source(mock_interaction)
        assert source == "channel:111111111"


class TestDMNotifications:
    """Tests for DM privacy notifications to Session Notes channel."""

    @pytest.mark.asyncio
    async def test_post_dm_notification_no_channel(self, bot_dm_only):
        """Should not raise when no session notes channel configured."""
        mock_user = MagicMock()
        mock_user.display_name = "TestPlayer"
        await bot_dm_only._post_dm_notification(mock_user)
        # Should complete without error

    @pytest.mark.asyncio
    async def test_post_dm_notification_with_channel(self, bot_with_channels):
        """Should post embed to session notes channel."""
        mock_channel = AsyncMock()
        bot_with_channels._session_notes_channel = mock_channel

        mock_user = MagicMock()
        mock_user.display_name = "TestPlayer"

        await bot_with_channels._post_dm_notification(mock_user)

        mock_channel.send.assert_called_once()
        call_kwargs = mock_channel.send.call_args
        embed = call_kwargs.kwargs.get("embed") or call_kwargs.args[0]
        assert "TestPlayer" in embed.description
        assert "private" in embed.description.lower()


class TestSessionNotesPosting:
    """Tests for public session note posting."""

    @pytest.mark.asyncio
    async def test_post_session_note_no_channel(self, bot_dm_only, caplog):
        """Should log warning when no channel configured."""
        await bot_dm_only.post_session_note("Test content", "Test Title")
        assert "No session notes channel configured" in caplog.text

    @pytest.mark.asyncio
    async def test_post_session_note_with_channel(self, bot_with_channels):
        """Should post embed with content to session notes channel."""
        mock_channel = AsyncMock()
        bot_with_channels._session_notes_channel = mock_channel

        await bot_with_channels.post_session_note("Test content", "Test Title")

        mock_channel.send.assert_called_once()
        call_kwargs = mock_channel.send.call_args
        embed = call_kwargs.kwargs.get("embed") or call_kwargs.args[0]
        assert embed.title == "Test Title"
        assert embed.description == "Test content"

    @pytest.mark.asyncio
    async def test_post_session_note_default_title(self, bot_with_channels):
        """Should use 'Session Note' as default title."""
        mock_channel = AsyncMock()
        bot_with_channels._session_notes_channel = mock_channel

        await bot_with_channels.post_session_note("Test content")

        call_kwargs = mock_channel.send.call_args
        embed = call_kwargs.kwargs.get("embed") or call_kwargs.args[0]
        assert embed.title == "Session Note"


class TestConfigParsing:
    """Tests for channel configuration dataclasses."""

    def test_channel_config_from_dict(self):
        from dungeonmaster.config import ChannelConfig

        data = {
            "id": 123456789,
            "name": "test-channel",
            "description": "A test channel",
        }
        config = ChannelConfig.from_dict(data)

        assert config.id == 123456789
        assert config.name == "test-channel"
        assert config.description == "A test channel"

    def test_channel_config_from_dict_missing_id(self):
        from dungeonmaster.config import ChannelConfig

        data = {
            "name": "test-channel",
            "description": "A test channel",
        }
        config = ChannelConfig.from_dict(data)

        assert config.id is None
        assert config.name == "test-channel"

    def test_discord_channels_config_from_dict(self):
        from dungeonmaster.config import DiscordChannelsConfig

        data = {
            "session_notes": {
                "id": 111,
                "name": "session-notes",
                "description": "Notes channel",
            },
            "gameplay": [
                {"id": 222, "name": "tavern", "description": "Tavern channel"},
                {"id": 333, "name": "adventure", "description": "Adventure channel"},
            ],
        }
        config = DiscordChannelsConfig.from_dict(data)

        assert config.session_notes is not None
        assert config.session_notes.id == 111
        assert len(config.gameplay) == 2
        assert config.gameplay[0].id == 222
        assert config.gameplay[1].name == "adventure"

    def test_discord_channels_config_gameplay_channel_ids(self):
        from dungeonmaster.config import DiscordChannelsConfig

        data = {
            "gameplay": [
                {"id": 111, "name": "a", "description": ""},
                {"id": None, "name": "b", "description": ""},
                {"id": 222, "name": "c", "description": ""},
            ],
        }
        config = DiscordChannelsConfig.from_dict(data)

        ids = config.gameplay_channel_ids()
        assert ids == [111, 222]  # None should be filtered out

    def test_discord_config_from_dict(self):
        from dungeonmaster.config import DiscordConfig

        data = {
            "token": "test-token",
            "dm_only": False,
            "guild_id": 123456,
            "channels": {
                "session_notes": {"id": 111, "name": "notes", "description": ""},
                "gameplay": [{"id": 222, "name": "tavern", "description": ""}],
            },
        }
        config = DiscordConfig.from_dict(data)

        assert config.token == "test-token"
        assert config.dm_only is False
        assert config.guild_id == 123456
        assert config.channels.session_notes.id == 111
        assert len(config.channels.gameplay) == 1
