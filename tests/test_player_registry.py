"""Tests for PlayerRegistry, RegisteredPlayer, and StateStore registry methods."""

import pytest

from dungeonmaster.data.state import (
    PlayerCharacter,
    PlayerRegistry,
    RegisteredPlayer,
    StateStore,
)


class TestPlayerCharacter:
    """Tests for PlayerCharacter dataclass."""

    def test_to_dict(self):
        char = PlayerCharacter(name="Gandalf", file_path="characters/Gandalf.md", is_active=True)
        d = char.to_dict()
        assert d == {
            "name": "Gandalf",
            "file_path": "characters/Gandalf.md",
            "is_active": True,
        }

    def test_from_dict(self):
        data = {
            "name": "Aragorn",
            "file_path": "characters/Aragorn.md",
            "is_active": False,
        }
        char = PlayerCharacter.from_dict(data)
        assert char.name == "Aragorn"
        assert char.file_path == "characters/Aragorn.md"
        assert char.is_active is False


class TestRegisteredPlayer:
    """Tests for RegisteredPlayer dataclass."""

    def test_active_character_returns_active(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Char1", file_path="c1.md", is_active=False),
                PlayerCharacter(name="Char2", file_path="c2.md", is_active=True),
            ],
        )
        active = player.active_character()
        assert active is not None
        assert active.name == "Char2"

    def test_active_character_returns_first_if_none_active(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Char1", file_path="c1.md", is_active=False),
                PlayerCharacter(name="Char2", file_path="c2.md", is_active=False),
            ],
        )
        active = player.active_character()
        assert active is not None
        assert active.name == "Char1"

    def test_active_character_returns_none_if_no_characters(self):
        player = RegisteredPlayer(discord_id="123", display_name="Test", characters=[])
        assert player.active_character() is None

    def test_get_character_found(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Gandalf", file_path="g.md", is_active=True),
            ],
        )
        char = player.get_character("gandalf")  # Case-insensitive
        assert char is not None
        assert char.name == "Gandalf"

    def test_get_character_not_found(self):
        player = RegisteredPlayer(discord_id="123", display_name="Test", characters=[])
        assert player.get_character("Gandalf") is None

    def test_set_active_success(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Char1", file_path="c1.md", is_active=True),
                PlayerCharacter(name="Char2", file_path="c2.md", is_active=False),
            ],
        )
        result = player.set_active("Char2")
        assert result is True
        assert player.characters[0].is_active is False
        assert player.characters[1].is_active is True

    def test_set_active_not_found(self):
        player = RegisteredPlayer(discord_id="123", display_name="Test", characters=[])
        result = player.set_active("NonExistent")
        assert result is False

    def test_to_dict_and_from_dict_roundtrip(self):
        player = RegisteredPlayer(
            discord_id="123456",
            display_name="PlayerOne",
            characters=[
                PlayerCharacter(name="Gandalf", file_path="characters/Gandalf.md", is_active=True),
            ],
            registered_at="2025-01-01T00:00:00Z",
        )
        d = player.to_dict()
        restored = RegisteredPlayer.from_dict(d)
        assert restored.discord_id == player.discord_id
        assert restored.display_name == player.display_name
        assert len(restored.characters) == 1
        assert restored.characters[0].name == "Gandalf"


class TestPlayerRegistry:
    """Tests for PlayerRegistry dataclass."""

    def test_get_player_found(self):
        player = RegisteredPlayer(discord_id="123", display_name="Test", characters=[])
        registry = PlayerRegistry(players={"123": player})
        assert registry.get_player("123") is player

    def test_get_player_not_found(self):
        registry = PlayerRegistry()
        assert registry.get_player("999") is None

    def test_get_active_character_path_found(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Gandalf", file_path="characters/Gandalf.md", is_active=True),
            ],
        )
        registry = PlayerRegistry(players={"123": player})
        path = registry.get_active_character_path("123")
        assert path == "characters/Gandalf.md"

    def test_get_active_character_path_not_registered(self):
        registry = PlayerRegistry()
        assert registry.get_active_character_path("999") is None

    def test_to_dict_and_from_dict_roundtrip(self):
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Char1", file_path="c1.md", is_active=True),
            ],
        )
        registry = PlayerRegistry(players={"123": player})
        d = registry.to_dict()
        restored = PlayerRegistry.from_dict(d)
        assert "123" in restored.players
        assert restored.players["123"].display_name == "Test"


class TestStateStoreRegistry:
    """Tests for StateStore player registry methods."""

    def test_load_player_registry_empty(self, vault):
        store = StateStore(vault)
        registry = store.load_player_registry()
        assert len(registry.players) == 0

    def test_save_and_load_player_registry(self, vault):
        store = StateStore(vault)
        player = RegisteredPlayer(
            discord_id="123",
            display_name="Test",
            characters=[
                PlayerCharacter(name="Gandalf", file_path="characters/Gandalf.md", is_active=True),
            ],
            registered_at="2025-01-01T00:00:00Z",
        )
        registry = PlayerRegistry(players={"123": player})
        store.save_player_registry(registry)

        loaded = store.load_player_registry()
        assert "123" in loaded.players
        assert loaded.players["123"].display_name == "Test"
        assert loaded.players["123"].characters[0].name == "Gandalf"

    def test_register_player_new(self, vault):
        store = StateStore(vault)
        player = store.register_player(
            discord_id="123",
            display_name="PlayerOne",
            character_name="Gandalf",
            character_file="characters/Gandalf.md",
        )
        assert player.discord_id == "123"
        assert player.display_name == "PlayerOne"
        assert len(player.characters) == 1
        assert player.characters[0].name == "Gandalf"
        assert player.characters[0].is_active is True

    def test_register_player_add_second_character(self, vault):
        store = StateStore(vault)
        store.register_player("123", "PlayerOne", "Gandalf", "characters/Gandalf.md")
        player = store.register_player("123", "PlayerOne", "Aragorn", "characters/Aragorn.md")

        assert len(player.characters) == 2
        # First character should still be active
        assert player.characters[0].is_active is True
        assert player.characters[1].is_active is False

    def test_register_player_update_existing_character(self, vault):
        store = StateStore(vault)
        store.register_player("123", "PlayerOne", "Gandalf", "characters/Gandalf.md")
        player = store.register_player("123", "PlayerOne", "Gandalf", "characters/Gandalf-v2.md")

        assert len(player.characters) == 1
        assert player.characters[0].file_path == "characters/Gandalf-v2.md"

    def test_set_active_character_success(self, vault):
        store = StateStore(vault)
        store.register_player("123", "Test", "Char1", "c1.md")
        store.register_player("123", "Test", "Char2", "c2.md")

        result = store.set_active_character("123", "Char2")
        assert result is True

        registry = store.load_player_registry()
        player = registry.get_player("123")
        active = player.active_character()
        assert active.name == "Char2"

    def test_set_active_character_not_found(self, vault):
        store = StateStore(vault)
        result = store.set_active_character("999", "NonExistent")
        assert result is False

    def test_unregister_character_success(self, vault):
        store = StateStore(vault)
        store.register_player("123", "Test", "Char1", "c1.md")
        store.register_player("123", "Test", "Char2", "c2.md")

        result = store.unregister_character("123", "Char1")
        assert result is True

        registry = store.load_player_registry()
        player = registry.get_player("123")
        assert len(player.characters) == 1
        assert player.characters[0].name == "Char2"
        # Char2 should now be active (was the remaining character)
        assert player.characters[0].is_active is True

    def test_unregister_character_not_found(self, vault):
        store = StateStore(vault)
        result = store.unregister_character("123", "NonExistent")
        assert result is False

    def test_get_active_character_path_via_store(self, vault):
        store = StateStore(vault)
        store.register_player("123", "Test", "Gandalf", "characters/Gandalf.md")

        path = store.get_active_character_path("123")
        assert path == "characters/Gandalf.md"

    def test_get_active_character_path_not_registered(self, vault):
        store = StateStore(vault)
        path = store.get_active_character_path("999")
        assert path is None

    def test_load_character_by_path(self, vault):
        store = StateStore(vault)
        # Create a character file
        char_path = vault.characters_dir() / "TestChar.md"
        vault.write_text(char_path, "# TestChar\nLevel 5 Wizard")

        content = store.load_character_by_path("characters/TestChar.md")
        assert "TestChar" in content
        assert "Level 5 Wizard" in content

    def test_load_character_by_path_not_found(self, vault):
        store = StateStore(vault)
        content = store.load_character_by_path("characters/NonExistent.md")
        assert content == ""

    def test_character_file_exists_true(self, vault):
        store = StateStore(vault)
        # Create a character file
        char_path = vault.characters_dir() / "ExistingChar.md"
        vault.write_text(char_path, "# ExistingChar")

        assert store.character_file_exists("ExistingChar") is True

    def test_character_file_exists_false(self, vault):
        store = StateStore(vault)
        assert store.character_file_exists("NonExistent") is False

    def test_get_character_file_path(self, vault):
        store = StateStore(vault)
        path = store.get_character_file_path("My Character")
        assert path == "characters/My Character.md"

    def test_get_character_file_path_sanitizes_special_chars(self, vault):
        store = StateStore(vault)
        path = store.get_character_file_path("Char<>Name")
        assert "<" not in path
        assert ">" not in path
