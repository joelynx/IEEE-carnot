"""R1 routing rule: identical to the §2.4 proxy, train-driven, generic."""

from __future__ import annotations

import unittest

from carnot import common, splits
from carnot.config import load_config
from carnot.routing import NoveltyRouter, skeleton


class Routing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = NoveltyRouter()
        cls.d = common.data()

    def count(self, ids):
        return sum(self.router.is_novel(self.d.questions[c]) for c in ids)

    def test_train_and_gold_splits_are_seen(self):
        self.assertEqual(self.count(self.d.ids("train")), 0)
        self.assertEqual(self.count(splits.load()["lockbox"]), 0)

    def test_test_proxy_count_matches_section_2_4(self):
        self.assertEqual(self.count(self.d.ids("test")), 348)

    def test_skeleton_masks_numbers_and_format_suffix(self):
        a = skeleton("A bond pays 5.25% on $1,000.\n\nAnswer format: x")
        self.assertEqual(a, skeleton("a  bond pays 7% on $250.\n\nAnswer format: y"))

    def test_r1_config_seen_path_is_r0(self):
        r0, r1 = load_config("configs/r0.json"), load_config("configs/r1.json")
        for key in ("model", "effort", "system_prompt", "exemplars", "n_samples", "max_retries", "sandbox"):
            self.assertEqual(r0[key], r1[key], key)

    def test_r2_differs_from_r1_only_in_novel_model(self):
        r1, r2 = load_config("configs/r1.json"), load_config("configs/r2.json")
        for key in ("model", "effort", "system_prompt", "exemplars", "n_samples", "max_retries", "sandbox"):
            self.assertEqual(r1[key], r2[key], key)
        novel1, novel2 = r1["routing"]["novel"], r2["routing"]["novel"]
        self.assertEqual({**novel1, "model": None}, {**novel2, "model": None})
        self.assertEqual((novel1["model"], novel2["model"]), ("claude-sonnet-5-5", "claude-opus-5-5"))

    def test_r3_differs_from_r1_only_in_novel_unit_hints(self):
        r1, r3 = load_config("configs/r1.json"), load_config("configs/r3.json")
        for key in ("model", "effort", "system_prompt", "exemplars", "n_samples", "max_retries", "sandbox"):
            self.assertEqual(r1[key], r3[key], key)
        self.assertNotIn("unit_hints", r3)
        self.assertEqual({**r3["routing"]["novel"], "unit_hints": None}, {**r1["routing"]["novel"], "unit_hints": None})
        self.assertEqual(r3["routing"]["novel"]["unit_hints"], "v2")


if __name__ == "__main__":
    unittest.main()
