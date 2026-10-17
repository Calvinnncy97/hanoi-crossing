"""Core engine for Hanoi Crossing.

Data model:

- A `Disk` is only its size. Its owner is derived from parity (odd is A,
  even is B) and its position is never stored on it.
- The `Board` is the single source of truth for where disks are. It maps
  every `Location` (the five poles and the two hands) to a stack of disks,
  bottom to top. `Board.move` is the only way to change it, so a disk is
  always in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Player(str, Enum):
    """One of the two players."""

    A = "A"
    B = "B"


class Location(str, Enum):
    """Every place a disk can be: five poles and two hands."""

    A1 = "1a"
    A3 = "3a"
    SHARED = "2"
    B1 = "1b"
    B3 = "3b"
    HAND_A = "hand_a"
    HAND_B = "hand_b"


@dataclass(frozen=True, order=True)
class Disk:
    """A disk, identified only by its size.

    Disks are immutable values. Where a disk is lives on the `Board`, not
    here, so the two can never disagree.
    """

    size: int

    @property
    def owner(self) -> Player:
        """The player who starts with this disk: odd sizes are A, even are B."""
        return Player.A if self.size % 2 else Player.B


@dataclass
class Board:
    """Where every disk is: one stack per location, listed bottom to top.

    This is the only record of disk positions. A hand is a stack that holds
    at most one disk, so lifting and placing are both just `move`.
    """

    stacks: dict[Location, list[Disk]]

    def where(self, disk: Disk) -> Location:
        """The location of `disk`, found by scanning the stacks."""
        for loc, stack in self.stacks.items():
            if disk in stack:
                return loc
        raise KeyError(f"disk {disk.size} is not on the board")

    def move(self, src: Location, dst: Location) -> None:
        """Move the top disk of `src` onto `dst`.

        This is the only method that changes the board. It does not check
        game rules; the rules layer does that before calling it.
        """
        self.stacks[dst].append(self.stacks[src].pop())
