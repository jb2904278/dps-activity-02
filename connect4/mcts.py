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
    # All the settings of the search in one object (filled in from the command line by play.py).
    cycles: int = 1000            # number of select/expand/simulate/back-propagate rounds
    expand_k: int = 7             # x: maximum children per node (7 = every legal column)
    max_depth: int = 42           # height of the tree; deeper positions are only simulated
    c: float = math.sqrt(2)       # exploration weight (playout part)
    w: float = 0.5                # objective weight (heuristic part)
    expansion_order: str = "heuristic"   # "heuristic" or "random"
    seed: Optional[int] = None    # fix for reproducible runs


@dataclass(eq=False)
class Node:
    # One box in the search tree = one board position.
    state: object                 # the board at this node
    parent: Optional["Node"] = None   # the node above (None for the root)
    move: Optional[int] = None    # the column played to get here from the parent
    depth: int = 0                # 0 = root, 1 = after one move, ...
    U: float = 0.0                # total utility of playouts through this node
    N: int = 0                    # number of playouts through this node
    objective: float = 0.0        # EVAL for the player who made `move`
    children: list = field(default_factory=list)   # nodes already added below this one
    untried: list = field(default_factory=list)    # the "to-do list": moves not expanded yet


class MCTS:
    def __init__(self, config=None, game=None):
        self.config = config or MCTSConfig()        # the settings (defaults if none given)
        self.game = game or ConnectFour()           # the game rules
        self.rng = random.Random(self.config.seed)  # ONE random generator, made from the seed;
                                                    # every random choice below comes from it


    def search(self, state):
        """Return the chosen column for `state`."""
        # Same search, but only return the move (used when playing against a human).
        return self.search_with_stats(state)["move"]

    def search_with_stats(self, state):
        """Run MCTS and return the move plus the statistics of every root child."""
        if self.game.is_terminal(state):
            raise ValueError("The game is already over")
        tree = self._make_node(state, None, None, 0)       # the root = the current board
        for _ in range(self.config.cycles):           # IS-TIME-REMAINING()
            leaf = self.select(tree)                  # 1. SELECT: walk down to a leaf
            child = self.expand(leaf)                 # 2. EXPAND: add one new child
            result = self.simulate(child)             # 3. SIMULATE: random game -> winner
            self.back_propagate(result, child)        # 4. BACK-PROPAGATE: update N and U
        best = max(tree.children, key=lambda n: (n.N, n.U))   # most playouts
        # Package the answer plus statistics for printing.
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
        # Keep going down only while this node has NO untried moves left (fully expanded),
        # has children, is above the height limit, and the game is not over.
        while (not node.untried and node.children
               and node.depth < self.config.max_depth
               and not self.game.is_terminal(node.state)):
            # go to the child with the highest utility (see utility() below)
            node = max(node.children, key=lambda ch: self.utility(ch, node))
        return node                                   # the leaf where we stopped

    def expand(self, leaf):
        """Add one new child (one of the x chosen moves), or return the leaf if it can't grow."""
        # Can't grow if the game is over, we are at the height limit, or the to-do list is empty.
        if (self.game.is_terminal(leaf.state) or leaf.depth >= self.config.max_depth
                or not leaf.untried):
            return leaf
        move = leaf.untried.pop(0)                    # take the FIRST move off the to-do list
        # play that move and make a node for the new board, one level deeper
        child = self._make_node(self.game.result(leaf.state, move), leaf, move, leaf.depth + 1)
        leaf.children.append(child)                   # attach it to the tree
        return child

    def simulate(self, node):
        """Random playout policy from the node's position. Returns the winner (or None)."""
        # Both sides play random columns (from self.rng, i.e. the seed) until the game ends.
        return play_random_game(node.state, self.rng)

    def back_propagate(self, result, node):
        """Credit every node on the path from the player's point of view who moved into it."""
        while node is not None:                       # from the new node up to the root
            node.N += 1                               # one more playout went through here
            mover = other(node.state.to_move)          # player who made node.move
            if result is None:                        # draw: half a point
                node.U += 0.5
            elif result == mover:                     # the mover won: a full point
                node.U += 1.0
            node = node.parent                        # step up one level

    # ------------------------------------------------------------------ #
    # Utility used by SELECT: playout part + objective part
    # ------------------------------------------------------------------ #
    def utility(self, child, parent):
        # utility = U/N + c * sqrt(ln N(parent) / N) + w * EVAL
        if child.N == 0:
            return math.inf                           # never visited: try it first
        cfg = self.config
        exploit = child.U / child.N                   # win rate so far (playout part)
        explore = cfg.c * math.sqrt(math.log(parent.N) / child.N)   # bonus for rarely visited children
        return exploit + explore + cfg.w * child.objective           # + heuristic (objective part)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _make_node(self, state, parent, move, depth):
        # Heuristic score of this board for the player who just moved (the root gets 0).
        objective = evaluate(state, other(state.to_move)) if parent is not None else 0.0 # when parent is NONE it returns 0.0
        node = Node(state, parent, move, depth, objective=objective)
        # Give the node a to-do list, unless the game is over or it's at the height limit.
        if not self.game.is_terminal(state) and depth < self.config.max_depth:
            node.untried = self._choose_moves(state)
        return node

    def _choose_moves(self, state):
        """The x moves this node may expand, in the order they will be expanded."""
        moves = self.game.actions(state)              # all legal columns
        k = max(1, self.config.expand_k)              # x (at least 1)
        if self.config.expansion_order == "random":   # random order: shuffle, keep x
            self.rng.shuffle(moves)
            return moves[:k]
        me = state.to_move                            # score moves from this player's view
        # For each column: (heuristic score after playing it, random tie-breaker, column)
        scored = [(evaluate(self.game.result(state, m), me), self.rng.random(), m) for m in moves]  # self.game.result(state, 0): drops X into column 0 and returns a new board
        # evaluate(that board, "X"): scores it for X. Raw 8, so tanh(8/60) = 0.133. 
        # self.rng.random(): a random float like 0.42. Used only when scores are equal.
        # m: the column number (e.g. 0, 1, 2, ...). Used to remember which move this score came from.
        # The list is sorted from highest total score (0.133 + 0.42) downwards, so the best move comes first.

        """
        The heuristic function (evaluate) gives a number for how good a board is for a player.
        It is called for each move, and the move that gives the best score is chosen.
        The random part is used to break ties between moves that have the same heuristic score. 
        The move is the actual column number that will be played. 

        For example, if the heuristic function evaluates the board after a move and gives it a 
        score of 0.8, it means that the move is good for the player who made it.

        [(0.133, 0.134, 0),
        (0.322, 0.847, 1),
        (0.067, 0.764, 2),
        (0.149, 0.255, 3),
        (0.366, 0.495, 4),
        (0.181, 0.449, 5),
        (-0.017, 0.652, 6)]
        
        """
        scored.sort(reverse=True)                     # best score first

        """
        [(0.366, 0.495, 4),
        (0.322, 0.847, 1),
        (0.181, 0.449, 5),
        (0.149, 0.255, 3),
        (0.133, 0.134, 0),
        (0.067, 0.764, 2),
        (-0.017, 0.652, 6)]
        
        The heuristic scores are sorted in descending order, so the move with the
        highest heuristic score comes first. 
        """
        return [m for _, _, m in scored[:k]]          # keep the top x columns

    def _count(self, node):
        # Number of nodes in the tree: this node plus everything below it.
        return 1 + sum(self._count(ch) for ch in node.children)


def random_move(game, state, rng=random):
    """Baseline opponent: a uniformly random legal column."""
    return rng.choice(game.actions(state))
