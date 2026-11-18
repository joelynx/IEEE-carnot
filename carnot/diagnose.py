"""Small pre-registered diagnostics on chosen gold cases.

  python -m carnot.diagnose --spec experiments/diagnostics/<name>.json [--concurrency 6]

The spec (written and hashed before the run) names the cases, the target
slot(s) per case, and the arms (model, effort, sample offset).  Every arm uses
the base config's prompt, exemplars, sandbox and retries, so only the model
settings differ.  Each sample is scored alone with the toolkit's score_case;
the target slot is scored on a row holding only that slot.  Plurality votes
over consecutive blocks of samples reuse Solver.solve (cache replays).
Gold splits only; never test.  Results: runs/diag_<name>_<ts>/ and
experiments/diagnostics.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import common, exemplars, splits
from .config import load_config, make_sandbox
from .formatter import build_row
from .llm_client import ClaudeCLI
from .run import git_commit
from .solver import Solver, load_system_prompt
from finreason_task1.scoring import score_case


def judge(question, gold, texts, targets):
    row, _ = build_row(question, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})
    full = score_case(question, gold, row)
    target_ok = {}
    for slot_id in targets:
        only = dict(row, final_answer=None, steps=[s for s in row["steps"] if s["slot_id"] == slot_id])
        target_ok[slot_id] = score_case(question, gold, only).matched_slots == 1
    others_total = (1 + full.total_slots) - len(targets)
    others_ok = full.fac + full.matched_slots - sum(target_ok.values())
    return {"row": row, "fac": full.fac, "matched_slots": full.matched_slots, "total_slots": full.total_slots,
            "all_correct": full.fac == 1 and full.matched_slots == full.total_slots,
            "target_ok": target_ok, "others_ok": others_ok, "others_total": others_total}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--concurrency", type=int, default=6)
    args = parser.parse_args(argv)

    spec_bytes = open(args.spec, "rb").read()
    spec = json.loads(spec_bytes)
    split_ids = set(splits.load()[spec["split"]])
    if spec["split"] not in {"tuning-eval", "tuning", "tuning-smoke"} or not set(spec["cases"]) <= split_ids:
        raise SystemExit("diagnostics run on tuning cases only")
    config = load_config(spec["base_config"])
    run_lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"diagnose {spec['name']}")  # noqa: F841
    d = common.data()
    exemplar_file = json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))
    system = load_system_prompt(common.ROOT / config["system_prompt"])
    sandbox = make_sandbox(config)
    k, block = spec["samples_per_case_per_arm"], spec["vote_block"]
    solvers, clients = {}, {}
    for arm in spec["arms"]:
        clients[arm["name"]] = ClaudeCLI(arm["model"], arm["effort"])
        solvers[arm["name"]] = Solver(clients[arm["name"]], sandbox, system, config["max_retries"])
    chosen = {c: exemplars.select(exemplar_file, d.template(c), "S") for c in spec["cases"]}

    jobs = [(arm, c, arm["sample_offset"] + i) for arm in spec["arms"] for c in spec["cases"] for i in range(k)]
    def work(job):
        arm, case_id, sample = job
        return job, solvers[arm["name"]].solve_sample(d.questions[case_id], chosen[case_id], sample)
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            done = list(pool.map(work, jobs))
        votes = []
        for arm in spec["arms"]:
            for case_id in spec["cases"]:
                for start in range(0, k, block):
                    outcome = solvers[arm["name"]].solve(d.questions[case_id], chosen[case_id], block,
                                                         arm["sample_offset"] + start)
                    fields = ["final"] + [s["slot_id"] for s in d.questions[case_id]["trace_spec"]["slots"]]
                    texts = {f: _winner(outcome, f) for f in fields if _winner(outcome, f) is not None}
                    votes.append({"arm": arm["name"], "case_id": case_id, "block_start": start,
                                  **judge(d.questions[case_id], d.gold[case_id], texts, spec["cases"][case_id])})
    finally:
        sandbox.close()

    samples = []
    usage = defaultdict(lambda: defaultdict(float))
    for (arm, case_id, sample), result in done:
        verdict = judge(d.questions[case_id], d.gold[case_id], result.texts, spec["cases"][case_id])
        model_ids = sorted({a["model_id"] for a in result.attempts if a.get("model_id")})
        for attempt in result.attempts:
            u = usage[arm["name"]]
            u["calls"] += 1
            u["fresh_calls"] += 0 if attempt["cached"] else 1
            u["cost_equivalent_usd"] += 0 if attempt["cached"] else float(attempt.get("cost_equivalent_usd") or 0)
            u["output_tokens"] += 0 if attempt["cached"] else int((attempt["usage"] or {}).get("output_tokens") or 0)
        samples.append({"arm": arm["name"], "case_id": case_id, "template_id": d.template(case_id), "sample": sample,
                        "model_ids": model_ids, "texts": result.texts, "issues": result.issues,
                        "attempts": len(result.attempts), **verdict})

    summary = {"arms": {}}
    for arm in spec["arms"]:
        mine = [s for s in samples if s["arm"] == arm["name"]]
        by_template = defaultdict(lambda: [0, 0])
        for s in mine:
            for ok in s["target_ok"].values():
                by_template[s["template_id"]][0] += ok
                by_template[s["template_id"]][1] += 1
        target = [ok for s in mine for ok in s["target_ok"].values()]
        arm_votes = [v for v in votes if v["arm"] == arm["name"]]
        summary["arms"][arm["name"]] = {
            "model": arm["model"], "effort": arm["effort"], "observed_model_ids": sorted({m for s in mine for m in s["model_ids"]}),
            "samples": len(mine),
            "target_slot_correct": f"{sum(target)}/{len(target)}",
            "target_slot_rate": sum(target) / len(target),
            "target_by_template": {t: f"{a}/{b}" for t, (a, b) in sorted(by_template.items())},
            "all_fields_correct": f"{sum(s['all_correct'] for s in mine)}/{len(mine)}",
            "non_target_fields_correct": f"{sum(s['others_ok'] for s in mine)}/{sum(s['others_total'] for s in mine)}",
            "non_target_rate": sum(s["others_ok"] for s in mine) / sum(s["others_total"] for s in mine),
            "votes_target_correct": f"{sum(all(v['target_ok'].values()) for v in arm_votes)}/{len(arm_votes)}",
            "votes_all_correct": f"{sum(v['all_correct'] for v in arm_votes)}/{len(arm_votes)}",
            "usage": dict(usage[arm["name"]]),
        }
    control, treatment = (summary["arms"][a["name"]] for a in spec["arms"])
    gain = treatment["target_slot_rate"] - control["target_slot_rate"]
    def rate(text):
        a, b = map(int, text.split("/"))
        return a / b
    both_templates = all(rate(treatment["target_by_template"][t]) >= rate(control["target_by_template"][t])
                         for t in control["target_by_template"])
    no_regression = treatment["non_target_rate"] >= control["non_target_rate"] - 0.10
    if gain >= 0.30 and both_templates and no_regression:
        verdict = "supports_stronger_model"
    elif gain <= 0.10:
        verdict = "against"
    else:
        verdict = "inconclusive"
    summary.update({"target_rate_gain": gain, "treatment_ge_control_on_every_template": both_templates,
                    "no_non_target_regression": no_regression, "verdict": verdict})

    started = datetime.now(timezone.utc)
    out = common.RUNS_DIR / f"diag_{spec['name']}_{started:%Y%m%dT%H%M%SZ}"
    out.mkdir(parents=True, exist_ok=True)
    common.write_jsonl(out / "samples.jsonl", samples)
    common.write_jsonl(out / "votes.jsonl", votes)
    record = {"name": spec["name"], "at": started.isoformat(), "spec": args.spec, "spec_sha256": common.sha256_bytes(spec_bytes),
              "out": out.relative_to(common.ROOT).as_posix(), "llm": {n: c.describe() for n, c in clients.items()},
              "git": git_commit(), **summary}
    common.write_bytes_atomic(out / "summary.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))
    common.append_jsonl(common.EXPERIMENTS_DIR / "diagnostics.jsonl", record)
    print(json.dumps(summary, indent=1))
    return 0


def _winner(outcome, field):
    row = outcome["row"]
    if field == "final":
        return row["final_answer"]["value"] if row["final_answer"] else None
    return next((s["value"] for s in row["steps"] if s["slot_id"] == field), None)


if __name__ == "__main__":
    sys.exit(main())
