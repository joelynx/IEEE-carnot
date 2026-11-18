"""One command: run a frozen config on a split, score or package, and log (PLAN.md §5.8).

  python -m carnot.run --config configs/r0.json --split tuning-eval --mode S
  python -m carnot.run --config configs/r0.json --split lockbox --mode H --lockbox-reason "confirm R1"
  python -m carnot.run --config configs/r0.json --split test928
  python -m carnot.run --config configs/r1.json --split tuning-eval --force-route novel   (§4a(c))

Gold splits are scored with the toolkit's score_submission.  leaderboard580 and
test928 are never scored: they are validated, packaged and re-validated with
the toolkit CLI exactly as the submission guide prescribes, and nothing is
packaged unless every case completed.  Responses are cached, so re-running the
same command after an interruption (e.g. a usage limit) resumes for free.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction

from . import common, exemplars, harness, splits
from .config import load_config, make_llm, make_sandbox, solver_options, system_prompt_path
from .formatter import parse_gold_value
from .llm_client import UsageLimitError
from .routing import NoveltyRouter
from .solver import Solver, load_system_prompt

GOLD_SPLITS = {"tuning-smoke", "tuning-eval", "lockbox", "dev290", "tuning", "exemplar-pool", "tuning-noex"}
PACKAGED_SPLITS = {"leaderboard580": "development_files/leaderboard_questions.jsonl",
                   "test928": "test_questions/test_questions.jsonl"}


def git_commit() -> dict:
    def git(*args):
        return subprocess.run(["git", "-C", str(common.ROOT), *args], capture_output=True, text=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"), "dirty_files": len(git("status", "--porcelain").splitlines())}


def classify(case: dict, question: dict, gold: dict | None) -> str:
    if gold is None:
        return "n/a"
    if case["fac"] == 1:
        return "correct"
    row = case["row"]
    if row["final_answer"] is None:
        issues = [s["issues"].get("final") for s in case["samples"]]
        reasons = " ".join(i or "" for i in issues)
        if "no successful attempt" in reasons:
            return "execution_error"
        if "missing key" in reasons:
            return "missing_output"
        return "format_or_type_error"
    spec = question["answer_spec"]
    if spec["type"] == "enum":
        return "wrong_category"
    predicted = parse_gold_value(row["final_answer"]["value"], spec)
    truth = parse_gold_value(gold["final_value"], spec)
    places = spec["rounding"].get("decimal_places")
    def close(a, b):
        if places is None:
            return a == b
        return abs(a - b) <= Fraction(1, 10**places)
    if close(predicted, -truth):
        return "sign_error"
    if close(predicted * 100, truth) or close(predicted, truth * 100):
        return "unit_or_percent_error"
    if close(predicted, truth):
        return "rounding_error"
    return "wrong_value"


def toolkit_cli(*args: str) -> dict:
    completed = subprocess.run([sys.executable, "-I", str(common.ROOT / "scripts" / "task1_cli.py"), *args],
                               capture_output=True, text=True, encoding="utf-8")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError:
        output = {"raw": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}
    output["_exit_code"] = completed.returncode
    return output


def write_results_table() -> None:
    log = common.EXPERIMENTS_DIR / "log.jsonl"
    if not log.exists():
        return
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = ["# Experiment results", "",
             "Generated from experiments/log.jsonl by carnot.run. Official = toolkit hierarchical score; micro = raw share.",
             "", "| run | config | split | mode | n | complete | seen FAC | seen steps | micro FAC | micro steps | input tok | output tok | cost-equiv $ |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s = (r.get("score") or {}).get("scores", {})
        dg = (r.get("score") or {}).get("diagnostics", {})
        u = r.get("usage", {})
        lines.append(
            f"| {r['run_id']} | {r['config']} | {r['split']} | {r['mode']} | {r['n_cases']} | {r['complete']} | "
            f"{s.get('seen_fac', '–')} | {s.get('seen_checkpoint', '–')} | {dg.get('micro_fac', '–')} | "
            f"{dg.get('micro_checkpoint', '–')} | {u.get('input_tokens', 0)} | {u.get('output_tokens', 0)} | "
            f"{u.get('cost_equivalent_usd', 0):.2f} |")
    common.write_bytes_atomic(common.EXPERIMENTS_DIR / "results.md", ("\n".join(lines) + "\n").encode("utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", required=True,
                        choices=sorted(GOLD_SPLITS | set(PACKAGED_SPLITS)))
    parser.add_argument("--mode", default="S", choices=["S", "H"])
    parser.add_argument("--limit", type=int, default=None, help="smoke runs only; disables official scoring")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--cache-only", action="store_true", help="fail on any missing cached model response")
    parser.add_argument("--lockbox-reason", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--sample-offset", type=int, default=0,
                        help="draw fresh samples (repeat runs for sigma_run); never used for submissions")
    parser.add_argument("--force-route", default=None, choices=["seen", "novel"],
                        help="apply one route's path to every question (§4a(c) checks); gold splits only")
    args = parser.parse_args(argv)
    if args.sample_offset and args.split in PACKAGED_SPLITS:
        parser.error("--sample-offset is for noise estimates on gold splits only")
    if args.force_route and args.split in PACKAGED_SPLITS:
        parser.error("--force-route is for checks on gold splits only")

    config = load_config(args.config)
    if args.force_route and "routing" not in config:
        parser.error("--force-route needs a config with a routing block")
    try:  # one model-calling run at a time; released by the OS when this process exits
        run_lock = common.RunLock(common.RUNS_DIR / ".run.lock",  # noqa: F841 (held for the process lifetime)
                                  f"{config['name']} {args.split} {args.mode} {' '.join(argv or sys.argv[1:])}")
    except common.LockHeld as exc:
        raise SystemExit(str(exc))
    release = common.verify_release()
    if args.split == "tuning-noex":  # the tuning set minus the config's few-shot exemplars
        exemplar_cases = {e["case_id"] for e in json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))["exemplars"]}
        case_ids = [c for c in splits.load()["tuning"] if c not in exemplar_cases]
    else:
        case_ids = splits.load()[args.split]
    if args.limit:
        case_ids = case_ids[: args.limit]
    if args.split == "lockbox":
        if not args.lockbox_reason:
            parser.error("--lockbox-reason is required for the lockbox")
        common.append_jsonl(common.EXPERIMENTS_DIR / "lockbox_access.jsonl",
                            {"event": "lockbox_look", "at": datetime.now(timezone.utc).isoformat(),
                             "config": config["name"], "config_sha256": config["_sha256"], "mode": args.mode,
                             "reason": args.lockbox_reason})
    exemplar_file = json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))
    exemplar_ids = {e["case_id"] for e in exemplar_file["exemplars"]}
    pool = set(splits.load()["exemplar-pool"])
    if not exemplar_ids <= pool or exemplar_ids & set(case_ids):
        raise SystemExit("leakage guard: exemplars must come from the exemplar pool and not be evaluated")

    d = common.data()
    llm, sandbox = make_llm(config), make_sandbox(config)
    llm.cache_only = args.cache_only
    system = load_system_prompt(system_prompt_path(config))
    route_systems = {"seen": system}
    seen_options = solver_options(config, "seen")
    solvers = {"seen": (Solver(llm, sandbox, system, config["max_retries"], **seen_options), config["n_samples"])}
    novel_options = None
    router = llm_novel = None
    if "routing" in config:
        router = NoveltyRouter()
        llm_novel = make_llm(config, "novel")
        llm_novel.cache_only = args.cache_only
        route_systems["novel"] = load_system_prompt(system_prompt_path(config, "novel"))
        novel_options = solver_options(config, "novel")
        solvers["novel"] = (Solver(llm_novel, sandbox, route_systems["novel"], config["max_retries"], **novel_options),
                            config["routing"]["novel"]["n_samples"])
    started = datetime.now(timezone.utc)
    suffix = f"_rep{args.sample_offset}" if args.sample_offset else ""
    suffix += f"_forced-{args.force_route}" if args.force_route else ""
    run_id = args.run_id or f"{started:%Y%m%dT%H%M%SZ}_{config['name']}_{args.split}_{args.mode}{suffix}"
    out = common.RUNS_DIR / run_id
    out.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()
    results: dict[str, dict] = {}
    failures: dict[str, str] = {}

    def work(case_id: str) -> tuple[str, dict]:
        if stop.is_set():
            raise RuntimeError("stopped")
        template = d.template(case_id)
        chosen = exemplars.select(exemplar_file, template, args.mode)
        question = d.questions[case_id]
        route = args.force_route or (router.route(question) if router else "seen")
        solver, n_samples = solvers[route]
        outcome = solver.solve(question, chosen, n_samples, args.sample_offset, exclude_template=template)
        outcome["exemplars"] = [e["case_id"] for e in chosen]
        outcome["route"] = route
        return case_id, outcome

    t0 = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool_executor:
            futures = [pool_executor.submit(work, case_id) for case_id in case_ids]
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
    by_route: dict[str, Counter] = defaultdict(Counter)
    fresh_calls = cached_calls = 0
    for outcome in results.values():
        route_usage = by_route[outcome["route"]]
        route_usage["questions"] += 1
        for sample in outcome["samples"]:
            for attempt in sample["attempts"]:
                if attempt["cached"]:
                    cached_calls += 1
                    route_usage["cached_calls"] += 1
                    continue
                fresh_calls += 1
                route_usage["fresh_calls"] += 1
                u = attempt["usage"] or {}
                for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    usage[key] += int(u.get(key) or 0)
                    route_usage[key] += int(u.get(key) or 0)
                thinking = int(((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0)
                usage["thinking_tokens"] += thinking
                route_usage["thinking_tokens"] += thinking
                usage["cost_equivalent_usd"] += float(attempt.get("cost_equivalent_usd") or 0)
                route_usage["cost_equivalent_usd"] += float(attempt.get("cost_equivalent_usd") or 0)

    rows = [results[c]["row"] for c in case_ids if c in results]
    record = {
        "run_id": run_id, "started": started.isoformat(), "config": config["name"], "config_sha256": config["_sha256"],
        "config_full": {k: v for k, v in config.items() if not k.startswith("_")},
        "split": args.split, "mode": args.mode, "limit": args.limit, "sample_offset": args.sample_offset,
        "n_cases": len(case_ids),
        "complete": complete, "failures": failures, "release_manifest_sha256": release,
        "split_ids_sha256": common.sha256_text("\n".join(case_ids)),
        "exemplars": sorted(exemplar_ids), "exemplar_file_sha256": common.sha256_file(common.ROOT / config["exemplars"]),
        "system_prompt_sha256": common.sha256_text(system), "llm": llm.describe(), "sandbox": sandbox.info,
        "route_system_prompt_sha256": {route: common.sha256_text(text) for route, text in route_systems.items()},
        "cache_only": args.cache_only,
        "git": git_commit(), "synthetic_data_used": False,
        "conventions": {route: {"hints": o["hints"], "echo_notes": o["echo"],
                                "slot_conventions": o["conventions"].info if o["conventions"] else None}
                        for route, o in (("seen", seen_options), ("novel", novel_options)) if o}, "fresh_calls": fresh_calls, "cached_calls": cached_calls,
        "usage": dict(usage), "wall_seconds": round(time.perf_counter() - t0),
        "routing": None if router is None else {**router.info, "forced": args.force_route,
                                                 "novel_settings": config["routing"]["novel"],
                                                 "llm_novel": llm_novel.describe(),
                                                 "by_route": {k: dict(v) for k, v in sorted(by_route.items())}},
    }

    case_records = []
    if args.split in GOLD_SPLITS and complete:
        scored = harness.score(rows, case_ids) if not args.limit else None
        per_case = {c["case_id"]: c for c in (scored["cases"] if scored else harness_cases(rows, case_ids))}
        record["score"] = scored["report"] if scored else None
        categories = Counter()
        breakdown = defaultdict(lambda: [0, 0])
        for case_id in case_ids:
            q, g, m = d.questions[case_id], d.gold[case_id], d.manifest[case_id]
            pc = per_case[case_id]
            entry = {**results[case_id], **pc}
            entry["failure"] = classify({**pc, **results[case_id]}, q, g)
            categories[entry["failure"]] += 1
            for key in (f"route={results[case_id]['route']}", f"domain={m['domain_id']}", f"difficulty={m['difficulty']}",
                        f"answer={q['answer_spec']['type']}", f"slots={len(q['trace_spec']['slots'])}"):
                breakdown[key][0] += pc["fac"]
                breakdown[key][1] += 1
            case_records.append({"case_id": case_id, **entry})
        record["failure_categories"] = dict(categories)
        record["breakdown_micro_fac"] = {k: f"{v[0]}/{v[1]}" for k, v in sorted(breakdown.items())}
        if not args.limit:
            record["micro"] = {"fac": f"{sum(c['fac'] for c in per_case.values())}/{len(case_ids)}"}
    else:
        case_records = [{"case_id": c, **results[c]} for c in case_ids if c in results]

    common.write_jsonl(out / "cases.jsonl", case_records)
    if complete:
        record["predictions_sha256"] = common.write_jsonl(out / "predictions.jsonl", rows)
    if args.split in PACKAGED_SPLITS and complete and not args.limit:
        questions_path = str(common.ROOT / PACKAGED_SPLITS[args.split])
        predictions_path, zip_path = str(out / "predictions.jsonl"), str(out / "submission.zip")
        record["toolkit"] = {
            "validate": toolkit_cli("validate", "--questions", questions_path, "--predictions", predictions_path),
            "package": toolkit_cli("package", "--questions", questions_path, "--predictions", predictions_path,
                                   "--output", zip_path),
            "validate_zip": toolkit_cli("validate-zip", "--questions", questions_path, "--submission-zip", zip_path),
        }
        ok = (record["toolkit"]["validate"].get("valid") and record["toolkit"]["package"].get("status") == "PASS"
              and record["toolkit"]["validate_zip"].get("valid"))
        record["package_ok"] = bool(ok)
        if ok:
            record["archive_sha256"] = record["toolkit"]["package"]["archive_sha256"]
            common.append_jsonl(common.ROOT / "submissions" / "registry.jsonl", {
                "run_id": run_id, "split": args.split, "config": config["name"], "config_sha256": config["_sha256"],
                "predictions_jsonl_sha256": record["toolkit"]["package"]["predictions_jsonl_sha256"],
                "archive_sha256": record["archive_sha256"], "zip": f"runs/{run_id}/submission.zip",
                "uploaded": False, "receipt_id": None})
    common.write_bytes_atomic(out / "summary.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))
    common.append_jsonl(common.EXPERIMENTS_DIR / "log.jsonl", {k: v for k, v in record.items() if k != "config_full"})
    write_results_table()
    brief = {k: record.get(k) for k in ("run_id", "complete", "failures", "fresh_calls", "cached_calls", "usage",
                                        "failure_categories", "micro", "package_ok", "archive_sha256")}
    brief["by_route"] = (record.get("routing") or {}).get("by_route")
    brief["scores"] = (record.get("score") or {}).get("scores")
    print(json.dumps(brief, indent=1))
    return 0 if complete else 3


def harness_cases(rows, case_ids):
    """Per-case results without aggregate scoring (used for --limit smoke runs)."""

    from finreason_task1.scoring import score_case
    d = common.data()
    by_id = {r["case_id"]: r for r in rows}
    out = []
    for case_id in case_ids:
        r = score_case(d.questions[case_id], d.gold[case_id], by_id[case_id])
        out.append({"case_id": case_id, "fac": r.fac, "matched_slots": r.matched_slots, "total_slots": r.total_slots})
    return out


if __name__ == "__main__":
    raise SystemExit(main())
