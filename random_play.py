"""Play one game where both sides pick random legal moves, and print the result as JSON.

Each side is a `RandomPlayer`, which only sees the list of legal actions,
the same way an outside agent would. The turn order is made here, not by
the engine: `alternate` gives A, B, A, B, ...; `random` picks a side at
random for every turn.

A random game can run for a long time, so it stops after `--max-turns`
turns; the result then has no winner.

The output has the same shape as `replay.py`'s, plus the seed, so any game
can be reproduced by running again with that seed.

Usage: uv run random_play.py [--n DISKS] [--seed SEED] [--order alternate|random] [--max-turns T]
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from collections.abc import Iterator

from engine import Game, Side
from players import RandomPlayer
from runner import final_state, run_turns


def turn_order(order: str, rng: random.Random, max_turns: int) -> Iterator[Side]:
    """Up to `max_turns` sides: alternating from A, or chosen at random with `rng`."""
    if order == "alternate":
        sides = itertools.cycle(Side)
    else:
        sides = (rng.choice(list(Side)) for _ in itertools.count())
    return itertools.islice(sides, max_turns)


def random_game(n: int, seed: int, order: str = "alternate", max_turns: int = 10_000) -> dict:
    """Play one random game and return the result as a JSON-ready dict.

    One seed drives everything: both players' choices and, for a random
    order, who moves when. The same arguments always give the same game.
    """
    rng = random.Random(seed)
    players = {side: RandomPlayer(side, rng.randrange(2**32)) for side in Side}
    game = Game(n)
    log = run_turns(game, players, turn_order(order, rng, max_turns))
    return {
        "seed": seed,
        "n": n,
        "order": order,
        "winner": game.winner.value if game.winner else None,
        "turns_played": len(log),
        "log": log,
        "final": final_state(game),
    }


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, play one random game and print the result."""
    parser = argparse.ArgumentParser(description="Play a game where both sides move at random.")
    parser.add_argument("--n", type=int, default=3, help="disks per player (default 3)")
    parser.add_argument("--seed", type=int, default=None, help="seed for a repeatable game (default: random)")
    parser.add_argument("--order", choices=("alternate", "random"), default="alternate", help="turn order (default alternate)")
    parser.add_argument("--max-turns", type=int, default=10_000, help="stop after this many turns (default 10000)")
    parser.add_argument("--no-log", action="store_true", help="leave the turn-by-turn log out of the output")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")
    if args.max_turns < 1:
        parser.error("--max-turns must be at least 1")

    seed = args.seed if args.seed is not None else random.randrange(2**32)
    result = random_game(args.n, seed, args.order, args.max_turns)
    if args.no_log:
        del result["log"]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
