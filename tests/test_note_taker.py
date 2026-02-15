"""Tests for NoteTaker."""

import pytest

from dungeonmaster.core.note_taker import NoteTaker


def test_note_taker_append(vault):
    vault.ensure_all_dirs()
    taker = NoteTaker(vault, note_id="test-note")
    taker.append("First line.")
    path = taker._path()
    assert path.exists()
    assert "First line" in vault.read_text(path)
    taker.append("Second line.")
    assert "Second line" in vault.read_text(path)


def test_note_taker_note_event(vault):
    vault.ensure_all_dirs()
    taker = NoteTaker(vault, note_id="events")
    taker.note_event("player", "I open the door.")
    taker.note_event("dm", "The room is dark.")
    text = vault.read_text(taker._path())
    assert "player" in text and "I open the door" in text
    assert "dm" in text and "The room is dark" in text
