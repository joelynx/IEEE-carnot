"""Synthetic template engine: sampling, display, toolkit validation, novelty, error messages."""

from __future__ import annotations

import random
import unittest
from fractions import Fraction

from carnot.config import load_config, make_sandbox
from carnot.synth import template as T

HAND = {  # engine test only; not part of any synthetic set
    "name": "engine_check_fee_drag", "domain_id": "personal_finance", "topic_id": "engine_check",
    "difficulty": "basic",
    "params": {"B": {"kind": "int", "min": 1000, "max": 9000, "step": 500},
               "f": {"kind": "decimal", "min": "0.25", "max": "2.5", "step": "0.25"},
               "who": {"kind": "choice", "values": ["saver", "retiree"]}},
    "question_template": "Use exact arithmetic. A {who} holds a balance of B={B} USD in a wrapper charging an annual fee of f={f} percent of the balance, levied once at year end. Compute the year-end fee in USD and the balance after the fee.",
    "answer_spec": {"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}},
    "slots": [{"slot_id": "engine_fee_rate_trace", "description": "Exact fee rate as a plain fraction of the balance.",
               "result_spec": {"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}},
              {"slot_id": "engine_fee_usd_trace", "description": "Exact fee in USD.",
               "result_spec": {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}}],
    "program": "def solve():\n    rate = P['f'] / 100\n    fee = P['B'] * rate\n    return {'final': P['B'] - fee, 'engine_fee_rate_trace': rate, 'engine_fee_usd_trace': fee}\n",
}


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sandbox = make_sandbox(load_config("configs/r1.json"))

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.close()

    def test_generates_valid_novel_instances(self):
        out = T.generate(HAND, "test", 3, self.sandbox)
        self.assertEqual(len(out.instances), 3)
        first = out.instances[0]
        self.assertTrue(first.question["question"].endswith("with no unit label or additional text."))
        self.assertTrue(first.question["case_id"].startswith("t1_syn"))
        fee = Fraction(first.params["B"]) * Fraction(first.params["f"]) / 100
        self.assertEqual(Fraction(first.gold["slot_values"]["engine_fee_usd_trace"]), fee)

    def test_display_strips_trailing_zeros(self):
        spec = {"kind": "decimal", "min": "0", "max": "5", "step": "0.25"}
        self.assertEqual(T._display(Fraction(4), spec), "4")
        self.assertEqual(T._display(Fraction(-21, 4), spec), "-5.25")
        self.assertEqual(T._display(Fraction(1, 2), spec), "0.5")

    def test_sampling_is_seeded(self):
        a = T.sample(HAND["params"], random.Random("x#1"))
        self.assertEqual(a, T.sample(HAND["params"], random.Random("x#1")))

    def test_static_errors(self):
        bad = dict(HAND, question_template=HAND["question_template"].replace("{who}", "someone"))
        with self.assertRaisesRegex(T.TemplateError, "unused"):
            T.check_template(bad)
        bad = dict(HAND, params=dict(HAND["params"], f={"kind": "decimal", "min": "0.25", "max": "2.6", "step": "0.25"}))
        with self.assertRaisesRegex(T.TemplateError, "whole number of steps"):
            T.check_template(bad)


if __name__ == "__main__":
    unittest.main()
