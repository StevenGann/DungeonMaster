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


def test_note_taker_set_public_note_callback(vault):
    """Test that public note callback can be set."""
    vault.ensure_all_dirs()
    taker = NoteTaker(vault, note_id="callback-test")

    callback_calls = []

    async def mock_callback(content, title):
        callback_calls.append((content, title))

    taker.set_public_note_callback(mock_callback)
    assert taker._public_note_callback is mock_callback


@pytest.mark.asyncio
async def test_note_taker_note_public_event(vault):
    """Test that public events are recorded to vault AND callback is called."""
    vault.ensure_all_dirs()

    callback_calls = []

    async def mock_callback(content, title):
        callback_calls.append((content, title))

    taker = NoteTaker(vault, note_id="public-events", public_note_callback=mock_callback)
    await taker.note_public_event("The dragon has been slain!", "Victory")

    # Check vault note was created
    text = vault.read_text(taker._path())
    assert "announcement" in text
    assert "The dragon has been slain!" in text

    # Check callback was called
    assert len(callback_calls) == 1
    assert callback_calls[0] == ("The dragon has been slain!", "Victory")


@pytest.mark.asyncio
async def test_note_taker_note_public_event_no_callback(vault):
    """Test that public events work without a callback (vault-only)."""
    vault.ensure_all_dirs()
    taker = NoteTaker(vault, note_id="public-no-callback")
    await taker.note_public_event("Important announcement", None)

    # Check vault note was created
    text = vault.read_text(taker._path())
    assert "announcement" in text
    assert "Important announcement" in text
