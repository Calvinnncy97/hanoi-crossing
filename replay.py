"""Replay a recorded Hanoi Crossing game and print the result as JSON.

Input is a JSON file (or `-` for stdin):

    {
      "n": 1,
      "turns": ["A", "B", "A"],
      "moves": {"A": ["lift 1", "place 3"], "B": ["lift 1"]}
    }

- `n` is the number of disks per player.
- `turns` says which side acts on each step, in order. Any pattern is allowed.
- `moves` lists each side's moves in the order that side plays them, with
  poles named as that side sees them: 1, 2 (shared) or 3. Each turn uses
  the acting side's next move; a side whose list has run out skips.

An illegal move wastes the turn. Once a side wins, the remaining turns are
not played.

Output is JSON with the winner, a log of every turn played, and the final
state of all poles and hands, using board names (1a, 3a, 2, 1b, 3b).

Usage: uv run replay.py GAME.json
"""

from __future__ import annotations

import argparse
import json
import sys

from engine import Game, Side
from players import ReplayPlayer
from runner import final_state, run_turns


def replay(record: dict) -> dict:
    """Play `record` through the engine and return the result as a JSON-ready dict.

    Raises ValueError if the record is malformed.
    """
    n = record.get("n")
    if not isinstance(n, int) or n < 1:
        raise ValueError("'n' must be a whole number of at least 1")
    try:
        turns = [Side(t) for t in record.get("turns", [])]
    except ValueError as error:
        raise ValueError(f"'turns' may only contain 'A' and 'B': {error}") from None
    moves = record.get("moves", {})
    unknown = set(moves) - {s.value for s in Side}
    if unknown:
        raise ValueError(f"'moves' has unknown sides: {sorted(unknown)}")
    players = {side: ReplayPlayer(side, moves.get(side.value, [])) for side in Side}

    game = Game(n)
    log = run_turns(game, players, turns)
    return {
        "winner": game.winner.value if game.winner else None,
        "turns_played": len(log),
        "turns_ignored": len(turns) - len(log),
        "log": log,
        "final": final_state(game),
    }


def main(argv: list[str] | None = None) -> None:
    """Read the record, replay it and print the result. Exits with status 1 on bad input."""
    parser = argparse.ArgumentParser(description="Replay a recorded Hanoi Crossing game.")
    parser.add_argument("file", help="JSON game record, or - for stdin")
    args = parser.parse_args(argv)
    try:
        source = sys.stdin if args.file == "-" else open(args.file, encoding="utf-8")
        with source:
            record = json.load(source)
        result = replay(record)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
