"""Play Hanoi Crossing in the terminal as side A.

The screen shows only what A can see: A's poles 1 and 3, the shared pole 2
and A's hand. Enter the number of an action to play it, or `q` to quit.

Usage: python cli.py [--n DISKS]
"""

from __future__ import annotations

import argparse
import sys

from engine import VISIBLE, Action, Game, Kind, Player, Side


def pole_names(side: Side) -> dict:
    """Map each pole `side` can see to the name that side uses for it: "1", "2" or "3"."""
    return {pole: str(i) for i, pole in enumerate(VISIBLE[side], start=1)}


def describe(action: Action, side: Side) -> str:
    """Text for `action` as `side` sees it, such as "lift from pole 1"."""
    if action.kind is Kind.SKIP:
        return "skip"
    preposition = "from" if action.kind is Kind.LIFT else "onto"
    return f"{action.kind.value} {preposition} pole {pole_names(side)[action.pole]}"


def render(game: Game, side: Side) -> str:
    """The part of the table `side` can see, one line per pole plus the hand."""
    lines = []
    for pole, name in pole_names(side).items():
        disks = " ".join(str(d.size) for d in game.table.board.towers[pole]) or "-"
        label = f"pole {name}" + (" (shared)" if name == "2" else "")
        lines.append(f"  {label:<17}| {disks}")
    held = game.table.hands[side]
    lines.append(f"  {'hand':<17}| {held.size if held else '-'}")
    return "\n".join(lines)


class HumanPlayer(Player):
    """Asks the person at the terminal to pick from the legal actions."""

    def choose(self, legal: list[Action]) -> Action:
        """Print the numbered actions and read a choice until it is valid.

        Exits the program on `q` or end of input.
        """
        for number, action in enumerate(legal, start=1):
            print(f"  {number}) {describe(action, self.side)}")
        while True:
            try:
                answer = input("Your move: ").strip().lower()
            except EOFError:
                answer = "q"
            if answer == "q":
                print("\nBye.")
                sys.exit(0)
            if answer.isdigit() and 1 <= int(answer) <= len(legal):
                return legal[int(answer) - 1]
            print(f"  Enter a number from 1 to {len(legal)}, or q to quit.")


def play(game: Game, player: Player) -> Side:
    """Let `player` take every turn until someone wins."""
    turn = 1
    while game.winner is None:
        print(f"\n--- Turn {turn} ---")
        print(render(game, player.side))
        game.step(player.side, player.choose(game.legal_actions(player.side)))
        turn += 1
    return game.winner


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, play one game and announce the winner."""
    parser = argparse.ArgumentParser(description="Play Hanoi Crossing as side A.")
    parser.add_argument("--n", type=int, default=3, help="disks per player (default 3)")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")

    game = Game(args.n)
    print(f"You are A with disks {', '.join(str(s) for s in range(1, 2 * args.n, 2))}.")
    print("Win by getting every disk you can see onto your pole 3, with an empty hand.")
    winner = play(game, HumanPlayer(Side.A))

    print("\n--- Final view ---")
    print(render(game, Side.A))
    print(f"\n{winner.value} wins.")


if __name__ == "__main__":
    main()
