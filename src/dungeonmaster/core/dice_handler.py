"""
Dice roll handler for AI-triggered dice rolls.

This module provides the workflow for AI-requested dice rolls:
1. AI declares a roll with notation (e.g., "1d20+5 DC:14")
2. DiceHandler executes the roll via DiceRoller (RNG)
3. Results are formatted and returned to the AI for narrative use

The key principle: The AI NEVER generates random numbers. It requests rolls,
and this handler performs them using actual RNG, then reports results back.
"""

import logging
import re
from dataclasses import dataclass

from dungeonmaster.core.dice import DiceRoller, DiceRollResult, RollOutcome


logger = logging.getLogger(__name__)


@dataclass
class DiceRollDeclaration:
    """A dice roll declaration from the AI."""

    notation: str  # Dice notation (e.g., "1d20+5 DC:14")
    purpose: str  # What the roll is for (e.g., "attack roll against goblin")
    character: str = ""  # Character making the roll (if applicable)


@dataclass
class DiceRollReport:
    """Complete report of a dice roll for display and AI consumption."""

    declaration: DiceRollDeclaration
    result: DiceRollResult
    display_text: str  # Formatted for user display
    ai_context: str  # Formatted for AI to interpret


class DiceHandler:
    """
    Handles the complete dice roll workflow.

    This class bridges between AI roll requests and the actual RNG-based
    dice roller, providing formatted output for both display and AI context.
    """

    # Pattern to detect AI dice roll requests in text
    # Matches: [ROLL: 1d20+5 DC:14 for attack against goblin]
    ROLL_REQUEST_PATTERN = re.compile(
        r"\[ROLL:\s*([^\]]+?)\s+for\s+([^\]]+)\]",
        re.IGNORECASE,
    )

    # Alternative simpler pattern: [ROLL: 1d20+5]
    ROLL_REQUEST_SIMPLE = re.compile(
        r"\[ROLL:\s*([^\]]+?)\]",
        re.IGNORECASE,
    )

    def __init__(self, dice_roller: DiceRoller | None = None):
        """
        Initialize the dice handler.

        Args:
            dice_roller: Optional DiceRoller instance. Creates new one if not provided.
        """
        self._roller = dice_roller or DiceRoller()

    def execute_roll(self, declaration: DiceRollDeclaration) -> DiceRollReport | None:
        """
        Execute a declared dice roll and return the complete report.

        Returns None if the dice notation cannot be parsed.
        """
        result = self._roller.roll_notation(declaration.notation, declaration.purpose)
        if result is None:
            logger.warning("Could not parse dice notation: %s", declaration.notation)
            return None

        display_text = self._format_display(declaration, result)
        ai_context = self._format_ai_context(declaration, result)

        return DiceRollReport(
            declaration=declaration,
            result=result,
            display_text=display_text,
            ai_context=ai_context,
        )

    def _format_display(
        self, declaration: DiceRollDeclaration, result: DiceRollResult
    ) -> str:
        """Format the roll result for user display (Discord, etc.)."""
        lines = []

        # Header with purpose
        if declaration.character:
            lines.append(f"**{declaration.character}** rolls for *{declaration.purpose}*")
        else:
            lines.append(f"Rolling for *{declaration.purpose}*")

        # Dice notation
        lines.append(f"🎲 `{declaration.notation}`")

        # Individual dice results
        lines.append(f"Dice: {result.format_rolls()}")

        # Total calculation
        if result.constant_modifier != 0 or result.multiplier != 1 or result.divisor != 1:
            sign = "+" if result.constant_modifier > 0 else ""
            calc_str = f"{result.raw_total} {sign}{result.constant_modifier}"
            if result.multiplier != 1:
                calc_str = f"({calc_str}) × {result.multiplier:g}"
            elif result.divisor != 1:
                calc_str = f"({calc_str}) ÷ {result.divisor:g}"
            lines.append(f"**Total:** {calc_str} = **{result.final_total}**")
        else:
            lines.append(f"**Total:** {result.final_total}")

        # DC and outcome
        if result.target_dc is not None:
            lines.append(f"Target DC: {result.target_dc}")

        # Outcome display
        outcome_icons = {
            RollOutcome.SUCCESS: "✅ **SUCCESS**",
            RollOutcome.FAILURE: "❌ **FAILURE**",
            RollOutcome.CRITICAL_SUCCESS: "💥 **CRITICAL SUCCESS!**",
            RollOutcome.CRITICAL_FAILURE: "💀 **CRITICAL FAILURE!**",
        }
        if result.outcome in outcome_icons:
            outcome_line = outcome_icons[result.outcome]
            if result.outcome_reason:
                outcome_line += f" ({result.outcome_reason})"
            lines.append(outcome_line)

        return "\n".join(lines)

    def _format_ai_context(
        self, declaration: DiceRollDeclaration, result: DiceRollResult
    ) -> str:
        """Format the roll result for AI to use in narrative."""
        lines = [
            "[DICE ROLL RESULT]",
            f"Roll requested: {declaration.notation}",
            f"Purpose: {declaration.purpose}",
        ]
        if declaration.character:
            lines.append(f"Character: {declaration.character}")

        lines.extend(
            [
                f"Individual dice: {result.format_rolls()}",
                f"Raw dice total: {result.raw_total}",
                f"Modifier: {'+' if result.constant_modifier >= 0 else ''}{result.constant_modifier}",
                f"Final total: {result.final_total}",
            ]
        )

        if result.target_dc is not None:
            lines.append(f"Target DC: {result.target_dc}")

        outcome_text = result.outcome.value.replace("_", " ").upper()
        lines.append(f"Outcome: {outcome_text}")

        if result.outcome_reason:
            lines.append(f"Special: {result.outcome_reason}")

        lines.append("[END DICE ROLL RESULT]")

        return "\n".join(lines)

    def parse_roll_requests(self, text: str) -> list[DiceRollDeclaration]:
        """
        Parse any dice roll requests from AI-generated text.

        Looks for patterns like:
        - [ROLL: 1d20+5 DC:14 for attack against goblin]
        - [ROLL: 2d6+3 for damage]
        - [ROLL: 1d20+2]

        Returns a list of parsed roll declarations.
        """
        declarations = []

        # Try detailed pattern first
        for match in self.ROLL_REQUEST_PATTERN.finditer(text):
            notation = match.group(1).strip()
            purpose = match.group(2).strip()
            declarations.append(
                DiceRollDeclaration(notation=notation, purpose=purpose)
            )

        # Try simple pattern for any remaining
        for match in self.ROLL_REQUEST_SIMPLE.finditer(text):
            notation = match.group(1).strip()
            # Check if this notation was already captured by detailed pattern
            if not any(d.notation == notation for d in declarations):
                # Check for "for" in the notation which means detailed pattern should have caught it
                if " for " not in notation.lower():
                    declarations.append(
                        DiceRollDeclaration(notation=notation, purpose="dice roll")
                    )

        return declarations

    def process_ai_response(
        self, ai_text: str, character: str = ""
    ) -> tuple[str, list[DiceRollReport]]:
        """
        Process an AI response, executing any dice roll requests.

        This is the main entry point for handling AI-triggered rolls.

        Args:
            ai_text: The AI's response text that may contain roll requests
            character: The character name to associate with rolls

        Returns:
            A tuple of:
            - Modified text with roll requests replaced by results
            - List of roll reports for logging/display
        """
        declarations = self.parse_roll_requests(ai_text)

        if not declarations:
            return ai_text, []

        reports = []
        modified_text = ai_text

        for declaration in declarations:
            declaration.character = character
            report = self.execute_roll(declaration)

            if report:
                reports.append(report)

                # Replace the roll request with the result
                if declaration.purpose != "dice roll":
                    pattern = rf"\[ROLL:\s*{re.escape(declaration.notation)}\s+for\s+{re.escape(declaration.purpose)}\]"
                else:
                    pattern = rf"\[ROLL:\s*{re.escape(declaration.notation)}\s*\]"

                replacement = f"\n{report.display_text}\n"
                modified_text = re.sub(pattern, replacement, modified_text, flags=re.IGNORECASE)

        return modified_text, reports

    def get_ai_roll_results_context(self, reports: list[DiceRollReport]) -> str:
        """
        Format all roll results as context for the AI's next response.

        This context string should be appended to the system prompt or
        included in the conversation when the AI needs to incorporate
        roll results into its narrative.
        """
        if not reports:
            return ""

        lines = ["The following dice rolls were executed:"]
        for report in reports:
            lines.append("")
            lines.append(report.ai_context)

        lines.append("")
        lines.append(
            "Use these results to continue the narrative. "
            "The outcomes are final and must be respected."
        )

        return "\n".join(lines)


# Singleton instance for convenience
_default_handler: DiceHandler | None = None


def get_dice_handler() -> DiceHandler:
    """Get the default DiceHandler instance."""
    global _default_handler
    if _default_handler is None:
        _default_handler = DiceHandler()
    return _default_handler
