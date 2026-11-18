"""Slot-convention examples: never from the question's own template; defaults leave prompts unchanged."""

from __future__ import annotations

import json
import unittest

from carnot import common, exemplars, splits
from carnot.conventions import SlotConventions
from carnot.solver import build_user_prompt, describe_spec


class Conventions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conv = SlotConventions("tuning", 2)
        cls.d = common.data()

    def test_never_own_template(self):
        for case_id in splits.load()["tuning-eval"][:200]:
            question, template = self.d.questions[case_id], self.d.template(case_id)
            block = self.conv.block(question, template)
            if block:
                own = [c for c in splits.load()["tuning"] if self.d.template(c) == template]
                for c in own:
                    body = self.d.questions[c]["question"].split("\n\nAnswer format:")[0].strip()
                    self.assertNotIn(body, block)

    def test_some_questions_get_examples(self):
        ids = splits.load()["tuning-eval"]
        hits = sum(self.conv.block(self.d.questions[c], self.d.template(c)) is not None for c in ids)
        self.assertGreater(hits, 50)

    def test_defaults_unchanged(self):
        ef = json.loads((common.ROOT / "exemplars/r0_exemplars.json").read_text(encoding="utf-8"))
        c = splits.load()["tuning-eval"][0]
        chosen = exemplars.select(ef, self.d.template(c), "S")
        self.assertEqual(build_user_prompt(self.d.questions[c], chosen), build_user_prompt(self.d.questions[c], chosen, "v1", None))

    def test_dimensionless_hint_v2(self):
        spec = {"type": "decimal", "unit": "dimensionless", "rounding": {"mode": "exact"}}
        self.assertIn("0.0525, not 5.25", describe_spec(spec, "v1"))
        self.assertNotIn("0.0525, not 5.25", describe_spec(spec, "v2"))
        ratio = {"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}
        self.assertEqual(describe_spec(ratio, "v1"), describe_spec(ratio, "v2"))


if __name__ == "__main__":
    unittest.main()
