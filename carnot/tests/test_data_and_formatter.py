"""End-to-end targets check, formatter round-trip on all gold, official weights."""

from __future__ import annotations

import unittest
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction

from carnot import common, harness
from carnot.formatter import build_row, parse_gold_value, render
from finreason_task1.contracts import validate_prediction_record


class Release(unittest.TestCase):
    def test_downloads_match_manifests(self):
        hashes = common.verify_release()
        self.assertEqual(
            hashes["release_manifest.json"],
            "78ba29228132323b5b54eddf1d1d4cc46defbce3559b4752d0cbf6773a9422f7",
        )


class TargetsEndToEnd(unittest.TestCase):
    def check(self, source):
        d = common.data()
        ids = d.ids(source)
        targets = {row["case_id"]: row for row in common.read_jsonl(common.DEV_DIR / f"{source}_targets.jsonl")}
        result = harness.score([targets[c] for c in ids], ids)
        scores = result["report"]["scores"]
        self.assertEqual((scores["seen_fac"], scores["seen_checkpoint"]), ("1", "1"))
        self.assertEqual([harness.target_row(c) for c in ids], [targets[c] for c in ids])

    def test_train(self):
        self.check("train")

    def test_dev(self):
        self.check("dev")


class FormatterRoundTrip(unittest.TestCase):
    def test_all_gold_fields(self):
        d = common.data()
        checked = 0
        for case_id, g in d.gold.items():
            q = d.questions[case_id]
            fields = [(q["answer_spec"], g["final_value"])] + [
                (slot["result_spec"], g["slot_values"][slot["slot_id"]]) for slot in q["trace_spec"]["slots"]
            ]
            for spec, text in fields:
                rendered = render(parse_gold_value(text, spec), spec)
                self.assertEqual(rendered.text, text, (case_id, spec, text))
                checked += 1
            row, dropped = build_row(
                q, g["final_value"], {k: v for k, v in g["slot_values"].items()}
            )
            self.assertEqual(dropped, [])
            self.assertEqual(validate_prediction_record(row, q), ())
        self.assertEqual(checked, 3091 + 5379 + 418)

    def test_rendering_rules(self):
        exact = {"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}
        half2 = {"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}
        boolean = {"type": "enum", "allowed_values": ["false", "true"]}
        tiers = {"type": "enum", "allowed_values": ["low_risk", "high_risk"]}
        self.assertEqual(render(Fraction(1, 3), exact).text, "1/3")
        self.assertEqual(render(Fraction(-7, 4), exact).text, "-1.75")
        self.assertEqual(render(Fraction(12), exact).text, "12")
        self.assertIsNone(render(Decimal("1.4142135623730950488016887242096980785696718753769480"), exact).text)
        self.assertIsNone(render(1.5, exact).text)
        self.assertEqual(render(Fraction(2345, 1000), half2).text, "2.35")
        self.assertEqual(render(Fraction(-1, 1000), half2).text, "0.00")
        self.assertEqual(render(1.005, half2).flags, ["float"])
        self.assertEqual(render(True, boolean).text, "true")
        self.assertEqual(render("High_Risk", tiers).text, "high_risk")
        self.assertIsNone(render("medium", tiers).text)
        self.assertIsNone(render(True, tiers).text)

    def test_gate_drops_only_bad_fields(self):
        d = common.data()
        q = next(
            q for c, q in sorted(d.questions.items())
            if d.source[c] == "dev" and len(q["trace_spec"]["slots"]) == 3
            and all(s["result_spec"]["type"] == "decimal" for s in q["trace_spec"]["slots"])
        )
        slots = [s["slot_id"] for s in q["trace_spec"]["slots"]]
        row, dropped = build_row(q, "not-a-number", {slots[0]: "1", slots[1]: "05", slots[2]: "2"})
        self.assertIsNone(row["final_answer"])
        self.assertEqual(sorted(dropped), sorted(["final", slots[1]]))
        self.assertEqual([s["slot_id"] for s in row["steps"]], [slots[0], slots[2]])


class OfficialWeights(unittest.TestCase):
    def test_dev_weights_depend_only_on_topics_per_domain(self):
        d = common.data()
        ids = d.ids("dev")
        weights = harness.cached_weights("dev290", ids)
        topics = defaultdict(set)
        for c in ids:
            topics[d.manifest[c]["domain_id"]].add(d.manifest[c]["topic_id"])
        for c in ids:
            t_d = len(topics[d.manifest[c]["domain_id"]])
            self.assertEqual(weights[c]["fac"], Fraction(1, 60 * t_d))
        self.assertEqual(sum(w["fac"] for w in weights.values()), 1)
        self.assertEqual(sum(w["checkpoint"] for w in weights.values()), 1)


if __name__ == "__main__":
    unittest.main()
