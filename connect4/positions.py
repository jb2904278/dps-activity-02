"""
Test positions used by the tests and the experiments (rows are written TOP row first).
`best` lists the moves considered correct; None means there is no single forced answer.
"""

from .game import ConnectFour, from_rows

# Each entry: name -> {"rows": the board (6 strings, top row first),
#                      "best": the correct column(s), used only to mark accuracy,
#                      "note": a description for people}
POSITIONS = {
    "empty": {
        "rows": None,
        "best": None,          # the centre column (3) is known to be strongest, but not forced
        "note": "Opening move on an empty board",
    },
    "win_in_1": {
        "rows": [".......",
                 ".......",
                 ".......",
                 ".......",
                 "OO.....",
                 "XXX...O"],
        "best": [3], # X should play in column 3 to win
        "note": "X completes four in a row on the bottom row",
    },
    "must_block": {
        "rows": [".......",
                 ".......",
                 ".......",
                 ".......",
                 "....X..",
                 "OOO.XX."],
        "best": [3],
        "note": "O threatens column 3; any other move loses at once",
    },
    "double_threat": {
        "rows": [".......",
                 ".......",
                 ".......",
                 ".......",
                 "..OO...",
                 "..XX..."],
        "best": [1, 4],
        "note": "X makes an open three (.XXX.) with both ends playable: a win two moves later",
    },
}


def load(name):
    # Turn a position's name (e.g. "double_threat") into a game state.
    spec = POSITIONS[name]                 # look up its entry in the dictionary
    if spec["rows"] is None:               # "empty" has no rows:
        return ConnectFour().initial       #   use the normal starting board
    return from_rows(spec["rows"])         # otherwise build the board from the 6 strings
