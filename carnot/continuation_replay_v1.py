"""Package B replay evidence: the new runner must reproduce saved behavior with zero fresh calls.

  python -m carnot.continuation_replay_v1 pilot-panel              # question-only panel of the 96 pilot cases
  python -m carnot.continuation_replay_v1 check-pilot --run-dir <dir>
  python -m carnot.continuation_replay_v1 check-historical --run-dir <dir> --mode S|H

The checks compare request keys, executed candidate outputs, votes, selected rows, verifier
verdicts and fallbacks with the prior campaign's saved records (read as UTF-8).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import common
from .continuation_state_v1 import PRIOR, ROOT
from .improvement_validation_v1 import read_json, save_json

PILOT_DIR = ROOT / "replay" / "pilot"
PILOT_PANEL = PILOT_DIR / "panel.json"
HISTORICAL = {"S": "runs/20261012T163526Z_r4_tuning-eval_S_forced-novel",
              "H": "runs/20261012T163913Z_r4_tuning-eval_H_forced-novel"}


def pilot_panel() -> None:
    if PILOT_PANEL.exists():
        raise SystemExit("pilot replay panel already exists")
    questions, gold, families = [], [], {}
    for directory in sorted((PRIOR / "pilot").glob("family_*")):
        if not (directory / "instances.jsonl").exists():
            continue
        for item in common.read_jsonl(directory / "instances.jsonl"):
            case_id = item["question"]["case_id"]
            questions.append({"question": item["question"], "manifest": item["manifest"], "family": directory.name})
            gold.append({"case_id": case_id, "gold": item["gold"]})
            families[case_id] = directory.name
    q_sha = common.write_jsonl(PILOT_DIR / "questions.jsonl", questions)
    g_sha = common.write_jsonl(PILOT_DIR / "gold.jsonl", gold)
    ids = sorted(families)
    save_json(PILOT_PANEL, {
        "panel_id": "pilot-replay", "kind": "synthetic", "partition": "development",
        "source": "experiments/improvement_20261020/pilot/family_*/instances.jsonl (development evidence only)",
        "case_ids": ids, "case_ids_sha256": common.sha256_text("\n".join(ids)), "families": families,
        "question_files": [{"path": (PILOT_DIR / "questions.jsonl").relative_to(common.ROOT).as_posix(), "sha256": q_sha}],
        "gold_files": [{"path": (PILOT_DIR / "gold.jsonl").relative_to(common.ROOT).as_posix(), "sha256": g_sha}]})
    print(f"wrote {len(ids)} pilot cases to {PILOT_PANEL.relative_to(common.ROOT)}")


def keys(samples) -> list[str]:
    return [a["cache_key"] for s in samples for a in s["attempts"]]


def same_outcome(new, old, label, problems) -> int:
    for k in ("row", "votes", "dropped_by_gate"):
        if new[k] != old[k]:
            problems.append(f"{label}: {k} differs")
    if [s["texts"] for s in new["samples"]] != [s["texts"] for s in old["samples"]]:
        problems.append(f"{label}: executed candidate outputs differ")
    if keys(new["samples"]) != keys(old["samples"]):
        problems.append(f"{label}: request keys differ")
    fresh = [a for s in new["samples"] for a in s["attempts"] if not a["cached"]]
    if fresh:
        problems.append(f"{label}: {len(fresh)} fresh calls")
    return sum(len(s["attempts"]) for s in new["samples"])


def check_pilot(run_dir: Path) -> None:
    panel = read_json(PILOT_PANEL)
    old = {}
    for family in sorted(set(panel["families"].values())):
        for name, path in (("r4", PRIOR / "pilot" / family / "evaluation_r4.json"),
                           ("p", PRIOR / "pilot" / family / "evaluation_r5p.json"),
                           ("d5", PRIOR / "diversity_pilot" / f"{family}.json"),
                           ("v", PRIOR / "verifier_pilot" / f"{family}.json")):
            for case in read_json(path)["cases"]:
                old.setdefault(case["case_id"], {})[name] = case
    problems, calls, counts = [], 0, {"cases": 0, "verifier_calls": 0, "extra_samples": 0, "triggered": 0}
    for case_id in panel["case_ids"]:
        new = read_json(run_dir / "cases" / f"{case_id}.json")
        saved = old[case_id]
        counts["cases"] += 1
        calls += same_outcome(new["arms"]["r4"], saved["r4"]["outcome"], f"{case_id}/R4", problems)
        calls += same_outcome(new["arms"]["p"], saved["p"]["outcome"], f"{case_id}/P", problems)
        calls += same_outcome(new["arms"]["d5"], saved["d5"]["outcome"], f"{case_id}/D5", problems)
        if new["selections"]["J"]["row"] != saved["d5"]["complete_row"] \
                or new["selections"]["J"]["choice"] != saved["d5"]["complete_row_choice"]:
            problems.append(f"{case_id}/J: complete-row selection differs")
        v_old = saved["v"]
        if new["selections"]["V"]["row"] != v_old["row"]:
            problems.append(f"{case_id}/V: selected row differs")
        if new["trigger"]["triggered"] != (v_old["call"] is not None):
            problems.append(f"{case_id}: trigger differs from the saved verifier eligibility")
        if v_old["call"] is not None:
            counts["triggered"] += 1
            call, verdict = new["arms"]["v"]["call"], new["arms"]["v"]["verdict"]
            counts["verifier_calls"] += 1
            calls += 1
            if not call["cached"] or call["cache_key"] != v_old["call"]["cache_key"] \
                    or call["raw_response"] != v_old["call"]["raw_response"]:
                problems.append(f"{case_id}/V: verifier request or response differs")
            for k in ("selected_original_index", "selected_anonymous_index", "reason", "rendered_evidence"):
                if verdict.get(k) != v_old["verdict"].get(k):
                    problems.append(f"{case_id}/V: verdict {k} differs")
            control = read_json(PRIOR / "sampling_control" / f"{case_id}.json")
            extra = new["arms"]["x1"]
            counts["extra_samples"] += 1
            calls += len(extra["extra_sample"]["attempts"])
            if extra["row"] != control["outcome"]["row"] or extra["votes"] != control["outcome"]["votes"]:
                problems.append(f"{case_id}/X1: six-sample vote differs")
            old_extra = control["outcome"]["samples"][5]
            if keys([extra["extra_sample"]]) != keys([old_extra]) or extra["extra_sample"]["texts"] != old_extra["texts"]:
                problems.append(f"{case_id}/X1: sixth-sample request or outputs differ")
            if not all(a["cached"] for a in extra["extra_sample"]["attempts"]):
                problems.append(f"{case_id}/X1: fresh call")
        elif "v" in new["arms"] or "x1" in new["arms"]:
            problems.append(f"{case_id}: verifier or extra sample ran without a saved counterpart")
    report = {"scope": "all 96 pilot cases: R4, P, D5 (D), J, V, X1; JB is new and has no saved counterpart",
              "run_dir": run_dir.as_posix(), "counts": counts, "cached_calls_compared": calls, "fresh_calls": 0 if not
              any("fresh" in p for p in problems) else None, "problems": problems, "identical": not problems,
              "replay_code_sha256": common.sha256_file(Path(__file__)),
              "runner_sha256": common.sha256_file(common.ROOT / "carnot/improvement_validation_v1.py")}
    save_json(ROOT / "replay_report.json", {**read_json(ROOT / "replay_report.json"), "pilot": report}
              if (ROOT / "replay_report.json").exists() else {"pilot": report})
    print(json.dumps({k: v for k, v in report.items() if k != "problems"} | {"problems": problems[:20]}, indent=1))
    if problems:
        raise SystemExit(f"{len(problems)} replay differences")


def check_historical(run_dir: Path, mode: str) -> None:
    old = {c["case_id"]: c for c in common.read_jsonl(common.ROOT / HISTORICAL[mode] / "cases.jsonl")}
    problems, calls = [], 0
    files = sorted((run_dir / "cases").glob("*.json"))
    if len(files) != len(old):
        problems.append(f"coverage {len(files)} != {len(old)}")
    for path in files:
        new = read_json(path)
        saved = old[new["case_id"]]
        if new["exemplars"] != saved["exemplars"]:
            problems.append(f"{new['case_id']}: exemplars differ")
        calls += same_outcome(new["arms"]["r4"], saved, f"{new['case_id']}/R4", problems)
    report = {"scope": f"tuning-eval forced-novel {mode}: historical R4 identities 0-4, cache-only",
              "source_run": HISTORICAL[mode], "run_dir": run_dir.as_posix(), "cases": len(files),
              "cached_calls_compared": calls, "problems": problems[:50], "identical": not problems,
              "replay_code_sha256": common.sha256_file(Path(__file__))}
    existing = read_json(ROOT / "replay_report.json") if (ROOT / "replay_report.json").exists() else {}
    existing[f"historical_r4_tuning_eval_{mode}"] = report
    save_json(ROOT / "replay_report.json", existing)
    print(json.dumps(report, indent=1))
    if problems:
        raise SystemExit(f"{len(problems)} historical replay differences")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["pilot-panel", "check-pilot", "check-historical"])
    parser.add_argument("--run-dir")
    parser.add_argument("--mode", choices=["S", "H"])
    args = parser.parse_args(argv)
    if args.action == "pilot-panel":
        pilot_panel()
    elif args.action == "check-pilot":
        check_pilot(Path(args.run_dir))
    else:
        check_historical(Path(args.run_dir), args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
