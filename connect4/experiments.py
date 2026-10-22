"""
Q1 experiments: how the utility function, number of cycles, expansion width x and tree
height change the move the MCTS move generator picks.

Every measurement runs the search several times with different random seeds and records:
    accuracy      share of runs that picked a correct move (tactical positions only)
    mode_share    share of runs that picked the most common move (1.0 = always the same move)
    distinct      how many different moves were picked
    ms            average time per search in milliseconds
    tree          average number of nodes in the search tree

Run from the Activity_02 folder:
    python3 -m connect4.experiments              # full run (about 15-25 minutes), writes results/
    python3 -m connect4.experiments --only A,E   # run just some experiments (A-F)
    python3 -m connect4.experiments --quick      # small run for CI / a smoke test
"""

import argparse
import csv
import os
import time
from collections import Counter
from dataclasses import asdict, replace

if __package__ in (None, ""):          # allow "Run/Debug Python File" on this file directly
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "connect4"

from .game import ConnectFour
from .mcts import MCTS, MCTSConfig
from .positions import POSITIONS, load

BASE = MCTSConfig(cycles=200, expand_k=7, max_depth=42, w=0.5)
TACTICAL = ["win_in_1", "must_block", "double_threat"]


def measure(config, position, trials):
    state = load(position)
    best = POSITIONS[position]["best"]
    moves, times, trees = [], [], []
    for seed in range(trials):
        cfg = replace(config, seed=seed)
        t0 = time.perf_counter()
        stats = MCTS(cfg).search_with_stats(state)
        times.append((time.perf_counter() - t0) * 1000)
        moves.append(stats["move"])
        trees.append(stats["tree_size"])
    counts = Counter(moves)
    mode, mode_n = counts.most_common(1)[0]
    return {
        "position": position,
        "accuracy": round(sum(m in best for m in moves) / trials, 3) if best else "",
        "mode_move": mode,
        "mode_share": round(mode_n / trials, 3),
        "distinct": len(counts),
        "moves": " ".join("{}:{}".format(m, n) for m, n in sorted(counts.items())),
        "ms": round(sum(times) / trials, 1),
        "tree": round(sum(trees) / trials, 1),
    }


def row(config, label, position, trials):
    r = {"label": label}
    r.update({k: v for k, v in asdict(config).items() if k != "seed"})
    t0 = time.perf_counter()
    r.update(measure(config, position, trials))
    print("    {:<22} {:<14} cycles={:<5} x={} height={:<3} -> move {} ({:.0%} of runs)  {:.1f}s".format(
        label, position, config.cycles, config.expand_k, config.max_depth,
        r["mode_move"], r["mode_share"], time.perf_counter() - t0), flush=True)
    return r


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print("  wrote", path, "({} rows)".format(len(rows)))


def read_csv(path):
    """Read a results CSV back, turning numbers into int/float."""
    def conv(v):
        for t in (int, float):
            try:
                return t(v)
            except ValueError:
                pass
        return v
    with open(path, newline="") as f:
        return [{k: conv(v) for k, v in r.items()} for r in csv.DictReader(f)]


# --------------------------------------------------------------------------- #
# Experiments
# --------------------------------------------------------------------------- #
def exp_determinism(trials):
    """A. Same settings, different seeds: is the move always the same?
    Also: same seed twice must give the same move (reproducibility)."""
    rows = [row(BASE, "baseline", p, trials) for p in POSITIONS]
    same_seed = []
    for p in POSITIONS:
        a = MCTS(replace(BASE, seed=123)).search(load(p))
        b = MCTS(replace(BASE, seed=123)).search(load(p))
        same_seed.append({"position": p, "run_1": a, "run_2": b, "identical": a == b})
    return rows, same_seed


def exp_cycles(trials, cycles_list):
    """B. Number of cycles, with and without the objective part of the utility."""
    rows = []
    for w in (0.0, 0.5):
        for n in cycles_list:
            cfg = replace(BASE, cycles=n, w=w)
            for p in POSITIONS:
                rows.append(row(cfg, "w={}".format(w), p, trials))
    return rows


def exp_utility(trials, ws, cs):
    """C. Utility function: objective weight w and exploration weight c."""
    rows = []
    for w in ws:
        for c in cs:
            cfg = replace(BASE, cycles=100, w=w, c=c)
            for p in POSITIONS:
                rows.append(row(cfg, "w={} c={}".format(w, c), p, trials))
    return rows


def exp_expansion(trials, ks):
    """D. Expansion width x, choosing the x moves by heuristic or at random."""
    rows = []
    for order in ("heuristic", "random"):
        for k in ks:
            cfg = replace(BASE, cycles=100, expand_k=k, expansion_order=order)
            for p in POSITIONS:
                rows.append(row(cfg, "{} k={}".format(order, k), p, trials))
    return rows


def exp_height(trials, depths):
    """E. Height of the tree (max_depth). Below it, positions are only simulated."""
    rows = []
    for d in depths:
        cfg = replace(BASE, cycles=100, max_depth=d)
        for p in POSITIONS:
            rows.append(row(cfg, "depth={}".format(d), p, trials))
    return rows


def play_game(cfg_x, cfg_o, seed):
    game = ConnectFour()
    state = game.initial
    players = {"X": MCTS(replace(cfg_x, seed=seed)), "O": MCTS(replace(cfg_o, seed=seed + 10_000))}
    while not game.is_terminal(state):
        state = game.result(state, players[state.to_move].search(state))
    return state.winner


def exp_matches(games, candidates, opponent):
    """F. Playing strength: each candidate plays `games` full games against the opponent,
    half as X (moving first) and half as O."""
    rows = []
    for label, cfg in candidates:
        w = d = l = 0
        for g in range(games):
            as_x = g % 2 == 0
            winner = play_game(cfg, opponent, g) if as_x else play_game(opponent, cfg, g)
            me = "X" if as_x else "O"
            if winner is None:
                d += 1
            elif winner == me:
                w += 1
            else:
                l += 1
        score = (w + 0.5 * d) / games
        rows.append({"label": label, "games": games, "wins": w, "draws": d, "losses": l,
                     "score": round(score, 3)})
        print("    {:<28} {}W {}D {}L  score {:.2f}".format(label, w, d, l, score))
    return rows


# --------------------------------------------------------------------------- #
# Charts (optional: needs matplotlib)
# --------------------------------------------------------------------------- #
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # categorical slots 1-4, fixed order
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def _style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.tick_params(colors=INK2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)


def make_charts(out, cycles_rows, util_rows, exp_rows, height_rows, match_rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed: skipping charts")
        return
    os.makedirs(out, exist_ok=True)

    # 1. accuracy vs cycles, one panel per tactical position, w=0 vs w=0.5
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True, facecolor=SURFACE)
    for ax, pos in zip(axes, TACTICAL):
        for i, w in enumerate(("w=0.0", "w=0.5")):
            pts = [(r["cycles"], r["accuracy"]) for r in cycles_rows if r["position"] == pos and r["label"] == w]
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=SERIES[i], linewidth=2, marker="o", markersize=6,
                    label="playout only (w = 0)" if w == "w=0.0" else "playout + objective (w = 0.5)")
        ax.set_xscale("log")
        ax.set_ylim(0, 1.05)
        _style(ax, pos.replace("_", " "), "cycles (log scale)", "share of runs correct" if pos == TACTICAL[0] else "")
    axes[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "accuracy_vs_cycles.png"), dpi=150)
    plt.close(fig)

    # 2. consistency on the empty board vs cycles
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor=SURFACE)
    for i, w in enumerate(("w=0.0", "w=0.5")):
        pts = [(r["cycles"], r["mode_share"]) for r in cycles_rows if r["position"] == "empty" and r["label"] == w]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=SERIES[i], linewidth=2, marker="o", markersize=6,
                label="playout only (w = 0)" if w == "w=0.0" else "playout + objective (w = 0.5)")
    ax.set_xscale("log")
    ax.set_ylim(0, 1.05)
    _style(ax, "Empty board: how often the most common move is chosen", "cycles (log scale)", "share of runs")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "consistency_empty_board.png"), dpi=150)
    plt.close(fig)

    # 3. double-threat accuracy vs objective weight w, one line per c
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor=SURFACE)
    cs = sorted({r["c"] for r in util_rows})
    for i, c in enumerate(cs):
        pts = sorted((r["w"], r["accuracy"]) for r in util_rows if r["position"] == "double_threat" and r["c"] == c)
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=SERIES[i], linewidth=2, marker="o", markersize=6, label="c = {:.2f}".format(c))
    ax.set_ylim(0, 1.05)
    _style(ax, "Double threat (100 cycles): accuracy vs objective weight", "objective weight w", "share of runs correct")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "utility_weights.png"), dpi=150)
    plt.close(fig)

    # 4. expansion width: double-threat accuracy, heuristic vs random choice of the x moves
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor=SURFACE)
    for i, order in enumerate(("heuristic", "random")):
        pts = sorted((r["expand_k"], r["accuracy"]) for r in exp_rows if r["position"] == "double_threat" and r["expansion_order"] == order)
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=SERIES[i], linewidth=2, marker="o", markersize=6, label="x moves chosen by " + order)
    ax.set_ylim(0, 1.05)
    _style(ax, "Double threat (100 cycles): accuracy vs expansion width x", "x (children per node)", "share of runs correct")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "expansion_width.png"), dpi=150)
    plt.close(fig)

    # 5. match results
    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=SURFACE)
    labels = [r["label"] for r in match_rows]
    scores = [r["score"] for r in match_rows]
    bars = ax.barh(labels, scores, color=SERIES[0], height=0.55)
    for b, s in zip(bars, scores):
        ax.text(s + 0.01, b.get_y() + b.get_height() / 2, "{:.2f}".format(s), va="center", fontsize=9, color=INK)
    ax.axvline(0.5, color=INK2, linewidth=1, linestyle="--")
    ax.set_xlim(0, 1.1)
    ax.invert_yaxis()
    _style(ax, "Score against plain UCT (win = 1, draw = 0.5)", "score", "")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "match_scores.png"), dpi=150)
    plt.close(fig)
    print("  charts written to", out)


def main(argv=None):
    p = argparse.ArgumentParser(description="Run the Q1 MCTS experiments")
    p.add_argument("--quick", action="store_true", help="tiny run for a smoke test")
    p.add_argument("--trials", type=int, default=30, help="seeds per measurement")
    p.add_argument("--games", type=int, default=20, help="games per match-up")
    p.add_argument("--out", default="results")
    p.add_argument("--charts-only", action="store_true", help="redraw charts from existing CSVs")
    p.add_argument("--only", default="ABCDEF", help="which experiments to run, e.g. A,B or E")
    args = p.parse_args(argv)

    if args.charts_only:
        names = ["B_cycles", "C_utility", "D_expansion", "E_height", "F_matches"]
        make_charts(os.path.join(args.out, "charts"), *[read_csv(os.path.join(args.out, n + ".csv")) for n in names])
        return

    if args.quick:
        args.trials, args.games = 3, 2
        cycles_list, ws, cs, ks, depths = [25, 100], [0.0, 0.5], [1.41], [1, 7], [1, 42]
    else:
        cycles_list = [10, 25, 50, 100, 200, 500, 1000, 2000]
        ws, cs = [0.0, 0.25, 0.5, 1.0, 2.0], [0.5, 1.41, 2.0]
        ks, depths = [1, 2, 3, 4, 5, 7], [1, 2, 3, 4, 6, 10, 42]

    only = set(args.only.upper().replace(",", "").replace(" ", ""))
    out = {}
    if "A" in only:
        print("A. determinism", flush=True); a_rows, same_seed = exp_determinism(args.trials)
        write_csv(a_rows, os.path.join(args.out, "A_determinism.csv"))
        write_csv(same_seed, os.path.join(args.out, "A_same_seed.csv"))
    if "B" in only:
        print("B. cycles", flush=True); out["b"] = exp_cycles(args.trials, cycles_list)
        write_csv(out["b"], os.path.join(args.out, "B_cycles.csv"))
    if "C" in only:
        print("C. utility", flush=True); out["c"] = exp_utility(args.trials, ws, cs)
        write_csv(out["c"], os.path.join(args.out, "C_utility.csv"))
    if "D" in only:
        print("D. expansion", flush=True); out["d"] = exp_expansion(args.trials, ks)
        write_csv(out["d"], os.path.join(args.out, "D_expansion.csv"))
    if "E" in only:
        print("E. tree height", flush=True); out["e"] = exp_height(args.trials, depths)
        write_csv(out["e"], os.path.join(args.out, "E_height.csv"))

    if "F" in only:
        print("F. matches (full games, the slowest part)", flush=True)
        opponent = replace(BASE, w=0.0)                     # plain UCT, 200 cycles
        candidates = [
            ("plain UCT (w=0), mirror", replace(BASE, w=0.0)),
            ("w=0.5", BASE),
            ("w=1.0", replace(BASE, w=1.0)),
            ("w=0.5, x=3", replace(BASE, expand_k=3)),
            ("w=0.5, height=4", replace(BASE, max_depth=4)),
            ("w=0, 50 cycles", replace(BASE, w=0.0, cycles=50)),
            ("w=0, 800 cycles", replace(BASE, w=0.0, cycles=800)),
        ]
        if args.quick:
            candidates = candidates[:2]
        out["f"] = exp_matches(args.games, candidates, opponent)
        write_csv(out["f"], os.path.join(args.out, "F_matches.csv"))

    if all(k in out for k in "bcdef"):
        make_charts(os.path.join(args.out, "charts"), out["b"], out["c"], out["d"], out["e"], out["f"])
    else:
        print("Charts skipped (they need B-F). Redraw later with --charts-only.")


if __name__ == "__main__":
    main()
