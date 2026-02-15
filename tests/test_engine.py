"""Tests for Engine handle_message (with mocked orchestrator)."""

from unittest.mock import AsyncMock

import pytest

from dungeonmaster.core.engine import Engine, _extract_scene_update
from dungeonmaster.core.session import SessionManager
from dungeonmaster.ai.orchestrator import AIOrchestrator
from dungeonmaster.ai.providers.base import GenerateResult


def test_extract_scene_update_none():
    assert _extract_scene_update("no json here") is None
    assert _extract_scene_update("```\n{}\n```") is None


def test_extract_scene_update_found():
    text = "Here is the scene:\n```json\n{\"scene_id\": \"room1\"}\n```"
    out = _extract_scene_update(text)
    assert out is not None
    assert out["scene_id"] == "room1"


@pytest.mark.asyncio
async def test_engine_handle_message(vault, state_store):
    async def fake_generate(prompt, system=None, task_type="narrative", **kwargs):
        return GenerateResult(text="The dragon roars.", model="test", raw=None)

    mock_provider = AsyncMock()
    mock_provider.generate = fake_generate
    mock_provider.default_model = "test"
    orchestrator = AIOrchestrator(narrative_provider=mock_provider, ruling_provider=None)
    engine = Engine(
        orchestrator=orchestrator,
        rag=None,
        state_store=state_store,
        session_manager=SessionManager(),
        note_taker=None,
    )
    reply = await engine.handle_message("sess1", "user1", "I attack the dragon.")
    assert "dragon" in reply.lower()
    session = engine._session_manager.get("sess1")
    assert session is not None
    assert len(session.turns) == 2  # user + assistant
