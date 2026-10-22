"""
Test positions used by the tests and the experiments (rows are written TOP row first).
`best` lists the moves considered correct; None means there is no single forced answer.
"""

from .game import ConnectFour, from_rows

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
        "best": [3],
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
    spec = POSITIONS[name]
    if spec["rows"] is None:
        return ConnectFour().initial
    return from_rows(spec["rows"])
