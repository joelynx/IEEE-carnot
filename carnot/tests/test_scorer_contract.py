"""Edge-case tests of the organiser scorer and validator (PLAN.md §5.1).

These pin down the frozen contract we optimise against; they test the toolkit,
not our code, so a failure means our reading of the contract is wrong.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from fractions import Fraction

from carnot import common  # noqa: F401
from finreason_task1.contracts import (
    ContractError,
    load_jsonl_bytes,
    validate_prediction_record,
)
from finreason_task1.scoring import ranking_value, score_case, score_submission

CASE = "t1_aaaaaaaaaaaaaaaaaaaa"


def question(case_id=CASE, answer_spec=None, slots=None):
    return {
        "schema_version": "finreason.task1.question/2.0.0",
        "dataset_version": "task1-v4",
        "case_id": case_id,
        "question": "Fixture question.",
        "answer_spec": answer_spec
        or {"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}},
        "trace_spec": {"slots": slots if slots is not None else [
            {"slot_id": "ratio_slot", "position": 1, "description": "A ratio.",
             "result_spec": {"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}},
            {"slot_id": "pct_slot", "position": 2, "description": "A percent.",
             "result_spec": {"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}},
        ]},
    }


def gold(final="2.35", slots=None, case_id=CASE):
    return {
        "schema_version": "finreason.task1.gold/2.0.0",
        "dataset_version": "task1-v4",
        "case_id": case_id,
        "final_value": final,
        "slot_values": slots if slots is not None else {"ratio_slot": "1/3", "pct_slot": "5.76"},
    }


def pred(final, steps=(), case_id=CASE):
    return {
        "schema_version": "finreason.task1.prediction/1.0.0",
        "dataset_version": "task1-v4",
        "case_id": case_id,
        "final_answer": None if final is None else {"value": final},
        "steps": [{"slot_id": k, "value": v} for k, v in steps],
    }


def fac(final, gold_final="2.35", answer_spec=None):
    q = question(answer_spec=answer_spec)
    return score_case(q, gold(final=gold_final), pred(final)).fac


def issues(row, q=None):
    return [i.code for i in validate_prediction_record(row, q or question())]


class HalfUpBoundaries(unittest.TestCase):
    def test_tie_rounds_up(self):
        self.assertEqual(fac("2.345"), 1)

    def test_just_below_tie(self):
        self.assertEqual(fac("2.3449999"), 0)

    def test_above(self):
        self.assertEqual(fac("2.355"), 0)

    def test_negative_tie_rounds_away_from_zero(self):
        self.assertEqual(fac("-1.235", gold_final="-1.24"), 1)

    def test_negative_zero(self):
        self.assertEqual(fac("-0.004", gold_final="0.00"), 1)

    def test_exponent_form(self):
        self.assertEqual(fac("2.35e0"), 1)

    def test_unpadded(self):
        self.assertEqual(fac("12314", gold_final="12314.00"), 1)


class ExactMode(unittest.TestCase):
    spec = {"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}

    def test_rational(self):
        self.assertEqual(fac("1/3", "1/3", self.spec), 1)

    def test_truncated_decimal_fails(self):
        self.assertEqual(fac("0.3333333333", "1/3", self.spec), 0)

    def test_float_noise_fails(self):
        self.assertEqual(fac("178.50000000000003", "178.5", self.spec), 0)

    def test_terminating_decimal(self):
        self.assertEqual(fac("0.25", "0.25", self.spec), 1)

    def test_reducible_rational_invalid(self):
        self.assertIn("E_VALUE", issues(pred("2/6"), question(answer_spec=self.spec)))

    def test_terminating_rational_invalid(self):
        self.assertIn("E_VALUE", issues(pred("1/4"), question(answer_spec=self.spec)))


class PercentIsNotConverted(unittest.TestCase):
    def test_percent_vs_fraction(self):
        q = question()
        result = score_case(q, gold(), pred("2.35", [("ratio_slot", "1/3"), ("pct_slot", "0.0576")]))
        self.assertEqual((result.fac, result.matched_slots), (1, 1))


class Steps(unittest.TestCase):
    def test_missing_slot_only_loses_that_slot(self):
        result = score_case(question(), gold(), pred("2.35", [("ratio_slot", "1/3")]))
        self.assertEqual((result.matched_slots, result.total_slots), (1, 2))

    def test_unknown_slot(self):
        self.assertIn("E_SLOT_ID", issues(pred("2.35", [("nope", "1")])))

    def test_out_of_order(self):
        self.assertIn("E_SLOT_ORDER", issues(pred("2.35", [("pct_slot", "1"), ("ratio_slot", "1")])))

    def test_duplicate(self):
        self.assertIn("E_SLOT_ID", issues(pred("2.35", [("ratio_slot", "1"), ("ratio_slot", "1")])))

    def test_null_step_value(self):
        row = pred("2.35")
        row["steps"] = [{"slot_id": "ratio_slot", "value": None}]
        self.assertIn("E_VALUE", issues(row))

    def test_invalid_file_raises_before_scoring(self):
        q = question()
        with self.assertRaises(ContractError):
            score_case(q, gold(), pred("2.35", [("nope", "1")]))

    def test_zero_slot_case_has_no_checkpoint(self):
        q = question(slots=[])
        result = score_case(q, gold(slots={}), pred("2.35"))
        self.assertIsNone(result.trace_accuracy)


class Types(unittest.TestCase):
    def test_bad_decimal_strings(self):
        for text in ("5%", "$5", "1,000", "+5", "05", "5.", " 5"):
            with self.subTest(text=text):
                self.assertIn("E_VALUE", issues(pred(text)))

    def test_number_instead_of_string(self):
        row = pred(None)
        row["final_answer"] = {"value": 2.35}
        self.assertIn("E_VALUE", issues(row))

    def test_enum_case_sensitive(self):
        spec = {"type": "enum", "allowed_values": ["false", "true"]}
        q = question(answer_spec=spec)
        self.assertIn("E_VALUE", issues(pred("True"), q))
        self.assertEqual(issues(pred("true"), q), [])


class FileLevel(unittest.TestCase):
    def test_encodings(self):
        good = (json.dumps(pred("1")) + "\n").encode()
        self.assertTrue(load_jsonl_bytes(good).valid)
        for bad in (good.replace(b"\n", b"\r\n"), b"\xef\xbb\xbf" + good, good + b"\n", good[:-1]):
            self.assertFalse(load_jsonl_bytes(bad).valid)

    def test_wrong_dataset_version(self):
        row = pred("2.35")
        row["dataset_version"] = "task1-v3"
        self.assertIn("E_DATASET_VERSION", issues(row))

    def test_extra_key(self):
        row = pred("2.35")
        row["note"] = "x"
        self.assertIn("E_SCHEMA", issues(row))


def _two_stratum_fixture():
    """12 domains x 1 topic; seen: basic/intermediate/advanced, hidden: intermediate/advanced."""

    questions, golds, manifest = {}, {}, []
    n = 0
    for d in range(12):
        for stratum, split, difficulties in (
            ("seen", "test_private_seen", ("basic", "intermediate", "advanced")),
            ("hidden", "test_private_hidden", ("intermediate", "advanced")),
        ):
            for diff in difficulties:
                n += 1
                case_id = f"t1_{n:020d}"
                q = question(case_id=case_id, slots=[
                    {"slot_id": "s", "position": 1, "description": "A slot.",
                     "result_spec": {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}}])
                questions[case_id] = q
                golds[case_id] = gold(case_id=case_id, slots={"s": "1"})
                manifest.append({
                    "schema_version": "finreason.task1.manifest/1.0.0", "dataset_version": "task1-v4",
                    "case_id": case_id, "split": split, "domain_id": f"domain_{d}", "topic_id": "topic",
                    "template_id": f"{stratum}.{d}.{diff}", "difficulty": diff, "structure_stratum": stratum,
                    "question_sha256": hashlib.sha256(json.dumps(
                        q, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                })
    return questions, golds, manifest


class Aggregation(unittest.TestCase):
    def test_combined_is_half_seen_half_hidden(self):
        questions, golds, manifest = _two_stratum_fixture()
        by_id = {m["case_id"]: m for m in manifest}
        # Correct on every hidden case, wrong on every seen case.
        preds = [pred("2.35" if by_id[c]["structure_stratum"] == "hidden" else "0", [("s", "1")], case_id=c)
                 for c in questions]
        report = score_submission(questions, golds, preds, manifest)
        self.assertEqual((report.seen_fac, report.hidden_fac, report.combined_fac),
                         (Fraction(0), Fraction(1), Fraction(1, 2)))
        self.assertEqual(report.ranking_tuple, ("0.500000", "1.000000", "1.000000"))

    def test_missing_difficulty_cell_raises(self):
        questions, golds, manifest = _two_stratum_fixture()
        drop = next(m["case_id"] for m in manifest if m["difficulty"] == "basic")
        manifest = [m for m in manifest if m["case_id"] != drop]
        del questions[drop], golds[drop]
        with self.assertRaises(ContractError):
            score_submission(questions, golds, [pred("0", case_id=c) for c in questions], manifest)

    def test_ranking_value_half_even(self):
        self.assertEqual(ranking_value(Fraction(1, 2_000_000)), "0.000000")
        self.assertEqual(ranking_value(Fraction(3, 2_000_000)), "0.000002")


if __name__ == "__main__":
    unittest.main()
