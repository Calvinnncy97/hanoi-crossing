"""Core engine for Hanoi Crossing.

Data model:

- A `Disk` is only its size. Its position is never stored on it.
- The `Board` manages the towers: one stack of disks per `Pole`.
- The `Table` holds the game state: the board and the disk in each hand.
  It moves a disk between a tower and a hand when asked, without checking
  any rules. Because the towers and hands live together here, every disk
  is always in exactly one place.
- The `Game` sets up the table, checks whether a move is legal, applies
  it and checks for a win.
- A `Player` makes the actions (lift, place, skip) for one side, through
  the game.
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
    moves between a tower and a hand. Neither checks game rules; `Game`
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
"""The poles each side can see and act on, in order: pole 1, pole 2, pole 3."""


class Kind(str, Enum):
    """The three kinds of action."""

    LIFT = "lift"
    PLACE = "place"
    SKIP = "skip"


@dataclass(frozen=True)
class Action:
    """One action: a kind, plus the target pole for lift and place."""

    kind: Kind
    pole: Pole | None = None


class Game:
    """One game: sets up the table, checks legal moves and detects a win.

    The game does not track whose turn it is. Every call to `step` names
    the acting side, so the caller decides the turn order.
    """

    def __init__(self, n: int) -> None:
        """Set up a table where each side has `n` disks on its pole 1, largest at the bottom."""
        self.n = n
        self.table = Table()
        self.winner: Side | None = None
        for size in range(2 * n, 0, -1):
            disk = Disk(size)
            self.table.board.push(VISIBLE[disk.owner][0], disk)

    def is_legal(self, side: Side, action: Action) -> bool:
        """True if `side` may take `action` now.

        Nothing is legal once the game is over. Skip is otherwise always
        legal. Lift needs a visible, non-empty pole and an empty hand.
        Place needs a held disk and a visible pole that is empty or topped
        by a larger disk.
        """
        if self.winner is not None:
            return False
        if action.kind is Kind.SKIP:
            return True
        if action.pole not in VISIBLE[side]:
            return False
        held = self.table.hands[side]
        top = self.table.board.top(action.pole)
        if action.kind is Kind.LIFT:
            return held is None and top is not None
        return held is not None and (top is None or top.size > held.size)

    def legal_actions(self, side: Side) -> list[Action]:
        """Every action `side` may take now."""
        candidates = [Action(Kind.SKIP)]
        candidates += [Action(kind, pole) for kind in (Kind.LIFT, Kind.PLACE) for pole in VISIBLE[side]]
        return [a for a in candidates if self.is_legal(side, a)]

    def has_won(self, side: Side) -> bool:
        """True if `side`'s hand, pole 1 and pole 2 are empty and pole 3 has disks."""
        pole1, pole2, pole3 = VISIBLE[side]
        board = self.table.board
        return (
            self.table.hands[side] is None
            and board.top(pole1) is None
            and board.top(pole2) is None
            and board.top(pole3) is not None
        )

    def step(self, side: Side, action: Action) -> bool:
        """Apply `action` for `side` and return whether it was legal.

        An illegal action changes nothing; the turn is simply wasted. After
        a legal action both sides are checked for a win, the actor first,
        because an action can also complete the other side's win (for
        example, lifting their disk off the shared pole).
        """
        if not self.is_legal(side, action):
            return False
        if action.kind is Kind.LIFT:
            self.table.to_hand(side, action.pole)
        elif action.kind is Kind.PLACE:
            self.table.to_pole(side, action.pole)
        other = Side.B if side is Side.A else Side.A
        self.winner = next((s for s in (side, other) if self.has_won(s)), None)
        return True


@dataclass
class Player:
    """One side's way of acting in a game.

    Each action goes through `Game.step`, so rules and the win check
    always apply. Returns False when the action was illegal.
    """

    side: Side
    game: Game

    def lift(self, pole: Pole) -> bool:
        """Lift the top disk of `pole` into this player's hand."""
        return self.game.step(self.side, Action(Kind.LIFT, pole))

    def place(self, pole: Pole) -> bool:
        """Place the held disk onto `pole`."""
        return self.game.step(self.side, Action(Kind.PLACE, pole))

    def skip(self) -> bool:
        """Do nothing this turn."""
        return self.game.step(self.side, Action(Kind.SKIP))
