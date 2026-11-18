"""The synthetic "Answer format:" sentence reproduces every released train and dev question."""

from __future__ import annotations

import re
import unittest

from carnot import common
from carnot.synth.answer_format import answer_format

SUFFIX = re.compile(r"\n\nAnswer format: (.*)\Z", re.S)


class AnswerFormat(unittest.TestCase):
    def test_matches_all_train_and_dev(self):
        d = common.data()
        ids = d.ids("train") + d.ids("dev")
        for case_id in ids:
            question = d.questions[case_id]
            self.assertEqual(answer_format(question["answer_spec"]), SUFFIX.search(question["question"]).group(1), case_id)
        self.assertEqual(len(ids), 3190)

    def test_unattested_forms_rejected(self):
        with self.assertRaises(ValueError):
            answer_format({"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 3}})


if __name__ == "__main__":
    unittest.main()
