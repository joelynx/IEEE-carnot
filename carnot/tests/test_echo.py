"""Echo notes: generic trigger, train-validated scope, defaults unchanged, R4 config diff."""

from __future__ import annotations

import json
import unittest

from carnot import common, exemplars, splits
from carnot.config import load_config
from carnot.solver import build_user_prompt, echoed_slots, output_table


class Echo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = common.data()

    def test_trigger_scope_in_train(self):
        hits = {self.d.template(c) for c in self.d.ids("train") + self.d.ids("dev") if echoed_slots(self.d.questions[c])}
        self.assertEqual(hits, {"fp.personal_finance.taxcalc.standard_deduction.basic.v1",
                                "fp.personal_finance.taxcalc.capital_gains.intermediate.v1"})

    def test_note_only_when_enabled(self):
        c = next(c for c in splits.load()["tuning-eval"] if echoed_slots(self.d.questions[c]))
        q = self.d.questions[c]
        self.assertNotIn("belongs to slot", output_table(q, "v2"))
        self.assertIn("belongs to slot", output_table(q, "v2", echo=True))
        other = next(c for c in splits.load()["tuning-eval"] if not echoed_slots(self.d.questions[c]))
        self.assertEqual(output_table(self.d.questions[other], "v2"), output_table(self.d.questions[other], "v2", echo=True))

    def test_defaults_unchanged(self):
        ef = json.loads((common.ROOT / "exemplars/r0_exemplars.json").read_text(encoding="utf-8"))
        c = next(c for c in splits.load()["tuning-eval"] if echoed_slots(self.d.questions[c]))
        chosen = exemplars.select(ef, self.d.template(c), "S")
        self.assertEqual(build_user_prompt(self.d.questions[c], chosen), build_user_prompt(self.d.questions[c], chosen, "v1", None, False))

    def test_r4_differs_from_r3_only_in_hints_and_echo(self):
        r3, r4 = load_config("configs/r3.json"), load_config("configs/r4.json")
        for key in ("model", "effort", "system_prompt", "exemplars", "n_samples", "max_retries", "sandbox"):
            self.assertEqual(r3[key], r4[key], key)
        self.assertEqual((r4["unit_hints"], r4["echo_notes"]), ("v2", True))
        self.assertNotIn("unit_hints", r3)
        self.assertEqual({**r4["routing"]["novel"], "echo_notes": None}, {**r3["routing"]["novel"], "echo_notes": None})


if __name__ == "__main__":
    unittest.main()
