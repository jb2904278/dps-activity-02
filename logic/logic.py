"""
Propositional logic for Q2-Q4, following the textbook's Chapter 7 algorithms and the
structure of its companion code (aima-python logic.py):

    Expr                 a sentence: a symbol, or an operator applied to sentences
    expr("A ==> B")      parse a sentence written with  ~  &  |  ==>  <=>
    pl_true(s, model)    truth of a sentence in a model (Section 7.4.2)
    tt_entails(kb, a)    TT-ENTAILS: truth-table enumeration (Section 7.4.4)
    to_cnf(s)            conversion to conjunctive normal form (Section 7.5.2)
    pl_resolution(kb, a) PL-RESOLUTION: proof by contradiction (Section 7.5.2)

Operator precedence, lowest to highest:  <=>   ==>   |   &   ~
"""

import itertools
import re


# --------------------------------------------------------------------------- #
# Sentences
# --------------------------------------------------------------------------- #
class Expr:
    """A propositional sentence. A symbol has op = its name and no args."""

    SHOW = {"~": "¬", "&": " ∧ ", "|": " ∨ ", "==>": " ⇒ ", "<=>": " ⇔ "}

    def __init__(self, op, *args):
        self.op, self.args = op, tuple(args)

    def is_symbol(self):
        return not self.args

    def __eq__(self, other):
        return isinstance(other, Expr) and self.op == other.op and self.args == other.args

    def __hash__(self):
        return hash((self.op, self.args))

    def __repr__(self):
        return self.show()

    def show(self, top=True):
        if self.is_symbol():
            return self.op
        if self.op == "~":
            return "¬" + self.args[0].show(False)
        inner = self.SHOW[self.op].join(a.show(False) for a in self.args)
        return inner if top else "(" + inner + ")"


TRUE, FALSE = Expr("True"), Expr("False")


def expr(text):
    """Parse a sentence such as '(Smoke & Heat) ==> Fire'."""
    tokens = re.findall(r"<=>|==>|[~&|()]|[A-Za-z_][A-Za-z_0-9]*", text)
    if "".join(tokens) != re.sub(r"\s+", "", text):
        raise ValueError("Cannot parse: " + text)
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take(tok=None):
        t = peek()
        if tok and t != tok:
            raise ValueError("Expected {} in {}".format(tok, text))
        pos[0] += 1
        return t

    def iff():
        left = implies()
        while peek() == "<=>":
            take(); left = Expr("<=>", left, implies())
        return left

    def implies():
        left = disj()
        if peek() == "==>":
            take(); return Expr("==>", left, implies())    # right-associative
        return left

    def disj():
        parts = [conj()]
        while peek() == "|":
            take(); parts.append(conj())
        return parts[0] if len(parts) == 1 else Expr("|", *parts)

    def conj():
        parts = [neg()]
        while peek() == "&":
            take(); parts.append(neg())
        return parts[0] if len(parts) == 1 else Expr("&", *parts)

    def neg():
        if peek() == "~":
            take(); return Expr("~", neg())
        if peek() == "(":
            take("("); e = iff(); take(")"); return e
        t = take()
        if t is None or not re.match(r"[A-Za-z_]", t):
            raise ValueError("Unexpected end or token in " + text)
        return TRUE if t == "True" else FALSE if t == "False" else Expr(t)

    result = iff()
    if peek() is not None:
        raise ValueError("Unexpected '{}' in {}".format(peek(), text))
    return result


def prop_symbols(s):
    """Set of proposition symbols in a sentence (True/False are not symbols)."""
    if s.is_symbol():
        return set() if s in (TRUE, FALSE) else {s.op}
    return set().union(*(prop_symbols(a) for a in s.args))


# --------------------------------------------------------------------------- #
# Semantics and model checking
# --------------------------------------------------------------------------- #
def pl_true(s, model):
    """Truth value of sentence s in a model (dict symbol -> bool)."""
    if s == TRUE:
        return True
    if s == FALSE:
        return False
    if s.is_symbol():
        return model[s.op]
    op, a = s.op, s.args
    if op == "~":
        return not pl_true(a[0], model)
    if op == "&":
        return all(pl_true(x, model) for x in a)
    if op == "|":
        return any(pl_true(x, model) for x in a)
    p, q = pl_true(a[0], model), pl_true(a[1], model)
    if op == "==>":
        return (not p) or q
    if op == "<=>":
        return p == q
    raise ValueError("Unknown operator " + op)


def tt_entails(kb, alpha):
    """TT-ENTAILS?(KB, alpha): does alpha hold in every model where KB holds?

    function TT-ENTAILS?(KB, alpha) returns true or false
        symbols <- a list of the proposition symbols in KB and alpha
        return TT-CHECK-ALL(KB, alpha, symbols, {})
    """
    symbols = sorted(prop_symbols(kb) | prop_symbols(alpha))
    return tt_check_all(kb, alpha, symbols, {})


def tt_check_all(kb, alpha, symbols, model):
    """function TT-CHECK-ALL(KB, alpha, symbols, model) returns true or false
        if EMPTY?(symbols) then
            if PL-TRUE?(KB, model) then return PL-TRUE?(alpha, model)
            else return true                      // when KB is false, always return true
        else
            P <- FIRST(symbols);  rest <- REST(symbols)
            return TT-CHECK-ALL(KB, alpha, rest, model U {P = true}) and
                   TT-CHECK-ALL(KB, alpha, rest, model U {P = false})
    """
    if not symbols:
        return pl_true(alpha, model) if pl_true(kb, model) else True
    p, rest = symbols[0], symbols[1:]
    return (tt_check_all(kb, alpha, rest, {**model, p: True}) and
            tt_check_all(kb, alpha, rest, {**model, p: False}))


def is_valid(s):
    """Valid = true in every model, i.e. entailed by the empty KB (True)."""
    return tt_entails(TRUE, s)


def is_satisfiable(s):
    """Satisfiable = true in some model, i.e. ~s is not valid."""
    return not tt_entails(TRUE, Expr("~", s))


def classify(s):
    if is_valid(s):
        return "valid"
    if not is_satisfiable(s):
        return "unsatisfiable"
    return "satisfiable but not valid (neither)"


def truth_table(s, symbols=None, extra=()):
    """Every model of the symbols, with the value of s (and of any `extra` sub-sentences).
    Rows are listed True-first, like the textbook's tables."""
    symbols = sorted(symbols or prop_symbols(s))
    rows = []
    for values in itertools.product([True, False], repeat=len(symbols)):
        model = dict(zip(symbols, values))
        rows.append((model, [pl_true(e, model) for e in extra], pl_true(s, model)))
    return symbols, rows


def count_models(s, vocabulary):
    """Number of models over `vocabulary` in which s is true. Symbols of the vocabulary
    that s does not mention can take either value, so they multiply the count."""
    _, rows = truth_table(s, symbols=vocabulary)
    return sum(1 for _, _, v in rows if v)


# --------------------------------------------------------------------------- #
# Conversion to CNF (Section 7.5.2), keeping every intermediate step
# --------------------------------------------------------------------------- #
def eliminate_iff(s):
    """Replace a <=> b with (a ==> b) & (b ==> a)."""
    if s.is_symbol():
        return s
    args = [eliminate_iff(a) for a in s.args]
    if s.op == "<=>":
        a, b = args
        return Expr("&", Expr("==>", a, b), Expr("==>", b, a))
    return Expr(s.op, *args)


def eliminate_implies(s):
    """Replace a ==> b with ~a | b."""
    if s.is_symbol():
        return s
    args = [eliminate_implies(a) for a in s.args]
    if s.op == "==>":
        return Expr("|", Expr("~", args[0]), args[1])
    return Expr(s.op, *args)


def move_not_inwards(s):
    """Push ~ down to the symbols with De Morgan's laws and double negation."""
    if s.is_symbol():
        return s
    if s.op == "~":
        a = s.args[0]
        if a.is_symbol():
            return s
        if a.op == "~":
            return move_not_inwards(a.args[0])                          # ~~x = x
        if a.op == "&":
            return Expr("|", *[move_not_inwards(Expr("~", x)) for x in a.args])
        if a.op == "|":
            return Expr("&", *[move_not_inwards(Expr("~", x)) for x in a.args])
    return Expr(s.op, *[move_not_inwards(a) for a in s.args])


def flatten(s):
    """(a | (b | c)) -> (a | b | c), and the same for &."""
    if s.is_symbol():
        return s
    args = []
    for a in (flatten(x) for x in s.args):
        if a.op == s.op and s.op in "&|" and not a.is_symbol():
            args.extend(a.args)
        else:
            args.append(a)
    return Expr(s.op, *args)


def distribute(s):
    """Distribute | over &: (a & b) | c  ->  (a | c) & (b | c)."""
    s = flatten(s)
    if s.is_symbol() or s.op == "~":
        return s
    if s.op == "&":
        return flatten(Expr("&", *[distribute(a) for a in s.args]))
    if s.op == "|":
        args = [distribute(a) for a in s.args]
        conj = next((a for a in args if a.op == "&" and not a.is_symbol()), None)
        if conj is None:
            return flatten(Expr("|", *args))
        rest = [a for a in args if a is not conj]
        return distribute(Expr("&", *[Expr("|", c, *rest) for c in conj.args]))
    return s


def simplify_clauses(clauses):
    """Remove repeated literals, tautological clauses (A | ~A) and duplicate clauses."""
    out = []
    for c in clauses:
        if any(negate(l) in c for l in c):
            continue
        if c not in out:
            out.append(c)
    return out


def to_cnf_steps(s):
    """Return the list of (description, sentence) steps of the CNF conversion."""
    steps = [("Original", s)]
    s1 = eliminate_iff(s)
    if s1 != s:
        steps.append(("1. Eliminate ⇔: α ⇔ β ≡ (α ⇒ β) ∧ (β ⇒ α)", s1))
    s2 = eliminate_implies(s1)
    if s2 != s1:
        steps.append(("2. Eliminate ⇒: α ⇒ β ≡ ¬α ∨ β", s2))
    s3 = move_not_inwards(s2)
    if s3 != s2:
        steps.append(("3. Move ¬ inwards (De Morgan, double negation)", s3))
    s4 = distribute(s3)
    if s4 != flatten(s3):
        steps.append(("4. Distribute ∨ over ∧", s4))
    clauses = simplify_clauses(clauses_of(s4))
    final = clauses_to_expr(clauses)
    if final != flatten(s4):
        steps.append(("5. Simplify: drop repeated literals and tautologies", final))
    return steps


def to_cnf(s):
    return to_cnf_steps(s)[-1][1]


# --------------------------------------------------------------------------- #
# Clauses and PL-RESOLUTION (Section 7.5.2)
# --------------------------------------------------------------------------- #
def negate(literal):
    return literal[1:] if literal.startswith("~") else "~" + literal


def literal_of(e):
    if e.is_symbol():
        return e.op
    if e.op == "~" and e.args[0].is_symbol():
        return "~" + e.args[0].op
    raise ValueError("Not a literal: {}".format(e))


def clauses_of(cnf):
    """CNF sentence -> list of clauses, each a frozenset of literal strings like 'P', '~P'."""
    cnf = flatten(cnf)
    conjuncts = cnf.args if (cnf.op == "&" and not cnf.is_symbol()) else (cnf,)
    out = []
    for c in conjuncts:
        lits = c.args if (c.op == "|" and not c.is_symbol()) else (c,)
        out.append(frozenset(literal_of(l) for l in lits))
    return out


def show_clause(c):
    if not c:
        return "{ }  (empty clause)"
    return " ∨ ".join(sorted(c, key=lambda l: (l.lstrip("~"), l.startswith("~")))).replace("~", "¬")


def clauses_to_expr(clauses):
    def lit(l):
        return Expr("~", Expr(l[1:])) if l.startswith("~") else Expr(l)

    def clause(c):
        ls = sorted(c, key=lambda l: (l.lstrip("~"), l.startswith("~")))
        return lit(ls[0]) if len(ls) == 1 else Expr("|", *[lit(l) for l in ls])

    if not clauses:
        return TRUE
    return clause(clauses[0]) if len(clauses) == 1 else Expr("&", *[clause(c) for c in clauses])


def pl_resolve(ci, cj):
    """All resolvents of two clauses (one per complementary pair), skipping tautologies."""
    out = []
    for l in ci:
        if negate(l) in cj:
            r = (ci - {l}) | (cj - {negate(l)})
            if not any(negate(x) in r for x in r):
                out.append(r)
    return out


def pl_resolution(kb, alpha):
    """PL-RESOLUTION(KB, alpha): True if KB entails alpha.

    function PL-RESOLUTION(KB, alpha) returns true or false
        clauses <- the set of clauses in the CNF representation of KB AND NOT alpha
        new <- { }
        loop do
            for each pair of clauses Ci, Cj in clauses do
                resolvents <- PL-RESOLVE(Ci, Cj)
                if resolvents contains the empty clause then return true
                new <- new U resolvents
            if new is a subset of clauses then return false
            clauses <- clauses U new

    Returns (entailed, proof) where proof lists (clause, parent1, parent2) for every
    clause used to derive the empty clause; input clauses have parents None.
    """
    goal = Expr("&", kb, Expr("~", alpha)) if kb != TRUE else Expr("~", alpha)
    clauses = simplify_clauses(clauses_of(to_cnf(goal)))
    parents = {c: (None, None) for c in clauses}
    while True:
        new = []
        for ci, cj in itertools.combinations(list(clauses), 2):
            for r in pl_resolve(ci, cj):
                if r not in parents:
                    parents[r] = (ci, cj)
                    new.append(r)
                if not r:
                    return True, _proof(frozenset(), parents)
        if not new:
            return False, []
        clauses = clauses + new


def _proof(clause, parents, seen=None):
    seen = seen if seen is not None else set()
    if clause in seen:
        return []
    seen.add(clause)
    p1, p2 = parents[clause]
    steps = []
    if p1 is not None:
        steps += _proof(p1, parents, seen) + _proof(p2, parents, seen)
    steps.append((clause, p1, p2))
    return steps
