"""Bounded development-only five-role generation and complete-row selection ablation."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import common, exemplars, splits
from .campaign_integrity import require_family_checks, require_preflight
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .formatter import build_row
from .improvement_campaign import ROOT, PILOT, StrictCLI, save, verify_protected
from .improvement_report import diagnostics
from .prospective import decision, paired_family_interval
from .selection import final_first_complete
from .solver import Solver, load_system_prompt
from finreason_task1.scoring import score_case

DEST = ROOT / "diversity_pilot"
RECIPE = ROOT / "diversity_preregistration.json"
ROLES_PATH = common.ROOT / "carnot/prompts/r5_diversity_roles.json"


def check_seal():
    verify_protected()
    for path, expected in json.loads((ROOT / "execution_seal.json").read_text())["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"initial comparison changed: {path}")


class RoleCLI:
    def __init__(self, roles):
        if len(roles) != 5 or any(r["effort"] != "medium" for r in roles):
            raise ValueError("this ablation requires exactly five medium-effort roles")
        self.roles = roles
        self.clients = {model: StrictCLI(model, "medium") for model in sorted({r["model"] for r in roles})}

    def complete(self, system, user, sample=0, tag=""):
        role = self.roles[sample]
        instruction = role["instruction"]
        effective = system if not instruction else system + "\n\nIndependent derivation role:\n" + instruction
        # The direct role reproduces R5-P sample zero's request and can reuse it.
        return self.clients[role["model"]].complete(effective, user, sample=sample, tag=tag)


def freeze():
    if RECIPE.exists() or list(DEST.glob("family_*.json")):
        raise SystemExit("diversity preregistration or results already exist")
    report = json.loads((ROOT / "pilot_report.json").read_text())
    if report["missing"] or report["unresolved_oracles"] or len(report["families"]) != 24:
        raise SystemExit("finish the initial pilot before selecting the follow-up")
    paths = ["carnot/improvement_diversity.py", "carnot/prompts/r5_diversity_roles.json",
             "experiments/improvement_20261020/pilot_report.json"]
    save(RECIPE, {"at": datetime.now(timezone.utc).isoformat(), "panel": "development_pilot_not_confirmation",
        "rationale": "Initial pilot exposed repeated-change interpretation errors, missing correct candidates "
                     "and correct candidates lost by field plurality. Test the planned bounded diversity/selection ablation.",
        "roles": json.loads(ROLES_PATH.read_text()), "families": [f["family"] for f in report["families"]],
        "data": "Same 96 development questions; no confirmation or Test data",
        "selection": ["existing_field_plurality", "final_first_complete_with_existing_fallback"],
        "max_retries": 2, "samples_per_question": 5, "verifier": "not_included",
        "prospective_policy": "unchanged; this pilot cannot authorize promotion",
        "hashes": {p: common.sha256_file(common.ROOT / p) for p in paths}})
    print("Frozen five roles and both selectors on all 24 development families.", flush=True)


def smoke():
    config = load_config("configs/r5p.json")
    llm, box = StrictCLI("claude-opus-5-5", "medium"), make_sandbox(config)
    data = common.data()
    cid = splits.load()["tuning-eval"][0]
    solver = Solver(llm, box, load_system_prompt(system_prompt_path(config, "novel")), 2,
                    **solver_options(config, "novel"))
    try:
        outcome = solver.solve(data.questions[cid], [], 1, 10001)
        score = score_case(data.questions[cid], data.gold[cid], outcome["row"])
        record = {"case_id": cid, "llm": llm.describe(), "fac": score.fac,
                  "matched_slots": score.matched_slots, "total_slots": score.total_slots, "outcome": outcome}
        save(ROOT / "diversity_preflight.json", record)
        require_preflight(record)
        print("Opus training preflight passed with the exact requested model identity.", flush=True)
    finally:
        box.close()


def score_dict(score):
    return {"fac": score.fac, "matched_slots": score.matched_slots, "total_slots": score.total_slots}


def evaluate(family):
    directory, output = PILOT / family, DEST / f"{family}.json"
    data_hash, recipe_hash = require_family_checks(directory), common.sha256_file(RECIPE)
    if output.exists():
        prior = json.loads(output.read_text())
        if prior["instances_sha256"] != data_hash or prior["recipe_sha256"] != recipe_hash:
            raise RuntimeError(f"stale diversity evaluation: {family}")
        return {"family": family, "counts": prior["counts"]}
    config = load_config("configs/r5p.json")
    roles = json.loads(RECIPE.read_text())["roles"]
    llm, box = RoleCLI(roles), make_sandbox(config)
    examples = exemplars.select(json.loads((common.ROOT / config["exemplars"]).read_text()), None, "H")
    solver = Solver(llm, box, load_system_prompt(system_prompt_path(config, "novel")), 2,
                    **solver_options(config, "novel"))
    cases, counts = [], {c: Counter() for c in ("r5d", "r5j")}
    try:
        for item in common.read_jsonl(directory / "instances.jsonl"):
            question, gold = item["question"], item["gold"]
            outcome = solver.solve(question, examples, len(roles))
            fields = ["final"] + [s["slot_id"] for s in question["trace_spec"]["slots"]]
            choice = final_first_complete([s["texts"] for s in outcome["samples"]], fields)
            row = outcome["row"]
            if choice["index"] is not None:
                texts = outcome["samples"][choice["index"]]["texts"]
                row, dropped = build_row(question, texts["final"], {k: texts[k] for k in fields if k != "final"})
                if dropped:
                    raise RuntimeError("complete-row selector produced an invalid row")
            scores = {"r5d": score_dict(score_case(question, gold, outcome["row"])),
                      "r5j": score_dict(score_case(question, gold, row))}
            for name, values in scores.items():
                counts[name].update({"cases": 1, "correct_final": values["fac"],
                                     "matched_slots": values["matched_slots"], "total_slots": values["total_slots"]})
            cases.append({"case_id": question["case_id"], "outcome": outcome,
                          "scores": scores, "complete_row_choice": choice, "complete_row": row})
            save(DEST / f"{family}_partial.json", cases)
        save(output, {"family": family, "instances_sha256": data_hash, "recipe_sha256": recipe_hash,
                      "counts": counts, "cases": cases,
                      "backends": {k: v.describe() for k, v in llm.clients.items()}})
        return {"family": family, "counts": counts}
    finally:
        box.close()


def report():
    recipe = json.loads(RECIPE.read_text())
    initial = json.loads((ROOT / "pilot_report.json").read_text())
    reference = {f["family"]: f for f in initial["families"]}
    summaries = {name: {"counts": Counter(), "diagnostics": Counter()} for name in ("r5d", "r5j")}
    resources = {r["role"]: Counter() for r in recipe["roles"]}
    families = []
    for family in recipe["families"]:
        record = json.loads((DEST / f"{family}.json").read_text())
        if record["recipe_sha256"] != common.sha256_file(RECIPE):
            raise RuntimeError("recipe mismatch")
        if record["instances_sha256"] != require_family_checks(PILOT / family):
            raise RuntimeError("dataset mismatch")
        items = {x["question"]["case_id"]: x for x in common.read_jsonl(PILOT / family / "instances.jsonl")}
        ids = [c["case_id"] for c in record["cases"]]
        if len(ids) != len(items) or set(ids) != set(items):
            raise RuntimeError("incomplete or duplicate diversity case coverage")
        result = dict(reference[family])
        for case in record["cases"]:
            for index, sample in enumerate(case["outcome"]["samples"]):
                counter = resources[recipe["roles"][index]["role"]]
                counter["samples"] += 1
                counter["retries"] += len(sample["attempts"]) - 1
                for attempt in sample["attempts"]:
                    counter["cached_calls" if attempt["cached"] else "fresh_calls"] += 1
                    if attempt["cached"]:
                        continue
                    counter["cost_equivalent_usd"] += attempt.get("cost_equivalent_usd") or 0
                    tokens = attempt.get("usage") or {}
                    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                        counter[key] += tokens.get(key) or 0
                    counter["thinking_tokens"] += (tokens.get("output_tokens_details") or {}).get("thinking_tokens") or 0
        for name in summaries:
            cases = [{"case_id": c["case_id"], "outcome": c["outcome"], **c["scores"][name]} for c in record["cases"]]
            summaries[name]["counts"].update(record["counts"][name])
            summaries[name]["diagnostics"].update(diagnostics(cases, items))
            result[name] = {"fac": sum(c["fac"] for c in cases) / len(cases),
                            "checkpoint": sum(c["matched_slots"] / c["total_slots"] for c in cases) / len(cases)}
        families.append(result)
    comparisons = {}
    for name in summaries:
        comparisons[name] = {}
        for metric in ("fac", "checkpoint"):
            values = [f[name][metric] - f["r4"][metric] for f in families]
            interval = paired_family_interval(values)
            comparisons[name][metric] = {**interval, "prospective": decision(interval["delta"],
                interval["one_sided_95_lower"], all_differences_zero=not any(values), independent_units=len(values))}
    result = {"panel": "development_pilot_not_confirmation", "families": families, "summaries": summaries,
              "fresh_usage_by_role": resources,
              "comparisons_against_r4": comparisons, "promotion": "not_eligible_pilot_only"}
    save(ROOT / "diversity_report.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "families"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "smoke", "evaluate", "report"])
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    check_seal()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 diversity " + args.action)
    if args.action == "freeze":
        freeze()
        return
    recipe = json.loads(RECIPE.read_text())
    for path, expected in recipe["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"diversity recipe input changed: {path}")
    if args.action == "smoke":
        smoke()
    elif args.action == "report":
        report()
    else:
        require_preflight(json.loads((ROOT / "diversity_preflight.json").read_text()))
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
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
