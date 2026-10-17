"""Tests for the replay frontend and the players it uses."""

import json

import pytest

from engine import Action, Kind, Pole, Side
from players import ReplayPlayer, parse_action
from replay import main, replay


class TestParseAction:
    """`parse_action` reads moves with poles named from the side's view."""

    def test_skip(self):
        """`skip` parses for either side."""
        assert parse_action("skip", Side.A) == Action(Kind.SKIP)

    def test_poles_are_relative_to_side(self):
        """Pole 1 is 1a for A and 1b for B; pole 2 is shared."""
        assert parse_action("lift 1", Side.A) == Action(Kind.LIFT, Pole.A1)
        assert parse_action("lift 1", Side.B) == Action(Kind.LIFT, Pole.B1)
        assert parse_action("place 2", Side.B) == Action(Kind.PLACE, Pole.SHARED)
        assert parse_action("  PLACE 3 ", Side.B) == Action(Kind.PLACE, Pole.B3)

    @pytest.mark.parametrize("text", ["", "jump 1", "lift", "lift 4", "skip 1", "lift 1a"])
    def test_rejects_bad_moves(self, text):
        """Anything other than lift/place 1-3 or skip is an error."""
        with pytest.raises(ValueError):
            parse_action(text, Side.A)


class TestReplayPlayer:
    """`ReplayPlayer` plays its recorded moves in order."""

    def test_plays_moves_then_skips(self):
        """After the recorded moves run out it skips."""
        player = ReplayPlayer(Side.A, ["lift 1", "place 3"])
        assert player.choose([]) == Action(Kind.LIFT, Pole.A1)
        assert player.choose([]) == Action(Kind.PLACE, Pole.A3)
        assert player.choose([]) == Action(Kind.SKIP)

    def test_bad_move_fails_up_front(self):
        """A typo is reported when the player is created."""
        with pytest.raises(ValueError):
            ReplayPlayer(Side.A, ["lift 1", "lfit 2"])


class TestReplay:
    """`replay` plays a record through the engine."""

    def test_example_from_brief(self):
        """N=1, turns A, B, A: A wins and B still holds disk 2."""
        result = replay({"n": 1, "turns": ["A", "B", "A"], "moves": {"A": ["lift 1", "place 3"], "B": ["lift 1"]}})
        assert result["winner"] == "A"
        assert result["final"]["poles"]["3a"] == [1]
        assert result["final"]["hands"] == {"A": None, "B": 2}
        assert [entry["move"] for entry in result["log"]] == ["lift 1a", "lift 1b", "place 3a"]

    def test_illegal_move_wastes_turn(self):
        """An illegal move is logged as illegal and uses up that move."""
        result = replay({"n": 1, "turns": ["A", "A", "A"], "moves": {"A": ["place 3", "lift 1", "place 3"]}})
        assert [entry["legal"] for entry in result["log"]] == [False, True, True]
        assert result["winner"] == "A"

    def test_side_without_moves_skips(self):
        """A side with no moves left skips its turns."""
        result = replay({"n": 1, "turns": ["B", "B"], "moves": {}})
        assert [entry["move"] for entry in result["log"]] == ["skip", "skip"]
        assert result["winner"] is None

    def test_turns_after_win_are_ignored(self):
        """Play stops at the win; the rest of the turns are counted as ignored."""
        result = replay({"n": 1, "turns": ["A", "A", "B", "B"], "moves": {"A": ["lift 1", "place 3"], "B": ["lift 1"]}})
        assert result["turns_played"] == 2
        assert result["turns_ignored"] == 2
        assert result["final"]["poles"]["1b"] == [2]

    def test_any_turn_order(self):
        """Turn order can be anything, such as one side acting many times in a row."""
        result = replay({"n": 2, "turns": ["A"] * 6, "moves": {"A": ["lift 1", "place 2", "lift 1", "place 3", "lift 2", "place 3"]}})
        assert result["winner"] == "A"
        assert result["final"]["poles"]["3a"] == [3, 1]

    @pytest.mark.parametrize(
        "record",
        [
            {"turns": []},
            {"n": 0, "turns": []},
            {"n": 1, "turns": ["C"]},
            {"n": 1, "turns": [], "moves": {"C": []}},
            {"n": 1, "turns": [], "moves": {"A": ["fly 1"]}},
        ],
    )
    def test_bad_records(self, record):
        """Malformed records raise ValueError."""
        with pytest.raises(ValueError):
            replay(record)


class TestReplayCli:
    """The `replay.py` command line."""

    def test_prints_json(self, tmp_path, capsys):
        """It reads a file and prints the result as JSON."""
        path = tmp_path / "game.json"
        path.write_text(json.dumps({"n": 1, "turns": ["A", "A"], "moves": {"A": ["lift 1", "place 3"]}}))
        main([str(path)])
        assert json.loads(capsys.readouterr().out)["winner"] == "A"

    def test_bad_input_exits_with_error(self, tmp_path, capsys):
        """Bad input prints an error and exits with status 1."""
        path = tmp_path / "game.json"
        path.write_text("{not json")
        with pytest.raises(SystemExit) as exit_info:
            main([str(path)])
        assert exit_info.value.code == 1
        assert capsys.readouterr().err.startswith("error:")
