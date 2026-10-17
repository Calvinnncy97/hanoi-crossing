"""Players that are not human."""

from __future__ import annotations

import random

from engine import Action, Player, Side


class RandomPlayer(Player):
    """Picks uniformly among the legal actions.

    Pass a seed to make its choices repeatable.
    """

    def __init__(self, side: Side, seed: int | None = None) -> None:
        """Create a random player for `side`."""
        super().__init__(side)
        self.rng = random.Random(seed)

    def choose(self, legal: list[Action]) -> Action:
        """Pick one of `legal` at random."""
        return self.rng.choice(legal)
