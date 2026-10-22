import json
import os
import unittest

from logic.logic import (Expr, classify, count_models, expr, is_satisfiable, is_valid,
                         pl_resolution, pl_true, to_cnf, tt_entails, clauses_of)

CASES = os.path.join(os.path.dirname(__file__), "data", "logic_cases.json")


class TestParsingAndSemantics(unittest.TestCase):
    def test_precedence(self):
        # & binds tighter than |, which binds tighter than ==>
        self.assertEqual(expr("A | B & C"), Expr("|", Expr("A"), Expr("&", Expr("B"), Expr("C"))))
        self.assertEqual(expr("A ==> B ==> C"), expr("A ==> (B ==> C)"))

    def test_pl_true(self):
        s = expr("Smoke ==> Fire")
        self.assertFalse(pl_true(s, {"Smoke": True, "Fire": False}))
        self.assertTrue(pl_true(s, {"Smoke": False, "Fire": False}))

    def test_tt_entails(self):
        self.assertTrue(tt_entails(expr("A & B"), expr("A")))
        self.assertFalse(tt_entails(expr("A | B"), expr("A")))


class TestClassification(unittest.TestCase):
    def test_cases_from_file(self):
        with open(CASES) as f:
            for case in json.load(f):
                with self.subTest(sentence=case["sentence"]):
                    self.assertEqual(classify(expr(case["sentence"])), case["class"])

    def test_q2(self):
        self.assertFalse(is_valid(expr("Smoke ==> Fire")))
        self.assertTrue(is_satisfiable(expr("Smoke ==> Fire")))
        self.assertTrue(is_valid(expr("((Smoke & Heat) ==> Fire) <=> ((Smoke ==> Fire) | (Heat ==> Fire))")))


class TestModels(unittest.TestCase):
    VOCAB = ["A", "B", "C", "D"]

    def test_q3a(self):
        self.assertEqual(count_models(expr("B | C"), self.VOCAB), 12)

    def test_q3b(self):
        self.assertEqual(count_models(expr("(A ==> B) & A & ~B & C & D"), self.VOCAB), 0)


class TestCNFAndResolution(unittest.TestCase):
    def test_cnf_sides_are_the_same_clause(self):
        lhs = to_cnf(expr("(Food ==> Party) | (Drinks ==> Party)"))
        rhs = to_cnf(expr("(Food & Drinks) ==> Party"))
        self.assertEqual(clauses_of(lhs), [frozenset({"~Food", "~Drinks", "Party"})])
        self.assertEqual(clauses_of(lhs), clauses_of(rhs))

    def test_cnf_is_equivalent(self):
        for text in ["A <=> (B | C)", "~(A & (B ==> C))", "(A & B) | (C & D)"]:
            s = expr(text)
            with self.subTest(sentence=text):
                self.assertTrue(is_valid(Expr("<=>", s, to_cnf(s))))

    def test_resolution_proves_q4(self):
        s = expr("((Food ==> Party) | (Drinks ==> Party)) ==> ((Food & Drinks) ==> Party)")
        entailed, proof = pl_resolution(Expr("True"), s)
        self.assertTrue(entailed)
        self.assertEqual(proof[-1][0], frozenset())        # ends with the empty clause

    def test_resolution_agrees_with_truth_tables(self):
        kb = expr("(B11 <=> (P12 | P21)) & ~B11")          # textbook example, Section 7.5.2
        self.assertTrue(pl_resolution(kb, expr("~P12"))[0])
        self.assertFalse(pl_resolution(kb, expr("P12"))[0])
        self.assertTrue(tt_entails(kb, expr("~P12")))


if __name__ == "__main__":
    unittest.main()
