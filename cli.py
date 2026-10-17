"""Play Hanoi Crossing in the terminal as side A against a random side B.

The screen shows only what A can see: A's poles 1 and 3, the shared pole 2
and A's hand, drawn as towers with Rich. Pick a move with the arrow keys
and Enter; Ctrl-C quits. Turns alternate A, B, A, ... B's moves on its own
poles stay hidden; only their effect on the shared pole shows.

Usage: uv run cli.py [--n DISKS] [--seed SEED]
"""

from __future__ import annotations

import argparse
import sys

import questionary
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from engine import VISIBLE, Action, Disk, Game, Kind, Player, Pole, Side
from players import RandomPlayer

console = Console()

DISK_COLOUR = {Side.A: "dodger_blue2", Side.B: "dark_orange"}
"""Disk colours by the side that started with them: A blue, B orange."""


def pole_names(side: Side) -> dict[Pole, str]:
    """Map each pole `side` can see to the name that side uses for it: "1", "2" or "3"."""
    return {pole: str(i) for i, pole in enumerate(VISIBLE[side], start=1)}


def describe(action: Action, side: Side) -> str:
    """Text for `action` as `side` sees it, such as "lift from pole 1"."""
    if action.kind is Kind.SKIP:
        return "skip"
    preposition = "from" if action.kind is Kind.LIFT else "onto"
    return f"{action.kind.value} {preposition} pole {pole_names(side)[action.pole]}"


def disk_text(disk: Disk) -> Text:
    """A disk drawn as a bar, wider for bigger disks, with its size in the middle.

    The bar is made of block characters, so it still reads as a disk in a
    terminal without colour.
    """
    colour = DISK_COLOUR[disk.owner]
    bar = "█" * disk.size
    return Text.assemble((bar, colour), (str(disk.size), f"bold white on {colour}"), (bar, colour))


def centered(content: Text, width: int) -> Text:
    """`content` padded with spaces on both sides to `width` characters."""
    left = (width - len(content)) // 2
    return Text.assemble(" " * left, content, " " * (width - len(content) - left))


def render(game: Game, side: Side, title: str) -> Panel:
    """A panel with the three towers `side` can see and the disk in its hand.

    Every tower is drawn tall enough to hold all disks in the game, so the
    picture keeps the same size from turn to turn.
    """
    names = pole_names(side)
    towers = [game.table.board.towers[pole] for pole in names]
    height = 2 * game.n
    width = max(2 * height + 5, 17)
    rows = []
    for level in range(height - 1, -1, -1):
        cells = [
            disk_text(tower[level]) if level < len(tower) else Text("│", style="grey50")
            for tower in towers
        ]
        rows.append(Text.assemble(*(centered(cell, width) for cell in cells)))
    base = "─" * (width // 2 - 1) + "┴" + "─" * (width - width // 2)
    rows.append(Text.assemble(*(centered(Text(base[: width - 2], style="grey50"), width) for _ in names)))
    labels = [f"pole {name}" + (" (shared)" if name == "2" else "") for name in names.values()]
    rows.append(Text.assemble(*(centered(Text(label, style="bold"), width) for label in labels)))
    held = game.table.hands[side]
    hand = Text.assemble("Hand: ", disk_text(held) if held else Text("empty", style="grey50"))
    return Panel(
        Group(Text(), *rows, Text(), hand),
        title=title,
        subtitle="[dodger_blue2]■[/] your disks  [dark_orange]■[/] B's disks",
        expand=False,
        padding=(0, 2),
    )


class HumanPlayer(Player):
    """Asks the person at the terminal to pick from the legal actions."""

    def choose(self, legal: list[Action]) -> Action:
        """Show the legal actions as an arrow-key menu and return the pick.

        Exits the program if the person cancels with Ctrl-C.
        """
        choices = [questionary.Choice(describe(action, self.side), value=action) for action in legal]
        action = questionary.select("Your move:", choices=choices, qmark="»").ask()
        if action is None:
            console.print("Bye.")
            sys.exit(0)
        return action


def play(game: Game, human: HumanPlayer, opponent: Player) -> Side:
    """Alternate turns, human first, until someone wins.

    The board is shown before each of the human's turns. The opponent's
    move is not described, since it may be on poles the human cannot see.
    """
    turn = 1
    while game.winner is None:
        player = human if turn % 2 else opponent
        if player is human:
            console.print(render(game, human.side, f"Turn {turn} · your view"))
        game.step(player.side, player.choose(game.legal_actions(player.side)))
        if player is opponent:
            console.print(f"[grey50]Turn {turn}: {opponent.side.value} took its turn.[/]\n")
        turn += 1
    return game.winner


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, play one game and announce the winner."""
    parser = argparse.ArgumentParser(description="Play Hanoi Crossing as side A against a random side B.")
    parser.add_argument("--n", type=int, default=3, help="disks per player (default 3)")
    parser.add_argument("--seed", type=int, default=None, help="seed for B's random moves")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")

    game = Game(args.n)
    console.rule("[bold]Hanoi Crossing")
    console.print("You are [bold dodger_blue2]A[/]. Win by getting every disk you can see onto your pole 3, with an empty hand.\n")
    winner = play(game, HumanPlayer(Side.A), RandomPlayer(Side.B, args.seed))
    console.print(render(game, Side.A, "Final view"))
    console.print("\n[bold green]You win![/]" if winner is Side.A else "\n[bold red]B wins.[/]")


if __name__ == "__main__":
    main()
