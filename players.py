"""Players that are not human: random and replayed from recorded moves."""

from __future__ import annotations

import random

from engine import VISIBLE, Action, Kind, Observation, Player, Side


class RandomPlayer(Player):
    """Picks uniformly among the legal actions.

    Pass a seed to make its choices repeatable.
    """

    def __init__(self, side: Side, seed: int | None = None) -> None:
        """Create a random player for `side`."""
        super().__init__(side)
        self.rng = random.Random(seed)

    def choose(self, view: Observation, legal: list[Action]) -> Action:
        """Pick one of `legal` at random; the view is not needed."""
        return self.rng.choice(legal)


def parse_action(text: str, side: Side) -> Action:
    """Read a move such as "lift 1", "place 3" or "skip", with poles named as `side` sees them.

    Raises ValueError for anything else.
    """
    words = text.strip().lower().split()
    if words == ["skip"]:
        return Action(Kind.SKIP)
    if len(words) == 2 and words[0] in ("lift", "place") and words[1] in ("1", "2", "3"):
        return Action(Kind(words[0]), VISIBLE[side][int(words[1]) - 1])
    raise ValueError(f"bad move {text!r}: expected 'lift <1-3>', 'place <1-3>' or 'skip'")


class ReplayPlayer(Player):
    """Plays a fixed list of recorded moves in order, then skips.

    The moves are parsed up front, so a typo is reported before the game
    starts. A recorded move is played even if it is illegal; the game
    then rejects it and the turn is wasted, as the rules say.
    """

    def __init__(self, side: Side, moves: list[str]) -> None:
        """Create a player for `side` that will play `moves` in order."""
        super().__init__(side)
        self.moves = [parse_action(text, side) for text in moves]
        self.played = 0

    def choose(self, view: Observation, legal: list[Action]) -> Action:
        """The next recorded move, or skip once they run out. The inputs are not needed."""
        if self.played >= len(self.moves):
            return Action(Kind.SKIP)
        self.played += 1
        return self.moves[self.played - 1]
