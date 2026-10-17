"""Core engine for Hanoi Crossing.

Data model:

- A `Disk` is only its size. Its position is never stored on it.
- The `Board` manages the towers: one stack of disks per `Pole`.
- The `Table` holds the game state: the board and the disk in each hand.
  Its one primitive, `move`, shifts a disk between a tower and a hand
  without checking any rules. Because the towers and hands live together
  here, every disk is always in exactly one place.
- An `Action` is a move as data. The kinds of move (lift, place, skip) are
  defined only here.
- The `Game` sets up the table, checks whether an action is legal, turns
  it into a table move and checks for a win.
- A `Player` decides which action its side takes.
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


@dataclass
class Table:
    """The board plus both players' hands.

    It only manages state. `move` is the only way a disk changes place,
    and it does not check game rules; `Game` does that first.
    """

    board: Board = field(default_factory=Board)
    hands: dict[Side, Disk | None] = field(default_factory=lambda: {s: None for s in Side})

    def move(self, src: Pole | Side, dst: Pole | Side) -> None:
        """Move one disk from `src` to `dst`.

        A `Pole` means the top of that tower; a `Side` means that side's
        hand.
        """
        if isinstance(src, Side):
            disk, self.hands[src] = self.hands[src], None
        else:
            disk = self.board.pop(src)
        if isinstance(dst, Side):
            self.hands[dst] = disk
        else:
            self.board.push(dst, disk)

    def where(self, disk: Disk) -> Pole | Side:
        """The pole holding `disk`, or the side holding it in hand."""
        for pole, tower in self.board.towers.items():
            if disk in tower:
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


def action_space(side: Side) -> tuple[Action, ...]:
    """Every action `side` can name, in a fixed order: skip, lift 1-3, place 1-3.

    Poles follow `VISIBLE`, so position i means the same move from each
    side's own view. The position is the action's number, for agents such
    as RL policies that work with integers.
    """
    poles = VISIBLE[side]
    return (
        Action(Kind.SKIP),
        *(Action(Kind.LIFT, pole) for pole in poles),
        *(Action(Kind.PLACE, pole) for pole in poles),
    )


@dataclass(frozen=True)
class Observation:
    """What one side is allowed to see.

    `poles` maps the side's own pole names ("1", "2" shared, "3") to the
    disk sizes on them, bottom to top. `hand` is the size of the held disk,
    or None. The other side's poles 1 and 3 and its hand are never
    included. Whose disk is whose follows from its size: odd is A, even
    is B.
    """

    side: Side
    n: int
    poles: dict[str, tuple[int, ...]]
    hand: int | None
    winner: Side | None


@dataclass(frozen=True)
class StepResult:
    """The outcome of one `Game.step`.

    `legal` says whether the action was applied. When it was not, `reason`
    says why. `winner` is the winner after the step, if any.
    """

    legal: bool
    reason: str | None = None
    winner: Side | None = None


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

    def illegal_reason(self, side: Side, action: Action) -> str | None:
        """Why `side` may not take `action` now, or None if it may.

        Nothing is legal once the game is over. Skip is otherwise always
        legal. Lift needs a visible, non-empty pole and an empty hand.
        Place needs a held disk and a visible pole that is empty or topped
        by a larger disk.
        """
        if self.winner is not None:
            return "the game is over"
        if action.kind is Kind.SKIP:
            return None
        if action.pole not in VISIBLE[side]:
            return f"pole {action.pole.value} is not visible to {side.value}"
        held = self.table.hands[side]
        top = self.table.board.top(action.pole)
        if action.kind is Kind.LIFT:
            if held is not None:
                return f"hand already holds disk {held.size}"
            if top is None:
                return f"pole {action.pole.value} is empty"
            return None
        if held is None:
            return "hand is empty"
        if top is not None and top.size < held.size:
            return f"disk {held.size} cannot go on smaller disk {top.size}"
        return None

    def is_legal(self, side: Side, action: Action) -> bool:
        """True if `side` may take `action` now."""
        return self.illegal_reason(side, action) is None

    def legal_actions(self, side: Side) -> list[Action]:
        """Every action `side` may take now, in `action_space` order."""
        return [a for a in action_space(side) if self.is_legal(side, a)]

    def legal_mask(self, side: Side) -> list[bool]:
        """One flag per entry of `action_space(side)`: True where that action is legal now."""
        return [self.is_legal(side, a) for a in action_space(side)]

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

    def observe(self, side: Side) -> Observation:
        """The part of the game `side` is allowed to see."""
        held = self.table.hands[side]
        return Observation(
            side=side,
            n=self.n,
            poles={
                str(i): tuple(d.size for d in self.table.board.towers[pole])
                for i, pole in enumerate(VISIBLE[side], start=1)
            },
            hand=held.size if held else None,
            winner=self.winner,
        )

    def step(self, side: Side, action: Action) -> StepResult:
        """Apply `action` for `side` and say what happened.

        An illegal action changes nothing; the turn is simply wasted, and
        the result gives the reason. After a legal action both sides are
        checked for a win, the actor first, because an action can also
        complete the other side's win (for example, lifting their disk off
        the shared pole).
        """
        reason = self.illegal_reason(side, action)
        if reason is not None:
            return StepResult(legal=False, reason=reason, winner=self.winner)
        if action.kind is Kind.LIFT:
            self.table.move(action.pole, side)
        elif action.kind is Kind.PLACE:
            self.table.move(side, action.pole)
        other = Side.B if side is Side.A else Side.A
        self.winner = next((s for s in (side, other) if self.has_won(s)), None)
        return StepResult(legal=True, winner=self.winner)


@dataclass
class Player:
    """Decides which action one side takes.

    This is the interface every kind of player implements: a replay of
    recorded moves, a random player, or later an RL agent. Subclasses
    override `choose`. The caller gets the inputs from `Game.observe` and
    `Game.legal_actions`, and passes the chosen action to `Game.step`.
    """

    side: Side

    def choose(self, view: Observation, legal: list[Action]) -> Action:
        """Pick an action, given what this side can see and the actions legal right now."""
        raise NotImplementedError
