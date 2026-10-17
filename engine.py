"""Core engine for Hanoi Crossing.

Data model:

- A `Disk` is only its size. Its position is never stored on it.
- The `Board` manages the towers: one stack of disks per `Pole`.
- The `Table` holds the game state: the board and the disk in each hand.
  It moves a disk between a tower and a hand when asked, without checking
  any rules. Because the towers and hands live together here, every disk
  is always in exactly one place.
- A `Player` makes the actions (lift, place, skip). It checks the rules,
  then asks the table to move the disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    """Which of the two players: A or B."""

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
    def owner(self) -> Side:
        """The side that starts with this disk: odd sizes are A, even are B."""
        return Side.A if self.size % 2 else Side.B


@dataclass
class Board:
    """The towers: one stack per pole, listed bottom to top."""

    towers: dict[Pole, list[Disk]] = field(default_factory=lambda: {p: [] for p in Pole})

    def push(self, pole: Pole, disk: Disk) -> None:
        """Put `disk` on top of `pole`."""
        self.towers[pole].append(disk)

    def top(self, pole: Pole) -> Disk | None:
        """The top disk of `pole`, or None if it is empty."""
        tower = self.towers[pole]
        return tower[-1] if tower else None

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

    It only manages state. `to_hand` and `to_pole` are the only ways a disk
    moves between a tower and a hand. Neither checks game rules; `Player`
    does that first.
    """

    board: Board = field(default_factory=Board)
    hands: dict[Side, Disk | None] = field(default_factory=lambda: {s: None for s in Side})

    def to_hand(self, side: Side, pole: Pole) -> None:
        """Move the top disk of `pole` into `side`'s hand."""
        self.hands[side] = self.board.pop(pole)

    def to_pole(self, side: Side, pole: Pole) -> None:
        """Move the disk in `side`'s hand onto `pole`."""
        self.board.push(pole, self.hands[side])
        self.hands[side] = None

    def where(self, disk: Disk) -> Pole | Side:
        """The pole holding `disk`, or the side holding it in hand."""
        pole = self.board.where(disk)
        if pole is not None:
            return pole
        for side, held in self.hands.items():
            if held == disk:
                return side
        raise KeyError(f"disk {disk.size} is not on the table")


VISIBLE: dict[Side, tuple[Pole, ...]] = {
    Side.A: (Pole.A1, Pole.SHARED, Pole.A3),
    Side.B: (Pole.B1, Pole.SHARED, Pole.B3),
}
"""The poles each side can see and act on, as poles 1, 2 and 3."""


@dataclass
class Player:
    """One player acting on a shared table.

    Each action checks the rules first. An illegal action changes nothing
    and returns False, so the caller can treat the turn as wasted.
    """

    side: Side
    table: Table

    @property
    def hand(self) -> Disk | None:
        """The disk this player holds, if any."""
        return self.table.hands[self.side]

    def lift(self, pole: Pole) -> bool:
        """Lift the top disk of a visible `pole` into an empty hand."""
        if pole not in VISIBLE[self.side] or self.hand is not None:
            return False
        if self.table.board.top(pole) is None:
            return False
        self.table.to_hand(self.side, pole)
        return True

    def place(self, pole: Pole) -> bool:
        """Place the held disk on a visible `pole` that is empty or topped by a larger disk."""
        if pole not in VISIBLE[self.side] or self.hand is None:
            return False
        top = self.table.board.top(pole)
        if top is not None and top.size < self.hand.size:
            return False
        self.table.to_pole(self.side, pole)
        return True

    def skip(self) -> bool:
        """Do nothing. Always legal."""
        return True
