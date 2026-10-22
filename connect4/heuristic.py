"""
Objective part of the utility: a static evaluation of a Connect Four position that comes
from the rules of the game, not from playouts (AIMA 4e, Section 5.4 "Heuristic Alpha-Beta
Tree Search", evaluation functions as a weighted sum of features).

    EVAL(s) = sum over every line of 4 cells ("window") of  w(window)
              + CENTER_WEIGHT * (my pieces in the centre column - opponent's)

A window only counts if it is still winnable for one side (it holds pieces of just
one player). The raw score is squashed into [-1, 1] with tanh so it can be added to
the playout win rate, which lives in [0, 1].
"""

import math

from .game import COLS, CONNECT, EMPTY, ROWS, other

# weight of a window holding n of my pieces and no opponent pieces
WINDOW_WEIGHTS = {1: 1.0, 2: 4.0, 3: 16.0}
CENTER_WEIGHT = 3.0
SCALE = 60.0  # tanh(score / SCALE)


def _windows():
    """All 69 lines of four cells on a 6x7 board, as lists of (col, row)."""
    out = []
    for c in range(COLS):
        for r in range(ROWS):
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                cells = [(c + i * dc, r + i * dr) for i in range(CONNECT)]
                if all(0 <= cc < COLS and 0 <= rr < ROWS for cc, rr in cells):
                    out.append(cells)
    return out


WINDOWS = _windows()


def raw_score(state, player):
    """Unbounded heuristic score from `player`'s point of view."""
    if state.winner is not None:
        return math.inf if state.winner == player else -math.inf
    opp = other(player)
    score = 0.0
    for cells in WINDOWS:
        mine = theirs = 0
        for c, r in cells:
            v = state.cell(c, r)
            if v == player:
                mine += 1
            elif v == opp:
                theirs += 1
        if mine and not theirs:
            score += WINDOW_WEIGHTS[mine]
        elif theirs and not mine:
            score -= WINDOW_WEIGHTS[theirs]
    centre = COLS // 2
    col = state.cols[centre]
    score += CENTER_WEIGHT * (col.count(player) - col.count(opp))
    return score


def evaluate(state, player):
    """Heuristic value in [-1, 1] from `player`'s point of view (+1 = `player` has won)."""
    s = raw_score(state, player)
    if s == math.inf:
        return 1.0
    if s == -math.inf:
        return -1.0
    return math.tanh(s / SCALE)
