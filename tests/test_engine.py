"""Unit tests for the engine, one group per class."""

import dataclasses

import pytest

from engine import (
    VISIBLE,
    Action,
    Board,
    Disk,
    Game,
    Kind,
    Player,
    Pole,
    Side,
    Table,
    action_space,
)
from players import RandomPlayer


class TestDisk:
    """`Disk` is an immutable size with a derived owner."""

    def test_odd_sizes_belong_to_a(self):
        """Odd disks start with side A."""
        assert Disk(1).owner is Side.A
        assert Disk(5).owner is Side.A

    def test_even_sizes_belong_to_b(self):
        """Even disks start with side B."""
        assert Disk(2).owner is Side.B
        assert Disk(6).owner is Side.B

    def test_equal_by_size(self):
        """Two disks of the same size are the same disk."""
        assert Disk(3) == Disk(3)
        assert Disk(3) != Disk(4)

    def test_immutable(self):
        """A disk's size cannot be changed."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            Disk(1).size = 2


class TestBoard:
    """`Board` keeps one stack per pole."""

    def test_starts_empty(self):
        """A new board has an empty tower for every pole."""
        board = Board()
        assert set(board.towers) == set(Pole)
        assert all(tower == [] for tower in board.towers.values())

    def test_push_and_top(self):
        """The last disk pushed is the top."""
        board = Board()
        board.push(Pole.A1, Disk(3))
        board.push(Pole.A1, Disk(1))
        assert board.top(Pole.A1) == Disk(1)
        assert board.towers[Pole.A1] == [Disk(3), Disk(1)]

    def test_top_of_empty_pole_is_none(self):
        """An empty pole has no top disk."""
        assert Board().top(Pole.SHARED) is None

    def test_pop_removes_top(self):
        """Popping returns the top disk and leaves the rest."""
        board = Board()
        board.push(Pole.B1, Disk(4))
        board.push(Pole.B1, Disk(2))
        assert board.pop(Pole.B1) == Disk(2)
        assert board.towers[Pole.B1] == [Disk(4)]

    def test_boards_do_not_share_towers(self):
        """Each board gets its own towers."""
        first, second = Board(), Board()
        first.push(Pole.A1, Disk(1))
        assert second.top(Pole.A1) is None


class TestTable:
    """`Table` holds towers and hands and moves disks between them."""

    def test_hands_start_empty(self):
        """Neither side holds a disk at first."""
        assert Table().hands == {Side.A: None, Side.B: None}

    def test_move_pole_to_hand(self):
        """Moving from a pole to a side puts the top disk in that hand."""
        table = Table()
        table.board.push(Pole.A1, Disk(1))
        table.move(Pole.A1, Side.A)
        assert table.hands[Side.A] == Disk(1)
        assert table.board.top(Pole.A1) is None

    def test_move_hand_to_pole(self):
        """Moving from a side to a pole empties the hand onto the pole."""
        table = Table()
        table.hands[Side.B] = Disk(2)
        table.move(Side.B, Pole.SHARED)
        assert table.hands[Side.B] is None
        assert table.board.top(Pole.SHARED) == Disk(2)

    def test_move_does_not_check_rules(self):
        """The table moves a big disk onto a small one; rules are the game's job."""
        table = Table()
        table.board.push(Pole.A3, Disk(1))
        table.hands[Side.A] = Disk(3)
        table.move(Side.A, Pole.A3)
        assert table.board.towers[Pole.A3] == [Disk(1), Disk(3)]

    def test_where_on_pole(self):
        """`where` finds a disk on a tower."""
        table = Table()
        table.board.push(Pole.B3, Disk(2))
        assert table.where(Disk(2)) is Pole.B3

    def test_where_in_hand(self):
        """`where` finds a disk held by either side, including the other side's disk."""
        table = Table()
        table.hands[Side.A] = Disk(2)
        assert table.where(Disk(2)) is Side.A

    def test_where_missing_disk(self):
        """`where` raises for a disk that is not on the table."""
        with pytest.raises(KeyError):
            Table().where(Disk(7))


class TestAction:
    """`Action` is a move as a value."""

    def test_skip_has_no_pole(self):
        """Skip defaults to no target pole."""
        assert Action(Kind.SKIP).pole is None

    def test_equal_by_value(self):
        """Actions with the same kind and pole are equal and hashable."""
        assert Action(Kind.LIFT, Pole.A1) == Action(Kind.LIFT, Pole.A1)
        assert len({Action(Kind.LIFT, Pole.A1), Action(Kind.LIFT, Pole.A1)}) == 1

    def test_immutable(self):
        """An action cannot be changed after creation."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            Action(Kind.SKIP).pole = Pole.A1


def lift(pole: Pole) -> Action:
    """Shorthand for a lift action."""
    return Action(Kind.LIFT, pole)


def place(pole: Pole) -> Action:
    """Shorthand for a place action."""
    return Action(Kind.PLACE, pole)


SKIP = Action(Kind.SKIP)


class TestActionSpace:
    """`action_space` numbers the actions the same way for both sides."""

    def test_seven_actions_in_fixed_order(self):
        """Skip, then lift 1-3, then place 1-3, with poles from A's view."""
        assert action_space(Side.A) == (
            SKIP,
            lift(Pole.A1), lift(Pole.SHARED), lift(Pole.A3),
            place(Pole.A1), place(Pole.SHARED), place(Pole.A3),
        )

    def test_same_number_same_move_for_both_sides(self):
        """Number 1 is "lift from my pole 1" for A and for B."""
        assert action_space(Side.A)[1] == lift(Pole.A1)
        assert action_space(Side.B)[1] == lift(Pole.B1)
        assert action_space(Side.A)[5] == action_space(Side.B)[5] == place(Pole.SHARED)


class TestGameSetup:
    """`Game.__init__` builds the starting table."""

    def test_disks_on_pole_one_largest_at_bottom(self):
        """A gets the odd disks on 1a, B the even disks on 1b."""
        game = Game(3)
        assert game.table.board.towers[Pole.A1] == [Disk(5), Disk(3), Disk(1)]
        assert game.table.board.towers[Pole.B1] == [Disk(6), Disk(4), Disk(2)]

    def test_everything_else_empty(self):
        """Other poles and both hands start empty, and nobody has won."""
        game = Game(2)
        for pole in (Pole.A3, Pole.SHARED, Pole.B3):
            assert game.table.board.top(pole) is None
        assert game.table.hands == {Side.A: None, Side.B: None}
        assert game.winner is None


class TestGameLegality:
    """`Game.is_legal` and `Game.legal_actions` apply the rules."""

    def test_opening_moves(self):
        """At the start a side can only skip or lift from its own pole 1."""
        game = Game(2)
        assert game.legal_actions(Side.A) == [SKIP, lift(Pole.A1)]
        assert game.legal_actions(Side.B) == [SKIP, lift(Pole.B1)]

    def test_cannot_touch_other_sides_poles(self):
        """A side cannot lift from or place on the other side's private poles."""
        game = Game(1)
        assert not game.is_legal(Side.A, lift(Pole.B1))
        game.step(Side.A, lift(Pole.A1))
        assert not game.is_legal(Side.A, place(Pole.B3))

    def test_cannot_lift_with_full_hand(self):
        """A side holding a disk cannot lift another."""
        game = Game(2)
        game.step(Side.A, lift(Pole.A1))
        assert not game.is_legal(Side.A, lift(Pole.A1))

    def test_cannot_lift_from_empty_pole(self):
        """Lifting needs a disk on the pole."""
        assert not Game(1).is_legal(Side.A, lift(Pole.A3))

    def test_cannot_place_with_empty_hand(self):
        """Placing needs a held disk."""
        assert not Game(1).is_legal(Side.A, place(Pole.A3))

    def test_cannot_place_on_smaller_disk(self):
        """A disk may only go on an empty pole or a larger disk."""
        game = Game(2)
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        game.step(Side.A, lift(Pole.A1))
        assert not game.is_legal(Side.A, place(Pole.A3))
        assert game.is_legal(Side.A, place(Pole.SHARED))

    def test_can_place_on_larger_disk(self):
        """A smaller disk may go on a larger one, including the other side's."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        game.step(Side.B, place(Pole.SHARED))
        game.step(Side.A, lift(Pole.A1))
        assert game.is_legal(Side.A, place(Pole.SHARED))

    def test_nothing_legal_after_win(self):
        """Once someone has won, no action is legal, not even skip."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        assert game.winner is Side.A
        assert game.legal_actions(Side.A) == []
        assert game.legal_actions(Side.B) == []

    def test_mask_matches_legal_actions(self):
        """The mask flags exactly the actions `legal_actions` lists."""
        game = Game(2)
        assert game.legal_mask(Side.A) == [True, True, False, False, False, False, False]
        game.step(Side.A, lift(Pole.A1))
        for side in Side:
            space = action_space(side)
            flagged = [a for a, ok in zip(space, game.legal_mask(side)) if ok]
            assert flagged == game.legal_actions(side)

    def test_mask_all_false_after_win(self):
        """Once the game is over, nothing is flagged."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        assert not any(game.legal_mask(Side.B))

    def test_legal_actions_are_all_legal(self):
        """Every action listed by `legal_actions` passes `is_legal`."""
        game = Game(2)
        game.step(Side.A, lift(Pole.A1))
        for action in game.legal_actions(Side.A):
            assert game.is_legal(Side.A, action)


class TestGameStep:
    """`Game.step` applies legal actions and detects wins."""

    def test_illegal_action_changes_nothing(self):
        """An illegal action returns False and leaves the table as it was."""
        game = Game(2)
        before = {pole: list(tower) for pole, tower in game.table.board.towers.items()}
        assert game.step(Side.A, place(Pole.A3)).legal is False
        assert game.table.board.towers == before
        assert game.table.hands == {Side.A: None, Side.B: None}

    def test_skip_changes_nothing(self):
        """Skip is legal and leaves the table as it was."""
        game = Game(1)
        assert game.step(Side.B, SKIP).legal is True
        assert game.table.board.top(Pole.B1) == Disk(2)

    def test_example_from_brief(self):
        """N=1, turns A, B, A: A wins while B still holds disk 2."""
        game = Game(1)
        assert game.step(Side.A, lift(Pole.A1)).legal
        assert game.step(Side.B, lift(Pole.B1)).legal
        assert game.step(Side.A, place(Pole.A3)).legal
        assert game.winner is Side.A
        assert game.table.hands[Side.B] == Disk(2)

    def test_no_win_while_shared_pole_has_disks(self):
        """A disk left on the shared pole blocks a win."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        game.step(Side.B, place(Pole.SHARED))
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        assert game.winner is None

    def test_win_on_other_sides_turn(self):
        """B lifting its disk off the shared pole completes A's win."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        game.step(Side.B, place(Pole.SHARED))
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        game.step(Side.B, lift(Pole.SHARED))
        assert game.winner is Side.A

    def test_win_with_stolen_disk(self):
        """A side can win with the other side's disk on its pole 3."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        game.step(Side.B, place(Pole.SHARED))
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        game.step(Side.A, lift(Pole.SHARED))
        assert game.winner is None
        game.step(Side.A, place(Pole.A1))
        assert game.winner is None
        game.step(Side.A, lift(Pole.A3))
        game.step(Side.A, place(Pole.SHARED))
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        game.step(Side.A, lift(Pole.SHARED))
        game.step(Side.A, place(Pole.A3))
        assert game.table.board.towers[Pole.A3] == [Disk(2), Disk(1)]
        assert game.winner is Side.A

    def test_step_after_win_is_rejected(self):
        """After a win every step returns False."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        result = game.step(Side.B, SKIP)
        assert result.legal is False
        assert result.reason == "the game is over"
        assert result.winner is Side.A

    def test_full_game_n2(self):
        """A plays the standard 3-move solution for two disks and wins."""
        game = Game(2)
        moves = [
            lift(Pole.A1), place(Pole.SHARED),
            lift(Pole.A1), place(Pole.A3),
            lift(Pole.SHARED), place(Pole.A3),
        ]
        for action in moves:
            assert game.step(Side.A, action).legal
        assert game.table.board.towers[Pole.A3] == [Disk(3), Disk(1)]
        assert game.winner is Side.A


class TestGameStepResult:
    """`Game.step` explains what happened."""

    def test_legal_step(self):
        """A legal step has no reason and reports no winner mid-game."""
        result = Game(2).step(Side.A, lift(Pole.A1))
        assert (result.legal, result.reason, result.winner) == (True, None, None)

    def test_winning_step_reports_winner(self):
        """The step that wins carries the winner."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        assert game.step(Side.A, place(Pole.A3)).winner is Side.A

    @pytest.mark.parametrize(
        ("setup", "action", "reason"),
        [
            ([], lift(Pole.B1), "pole 1b is not visible to A"),
            ([], lift(Pole.A3), "pole 3a is empty"),
            ([], place(Pole.A3), "hand is empty"),
            ([lift(Pole.A1)], lift(Pole.A1), "hand already holds disk 1"),
            (
                [lift(Pole.A1), place(Pole.A3), lift(Pole.A1)],
                place(Pole.A3),
                "disk 3 cannot go on smaller disk 1",
            ),
        ],
    )
    def test_illegal_reasons(self, setup, action, reason):
        """Each broken rule gives its own reason."""
        game = Game(2)
        for earlier in setup:
            assert game.step(Side.A, earlier).legal
        result = game.step(Side.A, action)
        assert result.legal is False
        assert result.reason == reason


class TestGameHasWon:
    """`Game.has_won` checks one side's win condition."""

    def test_not_won_at_start(self):
        """Neither side has won before any move."""
        game = Game(1)
        assert not game.has_won(Side.A)
        assert not game.has_won(Side.B)

    def test_needs_disks_on_pole_three(self):
        """With every visible pole empty, a side has not won."""
        game = Game(1)
        game.table.move(Pole.A1, Side.B)
        assert game.table.hands[Side.B] == Disk(1)
        game.table.move(Side.B, Pole.B3)
        assert not game.has_won(Side.A)

    def test_needs_empty_hand(self):
        """Holding a disk prevents a win."""
        game = Game(2)
        game.table.move(Pole.A1, Pole.A3)
        game.table.move(Pole.A1, Side.A)
        assert not game.has_won(Side.A)


class TestGameObserve:
    """`Game.observe` shows a side only what it may see."""

    def test_start(self):
        """At the start a side sees its own disks on pole 1 and nothing else."""
        view = Game(2).observe(Side.B)
        assert view.side is Side.B
        assert view.n == 2
        assert view.poles == {"1": (4, 2), "2": (), "3": ()}
        assert view.hand is None
        assert view.winner is None

    def test_poles_named_from_own_view(self):
        """Each side calls its own poles 1 and 3, and the shared pole 2."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        game.step(Side.A, place(Pole.A3))
        assert game.observe(Side.A).poles["3"] == (1,)
        assert game.observe(Side.B).poles["3"] == ()

    def test_hides_other_sides_private_poles_and_hand(self):
        """B's private poles and hand never show up in A's view."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        view = game.observe(Side.A)
        assert set(view.poles) == {"1", "2", "3"}
        assert all(2 not in tower for tower in view.poles.values())
        assert view.hand is None

    def test_shared_pole_seen_by_both(self):
        """A disk on the shared pole shows up in both views."""
        game = Game(1)
        game.step(Side.B, lift(Pole.B1))
        game.step(Side.B, place(Pole.SHARED))
        assert game.observe(Side.A).poles["2"] == (2,)
        assert game.observe(Side.B).poles["2"] == (2,)

    def test_shows_hand_and_winner(self):
        """The view includes the side's own held disk and the winner."""
        game = Game(1)
        game.step(Side.A, lift(Pole.A1))
        assert game.observe(Side.A).hand == 1
        game.step(Side.A, place(Pole.A3))
        assert game.observe(Side.B).winner is Side.A


class TestPlayer:
    """`Player` is the interface for choosing an action."""

    def test_base_choose_not_implemented(self):
        """The base class has no strategy of its own."""
        with pytest.raises(NotImplementedError):
            Player(Side.A).choose(Game(1).observe(Side.A), [SKIP])

    def test_subclass_drives_a_game(self):
        """A subclass gets the view and legal actions, and the caller steps the game."""

        class LastLegal(Player):
            """Always picks the last legal action."""

            def choose(self, view, legal):
                """Pick the last legal action."""
                assert view.side is self.side
                return legal[-1]

        game = Game(1)
        player = LastLegal(Side.A)
        action = player.choose(game.observe(player.side), game.legal_actions(player.side))
        assert action == lift(Pole.A1)
        assert game.step(player.side, action).legal
        assert game.table.hands[Side.A] == Disk(1)


def test_visible_poles():
    """Each side sees its own poles 1 and 3 plus the shared pole, in that order."""
    assert VISIBLE[Side.A] == (Pole.A1, Pole.SHARED, Pole.A3)
    assert VISIBLE[Side.B] == (Pole.B1, Pole.SHARED, Pole.B3)


class TestRandomPlayer:
    """`RandomPlayer` picks among the legal actions."""

    def test_always_picks_a_legal_action(self):
        """Every pick is one of the actions offered."""
        game = Game(2)
        player = RandomPlayer(Side.B, seed=0)
        for _ in range(200):
            legal = game.legal_actions(Side.B)
            if not legal:
                break
            action = player.choose(game.observe(Side.B), legal)
            assert action in legal
            game.step(Side.B, action)

    def test_same_seed_same_choices(self):
        """Two players with the same seed make the same picks."""
        game = Game(1)
        view, legal = game.observe(Side.A), game.legal_actions(Side.A)
        first, second = RandomPlayer(Side.A, seed=7), RandomPlayer(Side.A, seed=7)
        picks = [first.choose(view, legal) for _ in range(20)]
        assert picks == [second.choose(view, legal) for _ in range(20)]
