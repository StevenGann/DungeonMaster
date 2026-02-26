"""
Tests for the dice rolling system.

Tests cover:
- Basic dice notation parsing
- Modifiers (+/-)
- Keep highest/lowest (advantage/disadvantage)
- Drop highest/lowest
- Exploding dice
- Reroll mechanics
- Compounding and penetrating dice
- Fudge/Fate dice
- Success counting
- Multiple dice pools
- DC/target checks
- Critical success/failure detection
"""

import random

import pytest

from dungeonmaster.core.dice import (
    DiceRoller,
    DiceRollResult,
    DicePoolResult,
    DieResult,
    DicePoolSpec,
    RollOutcome,
)
from dungeonmaster.core.dice_handler import (
    DiceHandler,
    DiceRollDeclaration,
    DiceRollReport,
    get_dice_handler,
)


class TestDiceRoller:
    """Tests for the DiceRoller class."""

    def test_basic_roll_1d6(self):
        """Test basic 1d6 roll produces valid result."""
        roller = DiceRoller()
        result = roller.roll_notation("1d6")

        assert result is not None
        assert len(result.pools) == 1
        assert result.pools[0].dice_count == 1
        assert result.pools[0].dice_sides == 6
        assert 1 <= result.final_total <= 6

    def test_basic_roll_2d6(self):
        """Test 2d6 roll produces valid result."""
        roller = DiceRoller()
        result = roller.roll_notation("2d6")

        assert result is not None
        assert len(result.pools) == 1
        assert result.pools[0].dice_count == 2
        assert len(result.pools[0].dice_results) == 2
        assert 2 <= result.final_total <= 12

    def test_basic_roll_d20(self):
        """Test d20 (implicit 1d20) roll."""
        roller = DiceRoller()
        result = roller.roll_notation("d20")

        assert result is not None
        assert result.pools[0].dice_count == 1
        assert result.pools[0].dice_sides == 20
        assert 1 <= result.final_total <= 20

    def test_percentile_dice(self):
        """Test d% (percentile) roll."""
        roller = DiceRoller()
        result = roller.roll_notation("d%")

        assert result is not None
        assert result.pools[0].dice_sides == 100
        assert 1 <= result.final_total <= 100

    def test_positive_modifier(self):
        """Test dice with positive modifier."""
        # Use seeded random for deterministic test
        rng = random.Random(42)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("1d6+5")

        assert result is not None
        assert result.constant_modifier == 5
        assert result.final_total == result.raw_total + 5

    def test_negative_modifier(self):
        """Test dice with negative modifier."""
        rng = random.Random(42)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("1d6-2")

        assert result is not None
        assert result.constant_modifier == -2
        assert result.final_total == result.raw_total - 2

    def test_multiple_dice_pools(self):
        """Test multiple dice pools like 2d6+1d4+3."""
        rng = random.Random(42)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("2d6+1d4+3")

        assert result is not None
        assert len(result.pools) == 2
        assert result.pools[0].dice_count == 2
        assert result.pools[0].dice_sides == 6
        assert result.pools[1].dice_count == 1
        assert result.pools[1].dice_sides == 4
        assert result.constant_modifier == 3

    def test_keep_highest(self):
        """Test keeping highest dice (4d6kh3 for ability scores)."""
        # Seed to get predictable results
        rng = random.Random(123)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("4d6kh3")

        assert result is not None
        pool = result.pools[0]
        assert pool.dice_count == 4
        assert len(pool.dice_results) == 4
        assert len(pool.kept_results) == 3

        # Verify that dropped die has lowest value
        dropped = [d for d in pool.dice_results if not d.kept]
        kept = [d for d in pool.dice_results if d.kept]
        assert len(dropped) == 1
        assert all(dropped[0].value <= k.value for k in kept)

    def test_keep_lowest_disadvantage(self):
        """Test keeping lowest die (2d20kl1 for disadvantage)."""
        rng = random.Random(456)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("2d20kl1")

        assert result is not None
        pool = result.pools[0]
        assert pool.dice_count == 2
        assert len(pool.kept_results) == 1

        # The kept die should be the minimum
        all_values = [d.value for d in pool.dice_results]
        kept_value = pool.kept_results[0].value
        assert kept_value == min(all_values)

    def test_drop_lowest(self):
        """Test dropping lowest die (4d6dl1)."""
        rng = random.Random(789)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("4d6dl1")

        assert result is not None
        pool = result.pools[0]
        assert len(pool.kept_results) == 3
        dropped = [d for d in pool.dice_results if not d.kept]
        assert len(dropped) == 1

    def test_drop_highest(self):
        """Test dropping highest die (4d6dh1)."""
        rng = random.Random(101)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("4d6dh1")

        assert result is not None
        pool = result.pools[0]
        assert len(pool.kept_results) == 3
        dropped = [d for d in pool.dice_results if not d.kept]
        assert len(dropped) == 1

        # Verify that dropped die has highest value
        kept = [d for d in pool.dice_results if d.kept]
        assert all(dropped[0].value >= k.value for k in kept)

    def test_exploding_dice(self):
        """Test exploding dice (reroll on max)."""
        # Create a rigged random that always returns max
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                # First few calls return max, then stop
                if self.call_count <= 3:
                    return b
                return 1

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6!")

        assert result is not None
        pool = result.pools[0]
        die = pool.dice_results[0]
        assert die.exploded
        assert len(die.explosion_values) >= 2  # At least 2 explosions

    def test_reroll_ones(self):
        """Test rerolling 1s (1d6r1)."""
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                if self.call_count == 1:
                    return 1  # First roll is 1
                return 4  # Reroll is 4

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6r1")

        assert result is not None
        die = result.pools[0].dice_results[0]
        assert die.rerolled
        assert die.original == 1
        assert die.value == 4

    def test_dc_success(self):
        """Test DC check that succeeds."""
        class RiggedRandom:
            def randint(self, a, b):
                return 15

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+5 DC:14")

        assert result is not None
        assert result.target_dc == 14
        assert result.final_total == 20  # 15 + 5
        assert result.outcome == RollOutcome.SUCCESS

    def test_dc_failure(self):
        """Test DC check that fails."""
        class RiggedRandom:
            def randint(self, a, b):
                return 5

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+2 DC:15")

        assert result is not None
        assert result.target_dc == 15
        assert result.final_total == 7  # 5 + 2
        assert result.outcome == RollOutcome.FAILURE

    def test_critical_success_natural_20(self):
        """Test natural 20 is critical success."""
        class RiggedRandom:
            def randint(self, a, b):
                return 20

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+5 DC:25")

        assert result is not None
        assert result.outcome == RollOutcome.CRITICAL_SUCCESS
        assert "Natural 20" in result.outcome_reason

    def test_critical_failure_natural_1(self):
        """Test natural 1 is critical failure."""
        class RiggedRandom:
            def randint(self, a, b):
                return 1

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+10 DC:5")

        assert result is not None
        assert result.outcome == RollOutcome.CRITICAL_FAILURE
        assert "Natural 1" in result.outcome_reason

    def test_fudge_dice(self):
        """Test Fudge/Fate dice (dF)."""
        roller = DiceRoller()
        result = roller.roll_notation("4dF")

        assert result is not None
        pool = result.pools[0]
        assert pool.dice_sides == "F"
        assert pool.dice_count == 4
        # Fudge dice result should be between -4 and +4
        assert -4 <= result.final_total <= 4

    def test_success_counting(self):
        """Test success counting mode (8d6>=5)."""
        rng = random.Random(42)
        roller = DiceRoller(random_source=rng)
        result = roller.roll_notation("8d6>=5")

        assert result is not None
        pool = result.pools[0]
        assert pool.success_count is not None

        # Verify the count matches dice showing 5 or 6
        expected_successes = sum(
            1 for d in pool.kept_results if d.value >= 5
        )
        assert pool.success_count == expected_successes

    def test_multiply_result(self):
        """Test multiplication modifier (2d6*2)."""
        class RiggedRandom:
            def randint(self, a, b):
                return 3

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("2d6*2")

        assert result is not None
        assert result.multiplier == 2.0
        assert result.raw_total == 6  # 3 + 3
        assert result.final_total == 12  # 6 * 2

    def test_divide_result(self):
        """Test division modifier (2d6/2)."""
        class RiggedRandom:
            def randint(self, a, b):
                return 4

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("2d6/2")

        assert result is not None
        assert result.divisor == 2.0
        assert result.raw_total == 8  # 4 + 4
        assert result.final_total == 4  # 8 / 2

    def test_minimum_value(self):
        """Test minimum value constraint (2d6mi3)."""
        class RiggedRandom:
            def randint(self, a, b):
                return 1

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("2d6mi3")

        assert result is not None
        # Even though we rolled 1s, minimum is 3
        for die in result.pools[0].dice_results:
            assert die.value >= 3

    def test_maximum_value(self):
        """Test maximum value constraint (2d6ma4)."""
        class RiggedRandom:
            def randint(self, a, b):
                return 6

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("2d6ma4")

        assert result is not None
        # Even though we rolled 6s, maximum is 4
        for die in result.pools[0].dice_results:
            assert die.value <= 4

    def test_invalid_notation_returns_none(self):
        """Test that invalid notation returns None."""
        roller = DiceRoller()

        assert roller.roll_notation("not a dice roll") is None
        assert roller.roll_notation("") is None
        assert roller.roll_notation("abc") is None

    def test_format_rolls_basic(self):
        """Test roll formatting for display."""
        class RiggedRandom:
            def randint(self, a, b):
                return 4

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("2d6")

        formatted = result.format_rolls()
        assert "[4]" in formatted

    def test_format_result_complete(self):
        """Test complete result formatting."""
        class RiggedRandom:
            def randint(self, a, b):
                return 15

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+5 DC:14")

        formatted = result.format_result()
        assert "1d20+5 DC:14" in formatted
        assert "SUCCESS" in formatted


class TestDiceHandler:
    """Tests for the DiceHandler class."""

    def test_parse_roll_request_with_purpose(self):
        """Test parsing roll requests from AI text."""
        handler = DiceHandler()
        text = "Let me make an attack. [ROLL: 1d20+5 DC:14 for attack roll against the goblin]"

        declarations = handler.parse_roll_requests(text)

        assert len(declarations) == 1
        assert declarations[0].notation == "1d20+5 DC:14"
        assert declarations[0].purpose == "attack roll against the goblin"

    def test_parse_roll_request_simple(self):
        """Test parsing simple roll requests without purpose."""
        handler = DiceHandler()
        text = "Rolling damage [ROLL: 2d6+3]"

        declarations = handler.parse_roll_requests(text)

        assert len(declarations) == 1
        assert declarations[0].notation == "2d6+3"

    def test_parse_multiple_roll_requests(self):
        """Test parsing multiple roll requests."""
        handler = DiceHandler()
        text = """
        First attack: [ROLL: 1d20+5 DC:14 for first attack]
        Second attack: [ROLL: 1d20+5 DC:14 for second attack]
        """

        declarations = handler.parse_roll_requests(text)

        assert len(declarations) == 2

    def test_execute_roll_success(self):
        """Test executing a roll declaration."""
        handler = DiceHandler()
        declaration = DiceRollDeclaration(
            notation="1d20+5",
            purpose="attack roll",
            character="Grimjaw",
        )

        report = handler.execute_roll(declaration)

        assert report is not None
        assert report.declaration == declaration
        assert report.result is not None
        assert "Grimjaw" in report.display_text
        assert "attack roll" in report.display_text

    def test_execute_roll_invalid_notation(self):
        """Test executing a roll with invalid notation."""
        handler = DiceHandler()
        declaration = DiceRollDeclaration(
            notation="invalid",
            purpose="test",
        )

        report = handler.execute_roll(declaration)

        assert report is None

    def test_process_ai_response_with_rolls(self):
        """Test processing AI response that contains roll requests."""
        handler = DiceHandler()
        ai_text = "The goblin attacks! [ROLL: 1d20+3 DC:15 for goblin attack]"

        modified_text, reports = handler.process_ai_response(ai_text, character="Goblin")

        assert len(reports) == 1
        assert "[ROLL:" not in modified_text  # Roll request should be replaced
        assert "🎲" in modified_text  # Should have dice emoji

    def test_process_ai_response_no_rolls(self):
        """Test processing AI response with no roll requests."""
        handler = DiceHandler()
        ai_text = "The tavern is quiet tonight."

        modified_text, reports = handler.process_ai_response(ai_text)

        assert len(reports) == 0
        assert modified_text == ai_text

    def test_get_ai_roll_results_context(self):
        """Test formatting roll results for AI context."""
        handler = DiceHandler()
        declaration = DiceRollDeclaration(
            notation="1d20+5 DC:14",
            purpose="attack roll",
            character="Grimjaw",
        )

        report = handler.execute_roll(declaration)
        context = handler.get_ai_roll_results_context([report])

        assert "dice rolls were executed" in context
        assert "attack roll" in context
        assert "DICE ROLL RESULT" in context

    def test_singleton_handler(self):
        """Test get_dice_handler returns singleton."""
        handler1 = get_dice_handler()
        handler2 = get_dice_handler()

        assert handler1 is handler2


class TestDiceNotationEdgeCases:
    """Tests for edge cases and exotic notation."""

    def test_advantage_2d20kh1(self):
        """Test advantage roll."""
        roller = DiceRoller()
        result = roller.roll_notation("2d20kh1+5")

        assert result is not None
        pool = result.pools[0]
        assert pool.dice_count == 2
        assert len(pool.kept_results) == 1

        # Kept die should be the higher one
        all_values = [d.value for d in pool.dice_results]
        assert pool.kept_results[0].value == max(all_values)

    def test_disadvantage_2d20kl1(self):
        """Test disadvantage roll."""
        roller = DiceRoller()
        result = roller.roll_notation("2d20kl1+5")

        assert result is not None
        pool = result.pools[0]
        assert len(pool.kept_results) == 1

        all_values = [d.value for d in pool.dice_results]
        assert pool.kept_results[0].value == min(all_values)

    def test_ability_score_generation(self):
        """Test standard ability score generation (4d6 drop lowest)."""
        roller = DiceRoller()
        result = roller.roll_notation("4d6kh3")

        assert result is not None
        # Result should be between 3 (all 1s kept) and 18 (all 6s kept)
        assert 3 <= result.final_total <= 18

    def test_complex_expression(self):
        """Test complex expression with multiple pools and modifiers."""
        roller = DiceRoller()
        result = roller.roll_notation("1d8+2d6+5")

        assert result is not None
        assert len(result.pools) == 2
        assert result.constant_modifier == 5

    def test_cr_notation(self):
        """Test CR: notation (alternative to DC:)."""
        roller = DiceRoller()
        result = roller.roll_notation("1d20+5 CR:15")

        assert result is not None
        assert result.target_dc == 15

    def test_ac_notation(self):
        """Test AC: notation."""
        roller = DiceRoller()
        result = roller.roll_notation("1d20+5 AC:16")

        assert result is not None
        assert result.target_dc == 16

    def test_explode_with_threshold(self):
        """Test exploding dice with custom threshold."""
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                if self.call_count == 1:
                    return 5  # Should explode on >4
                return 2  # Stop exploding

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6!>4")

        assert result is not None
        die = result.pools[0].dice_results[0]
        assert die.exploded

    def test_compound_dice(self):
        """Test compounding dice (!!)."""
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                if self.call_count <= 2:
                    return b  # Max value
                return 1

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6!!")

        assert result is not None
        die = result.pools[0].dice_results[0]
        # Compounding adds to the same die value
        assert die.value > 6  # Should be more than one die's worth

    def test_penetrating_dice(self):
        """Test penetrating dice (!p)."""
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                if self.call_count == 1:
                    return 6  # Explode
                return 6  # Would be 5 with penetration

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6!p")

        assert result is not None
        die = result.pools[0].dice_results[0]
        assert die.exploded
        # Penetrating should subtract 1 from explosion rolls
        if die.explosion_values:
            assert die.explosion_values[0] == 5  # 6 - 1

    def test_reroll_recursive(self):
        """Test recursive reroll (rr)."""
        class RiggedRandom:
            def __init__(self):
                self.call_count = 0

            def randint(self, a, b):
                self.call_count += 1
                if self.call_count <= 3:
                    return 1  # Keep rerolling
                return 4

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d6rr1")

        assert result is not None
        die = result.pools[0].dice_results[0]
        assert die.rerolled
        assert die.value == 4  # Final value after recursive rerolls


class TestRollOutcomeFormatting:
    """Tests for roll outcome and formatting."""

    def test_format_dropped_dice(self):
        """Test that dropped dice are formatted with strikethrough."""
        class RiggedRandom:
            def __init__(self):
                self.values = [1, 5, 6, 4]
                self.index = 0

            def randint(self, a, b):
                v = self.values[self.index]
                self.index += 1
                return v

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("4d6kh3")

        formatted = result.format_rolls()
        assert "~~" in formatted  # Should have strikethrough markers

    def test_to_ai_context(self):
        """Test AI context formatting."""
        class RiggedRandom:
            def randint(self, a, b):
                return 15

            def choice(self, seq):
                return seq[0]

        roller = DiceRoller(random_source=RiggedRandom())
        result = roller.roll_notation("1d20+5 DC:14")

        context = result.to_ai_context()
        assert "Individual dice" in context
        assert "Final total" in context
        assert "SUCCESS" in context


class TestRollSimpleMethod:
    """Tests for the roll_simple convenience method."""

    def test_roll_simple_basic(self):
        """Test roll_simple with basic parameters."""
        roller = DiceRoller()
        result = roller.roll_simple(dice_count=2, dice_sides=6, modifier=3)

        assert result is not None
        assert result.pools[0].dice_count == 2
        assert result.pools[0].dice_sides == 6
        assert result.constant_modifier == 3

    def test_roll_simple_with_dc(self):
        """Test roll_simple with DC."""
        roller = DiceRoller()
        result = roller.roll_simple(
            dice_count=1, dice_sides=20, modifier=5, target_dc=15
        )

        assert result is not None
        assert result.target_dc == 15
        assert result.outcome in [
            RollOutcome.SUCCESS,
            RollOutcome.FAILURE,
            RollOutcome.CRITICAL_SUCCESS,
            RollOutcome.CRITICAL_FAILURE,
        ]
