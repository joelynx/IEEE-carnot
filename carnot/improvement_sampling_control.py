"""One extra independent Opus sample versus one verifier call on identical disagreements."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import common, exemplars
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .improvement_campaign import ROOT, PILOT, StrictCLI, save
from .improvement_diversity import check_seal
from .improvement_verifier import DEST as VERIFIER, DIVERSITY, RECIPE as V_RECIPE
from .solver import Solver, SampleResult, load_system_prompt
from finreason_task1.scoring import score_case

RECIPE = ROOT / "sampling_control_preregistration.json"
DEST = ROOT / "sampling_control"


class SavedPoolSolver(Solver):
    def __init__(self, *args, saved, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved = saved

    def solve_sample(self, question, examples, sample, exclude_template=None):
        if sample < len(self.saved):
            return SampleResult(**self.saved[sample])
        return super().solve_sample(question, examples, sample, exclude_template)


def freeze():
    if RECIPE.exists() or list(DEST.glob("*.json")):
        raise SystemExit("sampling control already frozen or evaluated")
    report = json.loads((ROOT / "verifier_report.json").read_text())
    jobs, paths = [], ["carnot/improvement_sampling_control.py", "experiments/improvement_20261020/verifier_report.json"]
    for family in report["families"]:
        source = VERIFIER / (family["family"] + ".json")
        paths.append(source.relative_to(common.ROOT).as_posix())
        for case in json.loads(source.read_text())["cases"]:
            if case["call"] is not None:
                jobs.append({"family": family["family"], "case_id": case["case_id"]})
    save(RECIPE, {"at": datetime.now(timezone.utc).isoformat(), "panel": "development_pilot_not_confirmation",
        "jobs": jobs, "model": "claude-opus-5-5", "effort": "medium", "additional_samples": 1,
        "sample_identity": 5, "max_retries": 0, "max_fresh_calls": len(jobs),
        "generation": "independent R5-P prompt and fixed H-mode exemplars; no existing answers or gold",
        "selection": "existing field plurality on five saved candidates plus the new sample",
        "resource_policy": "Same extra call count. Report actual input/output/thinking tokens and cost equivalents; "
                           "do not claim token-matched or cost-matched superiority from call count alone.",
        "limitations": "A six-sample vote can tie; the existing deterministic tie rule remains fixed.",
        "hashes": {p: common.sha256_file(common.ROOT / p) for p in paths}})
    print(f"Frozen one-sample control on the same {len(jobs)} disagreements.", flush=True)


def evaluate(job):
    family, cid = job["family"], job["case_id"]
    output = DEST / f"{cid}.json"
    if output.exists():
        prior = json.loads(output.read_text())
        if prior["recipe_sha256"] != common.sha256_file(RECIPE):
            raise RuntimeError("stale sampling control")
        return {"case_id": cid, "fac": prior["fac"]}
    item = next(x for x in common.read_jsonl(PILOT / family / "instances.jsonl") if x["question"]["case_id"] == cid)
    case = next(c for c in json.loads((DIVERSITY / f"{family}.json").read_text())["cases"] if c["case_id"] == cid)
    config = load_config("configs/r5p.json")
    llm, box = StrictCLI("claude-opus-5-5", "medium"), make_sandbox(config)
    examples = exemplars.select(json.loads((common.ROOT / config["exemplars"]).read_text()), None, "H")
    solver = SavedPoolSolver(llm, box, load_system_prompt(system_prompt_path(config, "novel")), 0,
                            saved=case["outcome"]["samples"], **solver_options(config, "novel"))
    try:
        outcome = solver.solve(item["question"], examples, 6)
        score = score_case(item["question"], item["gold"], outcome["row"])
        save(output, {"family": family, "case_id": cid, "recipe_sha256": common.sha256_file(RECIPE),
                      "fac": score.fac, "matched_slots": score.matched_slots, "total_slots": score.total_slots,
                      "baseline": case["scores"]["r5j"], "outcome": outcome, "backend": llm.describe()})
        return {"case_id": cid, "fac": score.fac, "matched_slots": score.matched_slots}
    finally:
        box.close()


def report():
    recipe = json.loads(RECIPE.read_text())
    diversity = json.loads((ROOT / "diversity_report.json").read_text())
    verifier = json.loads((ROOT / "verifier_report.json").read_text())
    counts = Counter(diversity["summaries"]["r5j"]["counts"])
    resources, changes, ties = Counter(), [], []
    for job in recipe["jobs"]:
        result = json.loads((DEST / (job["case_id"] + ".json")).read_text())
        if result["recipe_sha256"] != common.sha256_file(RECIPE):
            raise RuntimeError("sampling control identity mismatch")
        baseline = result["baseline"]
        counts["correct_final"] += result["fac"] - baseline["fac"]
        counts["matched_slots"] += result["matched_slots"] - baseline["matched_slots"]
        if result["fac"] != baseline["fac"] or result["matched_slots"] != baseline["matched_slots"]:
            changes.append({"case_id": job["case_id"], "final_delta": result["fac"] - baseline["fac"],
                            "slot_delta": result["matched_slots"] - baseline["matched_slots"]})
        votes = result["outcome"]["votes"]["final"]
        if votes and sum(v == max(votes.values()) for v in votes.values()) > 1:
            ties.append(job["case_id"])
        for attempt in result["outcome"]["samples"][-1]["attempts"]:
            resources["cached_calls" if attempt["cached"] else "fresh_calls"] += 1
            resources["cost_equivalent_usd"] += attempt.get("cost_equivalent_usd") or 0
            tokens = attempt.get("usage") or {}
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                resources[key] += tokens.get(key) or 0
            resources["thinking_tokens"] += (tokens.get("output_tokens_details") or {}).get("thinking_tokens") or 0
    result = {"panel": "development_pilot_not_confirmation", "counts": counts, "changes": changes,
              "resources": resources, "verifier_resources": verifier["resources"], "final_vote_ties": ties,
              "cost_ratio_to_verifier": resources["cost_equivalent_usd"] / verifier["resources"]["cost_equivalent_usd"],
              "interpretation_limit": "Development-only same-call-count control; actual token budgets differ. "
                                      "Six-sample ties use the unchanged existing tie rule. No general efficiency claim."}
    save(ROOT / "sampling_control_report.json", result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "evaluate", "report"])
    args = parser.parse_args()
    check_seal()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 sampling control " + args.action)
    for path, expected in json.loads(V_RECIPE.read_text())["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"verifier source changed: {path}")
    if args.action == "freeze":
        freeze()
        return
    recipe = json.loads(RECIPE.read_text())
    for path, expected in recipe["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"sampling control input changed: {path}")
    if args.action == "report":
        report()
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(evaluate, job) for job in recipe["jobs"]]
            try:
                for future in as_completed(futures):
                    print(json.dumps(future.result()), flush=True)
            except BaseException:
                for future in futures:
                    future.cancel()
                raise


if __name__ == "__main__":
    main()
