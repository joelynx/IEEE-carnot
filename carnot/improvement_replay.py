"""Replay the first pilot case in every family under both recipes, without fresh calls."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import common, exemplars
from .campaign_integrity import require_family_checks, require_evaluation_identity
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .improvement_campaign import ROOT, PILOT, StrictCLI, save, verify_protected
from .solver import Solver, load_system_prompt


def replay(job):
    name, directory = job
    config = load_config(f"configs/{name}.json")
    source = directory / f"evaluation_{name}.json"
    record = json.loads(source.read_text())
    require_evaluation_identity(record, config["_sha256"],
        common.sha256_file(system_prompt_path(config, "novel")), require_family_checks(directory))
    item = next(iter(common.read_jsonl(directory / "instances.jsonl")))
    original = next(c["outcome"] for c in record["cases"] if c["case_id"] == item["question"]["case_id"])
    settings = config["routing"]["novel"]
    llm = StrictCLI(settings["model"], settings["effort"], cache_only=True)
    box = make_sandbox(config)
    try:
        examples = exemplars.select(json.loads((common.ROOT / config["exemplars"]).read_text()), None, "H")
        solver = Solver(llm, box, load_system_prompt(system_prompt_path(config, "novel")),
                        config["max_retries"], **solver_options(config, "novel"))
        outcome = solver.solve(item["question"], examples, settings["n_samples"])
        for key in ("row", "votes", "dropped_by_gate"):
            if outcome[key] != original[key]:
                raise RuntimeError(f"{directory.name}/{name}: replay changed {key}")
        if [s["texts"] for s in outcome["samples"]] != [s["texts"] for s in original["samples"]]:
            raise RuntimeError("replay changed executed candidate outputs")
        attempts = [a for s in outcome["samples"] for a in s["attempts"]]
        old_attempts = [a for s in original["samples"] for a in s["attempts"]]
        if [a["cache_key"] for a in attempts] != [a["cache_key"] for a in old_attempts]:
            raise RuntimeError("replay changed request identities")
        if not all(a["cached"] for a in attempts):
            raise RuntimeError("cache-only invariant failed")
        return {"family": directory.name, "config": name, "case_id": item["question"]["case_id"],
                "evaluation_sha256": common.sha256_file(source), "cached_calls": len(attempts),
                "fresh_calls": 0, "identical": True}
    finally:
        box.close()


def main():
    verify_protected()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 pilot cache-only replay")
    seal = json.loads((ROOT / "execution_seal.json").read_text())
    for path, expected in seal["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"frozen input changed: {path}")
    directories = sorted(p.parent for p in PILOT.glob("family_*/instances.jsonl"))
    if len(directories) != 24 or not all((d / f"evaluation_{c}.json").exists()
                                       for d in directories for c in ("r4", "r5p")):
        raise SystemExit("complete pilot comparison required before replay")
    jobs = [(c, d) for d in directories for c in ("r4", "r5p")]
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(replay, j) for j in jobs]):
            results.append(future.result())
    results.sort(key=lambda r: (r["family"], r["config"]))
    summary = {"scope": "first case in each of 24 families, both recipes", "cases": len(results),
               "cached_calls": sum(r["cached_calls"] for r in results), "fresh_calls": 0,
               "all_identical": all(r["identical"] for r in results), "results": results,
               "replay_code_sha256": common.sha256_file(common.ROOT / "carnot/improvement_replay.py")}
    save(ROOT / "cache_replay.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))


if __name__ == "__main__":
    main()
