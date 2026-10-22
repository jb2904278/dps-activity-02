"""
Prints the working for Q2-Q4 (truth tables, model counts, CNF steps, resolution proof),
all computed by logic.py. Run from the Activity_02 folder:

    python3 -m logic.answers                       # print to the screen
    python3 -m logic.answers --out results/logic_answers.txt
"""

import argparse
import io

from .logic import (Expr, classify, count_models, expr, pl_resolution, show_clause,
                    to_cnf_steps, truth_table)

TF = {True: "T", False: "F"}


def print_table(s, extra, out):
    symbols, rows = truth_table(s, extra=extra)
    heads = symbols + [str(e) for e in extra] + ["Sentence"]
    widths = [max(len(h), 1) for h in heads]
    out.write(" | ".join(h.ljust(w) for h, w in zip(heads, widths)) + "\n")
    out.write("-+-".join("-" * w for w in widths) + "\n")
    for model, ex, val in rows:
        cells = [TF[model[p]] for p in symbols] + [TF[v] for v in ex] + [TF[val]]
        out.write(" | ".join(c.ljust(w) for c, w in zip(cells, widths)) + "\n")


def q2(out):
    out.write("=" * 70 + "\nQ2  Valid, unsatisfiable, or neither?\n" + "=" * 70 + "\n")
    a = expr("Smoke ==> Fire")
    out.write("\n(a) {}\n\n".format(a))
    print_table(a, [], out)
    out.write("\n=> {}\n".format(classify(a).upper()))

    lhs = expr("(Smoke & Heat) ==> Fire")
    rhs = expr("(Smoke ==> Fire) | (Heat ==> Fire)")
    b = Expr("<=>", lhs, rhs)
    out.write("\n(b) {}\n\n".format(b))
    print_table(b, [lhs, rhs], out)
    out.write("\n=> {}\n".format(classify(b).upper()))


def q3(out):
    out.write("\n" + "=" * 70 + "\nQ3  Number of models over the vocabulary {A, B, C, D}\n" + "=" * 70 + "\n")
    vocab = ["A", "B", "C", "D"]
    for label, text in (("a", "B | C"), ("b", "(A ==> B) & A & ~B & C & D")):
        s = expr(text)
        out.write("\n({}) {}\n".format(label, s))
        _, rows = truth_table(s, symbols=vocab)
        true_rows = [m for m, _, v in rows if v]
        out.write("    models: {} of 16\n".format(count_models(s, vocab)))
        for m in true_rows:
            out.write("      " + "  ".join("{}={}".format(k, TF[m[k]]) for k in vocab) + "\n")


def q4(out):
    out.write("\n" + "=" * 70 + "\nQ4  [(Food ⇒ Party) ∨ (Drinks ⇒ Party)] ⇒ [(Food ∧ Drinks) ⇒ Party]\n" + "=" * 70 + "\n")
    lhs = expr("(Food ==> Party) | (Drinks ==> Party)")
    rhs = expr("(Food & Drinks) ==> Party")
    s = Expr("==>", lhs, rhs)

    out.write("\n(a) Enumeration\n\n")
    print_table(s, [lhs, rhs], out)
    out.write("\n=> {}\n".format(classify(s).upper()))

    out.write("\n(b) CNF of each side\n")
    for name, side in (("Left-hand side", lhs), ("Right-hand side", rhs)):
        out.write("\n  {}:\n".format(name))
        for desc, e in to_cnf_steps(side):
            out.write("    {:<55} {}\n".format(desc, e))

    out.write("\n(c) Resolution: prove the sentence is valid by showing ¬(sentence) is unsatisfiable\n")
    entailed, proof = pl_resolution(Expr("True"), s)
    n = {}
    for clause, p1, p2 in proof:
        n[clause] = len(n) + 1
        if p1 is None:
            out.write("    {:>2}. {:<32} (from ¬sentence in CNF)\n".format(n[clause], show_clause(clause)))
        else:
            out.write("    {:>2}. {:<32} (resolve {} and {})\n".format(n[clause], show_clause(clause), n[p1], n[p2]))
    out.write("\n=> empty clause derived: {}  ->  the sentence is VALID\n".format(entailed))


def main(argv=None):
    p = argparse.ArgumentParser(description="Working for Q2-Q4")
    p.add_argument("--out", help="also save the output to this file")
    args = p.parse_args(argv)
    buf = io.StringIO()
    q2(buf); q3(buf); q4(buf)
    text = buf.getvalue()
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
