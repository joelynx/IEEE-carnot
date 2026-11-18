"""Paired comparison: weighted recomputation equals the official scorer; bootstrap mechanics."""

from __future__ import annotations

import unittest
from fractions import Fraction

from carnot import common, compare, harness


class WeightedEqualsOfficial(unittest.TestCase):
    def test_dev_with_errors(self):
        d = common.data()
        ids = d.ids("dev")
        rows = []
        for index, case_id in enumerate(ids):
            row = harness.target_row(case_id)
            if index % 7 == 0:
                row["final_answer"] = None
            if index % 5 == 0 and row["steps"]:
                row["steps"] = row["steps"][1:]  # an omitted slot is how the system abstains
            rows.append(row)
        scored = harness.score(rows, ids)
        cases = {
            c["case_id"]: {
                "fac": Fraction(c["fac"]),
                "checkpoint": Fraction(c["matched_slots"], c["total_slots"]) if c["total_slots"] else Fraction(0),
            }
            for c in scored["cases"]
        }
        recomputed = compare.weighted(cases, harness.cached_weights("dev290", ids))
        official = scored["report"]["scores"]
        self.assertLess(recomputed["fac"], 1)
        self.assertLess(recomputed["checkpoint"], 1)
        self.assertAlmostEqual(float(recomputed["fac"]), float(official["seen_fac"]), places=12)
        self.assertAlmostEqual(float(recomputed["checkpoint"]), float(official["seen_checkpoint"]), places=12)


class Bootstrap(unittest.TestCase):
    def test_zero_differences_give_zero_interval(self):
        ids = common.data().ids("dev")[:40]
        diffs = {c: {"fac": 0.0, "checkpoint": 0.0} for c in ids}
        draws = compare.bootstrap(diffs, compare.clusters(ids, "template"), 200, "t")
        self.assertEqual(compare.percentile_ci(draws["fac"]), (0.0, 0.0))

    def test_clusters_partition_cases(self):
        ids = common.data().ids("dev")
        for scheme in ("case", "template"):
            flat = [c for stratum in compare.clusters(ids, scheme) for unit in stratum for c in unit]
            self.assertEqual(sorted(flat), ids)

    def test_deterministic(self):
        ids = common.data().ids("dev")[:30]
        diffs = {c: {"fac": float(i % 3 == 0), "checkpoint": 0.5} for i, c in enumerate(ids)}
        strata = compare.clusters(ids, "case")
        self.assertEqual(compare.bootstrap(diffs, strata, 50, "s"), compare.bootstrap(diffs, strata, 50, "s"))

    def test_verdicts(self):
        self.assertTrue(compare.verdicts(0.01, 0.002, 0.02, 0.001)["improved"])
        self.assertTrue(compare.verdicts(-0.001, -0.003, 0.0, 0.001)["non_inferior"])
        self.assertFalse(compare.verdicts(-0.003, -0.005, -0.001, 0.001)["non_inferior"])


if __name__ == "__main__":
    unittest.main()
