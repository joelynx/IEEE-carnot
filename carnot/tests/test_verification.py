import json
import unittest
from unittest.mock import Mock

from carnot.verification import candidate_packet, check_evidence
from carnot.improvement_sampling_control import SavedPoolSolver


SPEC = {"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}
QUESTION = {"case_id": "synthetic_example", "question": "Return one USD.", "answer_spec": SPEC,
            "trace_spec": {"slots": []}}


def sample(value, model):
    texts = {"final": value}
    return {"texts": texts, "attempts": [{"code": f"def solve():\n    return {{'final': {value}}}",
                                          "rendered": texts, "sandbox": {"ok": True}, "model_id": model}]}


class VerifierContract(unittest.TestCase):
    def test_sampling_control_reuses_saved_candidates_without_calls(self):
        llm, box = Mock(), Mock()
        saved = {"texts": {"final": "1"}, "issues": {}, "attempts": []}
        solver = SavedPoolSolver(llm, box, "system", 0, saved=[saved])
        result = solver.solve_sample(QUESTION, [], 0)
        self.assertEqual(result.texts, saved["texts"])
        llm.complete.assert_not_called()
        box.run.assert_not_called()

    def test_packet_hides_identities_and_multiplicity_and_is_reproducible(self):
        samples = [sample("1", "secret_a"), sample("1", "secret_b"), sample("2", "secret_c")]
        mapping, prompt = candidate_packet(QUESTION, samples)
        self.assertEqual(len(mapping), 2)
        self.assertEqual((mapping, prompt), candidate_packet(QUESTION, samples))
        self.assertNotIn("secret", prompt)
        self.assertNotIn("original_index", prompt)
        self.assertNotIn("synthetic_example", prompt)

    def test_boolean_index_is_rejected_without_execution(self):
        box = Mock()
        answer = check_evidence(json.dumps({"selected_index": True}), [{}], QUESTION, box)
        self.assertEqual(answer["reason"], "invalid_index")
        box.run.assert_not_called()

    def test_evidence_must_match_the_selected_existing_candidate(self):
        candidates = [{"original_index": 4, "outputs": {"final": "1"}}]
        box = Mock()
        box.run.return_value = {"ok": True, "values": {"final": {"t": "frac", "n": "2", "d": "1"}}}
        raw = json.dumps({"selected_index": 0, "interpretation": "The question specifies one.",
                          "evidence_program": "def solve():\n    return {'final': 2}"})
        answer = check_evidence(raw, candidates, QUESTION, box)
        self.assertIsNone(answer["selected_original_index"])
        self.assertEqual(answer["reason"], "evidence_does_not_support_candidate")
        box.run.return_value["values"]["final"]["n"] = "1"
        answer = check_evidence(raw, candidates, QUESTION, box)
        self.assertEqual(answer["selected_original_index"], 4)

    def test_explicit_abstention_never_executes(self):
        box = Mock()
        answer = check_evidence('{"selected_index": null, "interpretation": "Ambiguous."}', [], QUESTION, box)
        self.assertEqual(answer["reason"], "verifier_abstained")
        box.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
