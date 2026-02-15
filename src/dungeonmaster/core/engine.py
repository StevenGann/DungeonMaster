"""
Core message-handling engine.

Single entrypoint for player messages: loads session (history), RAG context,
scene state, and character sheet; builds a system prompt; calls the AI
orchestrator; parses optional scene JSON from the reply and saves it; appends
to the note taker. See docs/ARCHITECTURE.md for the full sequence diagram.
"""

import json
import re
from typing import Any

from dungeonmaster.ai.orchestrator import AIOrchestrator
from dungeonmaster.ai.rag import RAGStore
from dungeonmaster.core.note_taker import NoteTaker
from dungeonmaster.core.session import SessionManager
from dungeonmaster.data.state import SceneState, StateStore


def _extract_scene_update(text: str) -> dict | None:
    """Parse first ```json ... ``` fenced block in text; return None if missing or invalid."""
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    return None


class Engine:
    """
    Single entrypoint for handling a player message: load context (RAG, state, character),
    call orchestrator, optionally update scene from structured output, append notes.
    """

    def __init__(
        self,
        orchestrator: AIOrchestrator,
        rag: RAGStore | None,
        state_store: StateStore,
        session_manager: SessionManager,
        note_taker: NoteTaker | None = None,
    ):
        self._orchestrator = orchestrator
        self._rag = rag
        self._state_store = state_store
        self._session_manager = session_manager
        self._note_taker = note_taker

    async def handle_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        task_type: str = "narrative",
    ) -> str:
        """
        Process one user message: add to session, build prompt with RAG + state + history,
        generate reply, optionally update scene and notes. Returns assistant text.
        """
        session = self._session_manager.get_or_create(session_id)
        session.add_turn("user", content)

        # Retrieve relevant rule/lore chunks for the system prompt
        rag_context = ""
        if self._rag:
            try:
                chunks = await self._rag.query(content, top_k=5)
                if chunks:
                    rag_context = "\n\n---\n\n".join(chunks)
            except Exception:
                pass

        scene = self._state_store.load_scene()
        scene_block = f"Current scene: {scene.location.name}. {scene.location.description}"
        if scene.positions:
            scene_block += "\nPositions: " + ", ".join(
                f"{p.entity_id}({p.entity_type})" for p in scene.positions
            )

        character = self._state_store.load_character(user_id)
        character_block = f"Player character sheet:\n{character}" if character else "No character sheet for this player yet."

        # Assemble system prompt: role, scene, character, optional RAG context
        system = f"""You are the Dungeon Master for a TTRPG. Use only the provided rule context when making rulings.

{scene_block}

{character_block}
"""
        if rag_context:
            system += f"\n\nRelevant rules/source material:\n{rag_context}"

        messages = session.to_messages()
        # Last message is the current user message; we're generating the DM reply
        prompt = messages[-1]["content"] if messages else content

        result = await self._orchestrator.generate(
            prompt=prompt,
            system=system,
            task_type=task_type,
        )

        reply = result.text.strip()
        session.add_turn("assistant", reply)

        # If the model returned a ```json ... ``` block, persist as new scene state
        scene_update = _extract_scene_update(reply)
        if scene_update:
            try:
                new_scene = SceneState.from_dict(scene_update)
                self._state_store.save_scene(new_scene)
            except (TypeError, KeyError):
                pass

        if self._note_taker:
            self._note_taker.note_event("player", content)
            self._note_taker.note_event("dm", reply)  # Append both to vault notes/


        return reply
