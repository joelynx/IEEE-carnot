"""Human review packet for authored templates (PLAN.md §4b, rule 6).

  python -m carnot.synth.review packet --author fable

Writes synth/<author>/REVIEW.md (everything the reviewer needs per template:
question, slots, parameter ranges, program, gold for every instance, cross-check
result) and synth/<author>/reviews.json, one entry per template with
"decision": accept | fix | reject and a "reason".  Existing decisions are kept
when the packet is regenerated.  No R1 or R2 output exists for these templates
at review time, and none is shown.
"""

from __future__ import annotations

import argparse
import json
import sys

from .. import common
from .author import SYNTH_DIR, rules_root


def packet(author: str, rules: str = "v2") -> tuple[str, dict]:
    root = rules_root(rules) / author
    plan = {a["index"]: a for a in json.loads((SYNTH_DIR / "plan_v1.json").read_text(encoding="utf-8"))["assignments"]}
    reviews_path = root / "reviews.json"
    reviews = json.loads(reviews_path.read_text(encoding="utf-8")) if reviews_path.exists() else {}
    entries = []
    for directory in sorted(root.glob("syn.*")):
        if not (directory / "instances.jsonl").exists():
            continue
        tpl = json.loads((directory / "template.json").read_text(encoding="utf-8"))
        log = json.loads((directory / "author_log.json").read_text(encoding="utf-8"))
        instances = common.read_jsonl(directory / "instances.jsonl")
        checks = sorted(directory.glob("crosscheck_*.json"))
        entries.append((log["assignment"]["index"], directory.name, tpl, log, instances,
                        [json.loads(c.read_text(encoding="utf-8")) for c in checks]))
        reviews.setdefault(directory.name, {"decision": None, "reason": "", "fix": ""})
    lines = [f"# Review packet: {author}-authored templates", "",
             "For each template: is the question clear and realistic, are its conventions stated, is the program right, "
             "and is every gold value correct? Record **accept**, **fix** (describe the change to the template) or "
             f"**reject** with a reason in `synth/{author}/reviews.json` (or tell Claude). Fixes change the template, never "
             "individual gold values. No R1 or R2 output exists for these questions.", "",
             f"House rules: {rules}. Templates: {len(entries)}.", ""]
    for index, tid, tpl, log, instances, checks in sorted(entries):
        first = instances[0]
        lines += [f"## {index}. {tpl['domain_id']} / {tpl['topic_id']} ({tpl['difficulty']})", "", f"`{tid}`", "",
                  f"Authored by {log['model']} (effort {log['effort']}) in {len(log['attempts'])} attempt(s)"
                  + (f"; rejected drafts: {'; '.join(a['error'][:160] for a in log['attempts'] if 'error' in a)}" if len(log['attempts']) > 1 else "")
                  + ".", "", "**Question (seed 0):**", "", "> " + first["question"]["question"].replace("\n", "\n> "), "",
                  "**Final answer spec:** `" + json.dumps(tpl["answer_spec"]) + "`", "", "| Slot | Description | Spec |", "|---|---|---|"]
        lines += [f"| `{s['slot_id']}` | {s['description']} | `{json.dumps(s['result_spec'])}` |" for s in tpl["slots"]]
        lines += ["", "**Parameters:** " + "; ".join(
            f"`{k}` " + (f"{v['min']}..{v['max']} step {v['step']}" if v["kind"] != "choice" else f"one of {v['values']}")
            for k, v in tpl["params"].items()), "", "**Program:**", "", "```python", tpl["program"].rstrip(), "```", "",
            "**Gold for every instance:**", "", "| Seed | Parameters | Final | " + " | ".join(s["slot_id"] for s in tpl["slots"]) + " |",
            "|---|---|---|" + "---|" * len(tpl["slots"])]
        for inst in instances:
            params = ", ".join(f"{k}={v}" for k, v in inst["params"].items())
            lines.append(f"| {inst['seed']} | {params} | {inst['gold']['final_value']} | "
                         + " | ".join(inst["gold"]["slot_values"][s["slot_id"]] for s in tpl["slots"]) + " |")
        if checks:
            for check in checks:
                verdict = "all fields agree" if not check["flagged"] else "**DISAGREEMENTS: " + "; ".join(
                    f"{d['field']}: checker {d['checker']} vs gold {d['gold']}" for d in check["disagreements"]) + "**"
                lines += ["", f"**Blind cross-check** ({check['model']}, {check['instances_checked']} instances): "
                          f"{check['fields_agreeing']}/{check['fields_checked']} fields, {verdict}."]
        else:
            lines += ["", "**Blind cross-check:** not run yet."]
        decision = reviews[tid]
        lines += ["", f"**Decision:** {decision['decision'] or '_pending_'}" + (f" ({decision['reason']})" if decision["reason"] else ""), "", "---", ""]
    return "\n".join(lines) + "\n", reviews


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("packet")
    make.add_argument("--author", default="fable")
    make.add_argument("--rules", default="v2")
    args = parser.parse_args(argv)
    text, reviews = packet(args.author, args.rules)
    root = rules_root(args.rules) / args.author
    common.write_bytes_atomic(root / "REVIEW.md", text.encode("utf-8"))
    common.write_bytes_atomic(root / "reviews.json", (json.dumps(reviews, indent=1) + "\n").encode("utf-8"))
    print(f"{root / 'REVIEW.md'}: {len(reviews)} templates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
