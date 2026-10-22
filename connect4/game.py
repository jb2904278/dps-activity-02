"""
Connect Four (6 rows x 7 columns) written with the textbook's Game interface
(AIMA 4e, Section 5.1, and the companion code games4e.py):

    initial                 the starting state
    to_move(state)          the player whose turn it is
    actions(state)          the legal moves (columns that are not full)
    result(state, move)     the transition model
    is_terminal(state)      the game is over (someone has 4 in a row, or the board is full)
    utility(state, player)  +1 win, 0 draw, -1 loss from `player`'s point of view

Board representation: a tuple of 7 strings, one per column, read from the BOTTOM up.
    cols[2] == "XO"  means column 2 has an X at the bottom and an O on top of it.
A tuple of strings is immutable and hashable, so states can be shared safely between
tree nodes. Random playouts use a faster mutable copy (see `play_random_game`).
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

ROWS, COLS, CONNECT = 6, 7, 4
X, O, EMPTY = "X", "O", "."
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))  # vertical, horizontal, two diagonals


def other(player):
    return O if player == X else X


@dataclass(frozen=True)
class State:
    cols: Tuple[str, ...]          # one string per column, bottom to top
    to_move: str = X
    winner: Optional[str] = None   # X, O, or None
    last_move: Optional[int] = None

    @property
    def n_moves(self):
        return sum(len(c) for c in self.cols)

    def cell(self, col, row):
        """Piece at (col, row) with row 0 at the bottom, or EMPTY."""
        c = self.cols[col]
        return c[row] if row < len(c) else EMPTY

    def __str__(self):
        lines = []
        for row in range(ROWS - 1, -1, -1):
            lines.append(" ".join(self.cell(c, row) for c in range(COLS)))
        lines.append(" ".join(str(c) for c in range(COLS)))
        return "\n".join(lines)


def wins_at(cell, col, row, player):
    """True if `player` has 4 in a row through (col, row). `cell(c, r)` returns the piece."""
    for dc, dr in DIRECTIONS:
        count = 1
        for sign in (1, -1):
            c, r = col + sign * dc, row + sign * dr
            while 0 <= c < COLS and 0 <= r < ROWS and cell(c, r) == player:
                count += 1
                c, r = c + sign * dc, r + sign * dr
        if count >= CONNECT:
            return True
    return False


class ConnectFour:
    """The game, following the textbook's Game class."""

    def __init__(self):
        self.initial = State(cols=("",) * COLS, to_move=X)

    def to_move(self, state):
        return state.to_move

    def actions(self, state):
        if self.is_terminal(state):
            return []
        return [c for c in range(COLS) if len(state.cols[c]) < ROWS]

    def result(self, state, move):
        if move not in self.actions(state):
            raise ValueError("Illegal move {} in state\n{}".format(move, state))
        p = state.to_move
        cols = list(state.cols)
        row = len(cols[move])
        cols[move] += p
        new = State(tuple(cols), other(p), None, move)
        winner = p if wins_at(new.cell, move, row, p) else None
        return State(new.cols, new.to_move, winner, move)

    def is_terminal(self, state):
        return state.winner is not None or state.n_moves == ROWS * COLS

    def utility(self, state, player):
        if state.winner is None:
            return 0
        return 1 if state.winner == player else -1


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def from_rows(rows):
    """Build a state from 6 strings written TOP row first, e.g.
        ".......",
        ".......",
        ".......",
        ".......",
        "...O...",
        "..XXX.O"
    The player to move is X if both have played the same number of pieces, else O."""
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        raise ValueError("Need {} rows of {} characters".format(ROWS, COLS))
    cols = []
    for c in range(COLS):
        s = ""
        for r in range(ROWS - 1, -1, -1):        # bottom row is the last string
            ch = rows[r][c]
            if ch == EMPTY:
                break
            s += ch
        cols.append(s)
    n_x = sum(col.count(X) for col in cols)
    n_o = sum(col.count(O) for col in cols)
    if n_x not in (n_o, n_o + 1):
        raise ValueError("X moves first, so X count must equal O count or be one more")
    state = State(tuple(cols), X if n_x == n_o else O)
    return State(state.cols, state.to_move, find_winner(state))


def find_winner(state):
    for c in range(COLS):
        for r in range(len(state.cols[c])):
            p = state.cols[c][r]
            if wins_at(state.cell, c, r, p):
                return p
    return None


def play_random_game(state, rng=random):
    """Random playout policy: both players pick uniformly random legal columns until the
    game ends. Returns the winner (X, O) or None for a draw. Uses mutable lists for speed."""
    if state.winner is not None:
        return state.winner
    grid = [list(c) for c in state.cols]
    p = state.to_move
    n = state.n_moves

    def cell(c, r):
        col = grid[c]
        return col[r] if r < len(col) else EMPTY

    open_cols = [c for c in range(COLS) if len(grid[c]) < ROWS]
    while n < ROWS * COLS:
        c = rng.choice(open_cols)
        grid[c].append(p)
        n += 1
        if len(grid[c]) == ROWS:
            open_cols.remove(c)
        if wins_at(cell, c, len(grid[c]) - 1, p):
            return p
        p = other(p)
    return None
