"""Regression coverage for route isolation, cache-only execution and row selection."""

import sqlite3
import threading
import unittest
from unittest.mock import Mock

from carnot.config import load_config, solver_options, system_prompt_path
from carnot.llm_client import ClaudeCLI, CacheMissError
from carnot.selection import final_first_complete
from carnot.prospective import decision, zero_event_upper, paired_family_interval
from carnot.improvement_quality import endpoints
from carnot.campaign_integrity import require_preflight, require_evaluation_identity
from carnot.improvement_diversity import RoleCLI


class RouteIsolation(unittest.TestCase):
    def test_r5p_preserves_seen_route(self):
        r4, r5 = load_config("configs/r4.json"), load_config("configs/r5p.json")
        for k in ("model", "effort", "n_samples", "system_prompt", "exemplars", "max_retries", "sandbox"):
            self.assertEqual(r4[k], r5[k])
        self.assertEqual(solver_options(r4), solver_options(r5))
        self.assertEqual(system_prompt_path(r4), system_prompt_path(r5))
        self.assertNotEqual(system_prompt_path(r5), system_prompt_path(r5, "novel"))
        self.assertEqual(system_prompt_path(r4), system_prompt_path(r4, "novel"))


class CacheOnly(unittest.TestCase):
    def test_cache_miss_never_calls_model(self):
        client = ClaudeCLI.__new__(ClaudeCLI)
        client.model, client.effort, client.version = "fake", "medium", "test"
        client.cache_only = True
        client.lock = threading.Lock()
        client.db = sqlite3.connect(":memory:")
        client.db.execute("CREATE TABLE calls (key TEXT, response TEXT)")
        client._call = Mock(side_effect=AssertionError("model called"))
        try:
            with self.assertRaises(CacheMissError):
                client.complete("system", "user")
            client._call.assert_not_called()
        finally:
            client.db.close()


class CompleteSelection(unittest.TestCase):
    def test_final_consensus_precedes_checkpoint_consensus(self):
        samples = [{"final": "1", "a": "x"}, {"final": "1", "a": "y"},
                   {"final": "1", "a": "y"}, {"final": "2", "a": "x"}, {"final": "2", "a": "x"}]
        self.assertEqual(final_first_complete(samples, ["final", "a"])["index"], 1)

    def test_abstains_without_complete_majority(self):
        self.assertIsNone(final_first_complete([{"final": "1"}, {"final": "1"}, {"final": "2", "a": "x"}],
                                               ["final", "a"])["index"])

    def test_tie_is_deterministic(self):
        samples = [{"final": "1", "a": "a"}, {"final": "2", "a": "b"}]
        self.assertEqual(final_first_complete(samples, ["final", "a"])["index"], 0)


class ProspectiveGates(unittest.TestCase):
    def test_wide_interval_does_not_establish_noninferiority(self):
        self.assertEqual(decision(0, -0.05)["status"], "inconclusive")

    def test_no_changes_is_not_a_safety_certificate(self):
        self.assertEqual(decision(0, 0, all_differences_zero=True, independent_units=24)["status"], "inconclusive")
        self.assertGreater(zero_event_upper(24), 0.1)

    def test_invariance_and_statistical_evidence_are_distinct(self):
        self.assertEqual(decision(0, 0, invariant=True)["status"], "invariant")
        self.assertEqual(decision(0.02, 0.001)["status"], "non_inferior")

    def test_family_bootstrap_is_reproducible(self):
        a = paired_family_interval([0, 0.25, -0.25, 0], replicates=200)
        self.assertEqual(a, paired_family_interval([0, 0.25, -0.25, 0], replicates=200))
        self.assertEqual(a["families"], 4)


class ParameterEndpoints(unittest.TestCase):
    def test_exact_decimal_and_unique_corners(self):
        from fractions import Fraction
        params = {"x": {"kind": "decimal", "min": "0.1", "max": "0.3", "step": "0.1"},
                  "side": {"kind": "choice", "values": ["long", "short"]}}
        cases = endpoints(params)
        self.assertEqual(len(cases), 4)
        self.assertEqual(cases[0][1]["x"], Fraction(1, 10))
        self.assertEqual(cases[1][1], {"x": Fraction(3, 10), "side": "short"})


class ResumeIntegrity(unittest.TestCase):
    def test_existing_failed_smoke_does_not_authorize_runs(self):
        with self.assertRaises(RuntimeError):
            require_preflight({"fac": 0, "matched_slots": 2, "total_slots": 2})

    def test_stale_evaluation_is_rejected_for_each_input(self):
        saved = {"config_sha256": "c", "system_sha256": "p", "instances_sha256": "d"}
        require_evaluation_identity(saved, "c", "p", "d")
        for values in (("new", "p", "d"), ("c", "new", "d"), ("c", "p", "new")):
            with self.subTest(values=values), self.assertRaises(RuntimeError):
                require_evaluation_identity(saved, *values)


class DiversityRequests(unittest.TestCase):
    def test_direct_role_preserves_cache_identity_and_other_roles_are_isolated(self):
        client = RoleCLI.__new__(RoleCLI)
        client.roles = [{"model": "sonnet", "instruction": ""},
                        {"model": "opus", "instruction": "Derive independently."}]
        client.clients = {"sonnet": Mock(), "opus": Mock()}
        client.complete("system", "question", sample=0, tag="attempt0")
        client.clients["sonnet"].complete.assert_called_once_with(
            "system", "question", sample=0, tag="attempt0")
        client.clients["opus"].complete.assert_not_called()
        client.complete("system", "question", sample=1, tag="attempt1")
        client.clients["opus"].complete.assert_called_once_with(
            "system\n\nIndependent derivation role:\nDerive independently.",
            "question", sample=1, tag="attempt1")


if __name__ == "__main__":
    unittest.main()
