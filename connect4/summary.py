"""
Print the tables of REPORT_Q1.md (section 3) straight from the experiment CSV files,
so the report's numbers can be checked against a fresh run.

Run from the Activity_02 folder:
    python3 -m connect4.experiments          # (re)creates results/*.csv
    python3 -m connect4.summary              # prints the report tables from results/
    python3 -m connect4.summary --dir results_check
"""

import argparse
import csv
import os


def load(folder, name):
    with open(os.path.join(folder, name + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


def pick(rows, **match):
    for r in rows:
        if all(str(r[k]) == str(v) for k, v in match.items()):
            return r
    raise KeyError(match)


def f2(x):
    return "{:.2f}".format(float(x)) if x != "" else "-"


def ms(x):
    return "{:.0f} ms".format(float(x))


def line(label, values, width=8):
    print("  {:<34}".format(label) + "".join("{:>{w}}".format(v, w=width) for v in values))


def section_a(d):
    print("\nA. Same settings, different seeds (baseline, 200 cycles)")
    rows = load(d, "A_determinism")
    print("  {:<15} {:<34} {:>9} {:>6} {:>9}".format("position", "moves chosen (col:times)", "accuracy", "mode", "distinct"))
    for r in rows:
        print("  {:<15} {:<34} {:>9} {:>6} {:>9}".format(
            r["position"], r["moves"], f2(r["accuracy"]), f2(r["mode_share"]), r["distinct"]))
    same = load(d, "A_same_seed")
    print("  same seed twice -> identical in all positions:", all(r["identical"] == "True" for r in same))


def section_b(d):
    print("\nB. Number of cycles")
    rows = load(d, "B_cycles")
    cyc = [10, 25, 50, 100, 200, 500, 1000, 2000]
    line("cycles", cyc)
    for w in ("0.0", "0.5"):
        line("double threat accuracy, w = " + w[:-2] if w == "0.0" else "double threat accuracy, w = 0.5",
             [f2(pick(rows, label="w=" + w, cycles=c, position="double_threat")["accuracy"]) for c in cyc])
    for w in ("0.0", "0.5"):
        line("empty: mode share, w = " + ("0" if w == "0.0" else "0.5"),
             [f2(pick(rows, label="w=" + w, cycles=c, position="empty")["mode_share"]) for c in cyc])
    line("time per move (empty, w = 0.5)",
         [ms(pick(rows, label="w=0.5", cycles=c, position="empty")["ms"]) for c in cyc], 9)


def section_c(d):
    print("\nC. Utility: w and c (100 cycles)  -- each cell: double-threat accuracy / empty mode share")
    rows = load(d, "C_utility")
    cs = ["0.5", "1.41", "2.0"]
    line("", ["c=" + c for c in cs], 13)
    for w in ["0.0", "0.25", "0.5", "1.0", "2.0"]:
        cells = []
        for c in cs:
            lab = "w={} c={}".format(w, c)
            a = pick(rows, label=lab, position="double_threat")["accuracy"]
            m = pick(rows, label=lab, position="empty")["mode_share"]
            cells.append("{} / {}".format(f2(a), f2(m)))
        line("w = " + w, cells, 13)


def section_d(d):
    print("\nD. Expansion width x (100 cycles)")
    rows = load(d, "D_expansion")
    ks = [1, 2, 3, 4, 5, 7]
    line("x", ks)
    for order in ("heuristic", "random"):
        line("win-in-1 accuracy, " + order,
             [f2(pick(rows, label="{} k={}".format(order, k), position="win_in_1")["accuracy"]) for k in ks])
    line("empty mode share, heuristic",
         [f2(pick(rows, label="heuristic k={}".format(k), position="empty")["mode_share"]) for k in ks])
    for order in ("heuristic", "random"):
        line("time per move (empty), " + order,
             [ms(pick(rows, label="{} k={}".format(order, k), position="empty")["ms"]) for k in ks])


def section_e(d):
    print("\nE. Height of the tree (100 cycles)")
    rows = load(d, "E_height")
    hs = [1, 2, 3, 4, 6, 10, 42]
    line("height", hs)
    line("double threat accuracy", [f2(pick(rows, label="depth={}".format(h), position="double_threat")["accuracy"]) for h in hs])
    line("empty mode share", [f2(pick(rows, label="depth={}".format(h), position="empty")["mode_share"]) for h in hs])
    line("tree size (nodes)", ["{:.0f}".format(float(pick(rows, label="depth={}".format(h), position="empty")["tree"])) for h in hs])


def section_f(d):
    print("\nF. 20 games each against plain UCT (w = 0, 200 cycles)")
    rows = load(d, "F_matches")
    print("  {:<28} {:>5} {:>6} {:>7} {:>6}".format("configuration", "wins", "draws", "losses", "score"))
    for r in rows:
        print("  {:<28} {:>5} {:>6} {:>7} {:>6}".format(r["label"], r["wins"], r["draws"], r["losses"], f2(r["score"])))


def main(argv=None):
    p = argparse.ArgumentParser(description="Print the report's tables from the experiment CSVs")
    p.add_argument("--dir", default="results", help="folder with the CSV files")
    args = p.parse_args(argv)
    total = 0
    for name, per in (("A_determinism", 30), ("B_cycles", 30), ("C_utility", 30), ("D_expansion", 30), ("E_height", 30)):
        total += len(load(args.dir, name)) * per
    total += len(load(args.dir, "A_same_seed")) * 2
    games = sum(int(r["games"]) for r in load(args.dir, "F_matches"))
    print("Data folder: {}   searches: {}   full games: {}".format(args.dir, total, games))
    for s in (section_a, section_b, section_c, section_d, section_e, section_f):
        s(args.dir)
    print("\nTiming (ms) depends on the computer; every other number should match REPORT_Q1.md exactly.")


if __name__ == "__main__":
    main()
