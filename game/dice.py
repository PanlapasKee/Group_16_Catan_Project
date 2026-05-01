"""
dice.py
=======
Encapsulates dice-rolling logic for the game.
Keeping this isolated makes it trivial to swap in weighted dice for testing.
"""

import random
from typing import Tuple


class Dice:
    """
    Represents a pair of standard six-sided dice.

    Attributes
    ----------
    last_roll : tuple[int, int]
        The individual values from the most recent roll.
    total     : int
        The sum of the most recent roll.
    """

    def __init__(self) -> None:
        self.last_roll: Tuple[int, int] = (0, 0)
        self.total: int = 0

    # ------------------------------------------------------------------
    def roll(self) -> int:
        """
        Roll both dice, store results, and return the total.

        :return: Sum of the two dice (2–12).
        """
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.last_roll = (d1, d2)
        self.total = d1 + d2
        return self.total

    # ------------------------------------------------------------------
    def __str__(self) -> str:
        d1, d2 = self.last_roll
        return f"🎲 {d1} + {d2} = {self.total}"
