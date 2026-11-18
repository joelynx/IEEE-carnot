"""Replay every pilot verifier call and its executed evidence without fresh model calls."""

import json

from . import common
from .config import load_config, make_sandbox
from .improvement_campaign import ROOT, PILOT, StrictCLI, save
from .improvement_diversity import check_seal
from .improvement_verifier import DEST, DIVERSITY, RECIPE, PROMPT
from .verification import candidate_packet, check_evidence


def main():
    check_seal()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 verifier cache-only replay")
    recipe = json.loads(RECIPE.read_text())
    for path, expected in recipe["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"verifier input changed: {path}")
    if not all((DEST / f"{f}.json").exists() for f in recipe["families"]):
        raise SystemExit("complete verifier evaluation required")
    llm = StrictCLI(recipe["model"], recipe["effort"], cache_only=True)
    box = make_sandbox(load_config("configs/r5p.json"))
    results = []
    try:
        for family in recipe["families"]:
            source = DEST / f"{family}.json"
            record = json.loads(source.read_text(encoding="utf-8"))
            if record["recipe_sha256"] != common.sha256_file(RECIPE):
                raise RuntimeError("verifier recipe mismatch")
            items = {x["question"]["case_id"]: x for x in common.read_jsonl(PILOT / family / "instances.jsonl")}
            candidates_by_case = {c["case_id"]: c for c in json.loads((DIVERSITY / f"{family}.json").read_text())["cases"]}
            for case in record["cases"]:
                if case["call"] is None:
                    continue
                question = items[case["case_id"]]["question"]
                samples = candidates_by_case[case["case_id"]]["outcome"]["samples"]
                candidates, user = candidate_packet(question, samples)
                response = llm.complete(PROMPT.read_text(), user, sample=0, tag="r5v-selection-v1")
                if not response.cached or response.key != case["call"]["cache_key"] or response.text != case["call"]["raw_response"]:
                    raise RuntimeError(f"verifier cache-only identity mismatch: {case['case_id']}; "
                                       f"cached={response.cached}; key_equal={response.key == case['call']['cache_key']}; "
                                       f"text_equal={response.text == case['call']['raw_response']}")
                verdict = check_evidence(response.text, candidates, question, box)
                for key in ("selected_original_index", "selected_anonymous_index", "reason", "rendered_evidence"):
                    if verdict.get(key) != case["verdict"].get(key):
                        raise RuntimeError(f"verifier replay changed {key}")
                results.append({"family": family, "case_id": case["case_id"], "identical": True,
                                "evaluation_sha256": common.sha256_file(source), "cache_key": response.key})
    finally:
        box.close()
    summary = {"scope": "every verifier call and its executed evidence", "cached_calls": len(results),
               "evaluation_text_encoding": "utf-8",
               "fresh_calls": 0, "all_identical": True, "results": results,
               "replay_code_sha256": common.sha256_file(common.ROOT / "carnot/improvement_verifier_replay.py")}
    save(ROOT / "verifier_cache_replay.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))


if __name__ == "__main__":
    main()
