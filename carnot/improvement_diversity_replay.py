"""Cache-only replay of one case per family from the frozen diversity experiment."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import common, exemplars
from .campaign_integrity import require_family_checks
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .formatter import build_row
from .improvement_campaign import ROOT, PILOT, save
from .improvement_diversity import DEST, RECIPE, RoleCLI, check_seal
from .selection import final_first_complete
from .solver import Solver, load_system_prompt


def replay(family):
    source = DEST / f"{family}.json"
    record = json.loads(source.read_text())
    if record["recipe_sha256"] != common.sha256_file(RECIPE):
        raise RuntimeError("diversity recipe mismatch")
    if record["instances_sha256"] != require_family_checks(PILOT / family):
        raise RuntimeError("diversity dataset mismatch")
    item = next(iter(common.read_jsonl(PILOT / family / "instances.jsonl")))
    case = next(c for c in record["cases"] if c["case_id"] == item["question"]["case_id"])
    config = load_config("configs/r5p.json")
    roles = json.loads(RECIPE.read_text())["roles"]
    llm, box = RoleCLI(roles), make_sandbox(config)
    for client in llm.clients.values():
        client.cache_only = True
    try:
        examples = exemplars.select(json.loads((common.ROOT / config["exemplars"]).read_text()), None, "H")
        solver = Solver(llm, box, load_system_prompt(system_prompt_path(config, "novel")), 2,
                        **solver_options(config, "novel"))
        outcome = solver.solve(item["question"], examples, len(roles))
        original = case["outcome"]
        if any(outcome[k] != original[k] for k in ("row", "votes", "dropped_by_gate")):
            raise RuntimeError("field-plurality replay changed")
        if [s["texts"] for s in outcome["samples"]] != [s["texts"] for s in original["samples"]]:
            raise RuntimeError("executed candidate outputs changed")
        attempts = [a for s in outcome["samples"] for a in s["attempts"]]
        old = [a for s in original["samples"] for a in s["attempts"]]
        if [a["cache_key"] for a in attempts] != [a["cache_key"] for a in old] or not all(a["cached"] for a in attempts):
            raise RuntimeError("cache-only request identity invariant failed")
        fields = ["final"] + [s["slot_id"] for s in item["question"]["trace_spec"]["slots"]]
        choice = final_first_complete([s["texts"] for s in outcome["samples"]], fields)
        row = outcome["row"]
        if choice["index"] is not None:
            texts = outcome["samples"][choice["index"]]["texts"]
            row, _ = build_row(item["question"], texts["final"], {k: texts[k] for k in fields if k != "final"})
        if choice != case["complete_row_choice"] or row != case["complete_row"]:
            raise RuntimeError("complete-row replay changed")
        return {"family": family, "case_id": case["case_id"], "cached_calls": len(attempts),
                "fresh_calls": 0, "identical": True, "evaluation_sha256": common.sha256_file(source)}
    finally:
        box.close()


def main():
    check_seal()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 diversity cache-only replay")
    recipe = json.loads(RECIPE.read_text())
    for path, expected in recipe["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"diversity recipe input changed: {path}")
    if not all((DEST / f"{f}.json").exists() for f in recipe["families"]):
        raise SystemExit("finish all diversity evaluations before replay")
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = [f.result() for f in as_completed([pool.submit(replay, family) for family in recipe["families"]])]
    results.sort(key=lambda r: r["family"])
    summary = {"scope": "first case of each development family; all five roles and both selectors",
               "cases": len(results), "cached_calls": sum(r["cached_calls"] for r in results),
               "fresh_calls": 0, "all_identical": True, "results": results,
               "replay_code_sha256": common.sha256_file(common.ROOT / "carnot/improvement_diversity_replay.py")}
    save(ROOT / "diversity_cache_replay.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))


if __name__ == "__main__":
    main()
