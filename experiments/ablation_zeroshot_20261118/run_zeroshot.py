"""Worked-example ablation: R0 with zero worked examples on tuning-eval (S-mode).

Pre-registered in experiments/ablation_zeroshot_20261118/preregistration.json before any
model call.  Everything except the examples is R0 as frozen in configs/r0.json: same model,
effort, system prompt, sandbox, retries, unit hints and formatter; one sample per question.
The only change is that the user prompt carries no "### Example" blocks
(solver.solve(question, [], ...), the call the exemplar bootstrap already uses).

  python -I experiments/ablation_zeroshot_20261118/run_zeroshot.py            (full run, resumes from the cache)
  python -I experiments/ablation_zeroshot_20261118/run_zeroshot.py --limit 3  (smoke)
  python -I experiments/ablation_zeroshot_20261118/run_zeroshot.py --cache-only   (replay, no model call)

Writes only under experiments/ablation_zeroshot_20261118/ (plus the shared response cache).
It does not touch runs/, experiments/log.jsonl, the lockbox, the leaderboard or the test set.
"""

import argparse
import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from carnot import common, compare, harness, splits  # noqa: E402
from carnot.config import load_config, make_llm, make_sandbox, solver_options, system_prompt_path  # noqa: E402
from carnot.llm_client import UsageLimitError  # noqa: E402
from carnot.run import classify, git_commit  # noqa: E402
from carnot.solver import Solver, load_system_prompt  # noqa: E402

CONFIG = ROOT / "configs" / "r0.json"
SPLIT, MODE = "tuning-eval", "S"
BASELINE = ROOT / "runs" / "20261011T184257Z_r0_tuning-eval_S"
SIGMA_RUNS = [BASELINE, ROOT / "runs" / "20261011T203538Z_r0_tuning-eval_S_rep1",
              ROOT / "runs" / "20261011T204616Z_r0_tuning-eval_S_rep2"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="smoke only; no official score")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--cache-only", action="store_true")
    args = parser.parse_args()

    config = load_config(CONFIG)
    try:
        run_lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"zeroshot ablation {SPLIT} {MODE}")  # noqa: F841
    except common.LockHeld as exc:
        raise SystemExit(str(exc))
    release = common.verify_release()
    case_ids = splits.load()[SPLIT]
    if args.limit:
        case_ids = case_ids[: args.limit]
    d = common.data()
    llm, sandbox = make_llm(config), make_sandbox(config)
    llm.cache_only = args.cache_only
    system = load_system_prompt(system_prompt_path(config))
    options = solver_options(config, "seen")
    solver = Solver(llm, sandbox, system, config["max_retries"], **options)
    started = datetime.now(timezone.utc)
    out = HERE / ("smoke" if args.limit else "run")
    out.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()
    results: dict[str, dict] = {}
    failures: dict[str, str] = {}

    def work(case_id: str):
        if stop.is_set():
            raise RuntimeError("stopped")
        outcome = solver.solve(d.questions[case_id], [], config["n_samples"], 0, exclude_template=d.template(case_id))
        outcome["exemplars"] = []
        outcome["route"] = "seen"
        return case_id, outcome

    t0 = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(work, case_id) for case_id in case_ids]
            for done, future in enumerate(as_completed(futures), start=1):
                try:
                    case_id, outcome = future.result()
                    results[case_id] = outcome
                except UsageLimitError as exc:
                    stop.set()
                    failures["usage_limit"] = str(exc)[:300]
                    print(f"USAGE LIMIT: {exc}"[:400], file=sys.stderr, flush=True)
                except Exception as exc:  # noqa: BLE001
                    if str(exc) != "stopped":
                        failures[f"error_{len(failures)}"] = f"{type(exc).__name__}: {exc}"[:300]
                        print(f"FAILURE: {type(exc).__name__}: {exc}"[:400], file=sys.stderr, flush=True)
                if done % 25 == 0 or done == len(futures):
                    print(f"[{done}/{len(futures)}] completed={len(results)} failures={len(failures)} "
                          f"elapsed={time.perf_counter() - t0:.0f}s", flush=True)
    finally:
        sandbox.close()

    complete = len(results) == len(case_ids)
    usage = Counter()
    fresh = cached = retries = model_mismatch = 0
    attempts_per_question = Counter()
    for outcome in results.values():
        attempts = outcome["samples"][0]["attempts"]
        attempts_per_question[len(attempts)] += 1
        retries += len(attempts) - 1
        for attempt in attempts:
            if attempt["model_id"] != config["model"]:
                model_mismatch += 1
            if attempt["cached"]:
                cached += 1
                continue
            fresh += 1
            u = attempt["usage"] or {}
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                usage[key] += int(u.get(key) or 0)
            usage["thinking_tokens"] += int(((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0)
            usage["cost_equivalent_usd"] += float(attempt.get("cost_equivalent_usd") or 0)

    rows = [results[c]["row"] for c in case_ids if c in results]
    record = {
        "run_id": "ablation_zeroshot_20261118_r0_tuning-eval_S", "started": started.isoformat(),
        "config": config["name"], "config_sha256": config["_sha256"],
        "config_full": {k: v for k, v in config.items() if not k.startswith("_")},
        "ablation": "zero worked examples (exemplars = [])",
        "split": SPLIT, "mode": MODE, "limit": args.limit, "sample_offset": 0, "n_cases": len(case_ids),
        "complete": complete, "failures": failures, "release_manifest_sha256": release,
        "split_ids_sha256": common.sha256_text("\n".join(case_ids)), "exemplars": [],
        "system_prompt_sha256": common.sha256_text(system), "llm": llm.describe(), "sandbox": sandbox.info,
        "conventions": {"seen": {"hints": options["hints"], "echo_notes": options["echo"], "slot_conventions": None}},
        "cache_only": args.cache_only, "git": git_commit(), "synthetic_data_used": False,
        "fresh_calls": fresh, "cached_calls": cached, "retries": retries,
        "attempts_per_question": dict(sorted(attempts_per_question.items())),
        "returned_model_id_mismatches": model_mismatch,
        "usage": dict(usage), "wall_seconds": round(time.perf_counter() - t0),
    }
    case_records = []
    if complete:
        scored = harness.score(rows, case_ids) if not args.limit else None
        per_case = {c["case_id"]: c for c in (scored["cases"] if scored else [])}
        record["score"] = scored["report"] if scored else None
        categories = Counter()
        for case_id in case_ids:
            entry = dict(results[case_id])
            if scored:
                entry.update(per_case[case_id])
                entry["failure"] = classify({**per_case[case_id], **results[case_id]}, d.questions[case_id], d.gold[case_id])
                categories[entry["failure"]] += 1
            case_records.append({"case_id": case_id, **entry})
        if scored:
            record["failure_categories"] = dict(categories)
            record["micro"] = {"fac": f"{sum(c['fac'] for c in per_case.values())}/{len(case_ids)}",
                               "slots": f"{sum(c['matched_slots'] for c in per_case.values())}/{sum(c['total_slots'] for c in per_case.values())}"}
    else:
        case_records = [{"case_id": c, **results[c]} for c in case_ids if c in results]
    common.write_jsonl(out / "cases.jsonl", case_records)
    if complete:
        record["predictions_sha256"] = common.write_jsonl(out / "predictions.jsonl", rows)
    common.write_bytes_atomic(out / "summary.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))

    brief = {k: record.get(k) for k in ("run_id", "complete", "failures", "fresh_calls", "cached_calls", "retries",
                                        "attempts_per_question", "returned_model_id_mismatches", "usage",
                                        "failure_categories", "micro")}
    brief["scores"] = (record.get("score") or {}).get("scores")
    print(json.dumps(brief, indent=1))

    if complete and not args.limit:  # paired comparison with the stored R0 run (same method as carnot.compare; not logged)
        result = compare.compare(str(BASELINE), str(out), [str(p) for p in SIGMA_RUNS], 10_000, "case")
        result["recorded_at"] = datetime.now(timezone.utc).isoformat()
        common.write_bytes_atomic(HERE / "comparison_vs_r0.json", (json.dumps(result, indent=1) + "\n").encode("utf-8"))
        print(json.dumps(result, indent=1))
    return 0 if complete else 3


if __name__ == "__main__":
    raise SystemExit(main())
