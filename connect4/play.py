"""
Command-line front end for the MCTS move generator.

Run from the Activity_02 folder:
    python3 -m connect4.play                                  # best move on an empty board
    python3 -m connect4.play --position double_threat --cycles 500 --k 3 --depth 4 --w 0.5
    python3 -m connect4.play --rows "......." "......." "......." "......." "..OO..." "..XX..."
    python3 -m connect4.play --human                          # play against it (you are X)
"""

import argparse

if __package__ in (None, ""):          # allow "Run/Debug Python File" on this file directly
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "connect4"

from .game import ConnectFour, X, from_rows
from .mcts import MCTS, MCTSConfig
from .positions import POSITIONS, load


def config_from(args):
    # Copy the command-line options into an MCTSConfig (the settings object MCTS reads).
    # Note the renames: --k -> expand_k, --depth -> max_depth, --order -> expansion_order.
    return MCTSConfig(cycles=args.cycles, expand_k=args.k, max_depth=args.depth, c=args.c,
                      w=args.w, expansion_order=args.order, seed=args.seed)


def show_stats(state, stats):
    # Print the board, then one line per root child: N, win rate (U/N) and heuristic.
    print(state)
    print("\n{} to move. Root children (column: playouts, win rate, objective):".format(state.to_move))
    for move, s in stats["children"].items():
        mark = "  <- chosen" if move == stats["move"] else ""     # mark the chosen column
        print("  {}: N={:>5}  win={:.2f}  obj={:+.2f}{}".format(move, s["N"], s["win_rate"], s["objective"], mark))
    print("Tree size: {} nodes".format(stats["tree_size"]))


def play_human(cfg):
    # Play a full game: you are X (first), the computer is O and runs MCTS on every turn.
    game = ConnectFour()
    state = game.initial                     # always starts from the empty board
    bot = MCTS(cfg)
    while not game.is_terminal(state):       # until someone wins or the board is full
        print("\n" + str(state))
        if state.to_move == X:               # your turn
            move = None
            while move not in game.actions(state):   # keep asking until the column is legal
                try:
                    move = int(input("Your move (column {}): ".format(game.actions(state))))
                except ValueError:           # not a number: ask again
                    move = None
        else:                                # computer's turn: a full MCTS search
            move = bot.search(state)
            print("Computer plays column", move)
        state = game.result(state, move)     # drop the piece, switch turns
    print("\n" + str(state))
    print("Draw." if state.winner is None else "{} wins.".format(state.winner))


def main(argv=None):
    # Read the command-line options, then either play a game (--human)
    # or run one search and print the chosen move.
    p = argparse.ArgumentParser(description="Monte Carlo tree search for Connect Four")
    p.add_argument("--position", choices=sorted(POSITIONS), default="empty") # which starting board to analyse
    p.add_argument("--rows", nargs=6, metavar="ROW", help="6 rows, top first, using X O and .") # can also provide custom board
    p.add_argument("--cycles", type=int, default=1000) # number of iterations
    p.add_argument("--k", type=int, default=7, help="expansion width x (children per node)") # number of children to expand
    p.add_argument("--depth", type=int, default=42, help="tree height") # max depth of tree
    p.add_argument("--c", type=float, default=1.41, help="exploration weight") # exploration weight
    p.add_argument("--w", type=float, default=0.5, help="objective (heuristic) weight") # objective weight
    p.add_argument("--order", choices=["heuristic", "random"], default="heuristic") # order of expansion
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--human", action="store_true", help="play a game against the computer")
    args = p.parse_args(argv)                # read what was actually typed (defaults for the rest)

    cfg = config_from(args)                  # pack the settings into MCTSConfig
    if args.human:                           # --human: play a full game instead
        play_human(cfg)
        return
    # The starting board: your own --rows if given, otherwise a named --position.
    state = from_rows(args.rows) if args.rows else load(args.position)
    # Create MCTS with the settings, search from this board, print the result.
    show_stats(state, MCTS(cfg).search_with_stats(state))


if __name__ == "__main__":
    main()
