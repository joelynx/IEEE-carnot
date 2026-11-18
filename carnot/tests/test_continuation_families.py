"""Continuation family tooling: design rule, coverage grid, draw recovery and program comparison."""

import copy
import json
import unittest
from collections import Counter
from fractions import Fraction

from carnot import continuation_families_v1 as fam
from carnot.sandbox.executor import Sandbox
from carnot.synth.template import TemplateError

TPL = {
    "name": "simple_fee", "domain_id": "fintech", "topic_id": "payment_technologies", "difficulty": "intermediate",
    "params": {"A": {"kind": "int", "min": 100, "max": 500, "step": 100},
               "R": {"kind": "decimal", "min": "1.5", "max": "3.0", "step": "0.5"},
               "SIDE": {"kind": "choice", "values": ["buyer", "seller"]}},
    "question_template": "{A} {R} {SIDE}",
    "answer_spec": {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}},
    "slots": [{"slot_id": "fee", "description": "Fee", "result_spec": {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}}],
    "program": ("def solve():\n    if P['A'] == 500 and P['SIDE'] == 'seller':\n        raise ValueError('invalid')\n"
                "    fee = P['A'] * P['R'] / 100\n    total = P['A'] + fee if P['SIDE'] == 'buyer' else P['A'] - fee\n"
                "    return {'final': total, 'fee': fee}\n"),
    "coverage_params": [{"A": 100, "R": "1.5", "SIDE": "buyer"}, {"A": 500, "R": "3.0", "SIDE": "seller"}],
}


class Design(unittest.TestCase):
    def test_frozen_design_satisfies_the_preregistered_table(self):
        families = fam.validate_design(fam.read_json(fam.DESIGN))
        self.assertEqual(len(families), 96)
        per_domain = Counter(f["domain_id"] for f in families)
        self.assertEqual(set(per_domain.values()), {8})
        a_pairs = Counter(f["mechanism_class"] for f in families if f["slot"] == "A" and f["member"] == 0)
        self.assertEqual(set(a_pairs.values()), {4})

    def test_class_table_violation_is_rejected(self):
        design = copy.deepcopy(fam.read_json(fam.DESIGN))
        design["pairs"][0]["mechanism_class"] = "O"
        with self.assertRaises(RuntimeError):
            fam.validate_design(design)


class Coverage(unittest.TestCase):
    def test_grid_values_are_exact_and_checked(self):
        sets = fam.coverage_sets(TPL)
        self.assertEqual(sets[0]["R"], Fraction(3, 2))
        for bad in ({"A": 150, "R": "1.5", "SIDE": "buyer"}, {"A": 100, "R": "1.75", "SIDE": "buyer"},
                    {"A": 100, "R": "1.5", "SIDE": "broker"}, {"A": 100, "R": "1.5"}):
            with self.subTest(bad=bad), self.assertRaises(TemplateError):
                fam.coverage_sets(dict(TPL, coverage_params=[bad, TPL["coverage_params"][0]]))
        with self.assertRaises(TemplateError):
            fam.coverage_sets(dict(TPL, coverage_params=[TPL["coverage_params"][0]]))


class Programs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.box = Sandbox("local", timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.box.close()

    def sets(self):
        return [("draw_x", fam.draw_values(TPL, 3))] + [(f"coverage_{i}", p) for i, p in enumerate(fam.coverage_sets(TPL))]

    def test_independent_equivalent_program_matches(self):
        alt = ("def solve():\n    fee = P['R'] * P['A'] / 100\n    sign = 1 if P['SIDE'] == 'buyer' else -1\n"
               "    return {'final': P['A'] + sign * fee, 'fee': fee}\n")
        result = fam.compare_programs(self.box, TPL, alt, self.sets())
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["compared"], 2)  # the seller corner is declared invalid by the reference
        self.assertIn({"set": "coverage_1", "reference": "declared_invalid"}, result["rows"])

    def test_different_interpretation_is_a_mismatch_and_not_an_error(self):
        alt = "def solve():\n    fee = P['A'] * P['R'] / 100\n    return {'final': P['A'] + fee, 'fee': fee}\n"
        sets = [("coverage_seller", {"A": 100, "R": Fraction(2), "SIDE": "seller"})]
        result = fam.compare_programs(self.box, TPL, alt, sets)
        self.assertEqual(result["mismatches"][0]["fields"], {"final": ["98", "102"]})
        self.assertEqual(result["second_errors"], [])

    def test_draw_values_are_deterministic_and_on_grid(self):
        values = fam.draw_values(TPL, 5)
        self.assertEqual(values, fam.draw_values(TPL, 5))
        self.assertIn(values["SIDE"], ("buyer", "seller"))
        self.assertEqual((values["R"] / Fraction(1, 2)).denominator, 1)


if __name__ == "__main__":
    unittest.main()
