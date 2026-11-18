"""Author new templates with a model outside the R1/R2 comparison (PLAN.md §4b).

  python -m carnot.synth.author plan                 # seeded topic plan (once)
  python -m carnot.synth.author run --first 2        # author the first N planned templates
  python -m carnot.synth.author run --index 3 7      # or chosen plan indices

The author sees only tuning-set questions (one per existing template of the
assigned topic, never lockbox, leaderboard or test text), the house rules in
prompts/synth_author_v2.txt (v1 was the pilot), and its own previous draft plus the exact error
when a check fails (at most MAX_REPAIRS repairs).  Sonnet and Opus, the models
being compared, take no part in authoring or filtering.  Output per template:
synth/<author>/<template_id>/{template.json, instances.jsonl, author_log.json}.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .. import common, splits
from ..config import load_config, make_sandbox
from ..llm_client import ClaudeCLI
from .template import DIFFICULTIES, TemplateError, generate, template_id

AUTHORS = {"fable": {"model": "claude-fable-5-1", "effort": "high"}}
PROMPTS = {"v2": common.ROOT / "carnot" / "prompts" / "synth_author_v2.txt",
           "v3": common.ROOT / "carnot" / "prompts" / "synth_author_v3.txt"}
SYNTH_DIR = common.ROOT / "synth"
PLAN = SYNTH_DIR / "plan_v1.json"
PLAN_SEED = "carnot-synth-plan-v1"
N_TEMPLATES = 25
N_INSTANCES = 6
MAX_REPAIRS = 2
JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


def make_plan() -> dict[str, Any]:
    """25 topics: 2 per domain plus 1 extra, seeded; difficulties cycle in draw order."""

    d = common.data()
    topics: dict[str, set[str]] = defaultdict(set)
    for case_id in d.ids("train"):
        row = d.manifest[case_id]
        topics[row["domain_id"]].add(row["topic_id"])
    rng = random.Random(PLAN_SEED)
    chosen = [(domain, topic) for domain in sorted(topics) for topic in rng.sample(sorted(topics[domain]), 2)]
    leftover = [(domain, topic) for domain in sorted(topics) for topic in sorted(topics[domain]) if (domain, topic) not in chosen]
    chosen.append(rng.choice(leftover))
    rng.shuffle(chosen)
    assignments = [{"index": i, "domain_id": domain, "topic_id": topic, "difficulty": DIFFICULTIES[i % 3]}
                   for i, (domain, topic) in enumerate(chosen)]
    return {"seed": PLAN_SEED, "n_templates": N_TEMPLATES, "n_instances": N_INSTANCES, "assignments": assignments,
            "made_at": datetime.now(timezone.utc).isoformat()}


def topic_examples(domain_id: str, topic_id: str) -> list[dict[str, Any]]:
    """One tuning-set case per existing template of the topic (tuning set only)."""

    d = common.data()
    tuning = set(splits.load()["tuning"])
    by_template: dict[str, list[str]] = defaultdict(list)
    for case_id in sorted(tuning):
        row = d.manifest[case_id]
        if row["domain_id"] == domain_id and row["topic_id"] == topic_id:
            by_template[row["template_id"]].append(case_id)
    return [{"template_id": t, "question": d.questions[ids[0]], "gold": d.gold[ids[0]], "difficulty": d.manifest[ids[0]]["difficulty"]}
            for t, ids in sorted(by_template.items())]


def user_prompt(assignment: dict[str, Any]) -> str:
    parts = [f"Assignment: write one new template for domain_id \"{assignment['domain_id']}\", topic_id "
             f"\"{assignment['topic_id']}\", difficulty \"{assignment['difficulty']}\".",
             "Existing templates in this topic (do not duplicate their structure, slots or slot descriptions):"]
    for n, example in enumerate(topic_examples(assignment["domain_id"], assignment["topic_id"]), start=1):
        q, g = example["question"], example["gold"]
        slots = [{"slot_id": s["slot_id"], "description": s["description"], "result_spec": s["result_spec"]}
                 for s in q["trace_spec"]["slots"]]
        parts.append(f"### Existing template {n} ({example['difficulty']})\n{q['question']}\n\nanswer_spec: "
                     f"{json.dumps(q['answer_spec'])}\nslots: {json.dumps(slots)}\nreference values: final="
                     f"{g['final_value']}, slots={json.dumps(g['slot_values'])}")
    parts.append("Write the new template now.")
    return "\n\n".join(parts)


def parse(text: str) -> dict[str, Any]:
    blocks = JSON_BLOCK.findall(text)
    if not blocks:
        raise TemplateError("no ```json code block found")
    try:
        return json.loads(blocks[-1])
    except json.JSONDecodeError as exc:
        raise TemplateError(f"the JSON does not parse: {exc}") from None


def rules_root(rules: str):
    """Output root per house-rule version: v2 at synth/<author>, later versions at synth/<rules>/<author>."""

    return SYNTH_DIR if rules == "v2" else SYNTH_DIR / rules


def plan_for(rules: str) -> dict[str, Any]:
    """v2: the drawn plan.  v3: the same assignments and order, every difficulty set to advanced."""

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if rules != "v2":
        plan = dict(plan, rules=rules, assignments=[dict(a, difficulty="advanced") for a in plan["assignments"]])
    return plan


def author_one(assignment: dict[str, Any], author: str, llm: ClaudeCLI, sandbox, rules: str = "v2") -> dict[str, Any]:
    system = PROMPTS[rules].read_text(encoding="utf-8")
    base = user_prompt(assignment)
    log: dict[str, Any] = {"assignment": assignment, "author": author, "rules": rules, "model": llm.model, "effort": llm.effort,
                           "system_prompt_sha256": common.sha256_text(system), "attempts": []}
    prompt, draft = base, None
    for attempt in range(MAX_REPAIRS + 1):
        response = llm.complete(system, prompt, tag=f"author{attempt}")
        record = {"attempt": attempt, "cache_key": response.key, "cached": response.cached, "model_id": response.model_id,
                  "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd}
        log["attempts"].append(record)
        try:
            draft = parse(response.text)
            for key in ("domain_id", "topic_id", "difficulty"):
                if draft.get(key) != assignment[key]:
                    raise TemplateError(f"{key} must be {assignment[key]!r}")
            generation = generate(draft, author, N_INSTANCES, sandbox, rules=rules)
        except TemplateError as exc:
            record["error"] = str(exc)[:1500]
            shown = json.dumps(draft, indent=1) if isinstance(draft, dict) else response.text[-3000:]
            prompt = (f"{base}\n\n### Your previous template\n```json\n{shown}\n```\n\nIt was rejected: {exc}\n"
                      "Write a corrected complete template (one ```json block).")
            continue
        tid = template_id(draft, author, rules)
        out = rules_root(rules) / author / tid
        out.mkdir(parents=True, exist_ok=True)
        common.write_bytes_atomic(out / "template.json", (json.dumps(draft, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        common.write_jsonl(out / "instances.jsonl", [
            {"seed": i.seed, "params": i.params, "question": i.question, "gold": i.gold, "manifest": i.manifest}
            for i in generation.instances])
        log.update(status="ok", template_id=tid, resampled_seeds=len(generation.errors))
        common.write_bytes_atomic(out / "author_log.json", (json.dumps(log, indent=1) + "\n").encode("utf-8"))
        return log
    log["status"] = "failed"
    failed = rules_root(rules) / author / "_failed"
    failed.mkdir(parents=True, exist_ok=True)
    common.write_bytes_atomic(failed / f"plan{assignment['index']:02d}.json", (json.dumps(log, indent=1) + "\n").encode("utf-8"))
    return log


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    run = sub.add_parser("run")
    run.add_argument("--author", default="fable", choices=sorted(AUTHORS))
    run.add_argument("--rules", default="v2", choices=sorted(PROMPTS))
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--first", type=int)
    group.add_argument("--index", type=int, nargs="+")
    args = parser.parse_args(argv)

    if args.command == "plan":
        if PLAN.exists():
            raise SystemExit(f"{PLAN} already exists; the plan is drawn once")
        plan = make_plan()
        SYNTH_DIR.mkdir(exist_ok=True)
        common.write_bytes_atomic(PLAN, (json.dumps(plan, indent=1) + "\n").encode("utf-8"))
        print(json.dumps(plan["assignments"], indent=1))
        return 0

    lock = common.RunLock(SYNTH_DIR / ".synth.lock", f"synth author {' '.join(argv or sys.argv[1:])}")  # noqa: F841
    plan = plan_for(args.rules)
    picked = plan["assignments"][: args.first] if args.first else [plan["assignments"][i] for i in args.index]
    settings = AUTHORS[args.author]
    llm = ClaudeCLI(settings["model"], settings["effort"])
    sandbox = make_sandbox(load_config("configs/r1.json"))
    results = []
    try:
        for assignment in picked:
            log = author_one(assignment, args.author, llm, sandbox, args.rules)
            summary = {"index": assignment["index"], "topic": f"{assignment['domain_id']}/{assignment['topic_id']}",
                       "difficulty": assignment["difficulty"], "status": log["status"], "template_id": log.get("template_id"),
                       "attempts": len(log["attempts"]),
                       "cost_equivalent_usd": round(sum(a.get("cost_equivalent_usd") or 0 for a in log["attempts"] if not a["cached"]), 4),
                       "errors": [a["error"][:200] for a in log["attempts"] if "error" in a]}
            results.append(summary)
            common.append_jsonl(SYNTH_DIR / "author_runs.jsonl", {**summary, "rules": args.rules, "at": datetime.now(timezone.utc).isoformat()})
            print(json.dumps(summary), flush=True)
    finally:
        sandbox.close()
    return 0 if all(r["status"] == "ok" for r in results) else 3


if __name__ == "__main__":
    raise SystemExit(main())
