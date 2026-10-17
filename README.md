# Hanoi Crossing

A two-player, hidden-information variant of the Tower of Hanoi. The core is a
small Python engine. Three frontends sit on top of it:

- **Replay**: plays a pre-recorded game (moves + turn order) and prints the final state.
- **Random play**: both sides pick random legal moves.
- **Interactive CLI**: you play A against a random B in the terminal.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                    # install dependencies
uv run replay.py examples/brief.json       # replay a recorded game
uv run random_play.py --n 3 --seed 7       # random vs random
uv run cli.py --n 3                        # play as A against a random B
uv run pytest                              # run the tests
```

## Project layout

```
engine.py        the game engine (no I/O, no randomness)
players.py       RandomPlayer, ReplayPlayer and move parsing
runner.py        shared turn loop and output for replay and random play
replay.py        replay frontend
random_play.py   random-play frontend
cli.py           interactive frontend (Rich + questionary)
examples/        sample game records for replay
tests/           pytest tests for the engine and frontends
```

The project is a flat uv project (`package = false` in `pyproject.toml`): the
modules are run directly with `uv run`, not installed as a package.

## Engine design

The engine (`engine.py`, about 330 lines) is built from small classes, each
with one job.

| Class | Job |
|---|---|
| `Disk` | Just a size, and it can't be changed. Its starting owner follows from parity: odd is A, even is B. It never stores its own position. |
| `Board` | The five towers (`1a`, `3a`, `2`, `1b`, `3b`), each a stack from bottom to top. |
| `Table` | The board plus both hands. Its one method `move(src, dst)` moves a disk between a pole and a hand. It checks no rules. |
| `Action` | One move as data: lift, place or skip, plus a pole. |
| `Game` | Sets up the table, checks whether moves are legal, applies them, detects a win, and gives each side its view. |
| `Player` | Decides which action a side takes: `choose(view, legal) -> Action`. |

Design decisions:

- **Where a disk is gets stored in one place only.** A disk does not store its
  position. The towers and hands do, and they all live in `Table`. `Table.move`
  is the only way a disk changes place, so a disk can't be in two places at once.
- **The rules live in `Game`, and the move kinds are defined once, in `Action`.**
  `Table` handles state and nothing else. `Game.step` is the only place where an
  action becomes a table move.
- **The engine doesn't track whose turn it is.** Every `step(side, action)`
  names the acting side. Turn order comes from the caller, in any pattern.
- **Players choose; they don't execute.** A `Player` gets its view and the legal
  actions, and returns an action. The caller passes it to `Game.step`. Human,
  replay, random and future RL players all fit this one interface.

### Using the engine as an agent would

Every frontend drives the engine the same way, and an outside agent would too:

```python
from engine import Game, Side, action_space

game = Game(3)
view = game.observe(Side.A)           # only what A may see
legal = game.legal_actions(Side.A)    # or game.legal_mask(Side.A) for RL
result = game.step(Side.A, legal[0])  # StepResult(legal, reason, winner)
```

- `observe(side)` returns an `Observation`: the side's poles under its own names
  (`"1"`, `"2"` shared, `"3"`), its hand, N and the winner. The other side's
  private poles and hand are never included. The interactive CLI draws the
  board from this view only.
- `step` returns a `StepResult` with whether the move was legal, the reason if
  it wasn't (e.g. `"disk 3 cannot go on smaller disk 1"`) and the winner.

### Reuse: RL training and an online service

The brief asks that the engine work unchanged as the core of an RL loop or a
service running many games. Neither is built here, but the engine already has
what they need:

- **RL.** `action_space(side)` gives 7 numbered actions (skip, lift 1-3, place
  1-3) named from the side's own view, so number *i* means the same move for A
  and B, and one policy can play either side. `legal_mask(side)` gives the
  matching legal flags. `observe` gives the hidden-information observation.
  `StepResult` gives the reason for an illegal move (to penalise it) and the
  winner (for the reward).
- **Many games at once.** A `Game` holds all of its own state, with no globals
  and no randomness. Any number of games can exist side by side.
  `Game.to_dict()` / `Game.from_dict()` save and restore a full game as JSON,
  for storage, restarts or sending over the network. Loading rejects states that
  could not happen in a real game. A single `Game` isn't thread-safe, so a
  service should handle one request at a time per game.

## Rule interpretations

Where the brief left room, these are the decisions:

1. **Either player may take the other's disks.** Any top disk on the shared pole
   can be lifted and carried to your own poles. Stealing and blocking are part
   of the game.
2. **Win condition (taken literally from the brief).** A side wins when its hand
   is empty, its pole 1 and the shared pole 2 are empty, and its pole 3 has at
   least one disk.
   - Whose disks are on pole 3 does not matter. You can win with the opponent's
     disk in your stack.
   - Any disk on the shared pole, from either side, blocks both sides.
   - If the opponent has carried off one of your disks, you can win without it.
   - A side with no disks left can never win, because its pole 3 must have one.
   - The alternative, "all of my own disks on pole 3", was rejected: one stolen
     disk would block a player for ever.
3. **Stacks are always ordered.** The placement rule (only onto an empty pole or
   a strictly larger disk) means every tower is always largest-at-the-bottom,
   so the win check doesn't need to check order.
4. **Wins are checked for both sides after every legal move,** the mover first.
   A side can win on the opponent's turn, e.g. when the opponent lifts their own
   disk off the shared pole. One move can't create two winners: any move that
   could complete the other side's win (lifting from the shared pole) fills the
   mover's hand.
5. **Illegal actions change nothing and use up the turn,** as the brief says. The
   step result says why the action was illegal.
6. **After a win the game is over.** Every later action is rejected with "the
   game is over". Skip is otherwise always legal.

## Frontends

### Replay

```bash
uv run replay.py examples/brief.json     # or - to read from stdin
```

Input:

```json
{
  "n": 1,
  "turns": ["A", "B", "A"],
  "moves": {"A": ["lift 1", "place 3"], "B": ["lift 1"]}
}
```

- `turns` says who acts on each step, in any order.
- `moves` lists each side's moves in order. Poles are named from that side's
  view (`1`, `2` shared, `3`), so `lift 1` is 1a for A and 1b for B.
- Each turn uses the acting side's next move. A side with no moves left skips.
- Recorded illegal moves are still played: the engine rejects them and the turn
  is wasted.
- Turns after a win are not played and are counted as ignored.
- A malformed file or move (e.g. `lfit 2`) prints `error: ...` and exits with
  status 1. Moves are checked before the game starts.

Output (JSON):
- `winner`, `turns_played` and `turns_ignored`;
- a `log` with each turn's side, move (board pole names), `legal` and `reason`;
- a `final` section with every pole and both hands.

The replay knows everything, so it shows both sides' private poles.

Examples: `examples/brief.json` is the example from the brief.
`examples/steal.json` has A take B's disk, waste one illegal move and win with
`[2, 1]` on 3a.

### Random play

```bash
uv run random_play.py --n 3 --seed 7 [--order alternate|random] [--max-turns 10000] [--no-log]
```

- Both sides are `RandomPlayer`s that pick uniformly among the legal actions,
  including skip.
- **Turn order** is made by the frontend, not the engine: `alternate` (A, B, A, ...)
  or `random` (a random side every turn).
- **One seed decides the whole game** and is printed in the output. Without
  `--seed`, a random one is chosen and printed, so any game can be re-run.
- Random games can be long, so `--max-turns` stops a game; it then has no
  winner. From 200 games per size: about 13 turns on average for N=1, 50 for
  N=2, 210 for N=3 and 820 for N=4.
- The output has the same shape as the replay's, plus `seed`, `n` and `order`.

### Interactive CLI

```bash
uv run cli.py --n 3 [--seed 7]
```

You play A against a random B, taking turns A, B, A, ... The board shows only
A's view, drawn as towers with Rich: your disks are blue and B's are orange.
You pick moves with the arrow keys using questionary. B's moves aren't
described, because they may be on poles you can't see; you only see their
effect on the shared pole.

## Tests

```bash
uv run pytest
```

102 tests:
- `tests/test_engine.py` tests the engine directly, one group per class:
  setup, every legal/illegal rule and its reason, wins (including on the
  opponent's turn and with a stolen disk), `observe` hiding private
  information, the action space and mask, and save/load.
- `tests/test_replay.py` and `tests/test_random_play.py` cover the frontends.

## Development process and AI use

The work was done step by step, with a git commit per step. Read `git log` from
the bottom up to follow it:

1. The data model: `Disk` and `Board`, then splitting hands into `Table`.
2. `Player` and `Game`; removing move kinds that had been repeated at several
   levels.
3. Unit tests, then the interactive CLI (plain at first, then Rich +
   questionary), the random player, replay and random play.
4. The reuse features, one commit each: `observe`, players receiving their view,
   `StepResult`, the numbered action space and mask, and save/load.

**AI tools used:** Claude Code (Anthropic's terminal coding agent, using the
Claude Opus 5.5 model).

- **Who decided what.** I set the design and the order of the work, one piece at
  a time. For example: storing disk positions only in the towers and hands,
  separating `Board` from `Table`, removing repeated move-kind abstractions, and
  building the CLI before the random player.
- **What Claude Code did.** It wrote the code, tests and this README from those
  instructions, ran the tests, and simulated games to check behaviour.
- **What I did with its output.** I reviewed each step before committing. I
  often asked for less than it first produced. I also checked the rules myself,
  e.g. playing the CLI to confirm the win condition and how B uses the shared
  pole.

## Limitations

- The engine is built for exactly two sides (A and B), as the brief describes.
- No RL environment wrapper or server is included; the brief asks for neither.
- Random players skip often, because skip is always legal, so random games run
  long.
