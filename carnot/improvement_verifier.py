"""One-call, select-only verifier ablation over frozen diversity candidates."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import common
from .campaign_integrity import require_family_checks, require_preflight
from .config import load_config, make_sandbox
from .formatter import build_row
from .improvement_campaign import ROOT, PILOT, StrictCLI, save
from .improvement_diversity import DEST as DIVERSITY, RECIPE as D_RECIPE, check_seal
from .prospective import decision, paired_family_interval
from .verification import candidate_packet, check_evidence
from finreason_task1.scoring import score_case

DEST = ROOT / "verifier_pilot"
RECIPE = ROOT / "verifier_preregistration.json"
PROMPT = common.ROOT / "carnot/prompts/verify_selection_v1.txt"


def freeze():
    if RECIPE.exists() or list(DEST.glob("family_*.json")):
        raise SystemExit("verifier preregistration or results already exist")
    diversity = json.loads((ROOT / "diversity_report.json").read_text())
    if len(diversity["families"]) != 24:
        raise SystemExit("complete diversity report required")
    require_preflight(json.loads((ROOT / "diversity_preflight.json").read_text()))
    paths = ["carnot/verification.py", "carnot/improvement_verifier.py", "carnot/prompts/verify_selection_v1.txt",
             "experiments/improvement_20261020/diversity_report.json", "experiments/improvement_20261020/diversity_preflight.json",
             "experiments/improvement_20261020/diversity_preregistration.json"]
    families = [f["family"] for f in diversity["families"]]
    paths += [(DIVERSITY / f"{f}.json").relative_to(common.ROOT).as_posix() for f in families]
    save(RECIPE, {"at": datetime.now(timezone.utc).isoformat(), "panel": "development_pilot_not_confirmation",
        "rationale": "Diversity supplied correct minority candidates but final plurality still lost one. "
                     "Test the planned select-only verifier on every disagreement, not only known errors.",
        "families": families, "model": "claude-opus-5-5", "effort": "medium",
        "max_calls_per_case": 1, "max_calls_total": 96, "retries": 0,
        "trigger": "at least two distinct complete executed output rows",
        "anonymization": "deduplicate output rows; hide models, vote counts and current selection; deterministic shuffled order",
        "acceptance": "valid index, nonempty interpretation, executed evidence matching every selected candidate output",
        "fallback": "R5-J on unanimity, insufficient complete candidates, abstention or invalid evidence",
        "no_value_edits": True, "gold_in_model_input": False,
        "hashes": {p: common.sha256_file(common.ROOT / p) for p in paths}})
    print("Frozen bounded verifier on all disagreements in the saved diversity pool.", flush=True)


def evaluate(family):
    source, output = DIVERSITY / f"{family}.json", DEST / f"{family}.json"
    recipe_hash, source_hash = common.sha256_file(RECIPE), common.sha256_file(source)
    if output.exists():
        prior = json.loads(output.read_text())
        if prior["recipe_sha256"] != recipe_hash or prior["source_sha256"] != source_hash:
            raise RuntimeError("stale verifier evaluation")
        return {"family": family, "counts": prior["counts"]}
    record = json.loads(source.read_text())
    if record["instances_sha256"] != require_family_checks(PILOT / family):
        raise RuntimeError("candidate data mismatch")
    items = {x["question"]["case_id"]: x for x in common.read_jsonl(PILOT / family / "instances.jsonl")}
    config = load_config("configs/r5p.json")
    llm = box = None
    results, counts = [], Counter()
    try:
        for case in record["cases"]:
            item = items[case["case_id"]]
            question = item["question"]
            candidates, user = candidate_packet(question, case["outcome"]["samples"])
            row = case["complete_row"]
            verdict = {"selected_original_index": None, "reason": "no_complete_disagreement"}
            call = None
            if len(candidates) >= 2:
                if llm is None:
                    llm, box = StrictCLI("claude-opus-5-5", "medium"), make_sandbox(config)
                response = llm.complete(PROMPT.read_text(), user, sample=0, tag="r5v-selection-v1")
                call = {"cache_key": response.key, "cached": response.cached, "model": response.model_id,
                        "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd,
                        "raw_response": response.text}
                verdict = check_evidence(response.text, candidates, question, box)
                if verdict["selected_original_index"] is not None:
                    texts = case["outcome"]["samples"][verdict["selected_original_index"]]["texts"]
                    row, dropped = build_row(question, texts["final"], {k: v for k, v in texts.items() if k != "final"})
                    if dropped:
                        raise RuntimeError("supported candidate failed row validation")
            score = score_case(question, item["gold"], row)
            counts.update({"cases": 1, "correct_final": score.fac, "matched_slots": score.matched_slots,
                           "total_slots": score.total_slots, "verifier_calls": int(call is not None)})
            results.append({"case_id": case["case_id"], "fac": score.fac, "matched_slots": score.matched_slots,
                            "total_slots": score.total_slots, "row": row, "verdict": verdict, "call": call,
                            "candidate_original_indices": [c["original_index"] for c in candidates],
                            "fallback_scores": case["scores"]["r5j"],
                            "gold_available_only_after_selection": True})
            save(DEST / f"{family}_partial.json", results)
        save(output, {"family": family, "recipe_sha256": recipe_hash, "source_sha256": source_hash,
                      "instances_sha256": record["instances_sha256"], "cases": results, "counts": counts,
                      "backend": llm.describe() if llm is not None else None})
        return {"family": family, "counts": counts}
    finally:
        if box is not None:
            box.close()


def report():
    recipe = json.loads(RECIPE.read_text())
    diversity = json.loads((ROOT / "diversity_report.json").read_text())
    reference = {f["family"]: f for f in diversity["families"]}
    families, changes = [], []
    counts, effects, reasons, resources, positions = (Counter() for _ in range(5))
    for family in recipe["families"]:
        record = json.loads((DEST / f"{family}.json").read_text())
        if record["recipe_sha256"] != common.sha256_file(RECIPE) or record["source_sha256"] != common.sha256_file(DIVERSITY / f"{family}.json"):
            raise RuntimeError("verifier result identity mismatch")
        items = list(common.read_jsonl(PILOT / family / "instances.jsonl"))
        cases = record["cases"]
        if len(cases) != len(items) or {c["case_id"] for c in cases} != {x["question"]["case_id"] for x in items}:
            raise RuntimeError("incomplete or duplicate verifier case coverage")
        counts.update(record["counts"])
        result = dict(reference[family])
        result["r5v"] = {"fac": sum(c["fac"] for c in cases) / len(cases),
                         "checkpoint": sum(c["matched_slots"] / c["total_slots"] for c in cases) / len(cases)}
        families.append(result)
        for case in cases:
            baseline = case["fallback_scores"]
            effects["wrong_to_correct_final"] += int(not baseline["fac"] and case["fac"])
            effects["correct_to_wrong_final"] += int(baseline["fac"] and not case["fac"])
            delta = case["matched_slots"] - baseline["matched_slots"]
            effects["slot_gains"] += max(0, delta)
            effects["slot_losses"] += max(0, -delta)
            reasons[case["verdict"]["reason"]] += 1
            if "selected_anonymous_index" in case["verdict"]:
                positions[str(case["verdict"]["selected_anonymous_index"])] += 1
            if baseline["fac"] != case["fac"] or delta:
                changes.append({"case_id": case["case_id"], "family": family,
                                "final_delta": case["fac"] - baseline["fac"], "slot_delta": delta})
            call = case["call"]
            if call:
                resources["cached_calls" if call["cached"] else "fresh_calls"] += 1
                resources["cost_equivalent_usd"] += call.get("cost_equivalent_usd") or 0
                tokens = call.get("usage") or {}
                for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    resources[key] += tokens.get(key) or 0
                resources["thinking_tokens"] += (tokens.get("output_tokens_details") or {}).get("thinking_tokens") or 0
    comparisons = {}
    for baseline in ("r4", "r5j"):
        comparisons[baseline] = {}
        for metric in ("fac", "checkpoint"):
            values = [f["r5v"][metric] - f[baseline][metric] for f in families]
            interval = paired_family_interval(values)
            comparisons[baseline][metric] = {**interval, "prospective": decision(interval["delta"],
                interval["one_sided_95_lower"], all_differences_zero=not any(values), independent_units=len(values))}
    result = {"panel": "development_pilot_not_confirmation", "families": families, "counts": counts,
              "effects_vs_r5j": effects, "verdict_reasons": reasons, "resources": resources,
              "selected_positions": positions, "changes": changes, "comparisons": comparisons,
              "limitations": "Few disagreements cannot establish position neutrality or semantic correctness. "
                             "Executed evidence corroborates outputs but is not an independent truth oracle.",
              "promotion": "not_eligible_pilot_only"}
    save(ROOT / "verifier_report.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "families"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "evaluate", "report"])
    args = parser.parse_args()
    check_seal()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 verifier " + args.action)
    for path, expected in json.loads(D_RECIPE.read_text())["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"diversity implementation changed: {path}")
    if args.action == "freeze":
        freeze()
        return
    recipe = json.loads(RECIPE.read_text())
    for path, expected in recipe["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"verifier input changed: {path}")
    if args.action == "report":
        report()
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(evaluate, f) for f in recipe["families"]]
            try:
                for future in as_completed(futures):
                    print(json.dumps(future.result()), flush=True)
            except BaseException:
                for future in futures:
                    future.cancel()
                raise


if __name__ == "__main__":
    main()
