"""Shared game loop for the non-interactive frontends (replay and random play).

The loop is the same however the moves are chosen: for each side in the
turn order, give that side's `Player` its view and the legal actions,
then pass its choice to `Game.step`.
"""

from __future__ import annotations

from collections.abc import Iterable

from engine import Action, Game, Kind, Player, Side


def move_text(action: Action) -> str:
    """An action with its pole's board name, such as "lift 1a", "place 2" or "skip"."""
    return action.kind.value if action.kind is Kind.SKIP else f"{action.kind.value} {action.pole.value}"


def run_turns(game: Game, players: dict[Side, Player], turns: Iterable[Side]) -> list[dict]:
    """Play `turns` in order until they run out or someone wins.

    Returns one log entry per turn played, with the turn number, the side,
    the move, whether it was legal and, if not, why. Turns after a win are
    not played.
    """
    log = []
    for number, side in enumerate(turns, start=1):
        if game.winner is not None:
            break
        action = players[side].choose(game.observe(side), game.legal_actions(side))
        result = game.step(side, action)
        log.append({
            "turn": number,
            "side": side.value,
            "move": move_text(action),
            "legal": result.legal,
            "reason": result.reason,
        })
    return log


def final_state(game: Game) -> dict:
    """Every pole and hand, using board names (1a, 3a, 2, 1b, 3b), as a JSON-ready dict."""
    return {
        "poles": {pole.value: [d.size for d in tower] for pole, tower in game.table.board.towers.items()},
        "hands": {side.value: (disk.size if disk else None) for side, disk in game.table.hands.items()},
    }
