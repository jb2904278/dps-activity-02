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
WINDOW_WEIGHTS = {1: 1.0, 2: 4.0, 3: 16.0}   # 1 piece = +1, 2 pieces = +4, 3 pieces = +16
CENTER_WEIGHT = 3.0                          # bonus per piece in the middle column
SCALE = 60.0  # tanh(score / SCALE)          # chosen so normal scores don't all become ±1


def _windows():
    """All 69 lines of four cells on a 6x7 board, as lists of (col, row)."""
    # Try every cell as a starting point and every direction; keep the lines
    # of 4 cells that fit completely on the board.

    """
    For each cell (c, r) on the board:
        Try every direction (right, up, up-right diagonal, down-right diagonal):
        For each direction:
            Check if the 4 cells in that direction are all on the board:
                If yes, add the list of these 4 cells to the WINDOWS list
    The WINDOWS list will contain all possible lines of 4 cells on the board
    (horizontal, vertical, and both diagonal directions).

    [
        [(0,0), (1,0), (2,0), (3,0)],   # from (0,0) going right 
        [(0,0), (0,1), (0,2), (0,3)],   # from (0,0) going up
        [(0,0), (1,1), (2,2), (3,3)],   # from (0,0) going up-right
        # from (0,0) going down-right: (0,-1)… is off the board → skipped
        [(0,1), (1,1), (2,1), (3,1)],   # from (0,1) going right
        ...
    ]   # 69 windows in total: 24 across, 21 up, 12 + 12 diagonal
  
    """
    out = []
    for c in range(COLS):
        for r in range(ROWS):
            # right, up, up-right diagonal, down-right diagonal
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                cells = [(c + i * dc, r + i * dr) for i in range(CONNECT)]   # 4 cells in a line
                if all(0 <= cc < COLS and 0 <= rr < ROWS for cc, rr in cells):   # all on the board?
                    out.append(cells)
    return out          # 24 across + 21 up + 12 + 12 diagonals = 69 


WINDOWS = _windows()    # worked out once, when the program starts


def raw_score(state, player):
    """Unbounded heuristic score from `player`'s point of view."""
    # Someone has already won: best or worst possible score.
    if state.winner is not None:
        return math.inf if state.winner == player else -math.inf
    opp = other(player)
    score = 0.0
    for cells in WINDOWS:                    # check all 69 windows one by one
        mine = theirs = 0
        for c, r in cells: # [(0,0), (1,0), (2,0), (3,0)] for first window
            """
            WINDOWS: A list of all 69 possible lines of four cells on the board. 
            For each line, it checks if the current player has any pieces in that line. 
            If the current player has pieces in the line, it adds the value of that line to the score. 
            If the opponent has pieces in the line, it subtracts the value of that line from the score. 

            For example, if the current player is X, and a window has three X's and no O's, the score will increase. 
            If the window has three O's and no X's, the score will decrease. 

            WINDOW_WEIGHTS: defines how much each window is worth. A window with 3 of my pieces is worth 16 points, while a window with 2 is worth 4 points, and a window with 1 is worth 1 point. 
            CENTER_WEIGHT: gives a bonus for having pieces in the center column. 
            SCALE: a constant used to scale the raw score before applying the tanh function. 

            count all possible pairs of that particular window and add and subtract based on X and O's pieces in that particular window
            if X has 3 and O has 0 then add 16 to the score
            if X has 2 and O has 0 then add 4 to the score
            if X has 1 and O has 0 then add 1 to the score
            if X has 0 and O has 1 then subtract 1 from the score
            if X has 0 and O has 2 then subtract 4 from the score
            if X has 0 and O has 3 then subtract 16 from the score
            if X has 1 and O has 1 then add 0 to the score
            if X has 2 and O has 1 then add 3 to the score
            if X has 1 and O has 2 then subtract 3 from the score
            """                  # count the pieces in this window
            v = state.cell(c, r)
            if v == player:
                mine += 1
            elif v == opp:
                theirs += 1
        if mine and not theirs:              # only my pieces: still winnable for me
            score += WINDOW_WEIGHTS[mine]    # +1 / +4 / +16
        elif theirs and not mine:            # only opponent's pieces: winnable for them
            score -= WINDOW_WEIGHTS[theirs]  # -1 / -4 / -16
        # both players' pieces ("dead") or empty: adds nothing
    centre = COLS // 2                       # column 3
    col = state.cols[centre]
    score += CENTER_WEIGHT * (col.count(player) - col.count(opp))   # centre bonus
    return score


def evaluate(state, player):
    """Heuristic value in [-1, 1] from `player`'s point of view (+1 = `player` has won)."""
    # This is EVAL in the utility formula: utility = U/N + exploration + w * EVAL
    s = raw_score(state, player) 
    if s == math.inf:            # player has won
        return 1.0
    if s == -math.inf:           # player has lost
        return -1.0
    return math.tanh(s / SCALE)  # squash into -1 ... +1, e.g. tanh(23 / 60) = 0.366
