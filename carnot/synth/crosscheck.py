"""Blind cross-check of authored templates (PLAN.md §4b, rule 5).

  python -m carnot.synth.crosscheck --author fable [--per-template 2]

A checker model outside the R1/R2 comparison (Fable for now; the non-Claude
model later) solves the first instances of every template from the question
text alone, through the same program-of-thought solver R1 and R2 use.  Each
field is judged with the toolkit's score_case on a row holding only that field.
Disagreements are flagged for the human review and never drop anything.
Output: synth/<author>/<template_id>/crosscheck.json and synth/crosscheck_<author>.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import common, exemplars
from ..config import load_config, make_sandbox
from ..formatter import build_row
from ..llm_client import ClaudeCLI
from ..solver import Solver, load_system_prompt
from finreason_task1.scoring import score_case
from .author import SYNTH_DIR, rules_root

CHECKERS = {"fable": {"model": "claude-fable-5-1", "effort": "medium"}}


def field_verdicts(question, gold, texts) -> dict[str, bool]:
    row, _ = build_row(question, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})
    verdicts = {"final": score_case(question, gold, dict(row, steps=[])).fac == 1}
    for slot in question["trace_spec"]["slots"]:
        only = dict(row, final_answer=None, steps=[s for s in row["steps"] if s["slot_id"] == slot["slot_id"]])
        verdicts[slot["slot_id"]] = score_case(question, gold, only).matched_slots == 1
    return verdicts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--author", default="fable")
    parser.add_argument("--rules", default="v2")
    parser.add_argument("--checker", default="fable", choices=sorted(CHECKERS))
    parser.add_argument("--per-template", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args(argv)

    lock = common.RunLock(SYNTH_DIR / ".crosscheck.lock", f"crosscheck {args.author} by {args.checker}")  # noqa: F841
    config = load_config("configs/r1.json")
    exemplar_file = json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))
    chosen = exemplars.select(exemplar_file, None, "S")
    settings = CHECKERS[args.checker]
    llm = ClaudeCLI(settings["model"], settings["effort"])
    sandbox = make_sandbox(config)
    solver = Solver(llm, sandbox, load_system_prompt(common.ROOT / config["system_prompt"]), config["max_retries"])
    template_dirs = sorted(p for p in (rules_root(args.rules) / args.author).glob("syn.*") if (p / "instances.jsonl").exists())
    jobs = []
    for directory in template_dirs:
        instances = common.read_jsonl(directory / "instances.jsonl")[: args.per_template]
        jobs += [(directory, instance) for instance in instances]

    def work(job):
        directory, instance = job
        outcome = solver.solve(instance["question"], chosen, 1, 0)
        texts = {"final": outcome["row"]["final_answer"]["value"]} if outcome["row"]["final_answer"] else {}
        texts.update({s["slot_id"]: s["value"] for s in outcome["row"]["steps"]})
        verdicts = field_verdicts(instance["question"], instance["gold"], texts)
        cost = sum(a.get("cost_equivalent_usd") or 0 for s in outcome["samples"] for a in s["attempts"] if not a["cached"])
        return directory, {"case_id": instance["question"]["case_id"], "seed": instance["seed"], "verdicts": verdicts,
                           "checker_values": texts, "gold": {"final": instance["gold"]["final_value"], **instance["gold"]["slot_values"]},
                           "cost_equivalent_usd": cost}

    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(work, jobs))
    finally:
        sandbox.close()

    by_template: dict = {}
    for directory, result in results:
        by_template.setdefault(directory, []).append(result)
    for directory, checks in sorted(by_template.items()):
        disagreements = [{"case_id": c["case_id"], "field": f, "checker": c["checker_values"].get(f), "gold": c["gold"][f]}
                         for c in checks for f, ok in c["verdicts"].items() if not ok]
        record = {"template_id": directory.name, "checker": args.checker, "model": llm.model, "effort": llm.effort,
                  "instances_checked": len(checks), "fields_checked": sum(len(c["verdicts"]) for c in checks),
                  "fields_agreeing": sum(sum(c["verdicts"].values()) for c in checks), "flagged": bool(disagreements),
                  "disagreements": disagreements, "checks": checks, "at": datetime.now(timezone.utc).isoformat()}
        common.write_bytes_atomic(directory / f"crosscheck_{args.checker}.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))
        common.append_jsonl(rules_root(args.rules) / f"crosscheck_{args.author}.jsonl", {k: v for k, v in record.items() if k != "checks"})
        print(f"{'FLAG' if disagreements else 'ok  '} {record['fields_agreeing']}/{record['fields_checked']} {directory.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
