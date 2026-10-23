"""
Monte Carlo tree search move generator for Connect Four, following Figure 5.11 of the
textbook (AIMA 4e):

    function MONTE-CARLO-TREE-SEARCH(state) returns an action
        tree <- NODE(state)
        while IS-TIME-REMAINING() do
            leaf   <- SELECT(tree)
            child  <- EXPAND(leaf)
            result <- SIMULATE(child)
            BACK-PROPAGATE(result, child)
        return the move in ACTIONS(state) whose node has highest number of playouts

How each step meets the activity's requirements (all settings live in MCTSConfig):

  SELECT     Walks down the tree choosing the child with the highest utility:
                 utility(n) = U(n)/N(n)                                   playout part (win rate)
                            + c * sqrt(ln N(parent) / N(n))               playout part (exploration, UCB1)
                            + w * EVAL(n)                                 objective part (rules of the game)
             U and N are stored from previous playouts. EVAL is the heuristic in heuristic.py.
             Setting w = 0 gives plain UCT; c = 0 removes exploration.

  EXPAND     Each node may get at most `expand_k` (= x) children. They are the x best moves
             by EVAL ("heuristic") or x random moves ("random"). One new child is added per
             cycle until all x exist, so every level of the tree has at most x branches.

  SIMULATE   When the walk reaches the fixed tree height `max_depth` (or a node that still
             has unexpanded moves), the game is finished with a random playout policy.

  repeat     `cycles` iterations replace IS-TIME-REMAINING().
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from .game import ConnectFour, other, play_random_game
from .heuristic import evaluate


@dataclass
class MCTSConfig:
    cycles: int = 1000            # number of select/expand/simulate/back-propagate rounds
    expand_k: int = 7             # x: maximum children per node (7 = every legal column)
    max_depth: int = 42           # height of the tree; deeper positions are only simulated
    c: float = math.sqrt(2)       # exploration weight (playout part)
    w: float = 0.5                # objective weight (heuristic part)
    expansion_order: str = "heuristic"   # "heuristic" or "random"
    seed: Optional[int] = None    # fix for reproducible runs


@dataclass(eq=False)
class Node:
    state: object
    parent: Optional["Node"] = None
    move: Optional[int] = None
    depth: int = 0
    U: float = 0.0                # total utility of playouts through this node
    N: int = 0                    # number of playouts through this node
    objective: float = 0.0        # EVAL for the player who made `move`
    children: list = field(default_factory=list)
    untried: list = field(default_factory=list)


class MCTS:
    def __init__(self, config=None, game=None):
        self.config = config or MCTSConfig()
        self.game = game or ConnectFour()
        self.rng = random.Random(self.config.seed)


    def search(self, state):
        """Return the chosen column for `state`."""
        return self.search_with_stats(state)["move"]

    def search_with_stats(self, state):
        """Run MCTS and return the move plus the statistics of every root child."""
        if self.game.is_terminal(state):
            raise ValueError("The game is already over")
        tree = self._make_node(state, None, None, 0)
        for _ in range(self.config.cycles):           # IS-TIME-REMAINING()
            leaf = self.select(tree)
            child = self.expand(leaf)
            result = self.simulate(child)
            self.back_propagate(result, child)
        best = max(tree.children, key=lambda n: (n.N, n.U))   # most playouts
        return {
            "move": best.move,
            "children": {
                n.move: {"N": n.N, "win_rate": n.U / n.N if n.N else 0.0, "objective": n.objective}
                for n in sorted(tree.children, key=lambda n: n.move)
            },
            "tree_size": self._count(tree),
        }

    def select(self, node):
        """Go down while the node is fully expanded, not terminal and above the height limit."""
        while (not node.untried and node.children
               and node.depth < self.config.max_depth
               and not self.game.is_terminal(node.state)):
            node = max(node.children, key=lambda ch: self.utility(ch, node))
        return node

    def expand(self, leaf):
        """Add one new child (one of the x chosen moves), or return the leaf if it can't grow."""
        if (self.game.is_terminal(leaf.state) or leaf.depth >= self.config.max_depth
                or not leaf.untried):
            return leaf
        move = leaf.untried.pop(0)
        child = self._make_node(self.game.result(leaf.state, move), leaf, move, leaf.depth + 1)
        leaf.children.append(child)
        return child

    def simulate(self, node):
        """Random playout policy from the node's position. Returns the winner (or None)."""
        return play_random_game(node.state, self.rng)

    def back_propagate(self, result, node):
        """Credit every node on the path from the player's point of view who moved into it."""
        while node is not None:
            node.N += 1
            mover = other(node.state.to_move)          # player who made node.move
            if result is None:
                node.U += 0.5
            elif result == mover:
                node.U += 1.0
            node = node.parent

    # ------------------------------------------------------------------ #
    # Utility used by SELECT: playout part + objective part
    # ------------------------------------------------------------------ #
    def utility(self, child, parent):
        if child.N == 0:
            return math.inf
        cfg = self.config
        exploit = child.U / child.N
        explore = cfg.c * math.sqrt(math.log(parent.N) / child.N)
        return exploit + explore + cfg.w * child.objective

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _make_node(self, state, parent, move, depth):
        objective = evaluate(state, other(state.to_move)) if parent is not None else 0.0
        node = Node(state, parent, move, depth, objective=objective)
        if not self.game.is_terminal(state) and depth < self.config.max_depth:
            node.untried = self._choose_moves(state)
        return node

    def _choose_moves(self, state):
        """The x moves this node may expand, in the order they will be expanded."""
        moves = self.game.actions(state)
        k = max(1, self.config.expand_k)
        if self.config.expansion_order == "random":
            self.rng.shuffle(moves)
            return moves[:k]
        me = state.to_move
        scored = [(evaluate(self.game.result(state, m), me), self.rng.random(), m) for m in moves]
        scored.sort(reverse=True)
        return [m for _, _, m in scored[:k]]

    def _count(self, node):
        return 1 + sum(self._count(ch) for ch in node.children)


def random_move(game, state, rng=random):
    """Baseline opponent: a uniformly random legal column."""
    return rng.choice(game.actions(state))
