"""
Core message-handling engine.

Single entrypoint for player messages: loads session (history), RAG context,
scene state, and character sheet; builds a system prompt; calls the AI
orchestrator; parses optional scene JSON from the reply and saves it; appends
to the note taker. See docs/ARCHITECTURE.md for the full sequence diagram.

Dice Rolling:
The AI can request dice rolls using the [ROLL: notation for purpose] syntax.
These are intercepted, executed via RNG, and the results are injected back
into the conversation. The AI then continues with the roll outcomes.
"""

import json
import logging
import re

from dungeonmaster.ai.orchestrator import AIOrchestrator
from dungeonmaster.core.dice_handler import DiceHandler, get_dice_handler


logger = logging.getLogger(__name__)
from dungeonmaster.ai.rag import RAGStore
from dungeonmaster.core.note_taker import NoteTaker
from dungeonmaster.core.session import SessionManager
from dungeonmaster.data.state import SceneState, StateStore


# Instructions for the AI on how to request dice rolls
DICE_ROLL_INSTRUCTIONS = """
DICE ROLLING PROTOCOL:
When a situation requires a dice roll (attacks, skill checks, saving throws, damage, etc.),
you MUST NOT generate random numbers yourself. Instead, use the following syntax to request a roll:

[ROLL: {notation} for {purpose}]

Examples:
- [ROLL: 1d20+5 DC:14 for attack roll against the goblin]
- [ROLL: 2d6+3 for longsword damage]
- [ROLL: 1d20+2 DC:12 for Dexterity saving throw]
- [ROLL: 1d20+4 for initiative]
- [ROLL: 4d6kh3 for ability score generation]
- [ROLL: 2d20kh1+5 DC:15 for attack with advantage]
- [ROLL: 2d20kl1+5 DC:15 for attack with disadvantage]
- [ROLL: 1d6! for exploding damage]
- [ROLL: 8d6>=5 for World of Darkness successes]

Supported notation:
- Basic: 1d20, 2d6, d8, d% (percentile), dF (Fudge/Fate dice)
- Modifiers: +5, -3
- Multiple pools: 2d6+1d4+3
- Keep highest/lowest: 4d6kh3 (keep highest 3), 2d20kl1 (disadvantage)
- Drop highest/lowest: 4d6dl1 (drop lowest 1)
- Exploding: 1d6! (explode on max), 1d6!>4 (explode on >4)
- Reroll: 1d6r1 (reroll 1s once), 1d6rr<3 (reroll <3 recursively)
- Success counting: 8d6>=5 (count dice >=5)
- Multiply/divide: 2d6*2, 1d10/2
- DC/CR/AC: 1d20+5 DC:14, 1d20+3 AC:16

The system will execute the roll with actual RNG, then provide you with the results.
You MUST wait for the dice results before narrating the outcome.
After receiving roll results, incorporate them into your narrative response.
"""


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

    Dice Rolling Workflow:
    1. Player sends action requiring a roll
    2. AI generates response with [ROLL: notation for purpose] tags
    3. Engine intercepts these, executes actual RNG rolls
    4. Engine sends roll results back to AI for narrative continuation
    5. AI incorporates results into final response
    """

    def __init__(
        self,
        orchestrator: AIOrchestrator,
        rag: RAGStore | None,
        state_store: StateStore,
        session_manager: SessionManager,
        note_taker: NoteTaker | None = None,
        dice_handler: DiceHandler | None = None,
    ):
        self._orchestrator = orchestrator
        self._rag = rag
        self._state_store = state_store
        self._session_manager = session_manager
        self._note_taker = note_taker
        self._dice_handler = dice_handler or get_dice_handler()

    async def handle_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        task_type: str = "narrative",
        source: str = "dm",
    ) -> str:
        """
        Process one user message: add to session, build prompt with RAG + state + history,
        generate reply, optionally update scene and notes. Returns assistant text.

        Args:
            session_id: Unique session identifier (typically user_id for 1:1 sessions)
            user_id: Discord user ID
            content: Message content from the player
            task_type: "narrative" or "ruling" to route to appropriate AI provider
            source: Message source - "dm" for direct messages, "channel:{id}" for guild channels
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
            except Exception as e:
                logger.warning("RAG query failed for session %s: %s", session_id, e)

        scene = self._state_store.load_scene()
        scene_block = f"Current scene: {scene.location.name}. {scene.location.description}"
        if scene.positions:
            scene_block += "\nPositions: " + ", ".join(
                f"{p.entity_id}({p.entity_type})" for p in scene.positions
            )

        # Look up character via player registry; fallback to legacy user_id-based lookup
        character_path = self._state_store.get_active_character_path(user_id)
        if character_path:
            character = self._state_store.load_character_by_path(character_path)
        else:
            character = self._state_store.load_character(user_id)
        character_block = f"Player character sheet:\n{character}" if character else "No character sheet for this player yet."

        # Get character name for dice rolls
        character_name = ""
        if character:
            # Try to extract character name from the first line of the character sheet
            first_line = character.split("\n")[0] if character else ""
            if first_line.startswith("# "):
                character_name = first_line[2:].strip()

        # Assemble system prompt: role, scene, character, dice instructions, optional RAG context
        system = f"""You are the Dungeon Master for a TTRPG. Use only the provided rule context when making rulings.

{scene_block}

{character_block}

{DICE_ROLL_INSTRUCTIONS}
"""
        if rag_context:
            system += f"\n\nRelevant rules/source material:\n{rag_context}"

        messages = session.to_messages()
        # Last message is the current user message; we're generating the DM reply
        prompt = messages[-1]["content"] if messages else content

        # First pass: Generate AI response (may contain roll requests)
        result = await self._orchestrator.generate(
            prompt=prompt,
            system=system,
            task_type=task_type,
        )

        reply = result.text.strip()

        # Check for dice roll requests and process them
        processed_reply, roll_reports = self._dice_handler.process_ai_response(
            reply, character=character_name
        )

        # If there were dice rolls, do a second pass to let AI narrate the outcomes
        if roll_reports:
            roll_context = self._dice_handler.get_ai_roll_results_context(roll_reports)

            # Build continuation prompt with roll results
            continuation_prompt = f"""The dice have been rolled. Here are the results:

{roll_context}

Now continue your narrative response, incorporating these dice roll results.
Describe what happens based on the outcomes. Do NOT request any more rolls for this action.
"""

            # Second pass: AI narrates the outcome
            continuation_result = await self._orchestrator.generate(
                prompt=continuation_prompt,
                system=system,
                task_type=task_type,
            )

            continuation_text = continuation_result.text.strip()

            # Combine the processed reply (with roll results displayed) and continuation
            # Remove any trailing incomplete sentences from processed_reply before the roll
            final_reply = self._combine_roll_response(processed_reply, continuation_text)
        else:
            final_reply = processed_reply

        session.add_turn("assistant", final_reply)

        # If the model returned a ```json ... ``` block, persist as new scene state
        scene_update = _extract_scene_update(final_reply)
        if scene_update:
            try:
                new_scene = SceneState.from_dict(scene_update)
                self._state_store.save_scene(new_scene)
            except (TypeError, KeyError) as e:
                logger.warning("Failed to parse scene update from reply: %s", e)

        if self._note_taker:
            self._note_taker.note_event("player", content)
            self._note_taker.note_event("dm", final_reply)

            # Also log dice rolls as separate events
            for report in roll_reports:
                self._note_taker.note_event(
                    "dice",
                    f"{report.declaration.character or 'Unknown'}: {report.declaration.notation} "
                    f"for {report.declaration.purpose} = {report.result.final_total} "
                    f"({report.result.outcome.value})"
                )

        return final_reply

    def _combine_roll_response(self, roll_display: str, continuation: str) -> str:
        """
        Combine the roll display with the AI's narrative continuation.

        The roll_display contains the dice roll results formatted for display.
        The continuation is the AI's narrative based on those results.
        """
        # Remove any "[ROLL:" artifacts that weren't properly replaced
        roll_display = re.sub(r"\[ROLL:[^\]]*\]", "", roll_display)

        # Clean up whitespace
        roll_display = roll_display.strip()
        continuation = continuation.strip()

        if not roll_display:
            return continuation
        if not continuation:
            return roll_display

        # If the roll_display ends with incomplete sentence or setup, just append
        return f"{roll_display}\n\n{continuation}"

    async def handle_direct_roll(
        self,
        notation: str,
        purpose: str = "manual roll",
        character: str = "",
    ) -> str:
        """
        Handle a direct dice roll request (e.g., from /roll command).

        This bypasses the AI and just performs the roll, returning formatted results.

        Args:
            notation: Dice notation string (e.g., "2d6+3", "1d20+5 DC:14")
            purpose: Description of what the roll is for
            character: Character name making the roll

        Returns:
            Formatted roll result string for display
        """
        from dungeonmaster.core.dice_handler import DiceRollDeclaration

        declaration = DiceRollDeclaration(
            notation=notation,
            purpose=purpose,
            character=character,
        )

        report = self._dice_handler.execute_roll(declaration)

        if report is None:
            return f"❌ Could not parse dice notation: `{notation}`"

        return report.display_text
