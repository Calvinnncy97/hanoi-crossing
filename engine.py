"""Core engine for Hanoi Crossing.

Data model:

- A `Disk` is only its size. Its position is never stored on it.
- The `Board` manages the towers: one stack of disks per `Pole`.
- The `Table` owns the board and both players' hands. It is the only place
  disks move between towers and hands, so every disk is always in exactly
  one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Player(str, Enum):
    """One of the two players."""

    A = "A"
    B = "B"


class Pole(str, Enum):
    """The five poles: each player's poles 1 and 3, and the shared pole 2."""

    A1 = "1a"
    A3 = "3a"
    SHARED = "2"
    B1 = "1b"
    B3 = "3b"


@dataclass(frozen=True, order=True)
class Disk:
    """A disk, identified only by its size."""

    size: int

    @property
    def owner(self) -> Player:
        """The player who starts with this disk: odd sizes are A, even are B."""
        return Player.A if self.size % 2 else Player.B


@dataclass
class Board:
    """The towers: one stack per pole, listed bottom to top."""

    towers: dict[Pole, list[Disk]] = field(default_factory=lambda: {p: [] for p in Pole})

    def push(self, pole: Pole, disk: Disk) -> None:
        """Put `disk` on top of `pole`."""
        self.towers[pole].append(disk)

    def pop(self, pole: Pole) -> Disk:
        """Remove and return the top disk of `pole`."""
        return self.towers[pole].pop()

    def where(self, disk: Disk) -> Pole | None:
        """The pole holding `disk`, or None if it is not on any tower."""
        for pole, tower in self.towers.items():
            if disk in tower:
                return pole
        return None


@dataclass
class Table:
    """The board plus both players' hands.

    Lifting and placing are the only ways a disk moves between a tower and
    a hand. Neither checks game rules; the rules layer does that first.
    """

    board: Board = field(default_factory=Board)
    hands: dict[Player, Disk | None] = field(default_factory=lambda: {p: None for p in Player})

    def lift(self, player: Player, pole: Pole) -> None:
        """Move the top disk of `pole` into `player`'s hand."""
        self.hands[player] = self.board.pop(pole)

    def place(self, player: Player, pole: Pole) -> None:
        """Move the disk in `player`'s hand onto `pole`."""
        self.board.push(pole, self.hands[player])
        self.hands[player] = None

    def where(self, disk: Disk) -> Pole | Player:
        """The pole holding `disk`, or the player holding it in hand."""
        pole = self.board.where(disk)
        if pole is not None:
            return pole
        for player, held in self.hands.items():
            if held == disk:
                return player
        raise KeyError(f"disk {disk.size} is not on the table")
