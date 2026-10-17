"""Tests for the random-play frontend."""

import json
import random

from engine import Side
from random_play import main, random_game, turn_order


class TestTurnOrder:
    """`turn_order` makes the sequence of sides, outside the engine."""

    def test_alternate_starts_with_a(self):
        """Alternate order is A, B, A, B, ..."""
        assert list(turn_order("alternate", random.Random(0), 4)) == [Side.A, Side.B, Side.A, Side.B]

    def test_random_uses_both_sides(self):
        """Random order picks each side at some point and stops at the limit."""
        sides = list(turn_order("random", random.Random(0), 50))
        assert len(sides) == 50
        assert set(sides) == {Side.A, Side.B}


class TestRandomGame:
    """`random_game` plays both sides at random."""

    def test_same_seed_same_game(self):
        """A seed fully decides the game."""
        assert random_game(3, seed=42) == random_game(3, seed=42)
        assert random_game(3, seed=42, order="random") == random_game(3, seed=42, order="random")

    def test_every_move_is_legal(self):
        """Random players only pick legal actions."""
        for seed in range(20):
            assert all(entry["legal"] for entry in random_game(2, seed)["log"])

    def test_ends_with_win_or_turn_limit(self):
        """A game stops at a win, or at the turn limit with no winner."""
        for seed in range(20):
            result = random_game(3, seed, max_turns=50)
            assert result["winner"] is not None or result["turns_played"] == 50
            if result["winner"] is not None:
                assert result["turns_played"] <= 50

    def test_games_usually_finish(self):
        """With the default limit, small games end with a winner."""
        results = [random_game(2, seed) for seed in range(50)]
        assert all(result["winner"] in ("A", "B") for result in results)

    def test_final_state_holds_every_disk_once(self):
        """No disk is lost or duplicated."""
        final = random_game(3, seed=1, order="random")["final"]
        sizes = [s for tower in final["poles"].values() for s in tower]
        sizes += [s for s in final["hands"].values() if s is not None]
        assert sorted(sizes) == [1, 2, 3, 4, 5, 6]


class TestRandomPlayCli:
    """The `random_play.py` command line."""

    def test_prints_json_with_seed(self, capsys):
        """It prints the result, including the seed used."""
        main(["--n", "2", "--seed", "5", "--no-log"])
        result = json.loads(capsys.readouterr().out)
        assert result["seed"] == 5
        assert "log" not in result
        assert result["winner"] in ("A", "B", None)
