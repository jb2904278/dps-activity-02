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

ROWS, COLS, CONNECT = 6, 7, 4                   # board size, and how many in a row wins
X, O, EMPTY = "X", "O", "."                     # the two players and the empty-cell symbol
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))  # vertical, horizontal, two diagonals


def other(player):
    # Return the opponent: X -> O, O -> X.
    return O if player == X else X


@dataclass(frozen=True)          # frozen = the state can never be changed after it is made
class State:
    # One board position. Every move creates a NEW State; the old one stays the same.
    cols: Tuple[str, ...]          # ("", "", "XO", "XO", "", "", "") one string per column, bottom to top
    to_move: str = X               # whose turn it is
    winner: Optional[str] = None   # X, O, or None
    last_move: Optional[int] = None  # the column that was just played (None at the start)

    @property
    def n_moves(self):
        # Total pieces on the board = total length of all 7 column strings.
        return sum(len(c) for c in self.cols)

    def cell(self, col, row):
        """Piece at (col, row) with row 0 at the bottom, or EMPTY."""
        c = self.cols[col]                         # the column string, e.g. "XO"
        return c[row] if row < len(c) else EMPTY   # above the top piece = empty

    def __str__(self):
        # Turn the board into text for printing (top row first, column numbers underneath).
        lines = []
        for row in range(ROWS - 1, -1, -1):       # rows 5, 4, ... 0 (top to bottom)
            lines.append(" ".join(self.cell(c, row) for c in range(COLS)))
        lines.append(" ".join(str(c) for c in range(COLS)))   # "0 1 2 3 4 5 6"
        return "\n".join(lines)


def wins_at(cell, col, row, player):
    """True if `player` has 4 in a row through (col, row). `cell(c, r)` returns the piece."""
    # Only lines through the piece just played can be new wins, so we check
    # the 4 directions starting from that one cell.
    for dc, dr in DIRECTIONS:                      # e.g. (1, 0) = left/right
        count = 1                                  # the piece itself
        for sign in (1, -1):                       # walk forwards, then backwards
            c, r = col + sign * dc, row + sign * dr
            # keep stepping while we stay on the board and see the same player's piece
            while 0 <= c < COLS and 0 <= r < ROWS and cell(c, r) == player:
                count += 1
                c, r = c + sign * dc, r + sign * dr
        if count >= CONNECT:                       # 4 or more in this direction -> win
            return True
    return False


class ConnectFour:
    """The game, following the textbook's Game class."""

    def __init__(self):
        # The starting position: 7 empty columns, X moves first.
        self.initial = State(cols=("",) * COLS, to_move=X)

    def to_move(self, state):
        # Whose turn it is in this state.
        return state.to_move

    def actions(self, state):
        # Legal moves = columns that are not full yet. No moves once the game is over.
        if self.is_terminal(state):
            return []
        return [c for c in range(COLS) if len(state.cols[c]) < ROWS]

    def result(self, state, move):
        # Drop the current player's piece into column `move` and return the NEW state.
        if move not in self.actions(state):
            raise ValueError("Illegal move {} in state\n{}".format(move, state))
        p = state.to_move                  # the player making this move
        cols = list(state.cols)            # copy the columns so we can change one
        row = len(cols[move])              # the piece lands on top of what is there
        cols[move] += p                    # add the piece to that column
        new = State(tuple(cols), other(p), None, move)   # now it's the opponent's turn
        # Did this piece make four in a row?
        winner = p if wins_at(new.cell, move, row, p) else None
        return State(new.cols, new.to_move, winner, move)

    def is_terminal(self, state):
        # Game over when someone has won, or all 42 cells are filled (a draw).
        return state.winner is not None or state.n_moves == ROWS * COLS

    def utility(self, state, player):
        # Final score from `player`'s point of view: +1 win, -1 loss, 0 draw.
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
    # 1. Safety check: exactly 6 strings (ROWS), each exactly 7 characters (COLS).
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        raise ValueError("Need {} rows of {} characters".format(ROWS, COLS))
    # 2. Turn the rows into columns, reading each column from the BOTTOM up.
    cols = []
    for c in range(COLS):                        # columns 0, 1, ... 6
        s = ""                                   # this column's pieces, bottom first
        for r in range(ROWS - 1, -1, -1):        # bottom row is the last string (rows 5 -> 0)
            ch = rows[r][c]                      # the cell at row r, column c
            if ch == EMPTY:                      # "." = empty: nothing can sit above it,
                break                            # so stop reading this column
            s += ch                              # add the X or O
        cols.append(s)                           # e.g. column 2 of double_threat -> "XO"
    # 3. Count the pieces.
    n_x = sum(col.count(X) for col in cols)
    n_o = sum(col.count(O) for col in cols)
    # 4. X moves first, so X has the same number of pieces as O, or one more.
    if n_x not in (n_o, n_o + 1):
        raise ValueError("X moves first, so X count must equal O count or be one more")
    # 5. Equal counts -> X to move; otherwise O to move.
    state = State(tuple(cols), X if n_x == n_o else O) # saying its X is turn in first iteration for double threat
    # 6. Record a winner if the board already has four in a row.
    return State(state.cols, state.to_move, find_winner(state))


def find_winner(state):
    # Check every piece on the board: does it belong to a line of four?
    # (Used only for boards built from text, where we don't know the last move.)
    for c in range(COLS): # columns 0, 1, ... 6
        for r in range(len(state.cols[c])): #bottom up
            p = state.cols[c][r] # piece at (c, r)
            if wins_at(state.cell, c, r, p): #check if the piece at (c, r) makes a four in a row
                return p
    return None


def play_random_game(state, rng=random):
    """Random playout policy: both players pick uniformly random legal columns until the
    game ends. Returns the winner (X, O) or None for a draw. Uses mutable lists for speed."""
    # This is MCTS's SIMULATE step. `rng` is the random generator made from the seed.
    if state.winner is not None:              # game already over: nothing to play
        return state.winner
    grid = [list(c) for c in state.cols]      # editable copy of the board (lists, not strings)
    p = state.to_move                         # who moves first in the playout
    n = state.n_moves                         # pieces already on the board

    def cell(c, r):
        # Same as State.cell, but for the editable grid.
        col = grid[c]
        return col[r] if r < len(col) else EMPTY

    open_cols = [c for c in range(COLS) if len(grid[c]) < ROWS]   # columns not yet full
    while n < ROWS * COLS:                    # until the board is full
        c = rng.choice(open_cols)             # pick a RANDOM legal column (uses the seed)
        grid[c].append(p)                     # drop the piece
        n += 1
        if len(grid[c]) == ROWS:              # column is now full: can't play there again
            open_cols.remove(c)
        if wins_at(cell, c, len(grid[c]) - 1, p):   # did that piece make four in a row?
            return p                          # yes: this player wins the playout
        p = other(p)                          # next player's turn
    return None                               # board full, nobody won: draw
