"""
Dice rolling module for DungeonMaster.

Provides RNG-based dice rolling with comprehensive support for standard dice notation:

Basic:
- NdX: Roll N dice with X sides (e.g., 2d6, 1d20, d8)
- d%: Percentile die (1d100)
- dF: Fudge/Fate dice (-1, 0, +1)

Modifiers:
- +/- constants: 1d20+5, 2d6-2
- Multiple terms: 2d6+1d4+3

Keep/Drop:
- kh/kl: Keep highest/lowest (4d6kh3, 2d20kl1)
- dh/dl: Drop highest/lowest (4d6dl1)

Exploding/Reroll:
- !: Exploding dice (1d6!, 1d6!>5)
- !!: Compounding dice
- !p: Penetrating dice
- r: Reroll (1d6r1, 1d6r<2)
- ro/rr: Reroll once/recursively

Target/Success:
- >=, >, etc.: Count successes (8d6>=5)
- DC:/CR:/AC:: Success threshold for total

Advanced:
- */÷: Multiplication/division (2d6*2)
- mi/ma: Minimum/maximum per die (2d6mi2)
- (): Grouping ((2d6+3)*2)

The AI does NOT roll dice - it requests rolls through this module, which uses
actual RNG to produce results. This ensures fair, verifiable dice rolls.
"""

import random
import re
from dataclasses import dataclass, field
from enum import Enum


class RollOutcome(Enum):
    """Outcome categories for dice rolls."""

    NORMAL = "normal"
    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL_SUCCESS = "critical_success"  # Natural 20 on d20
    CRITICAL_FAILURE = "critical_failure"  # Natural 1 on d20


@dataclass
class DieResult:
    """Result of rolling a single die."""

    value: int  # Final value used
    original: int  # Original rolled value (before rerolls)
    kept: bool = True  # Whether this die was kept (not dropped)
    exploded: bool = False  # Whether this die exploded
    rerolled: bool = False  # Whether this die was rerolled
    explosion_values: list[int] = field(default_factory=list)  # Chain of explosions

    @property
    def total(self) -> int:
        """Total value including explosions."""
        return self.value + sum(self.explosion_values)


@dataclass
class DicePoolResult:
    """Result of rolling a single dice pool (e.g., 4d6kh3)."""

    expression: str  # The expression (e.g., "4d6kh3")
    dice_count: int
    dice_sides: int | str  # int for normal, "F" for fudge
    dice_results: list[DieResult]
    kept_results: list[DieResult]  # Dice that weren't dropped
    raw_total: int  # Sum before modifiers
    success_count: int | None = None  # For target-based rolls

    def format_rolls(self) -> str:
        """Format individual die results as [4][1][~~6~~] style (strikethrough for dropped)."""
        parts = []
        for die in self.dice_results:
            if die.exploded and die.explosion_values:
                # Show explosion chain
                chain = [str(die.value)] + [str(v) for v in die.explosion_values]
                val_str = "!".join(chain)
            else:
                val_str = str(die.value)

            if die.rerolled:
                val_str = f"~~{die.original}~~→{val_str}"

            if not die.kept:
                parts.append(f"[~~{val_str}~~]")
            else:
                parts.append(f"[{val_str}]")
        return "".join(parts)


@dataclass
class DiceRollResult:
    """Result of a complete dice roll expression."""

    notation: str  # Original notation (e.g., "2d6+1d4+3 DC:15")
    pools: list[DicePoolResult]  # Individual dice pools
    constant_modifier: int  # Sum of all +/- constants
    multiplier: float  # Multiplication factor (default 1)
    divisor: float  # Division factor (default 1)
    raw_total: int  # Sum of all pools before constants
    final_total: int  # Final result after all math
    target_dc: int | None = None
    outcome: RollOutcome = RollOutcome.NORMAL
    outcome_reason: str = ""

    def format_rolls(self) -> str:
        """Format all pools' individual die results."""
        return " + ".join(pool.format_rolls() for pool in self.pools)

    def format_result(self) -> str:
        """Format the complete roll result for display."""
        parts = [f"🎲 **{self.notation}**"]
        parts.append(f"Rolls: {self.format_rolls()}")

        # Build calculation string
        calc_parts = []
        for pool in self.pools:
            calc_parts.append(str(pool.raw_total))

        if self.constant_modifier != 0:
            sign = "+" if self.constant_modifier > 0 else ""
            calc_parts.append(f"{sign}{self.constant_modifier}")

        if self.multiplier != 1:
            calc_str = f"({' + '.join(calc_parts)}) × {self.multiplier:g}"
        elif self.divisor != 1:
            calc_str = f"({' + '.join(calc_parts)}) ÷ {self.divisor:g}"
        else:
            calc_str = " + ".join(calc_parts) if len(calc_parts) > 1 else calc_parts[0]

        if len(self.pools) > 1 or self.constant_modifier != 0 or self.multiplier != 1 or self.divisor != 1:
            parts.append(f"Total: {calc_str} = **{self.final_total}**")
        else:
            parts.append(f"Total: **{self.final_total}**")

        if self.target_dc is not None:
            parts.append(f"DC: {self.target_dc}")

        if self.outcome != RollOutcome.NORMAL:
            outcome_display = {
                RollOutcome.SUCCESS: "✅ **SUCCESS**",
                RollOutcome.FAILURE: "❌ **FAILURE**",
                RollOutcome.CRITICAL_SUCCESS: "💥 **CRITICAL SUCCESS!**",
                RollOutcome.CRITICAL_FAILURE: "💀 **CRITICAL FAILURE!**",
            }
            parts.append(outcome_display.get(self.outcome, ""))
            if self.outcome_reason:
                parts.append(f"({self.outcome_reason})")

        return "\n".join(parts)

    def to_ai_context(self) -> str:
        """Format result for AI to interpret and use in narrative."""
        lines = [
            f"Dice Roll Result for {self.notation}:",
            f"  Individual dice: {self.format_rolls()}",
        ]
        for pool in self.pools:
            lines.append(f"  Pool {pool.expression}: {pool.raw_total}")
        lines.extend([
            f"  Raw total (dice only): {self.raw_total}",
            f"  Modifier: {'+' if self.constant_modifier >= 0 else ''}{self.constant_modifier}",
            f"  Final total: {self.final_total}",
        ])
        if self.target_dc is not None:
            lines.append(f"  Target DC: {self.target_dc}")
            lines.append(f"  Outcome: {self.outcome.value.replace('_', ' ').upper()}")
            if self.outcome_reason:
                lines.append(f"  Note: {self.outcome_reason}")
        return "\n".join(lines)


@dataclass
class DicePoolSpec:
    """Specification for a single dice pool."""

    count: int = 1
    sides: int | str = 6  # int for normal dice, "F" for fudge
    keep_highest: int | None = None
    keep_lowest: int | None = None
    drop_highest: int | None = None
    drop_lowest: int | None = None
    explode: bool = False
    explode_threshold: int | None = None  # None = max value
    explode_compare: str = ">="  # >=, >, =, etc.
    compound: bool = False  # !! instead of !
    penetrate: bool = False  # !p - subtract 1 from explosions
    reroll_value: int | None = None
    reroll_compare: str = "="
    reroll_once: bool = True  # ro vs rr
    min_value: int | None = None  # mi modifier
    max_value: int | None = None  # ma modifier
    target_compare: str | None = None  # For success counting
    target_value: int | None = None
    original_expr: str = ""


class DiceRoller:
    """
    RNG-based dice roller with comprehensive notation support.

    This class handles actual random dice rolls. The AI should NEVER generate
    random numbers itself - it should request rolls through this class.
    """

    # Maximum explosions to prevent infinite loops
    MAX_EXPLOSIONS = 100

    # Regex patterns for parsing
    # Main dice pattern: 4d6kh3dl1!>5r<2mi2
    DICE_POOL_PATTERN = re.compile(
        r"(\d*)d(\d+|F|%)"  # Count and sides
        r"((?:k[hl]?\d+|d[hl]\d+|!{1,2}p?(?:[<>=!]+\d+)?|r[or]?(?:[<>=!]+)?\d+|mi\d+|ma\d+)*)"  # Modifiers
        r"(?:\s*([<>=!]+)\s*(\d+))?"  # Optional target for success counting
        , re.IGNORECASE
    )

    # Pattern for the full expression with +/- terms, multipliers, DC
    EXPRESSION_PATTERN = re.compile(
        r"^(.+?)"  # Dice expression(s)
        r"(?:\s*([*/])\s*(\d+(?:\.\d+)?))?"  # Optional multiply/divide
        r"(?:\s+(?:DC|CR|AC)[:\s]*(\d+))?"  # Optional DC/CR/AC
        r"$", re.IGNORECASE
    )

    def __init__(self, random_source: random.Random | None = None):
        """
        Initialize the dice roller.

        Args:
            random_source: Optional custom Random instance for testing.
                          Uses system random by default.
        """
        self._random = random_source or random.Random()

    def _roll_die(self, sides: int) -> int:
        """Roll a single die with the given number of sides."""
        return self._random.randint(1, sides)

    def _roll_fudge(self) -> int:
        """Roll a single Fudge/Fate die (-1, 0, +1)."""
        return self._random.choice([-1, 0, 1])

    def _check_compare(self, value: int, compare: str, threshold: int) -> bool:
        """Check if a value meets a comparison threshold."""
        if compare == "=" or compare == "==":
            return value == threshold
        elif compare == "!=":
            return value != threshold
        elif compare == ">":
            return value > threshold
        elif compare == ">=":
            return value >= threshold
        elif compare == "<":
            return value < threshold
        elif compare == "<=":
            return value <= threshold
        return False

    def _parse_compare(self, text: str) -> tuple[str, int]:
        """Parse a comparison string like '>=5' or '<3' into (operator, value)."""
        match = re.match(r"([<>=!]+)(\d+)", text)
        if match:
            return match.group(1), int(match.group(2))
        # Just a number means equals
        match = re.match(r"(\d+)", text)
        if match:
            return "=", int(match.group(1))
        return "=", 0

    def _parse_pool_modifiers(self, mod_str: str, sides: int) -> dict:
        """Parse modifier string like 'kh3dl1!>5r<2mi2' into a dict of settings."""
        mods = {
            "keep_highest": None,
            "keep_lowest": None,
            "drop_highest": None,
            "drop_lowest": None,
            "explode": False,
            "explode_threshold": sides,  # Default: max value
            "explode_compare": ">=",
            "compound": False,
            "penetrate": False,
            "reroll_value": None,
            "reroll_compare": "=",
            "reroll_once": True,
            "min_value": None,
            "max_value": None,
        }

        if not mod_str:
            return mods

        # Keep highest/lowest: kh3, kl2, k3 (defaults to kh)
        keep_match = re.search(r"k([hl])?(\d+)", mod_str, re.IGNORECASE)
        if keep_match:
            direction = (keep_match.group(1) or "h").lower()
            count = int(keep_match.group(2))
            if direction == "h":
                mods["keep_highest"] = count
            else:
                mods["keep_lowest"] = count

        # Drop highest/lowest: dh1, dl2
        drop_match = re.search(r"d([hl])(\d+)", mod_str, re.IGNORECASE)
        if drop_match:
            direction = drop_match.group(1).lower()
            count = int(drop_match.group(2))
            if direction == "h":
                mods["drop_highest"] = count
            else:
                mods["drop_lowest"] = count

        # Exploding: !, !!, !p, !>5, !!>=4, !p>3
        explode_match = re.search(r"(!{1,2})(p)?(?:([<>=!]+)(\d+))?", mod_str, re.IGNORECASE)
        if explode_match and explode_match.group(0):
            bangs = explode_match.group(1)
            penetrate = explode_match.group(2)
            compare = explode_match.group(3)
            threshold = explode_match.group(4)

            mods["explode"] = True
            mods["compound"] = len(bangs) == 2
            mods["penetrate"] = penetrate is not None

            if compare and threshold:
                mods["explode_compare"] = compare
                mods["explode_threshold"] = int(threshold)

        # Reroll: r1, r<2, ro<=3, rr1
        reroll_match = re.search(r"r([or])?([<>=!]*)(\d+)", mod_str, re.IGNORECASE)
        if reroll_match:
            once_flag = reroll_match.group(1)
            compare = reroll_match.group(2) or "="
            value = int(reroll_match.group(3))

            mods["reroll_value"] = value
            mods["reroll_compare"] = compare if compare else "="
            mods["reroll_once"] = once_flag != "r"  # 'r' means recursive

        # Min/max: mi2, ma6
        min_match = re.search(r"mi(\d+)", mod_str, re.IGNORECASE)
        if min_match:
            mods["min_value"] = int(min_match.group(1))

        max_match = re.search(r"ma(\d+)", mod_str, re.IGNORECASE)
        if max_match:
            mods["max_value"] = int(max_match.group(1))

        return mods

    def _roll_pool(self, spec: DicePoolSpec) -> DicePoolResult:
        """Roll a single dice pool according to its specification."""
        dice_results: list[DieResult] = []

        # Handle Fudge dice
        if spec.sides == "F":
            for _ in range(spec.count):
                value = self._roll_fudge()
                dice_results.append(DieResult(value=value, original=value))
            kept = dice_results[:]
            return DicePoolResult(
                expression=spec.original_expr,
                dice_count=spec.count,
                dice_sides="F",
                dice_results=dice_results,
                kept_results=kept,
                raw_total=sum(d.value for d in kept),
            )

        sides = int(spec.sides)

        # Roll each die
        for _ in range(spec.count):
            original = self._roll_die(sides)
            value = original

            # Handle rerolls
            rerolled = False
            if spec.reroll_value is not None:
                reroll_count = 0
                max_rerolls = 1 if spec.reroll_once else self.MAX_EXPLOSIONS
                while reroll_count < max_rerolls and self._check_compare(
                    value, spec.reroll_compare, spec.reroll_value
                ):
                    value = self._roll_die(sides)
                    rerolled = True
                    reroll_count += 1

            # Apply min/max constraints
            if spec.min_value is not None:
                value = max(value, spec.min_value)
            if spec.max_value is not None:
                value = min(value, spec.max_value)

            # Handle explosions
            explosion_values: list[int] = []
            exploded = False
            if spec.explode:
                threshold = spec.explode_threshold if spec.explode_threshold else sides
                explosion_count = 0
                check_value = value

                while explosion_count < self.MAX_EXPLOSIONS and self._check_compare(
                    check_value, spec.explode_compare, threshold
                ):
                    exploded = True
                    new_roll = self._roll_die(sides)
                    if spec.penetrate:
                        new_roll = max(1, new_roll - 1)

                    if spec.compound:
                        # Compounding: add to the same die's value
                        value += new_roll
                        check_value = new_roll
                    else:
                        # Regular exploding: track separately
                        explosion_values.append(new_roll)
                        check_value = new_roll

                    explosion_count += 1

            dice_results.append(DieResult(
                value=value,
                original=original,
                kept=True,
                exploded=exploded,
                rerolled=rerolled,
                explosion_values=explosion_values,
            ))

        # Handle keep/drop
        kept_results = dice_results[:]

        if spec.drop_lowest:
            # Sort by total value and mark lowest N as not kept
            sorted_dice = sorted(kept_results, key=lambda d: d.total)
            for i in range(min(spec.drop_lowest, len(sorted_dice))):
                sorted_dice[i].kept = False
            kept_results = [d for d in kept_results if d.kept]

        if spec.drop_highest:
            sorted_dice = sorted(kept_results, key=lambda d: d.total, reverse=True)
            for i in range(min(spec.drop_highest, len(sorted_dice))):
                sorted_dice[i].kept = False
            kept_results = [d for d in kept_results if d.kept]

        if spec.keep_highest:
            sorted_dice = sorted(kept_results, key=lambda d: d.total, reverse=True)
            for i, die in enumerate(sorted_dice):
                if i >= spec.keep_highest:
                    die.kept = False
            kept_results = [d for d in kept_results if d.kept]

        if spec.keep_lowest:
            sorted_dice = sorted(kept_results, key=lambda d: d.total)
            for i, die in enumerate(sorted_dice):
                if i >= spec.keep_lowest:
                    die.kept = False
            kept_results = [d for d in kept_results if d.kept]

        # Calculate total
        if spec.target_compare and spec.target_value is not None:
            # Success counting mode
            success_count = sum(
                1 for d in kept_results
                if self._check_compare(d.total, spec.target_compare, spec.target_value)
            )
            return DicePoolResult(
                expression=spec.original_expr,
                dice_count=spec.count,
                dice_sides=sides,
                dice_results=dice_results,
                kept_results=kept_results,
                raw_total=success_count,
                success_count=success_count,
            )
        else:
            raw_total = sum(d.total for d in kept_results)
            return DicePoolResult(
                expression=spec.original_expr,
                dice_count=spec.count,
                dice_sides=sides,
                dice_results=dice_results,
                kept_results=kept_results,
                raw_total=raw_total,
            )

    def parse_notation(self, notation: str) -> tuple[list[DicePoolSpec], int, float, float, int | None] | None:
        """
        Parse a dice notation string into pool specifications and modifiers.

        Returns:
            Tuple of (pool_specs, constant_modifier, multiplier, divisor, target_dc)
            or None if parsing fails.
        """
        notation = notation.strip()
        if not notation:
            return None

        # Extract DC/CR/AC and multiply/divide from the end
        expr_match = self.EXPRESSION_PATTERN.match(notation)
        if not expr_match:
            return None

        dice_expr = expr_match.group(1).strip()
        mult_op = expr_match.group(2)
        mult_val = expr_match.group(3)
        target_dc = int(expr_match.group(4)) if expr_match.group(4) else None

        multiplier = 1.0
        divisor = 1.0
        if mult_op and mult_val:
            if mult_op == "*":
                multiplier = float(mult_val)
            else:
                divisor = float(mult_val)

        # Parse individual terms (split on + and -)
        # We need to be careful with negative numbers vs subtraction
        pools: list[DicePoolSpec] = []
        constant_modifier = 0

        # Tokenize the expression
        # Handle patterns like: 2d6+1d4+3-2+1d8
        terms = re.split(r"(?=[+-])", dice_expr)
        terms = [t.strip() for t in terms if t.strip()]

        for term in terms:
            # Handle sign
            sign = 1
            if term.startswith("-"):
                sign = -1
                term = term[1:].strip()
            elif term.startswith("+"):
                term = term[1:].strip()

            # Check if it's a dice pool or a constant
            pool_match = self.DICE_POOL_PATTERN.match(term)
            if pool_match and "d" in term.lower():
                count_str = pool_match.group(1)
                sides_str = pool_match.group(2)
                modifiers = pool_match.group(3) or ""
                target_cmp = pool_match.group(4)
                target_val = pool_match.group(5)

                count = int(count_str) if count_str else 1

                # Handle special die types
                if sides_str.upper() == "F":
                    sides: int | str = "F"
                elif sides_str == "%":
                    sides = 100
                else:
                    sides = int(sides_str)

                # Parse modifiers
                if isinstance(sides, int):
                    mods = self._parse_pool_modifiers(modifiers, sides)
                else:
                    mods = self._parse_pool_modifiers(modifiers, 1)  # Fudge dice

                spec = DicePoolSpec(
                    count=count,
                    sides=sides,
                    keep_highest=mods["keep_highest"],
                    keep_lowest=mods["keep_lowest"],
                    drop_highest=mods["drop_highest"],
                    drop_lowest=mods["drop_lowest"],
                    explode=mods["explode"],
                    explode_threshold=mods["explode_threshold"],
                    explode_compare=mods["explode_compare"],
                    compound=mods["compound"],
                    penetrate=mods["penetrate"],
                    reroll_value=mods["reroll_value"],
                    reroll_compare=mods["reroll_compare"],
                    reroll_once=mods["reroll_once"],
                    min_value=mods["min_value"],
                    max_value=mods["max_value"],
                    target_compare=target_cmp,
                    target_value=int(target_val) if target_val else None,
                    original_expr=term if sign == 1 else f"-{term}",
                )
                pools.append(spec)

                # Handle negative pools (subtract the result)
                if sign == -1:
                    # We'll handle this during rolling
                    spec.original_expr = f"-{term}"

            else:
                # It's a constant
                try:
                    constant_modifier += sign * int(term)
                except ValueError:
                    # Invalid term
                    return None

        if not pools and constant_modifier == 0:
            return None

        return pools, constant_modifier, multiplier, divisor, target_dc

    def roll_notation(self, notation: str, purpose: str = "") -> DiceRollResult | None:
        """
        Parse and execute a dice notation string.

        Returns None if the notation cannot be parsed.
        """
        parsed = self.parse_notation(notation)
        if parsed is None:
            return None

        pools_specs, constant_modifier, multiplier, divisor, target_dc = parsed

        # Roll each pool
        pools: list[DicePoolResult] = []
        for spec in pools_specs:
            result = self._roll_pool(spec)
            pools.append(result)

        # Calculate totals
        raw_total = sum(p.raw_total for p in pools)
        final_total = raw_total + constant_modifier

        # Apply multiplier/divisor
        if multiplier != 1:
            final_total = int(final_total * multiplier)
        if divisor != 1:
            final_total = int(final_total / divisor)

        # Determine outcome
        outcome = RollOutcome.NORMAL
        outcome_reason = ""

        # Check for critical results on d20 rolls
        is_single_d20 = (
            len(pools) == 1
            and pools[0].dice_count == 1
            and pools[0].dice_sides == 20
            and len(pools[0].kept_results) == 1
        )

        if is_single_d20:
            natural_roll = pools[0].dice_results[0].value
            if natural_roll == 20:
                outcome = RollOutcome.CRITICAL_SUCCESS
                outcome_reason = "Natural 20!"
            elif natural_roll == 1:
                outcome = RollOutcome.CRITICAL_FAILURE
                outcome_reason = "Natural 1!"

        # Check DC if specified
        if target_dc is not None:
            if outcome == RollOutcome.CRITICAL_SUCCESS:
                pass  # Keep critical success
            elif outcome == RollOutcome.CRITICAL_FAILURE:
                pass  # Keep critical failure
            elif final_total >= target_dc:
                outcome = RollOutcome.SUCCESS
            else:
                outcome = RollOutcome.FAILURE

        return DiceRollResult(
            notation=notation,
            pools=pools,
            constant_modifier=constant_modifier,
            multiplier=multiplier,
            divisor=divisor,
            raw_total=raw_total,
            final_total=final_total,
            target_dc=target_dc,
            outcome=outcome,
            outcome_reason=outcome_reason,
        )

    def roll_simple(
        self,
        dice_count: int,
        dice_sides: int,
        modifier: int = 0,
        target_dc: int | None = None,
        purpose: str = "",
    ) -> DiceRollResult:
        """
        Roll dice with explicit parameters (no notation parsing needed).
        """
        notation = f"{dice_count}d{dice_sides}"
        if modifier > 0:
            notation += f"+{modifier}"
        elif modifier < 0:
            notation += str(modifier)
        if target_dc:
            notation += f" DC:{target_dc}"

        result = self.roll_notation(notation)
        if result is None:
            # This shouldn't happen with valid parameters, but handle it
            raise ValueError(f"Invalid dice parameters: {dice_count}d{dice_sides}")
        return result
