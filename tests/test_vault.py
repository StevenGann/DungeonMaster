"""Tests for Vault paths and read/write."""

from pathlib import Path

import pytest

from dungeonmaster.data.vault import Vault


def test_vault_dirs(vault: Vault):
    root = vault.root
    assert vault.systems_dir() == root / "systems"
    assert vault.notes_dir() == root / "notes"
    assert vault.characters_dir() == root / "characters"
    assert vault.npcs_dir() == root / "npcs"
    assert vault.state_dir() == root / "state"
    assert vault.scene_path() == root / "state" / "scene.json"


def test_character_path_sanitizes(vault: Vault):
    p = vault.character_path("user#123")
    assert " " not in p.name
    assert p.suffix == ".md"


def test_read_write_text(vault: Vault):
    path = vault.notes_dir() / "test.md"
    vault.write_text(path, "# Hello\n\nWorld.")
    assert vault.read_text(path) == "# Hello\n\nWorld."
    assert vault.exists(path)


def test_list_system_files_empty(vault: Vault):
    assert vault.list_system_files() == []


def test_list_system_files(vault: Vault):
    (vault.systems_dir() / "foo.md").write_text("x")
    (vault.systems_dir() / "bar.txt").write_text("y")
    (vault.systems_dir() / "sub").mkdir(parents=True)
    (vault.systems_dir() / "sub" / "baz.md").write_text("z")
    files = vault.list_system_files()
    assert len(files) == 3
    names = {f.name for f in files}
    assert names == {"foo.md", "bar.txt", "baz.md"}
