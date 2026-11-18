"""Verified fixed exemplars for R0 (PLAN.md §3.2, P0.4).

Exemplars come only from the exemplar pool (tuning minus tuning-eval), so no
evaluated, lockbox, leaderboard or test case is ever shown as an example.
Three feature categories are defined from public spec fields only:

  A  decimal final, >= 2 slots, all exact decimals, incl. a percent or ratio unit
  B  enum (categorical) final with >= 1 decimal slot
  C  decimal final with >= 1 half-up-rounded slot

For each category, templates are visited in a seeded order; one pool case per
template is solved zero-shot by the R0 solver; a program is kept only if the
toolkit scorer gives FAC = 1 and every slot correct against train gold.  Two
verified exemplars per category (distinct templates) are kept: a primary and a
backup used in H-mode when the query shares the primary's template.

Usage:  python -m carnot.exemplars --config configs/r0.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict

from . import common, splits
from .config import load_config, make_llm, make_sandbox
from .solver import PERCENT_UNITS, Solver, load_system_prompt
from finreason_task1.scoring import score_case

CATEGORIES = ("A", "B", "C")
MAX_CANDIDATES = 8


def category_of(question) -> set[str]:
    answer = question["answer_spec"]
    slots = question["trace_spec"]["slots"]
    decimal_slots = [s for s in slots if s["result_spec"]["type"] == "decimal"]
    found = set()
    if (answer["type"] == "decimal" and len(slots) >= 2 and len(decimal_slots) == len(slots)
            and all(s["result_spec"]["rounding"]["mode"] == "exact" for s in slots)
            and any(s["result_spec"]["unit"] in PERCENT_UNITS | {"ratio"} for s in slots)):
        found.add("A")
    if answer["type"] == "enum" and decimal_slots:
        found.add("B")
    if answer["type"] == "decimal" and any(
            s["result_spec"]["rounding"]["mode"] == "half_up" for s in decimal_slots):
        found.add("C")
    return found


def candidates(category: str) -> list[str]:
    d = common.data()
    by_template = defaultdict(list)
    for case_id in splits.load()["exemplar-pool"]:
        if category in category_of(d.questions[case_id]):
            by_template[d.template(case_id)].append(case_id)
    templates = sorted(by_template)
    random.Random(int(hashlib.sha256(f"carnot-exemplars-{category}".encode()).hexdigest(), 16)).shuffle(templates)
    return [sorted(by_template[t])[0] for t in templates]


def verified(question, gold, row) -> bool:
    result = score_case(question, gold, row)
    return result.fac == 1 and result.matched_slots == result.total_slots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    llm, sandbox = make_llm(config), make_sandbox(config)
    system = load_system_prompt(common.ROOT / config["system_prompt"])
    solver = Solver(llm, sandbox, system, config["max_retries"])
    d = common.data()
    chosen, log = [], []
    try:
        for category in CATEGORIES:
            kept = []
            for case_id in candidates(category)[:MAX_CANDIDATES]:
                if any(e["template_id"] == d.template(case_id) for e in chosen + kept):
                    continue
                question = d.questions[case_id]
                outcome = solver.solve(question, [], n_samples=1)
                attempts = outcome["samples"][0]["attempts"]
                ok = verified(question, d.gold[case_id], outcome["row"])
                program = next((a["code"] for a in reversed(attempts) if a.get("rendered") and not a.get("issues")), None)
                log.append({"category": category, "case_id": case_id, "verified": ok,
                            "attempts": len(attempts), "usage": [a["usage"] for a in attempts]})
                print(f"{category} {case_id} {d.template(case_id)} verified={ok}", flush=True)
                if ok and program:
                    kept.append({"category": category, "role": "primary" if not kept else "backup",
                                 "case_id": case_id, "template_id": d.template(case_id),
                                 "question": question, "program": program})
                if len(kept) == 2:
                    break
            if len(kept) < 2:
                raise SystemExit(f"category {category}: only {len(kept)} verified exemplars")
            chosen += kept
    finally:
        sandbox.close()
    out = common.ROOT / config["exemplars"]
    content = {"config": config["name"], "llm": llm.describe(), "system_prompt_sha256": common.sha256_text(system),
               "exemplars": chosen, "bootstrap_log": log}
    common.write_bytes_atomic(out, (json.dumps(content, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"wrote {out}")
    return 0


def select(exemplar_file: dict, template_id: str | None, mode: str) -> list[dict]:
    """Primary exemplar per category; in H-mode swap in the backup if templates collide."""

    by_category = defaultdict(dict)
    for example in exemplar_file["exemplars"]:
        by_category[example["category"]][example["role"]] = example
    picked = []
    for category in CATEGORIES:
        primary, backup = by_category[category]["primary"], by_category[category]["backup"]
        if mode != "S" and template_id is not None and primary["template_id"] == template_id:
            picked.append(backup)
        else:
            picked.append(primary)
    return picked


if __name__ == "__main__":
    raise SystemExit(main())
