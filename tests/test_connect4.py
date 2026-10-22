import random
import unittest
from dataclasses import replace

from connect4.game import ConnectFour, O, X, from_rows, play_random_game
from connect4.heuristic import evaluate
from connect4.mcts import MCTS, MCTSConfig
from connect4.positions import POSITIONS, load


class TestGame(unittest.TestCase):
    def setUp(self):
        self.g = ConnectFour()

    def test_initial(self):
        s = self.g.initial
        self.assertEqual(self.g.actions(s), list(range(7)))
        self.assertEqual(self.g.to_move(s), X)
        self.assertFalse(self.g.is_terminal(s))

    def test_pieces_stack_and_turns_alternate(self):
        s = self.g.result(self.g.initial, 3)
        s = self.g.result(s, 3)
        self.assertEqual(s.cols[3], "XO")
        self.assertEqual(s.to_move, X)

    def test_full_column_is_not_legal(self):
        s = self.g.initial
        for _ in range(6):
            s = self.g.result(s, 0)
        self.assertNotIn(0, self.g.actions(s))
        with self.assertRaises(ValueError):
            self.g.result(s, 0)

    def test_wins_in_every_direction(self):
        boards = {
            "horizontal": [".......", ".......", ".......", ".......", "OOO....", "XXXX..."],
            "vertical":   [".......", ".......", "X......", "X......", "XO.....", "XOO...."],
            "diagonal /": [".......", ".......", "...X...", "..XO...", ".XOO...", "XOOX.X."],
            "diagonal \\": [".......", ".......", "X......", "OX.....", "OOX....", "XOOX.X."],
        }
        for name, rows in boards.items():
            with self.subTest(direction=name):
                s = from_rows(rows)
                self.assertEqual(s.winner, X)
                self.assertTrue(self.g.is_terminal(s))
                self.assertEqual(self.g.utility(s, X), 1)
                self.assertEqual(self.g.utility(s, O), -1)

    def test_from_rows_rejects_bad_counts(self):
        with self.assertRaises(ValueError):
            from_rows([".......", ".......", ".......", ".......", ".......", "OO....."])

    def test_random_playout_always_finishes(self):
        rng = random.Random(0)
        for _ in range(200):
            self.assertIn(play_random_game(self.g.initial, rng), (X, O, None))


class TestHeuristic(unittest.TestCase):
    def test_range_and_terminal_values(self):
        s = load("must_block")
        self.assertTrue(-1 <= evaluate(s, X) <= 1)
        won = ConnectFour().result(load("win_in_1"), 3)
        self.assertEqual(evaluate(won, X), 1.0)
        self.assertEqual(evaluate(won, O), -1.0)

    def test_blocking_scores_higher_than_not_blocking(self):
        g, s = ConnectFour(), load("must_block")
        self.assertGreater(evaluate(g.result(s, 3), X), evaluate(g.result(s, 6), X))

    def test_centre_is_preferred_on_empty_board(self):
        g = ConnectFour()
        scores = [evaluate(g.result(g.initial, c), X) for c in range(7)]
        self.assertEqual(scores.index(max(scores)), 3)


class TestMCTS(unittest.TestCase):
    def test_tactical_positions_default_settings(self):
        for name in ("win_in_1", "must_block", "double_threat"):
            with self.subTest(position=name):
                move = MCTS(MCTSConfig(cycles=600, seed=1)).search(load(name))
                self.assertIn(move, POSITIONS[name]["best"])

    def test_same_seed_same_move(self):
        cfg = MCTSConfig(cycles=150, seed=7)
        s = load("double_threat")
        self.assertEqual(MCTS(cfg).search(s), MCTS(cfg).search(s))

    def test_cycles_equal_root_playouts(self):
        stats = MCTS(MCTSConfig(cycles=300, seed=0)).search_with_stats(load("empty"))
        self.assertEqual(sum(c["N"] for c in stats["children"].values()), 300)

    def test_expansion_width_limits_children(self):
        stats = MCTS(MCTSConfig(cycles=300, expand_k=3, seed=0)).search_with_stats(load("empty"))
        self.assertEqual(len(stats["children"]), 3)

    def test_tree_height_limits_tree_size(self):
        # height 2, width 3: at most 1 + 3 + 9 nodes
        stats = MCTS(MCTSConfig(cycles=500, expand_k=3, max_depth=2, seed=0)).search_with_stats(load("empty"))
        self.assertLessEqual(stats["tree_size"], 13)

    def test_returns_legal_move(self):
        g = ConnectFour()
        for name in POSITIONS:
            with self.subTest(position=name):
                s = load(name)
                self.assertIn(MCTS(MCTSConfig(cycles=50, seed=3)).search(s), g.actions(s))

    def test_beats_random_player(self):
        g, rng = ConnectFour(), random.Random(0)
        bot = MCTS(MCTSConfig(cycles=200, seed=0))
        wins = 0
        for game_no in range(4):
            s = g.initial
            bot_side = X if game_no % 2 == 0 else O
            while not g.is_terminal(s):
                move = bot.search(s) if s.to_move == bot_side else rng.choice(g.actions(s))
                s = g.result(s, move)
            wins += s.winner == bot_side
        self.assertEqual(wins, 4)

    def test_terminal_state_raises(self):
        won = ConnectFour().result(load("win_in_1"), 3)
        with self.assertRaises(ValueError):
            MCTS().search(won)


if __name__ == "__main__":
    unittest.main()
