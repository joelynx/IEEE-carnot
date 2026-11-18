"""Continuation runner (improvement_validation_v1): isolation, cache-only, resume and selectors."""

import json
import sqlite3
import tempfile
import threading
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

from carnot import common, splits
from carnot import improvement_validation_v1 as v1
from carnot.llm_client import CacheMissError, Response

from carnot.synth.answer_format import with_answer_format
from carnot.synth.template import DATASET_VERSION
from finreason_task1.contracts import QUESTION_SCHEMA_VERSION

SPEC = {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}
SLOT = {"slot_id": "a", "description": "Amount", "position": 1, "result_spec": SPEC}
CASE = "t1_synexample0000000000"
QUESTION = {"schema_version": QUESTION_SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "case_id": CASE,
            "question": with_answer_format("A firm has one dollar. What is it worth?", SPEC),
            "answer_spec": SPEC, "trace_spec": {"slots": [SLOT]}}
FIELDS = ["final", "a"]


def sample(final=None, a=None):
    texts = {k: v for k, v in (("final", final), ("a", a)) if v is not None}
    code = "def solve():\n    return {}"
    return {"texts": texts, "issues": {}, "attempts": [
        {"code": code, "rendered": texts, "sandbox": {"ok": True}, "cache_key": "k", "cached": True}]}


def pool(*rows):
    samples = [sample(*r) for r in rows]
    return {"samples": samples, "row": {"case_id": CASE, "plurality": True}, "votes": {},
            "dropped_by_gate": []}


class BalancedSelector(unittest.TestCase):
    def test_model_groups_have_equal_total_weight(self):
        self.assertEqual(sum(v1.JB_WEIGHTS[:3]), Fraction(1, 2))
        self.assertEqual(sum(v1.JB_WEIGHTS[3:]), Fraction(1, 2))

    def test_equal_group_support_breaks_by_earliest_role(self):
        texts = [{"final": "1", "a": "10"}] * 3 + [{"final": "2", "a": "20"}] * 2
        self.assertEqual(v1.balanced_complete_row(texts, FIELDS)["index"], 0)

    def test_two_opus_roles_outweigh_two_sonnet_roles(self):
        texts = [{"final": "1", "a": "10"}, {"final": "1", "a": "10"}, {"final": "3", "a": "30"},
                 {"final": "2", "a": "20"}, {"final": "2", "a": "20"}]
        choice = v1.balanced_complete_row(texts, FIELDS)
        self.assertEqual((choice["index"], choice["weight"], choice["roles"]), (3, "1/2", [3, 4]))

    def test_incomplete_roles_get_no_weight_and_no_redistribution(self):
        texts = [{"final": "1"}, {"final": "1"}, {"final": "1"}, {"final": "2", "a": "20"}, {"final": "3", "a": "30"}]
        choice = v1.balanced_complete_row(texts, FIELDS)
        self.assertEqual((choice["index"], choice["weight"]), (3, "1/4"))

    def test_rows_differing_only_in_a_checkpoint_do_not_pool(self):
        texts = [{"final": "1", "a": "10"}, {"final": "1", "a": "40"}, {}, {"final": "2", "a": "20"}, {}]
        self.assertEqual(v1.balanced_complete_row(texts, FIELDS)["index"], 3)

    def test_no_complete_row_abstains(self):
        self.assertIsNone(v1.balanced_complete_row([{"final": "1"}] * 5, FIELDS)["index"])


class PoolSelections(unittest.TestCase):
    def test_all_recipes_fall_back_to_the_field_plurality_row_without_complete_rows(self):
        d5 = pool(("1",), ("1",), ("2",), ("2",), (None,))
        chosen = v1.selections(QUESTION, d5, None, None, False)
        for name in ("D", "J", "JB", "X1", "X1C", "V"):
            self.assertEqual(chosen[name]["row"], d5["row"], name)
        self.assertEqual(chosen["JB"]["fallback"], "J")

    def test_complete_row_selection_rebuilds_a_valid_row(self):
        d5 = pool(("1", "10"), ("1", "10"), ("2", "20"), ("1",), (None,))
        chosen = v1.selections(QUESTION, d5, None, None, True)
        self.assertEqual(chosen["J"]["row"]["final_answer"], {"value": "1"})
        self.assertEqual(chosen["J"]["row"]["steps"], [{"slot_id": "a", "value": "10"}])
        self.assertEqual(chosen["V"]["reason"], "no_call")

    def test_supported_verifier_choice_selects_an_existing_candidate_without_edits(self):
        d5 = pool(("1", "10"), ("1", "10"), ("2", "20"), ("1", "10"), ("1", "10"))
        verdict = {"selected_original_index": 2, "reason": "supported_existing_candidate"}
        chosen = v1.selections(QUESTION, d5, None, verdict, True)
        self.assertEqual(chosen["V"]["row"]["final_answer"], {"value": "2"})
        self.assertEqual(chosen["J"]["row"]["final_answer"], {"value": "1"})

    def test_abstention_or_bad_evidence_keeps_j(self):
        d5 = pool(("1", "10"), ("2", "20"), ("2", "20"), ("1", "10"), ("1", "10"))
        for reason in ("verifier_abstained", "evidence_does_not_support_candidate", "malformed_response"):
            chosen = v1.selections(QUESTION, d5, None, {"selected_original_index": None, "reason": reason}, True)
            self.assertEqual(chosen["V"]["row"], chosen["J"]["row"])
            self.assertEqual(chosen["V"]["reason"], reason)

    def test_six_sample_arms_share_one_saved_sixth_sample(self):
        d5 = pool(("1", "10"), ("1", "10"), ("1", "10"), ("2", "20"), ("2", "20"))
        six = {"samples": d5["samples"] + [sample("2", "20")], "row": {"case_id": CASE, "six": True}}
        chosen = v1.selections(QUESTION, d5, six, None, True)
        self.assertEqual(chosen["X1"]["row"], six["row"])
        # 3-3 final tie: complete-row selection takes the earlier group.
        self.assertEqual(chosen["X1C"]["row"]["final_answer"], {"value": "1"})


class Isolation(unittest.TestCase):
    def setUp(self):
        self.loaded = splits.load()

    def panel(self, ids, **extra):
        return {"panel_id": "p", "kind": "tuning", "split": "tuning-eval", "partition": "regression",
                "case_ids": ids, "case_ids_sha256": common.sha256_text("\n".join(ids)), **extra}

    def test_test_lockbox_dev_and_leaderboard_cases_are_refused(self):
        for split in ("lockbox", "test928", "leaderboard580", "dev290"):
            with self.subTest(split=split), self.assertRaises(RuntimeError):
                v1.check_allowed(self.panel(self.loaded[split][:3]), None, "10", ["r4"])

    def test_tuning_panel_must_equal_its_split(self):
        with self.assertRaises(RuntimeError):
            v1.check_allowed(self.panel(sorted(self.loaded["tuning-eval"])[:10]), None, "10", ["r4"])
        v1.check_allowed(v1.tuning_panel("tuning-eval"), None, "10", ["r4"])

    def test_tuning_noex_matches_the_historical_definition(self):
        ids = v1.panel_case_ids("tuning-noex")
        self.assertEqual(len(ids), 2314)
        self.assertTrue(set(self.loaded["tuning-eval"]) <= set(ids))

    def test_confirmation_needs_a_matching_frozen_preregistration(self):
        panel = {"panel_id": "c", "kind": "synthetic", "partition": "confirmation", "case_ids": ["t1_synx"]}
        with self.assertRaises(RuntimeError):
            v1.check_allowed(panel, None, "sha", ["r4", "p"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prereg.json"
            path.write_text(json.dumps({"status": "frozen", "panel_sha256": "other", "arms": ["r4", "p"]}))
            with self.assertRaises(RuntimeError):
                v1.check_allowed(panel, path, "sha", ["r4", "p"])
            path.write_text(json.dumps({"status": "frozen", "panel_sha256": "sha", "arms": ["p", "r4"]}))
            v1.check_allowed(panel, path, "sha", ["r4", "p"])

    def test_question_loading_never_touches_gold(self):
        with mock.patch.object(common, "data", side_effect=AssertionError("gold loaded")):
            questions, templates, _ = v1.load_questions(v1.tuning_panel("tuning-eval"))
        self.assertEqual(len(questions), 580)
        self.assertTrue(all(templates.values()))
        with tempfile.TemporaryDirectory(dir=common.ROOT) as tmp:
            qpath = Path(tmp) / "questions.jsonl"
            sha = common.write_jsonl(qpath, [{"question": QUESTION, "family": "f"}])
            panel = {"kind": "synthetic", "case_ids": [CASE],
                     "question_files": [{"path": qpath.relative_to(common.ROOT).as_posix(), "sha256": sha}],
                     "gold_files": [{"path": "does/not/exist.jsonl", "sha256": "0"}]}
            questions, templates, _ = v1.load_questions(panel)
        self.assertEqual(templates, {CASE: None})

    def test_changed_question_file_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=common.ROOT) as tmp:
            qpath = Path(tmp) / "questions.jsonl"
            common.write_jsonl(qpath, [{"question": QUESTION}])
            panel = {"kind": "synthetic", "case_ids": [CASE],
                     "question_files": [{"path": qpath.relative_to(common.ROOT).as_posix(), "sha256": "stale"}]}
            with self.assertRaises(RuntimeError):
                v1.load_questions(panel)

    def test_scoring_refuses_before_predictions_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            panel = v1.tuning_panel("tuning-eval")
            (run / "panel.json").write_text(json.dumps(panel))
            sha = common.sha256_file(run / "panel.json")
            (run / "run.json").write_text(json.dumps({"panel_path": (run / "panel.json").as_posix(),
                                                      "identity": {"panel_sha256": sha}}))
            with mock.patch.object(common, "data", side_effect=AssertionError("gold loaded")), \
                    self.assertRaises(SystemExit):
                v1.score(Mock(run_dir=str(run), confirmation_prereg=None))


class Backend(unittest.TestCase):
    def client(self, model="m"):
        client = v1.StrictClient.__new__(v1.StrictClient)
        client.model, client.effort, client.version = model, "medium", "test"
        client.lock = threading.Lock()
        client.db = sqlite3.connect(":memory:")
        client.db.execute("CREATE TABLE calls (key TEXT PRIMARY KEY, created REAL, request TEXT, response TEXT)")
        client.sysprompt_dir = Path(tempfile.mkdtemp())
        return client

    def test_cache_only_never_calls_the_model(self):
        client = self.client()
        client.cache_only = True
        client._call = Mock(side_effect=AssertionError("model called"))
        with self.assertRaises(CacheMissError):
            client.complete("system", "user")
        client._call.assert_not_called()

    def test_substituted_model_stops_the_run(self):
        client = self.client("claude-opus-5-5")
        client.cache_only = False
        client._call = Mock(return_value={"result": "10", "modelUsage": {"claude-sonnet-5-5": {}}})
        with self.assertRaises(v1.ModelMismatch):
            client.complete("system", "user")


class Requests(unittest.TestCase):
    def test_direct_role_is_byte_identical_to_p_and_roles_are_isolated(self):
        roles = json.loads(v1.ROLES_PATH.read_text(encoding="utf-8"))
        clients = {"claude-sonnet-5-5": Mock(), "claude-opus-5-5": Mock()}
        role_client = v1.RoleClient(roles, clients)
        role_client.complete("SYS", "USER", sample=0, tag="attempt0")
        clients["claude-sonnet-5-5"].complete.assert_called_once_with("SYS", "USER", sample=0, tag="attempt0")
        role_client.complete("SYS", "USER", sample=4, tag="attempt1")
        system = clients["claude-opus-5-5"].complete.call_args.args[0]
        self.assertTrue(system.startswith("SYS\n\nIndependent derivation role:\n"))
        self.assertEqual(clients["claude-opus-5-5"].complete.call_args.kwargs, {"sample": 4, "tag": "attempt1"})

    def test_extra_sample_reuses_the_pool_and_makes_one_attempt(self):
        llm, box = Mock(), Mock()
        llm.complete.return_value = Response("no code", "m", {}, 0.0, False, "key")
        saved = [sample("1", "10") for _ in range(5)]
        solver = v1.SavedPoolSolver(llm, box, "SYS", 0, saved=saved, hints="v2", echo=True)
        outcome = solver.solve(QUESTION, [], 6)
        self.assertEqual(llm.complete.call_count, 1)
        self.assertEqual(llm.complete.call_args.kwargs, {"sample": 5, "tag": "attempt0"})
        self.assertEqual(len(outcome["samples"][5]["attempts"]), 1)
        self.assertEqual(outcome["row"]["final_answer"], {"value": "1"})

    def test_seen_questions_are_delegated_to_the_unchanged_r4_seen_solver(self):
        made = []

        class FakeClient:
            def __init__(self, model, effort):
                self.model, self.effort, self.cache_only, self.version = model, effort, False, "test"
                made.append((model, effort))

        with mock.patch.object(v1, "StrictClient", FakeClient), mock.patch.object(v1, "make_sandbox", Mock()):
            gen = v1.Generator(v1.ARMS, "S", 500, "routed", True, False)
        r4 = v1.load_config(v1.R4_CONFIG)
        self.assertEqual((gen.seen_solver.llm.model, gen.seen_solver.llm.effort), (r4["model"], r4["effort"]))
        self.assertEqual(gen.seen_solver.system, (common.ROOT / r4["system_prompt"]).read_text(encoding="utf-8"))
        self.assertEqual((gen.seen_solver.hints, gen.seen_solver.echo), (r4["unit_hints"], r4["echo_notes"]))
        self.assertEqual(gen.solvers["r4"].system, gen.seen_solver.system)
        self.assertNotEqual(gen.solvers["p"].system, gen.seen_solver.system)
        gen.router = Mock(is_novel=Mock(return_value=False))
        gen.seen_solver = Mock(solve=Mock(return_value={"row": {"seen": True}}))
        record = gen.run_case(QUESTION, "tpl")
        self.assertEqual(record["route"], "seen")
        self.assertEqual(gen.seen_solver.solve.call_args.args[2:4], (1, 0))
        self.assertEqual({k: v["row"] for k, v in record["selections"].items()},
                         {k: {"seen": True} for k in v1.RECIPES})


class Resume(unittest.TestCase):
    def test_saved_cases_are_skipped_and_stale_ones_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "cases").mkdir()
            (run / "cases" / "a.json").write_text(json.dumps({"identity_sha256": "I", "question_sha256": "qa"}))
            self.assertEqual(v1.pending_cases(run, ["a", "b"], "I", {"a": "qa", "b": "qb"}), ["b"])
            with self.assertRaises(RuntimeError):
                v1.pending_cases(run, ["a", "b"], "J", {"a": "qa", "b": "qb"})
            with self.assertRaises(RuntimeError):
                v1.pending_cases(run, ["a", "b"], "I", {"a": "changed", "b": "qb"})

    def test_predictions_are_deterministic_and_written_once_per_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for c in ("b", "a"):
                v1.save_json(run / "cases" / f"{c}.json", {"selections": {
                    "R4": {"row": {"case_id": c}}, "P": {"row": {"case_id": c, "p": 1}}}})
            first = v1.write_predictions(run, ["b", "a"], ["r4", "p"])
            self.assertEqual(sorted(first), ["P", "R4"])
            self.assertEqual(first, v1.write_predictions(run, ["a", "b"], ["r4", "p"]))
            rows = common.read_jsonl(run / "predictions" / "R4.jsonl")
            self.assertEqual([r["case_id"] for r in rows], ["a", "b"])

    def test_case_order_is_a_fixed_permutation(self):
        panel = v1.tuning_panel("tuning-eval")
        order = v1.case_order(panel)
        self.assertEqual(order, v1.case_order(panel))
        self.assertEqual(sorted(order), panel["case_ids"])
        self.assertNotEqual(order, panel["case_ids"])


if __name__ == "__main__":
    unittest.main()
