"""Difficulty probe of authored templates with a model outside the comparison (pre-registration haiku_probe_v1).

  python -m carnot.synth.probe --author fable

For every template: 4 probe instances from seeds 1000 upward (disjoint from the
evaluation instances, never evaluated), each solved once by Haiku 5.5 through
the R1/R2 program-of-thought solver.  A template is *trivial* iff Haiku gets
every field right on all 4.  Trivial templates leave the primary R1-vs-R2
analysis and stay in the secondary one; nothing is deleted.
Output: synth/<author>/<template_id>/probe_haiku.json and synth/probe_haiku_<author>.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import common, exemplars
from ..config import load_config, make_sandbox
from ..llm_client import ClaudeCLI
from ..solver import Solver, load_system_prompt
from .author import SYNTH_DIR, rules_root
from .crosscheck import field_verdicts
from .template import generate

PROBE = {"model": "claude-haiku-5-5", "effort": "medium", "instances": 4, "seed_start": 1000}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--author", default="fable")
    parser.add_argument("--rules", default="v2")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args(argv)

    lock = common.RunLock(SYNTH_DIR / ".probe.lock", f"haiku probe {args.author}")  # noqa: F841
    config = load_config("configs/r1.json")
    exemplar_file = json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))
    chosen = exemplars.select(exemplar_file, None, "S")
    llm = ClaudeCLI(PROBE["model"], PROBE["effort"])
    sandbox = make_sandbox(config)
    solver = Solver(llm, sandbox, load_system_prompt(common.ROOT / config["system_prompt"]), config["max_retries"])
    jobs = []
    try:
        for directory in sorted((rules_root(args.rules) / args.author).glob("syn.*")):
            if not (directory / "instances.jsonl").exists():
                continue
            tpl = json.loads((directory / "template.json").read_text(encoding="utf-8"))
            evaluation_ids = {row["question"]["case_id"] for row in common.read_jsonl(directory / "instances.jsonl")}
            probes = generate(tpl, args.author, PROBE["instances"], sandbox, seed_start=PROBE["seed_start"], rules=args.rules).instances
            assert not evaluation_ids & {p.question["case_id"] for p in probes}, "probe instances must be disjoint"
            jobs += [(directory, probe) for probe in probes]

        def work(job):
            directory, probe = job
            outcome = solver.solve(probe.question, chosen, 1, 0)
            texts = {"final": outcome["row"]["final_answer"]["value"]} if outcome["row"]["final_answer"] else {}
            texts.update({s["slot_id"]: s["value"] for s in outcome["row"]["steps"]})
            verdicts = field_verdicts(probe.question, probe.gold, texts)
            return directory, {"case_id": probe.question["case_id"], "seed": probe.seed, "params": probe.params,
                               "verdicts": verdicts, "all_correct": all(verdicts.values()), "probe_values": texts,
                               "gold": {"final": probe.gold["final_value"], **probe.gold["slot_values"]}}

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(work, jobs))
    finally:
        sandbox.close()

    by_template: dict = {}
    for directory, result in results:
        by_template.setdefault(directory, []).append(result)
    trivial = 0
    for directory, checks in sorted(by_template.items()):
        solved = sum(c["all_correct"] for c in checks)
        record = {"template_id": directory.name, "probe": PROBE, "instances": len(checks), "all_correct": solved,
                  "trivial": solved == len(checks) == PROBE["instances"],
                  "fields_correct": f"{sum(sum(c['verdicts'].values()) for c in checks)}/{sum(len(c['verdicts']) for c in checks)}",
                  "checks": checks, "at": datetime.now(timezone.utc).isoformat()}
        trivial += record["trivial"]
        common.write_bytes_atomic(directory / "probe_haiku.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))
        common.append_jsonl(rules_root(args.rules) / f"probe_haiku_{args.author}.jsonl", {k: v for k, v in record.items() if k != "checks"})
        print(f"{'TRIVIAL' if record['trivial'] else 'keeps  '} {solved}/{len(checks)} all-correct, fields {record['fields_correct']}  {directory.name}", flush=True)
    print(f"trivial: {trivial} of {len(by_template)}; non-trivial: {len(by_template) - trivial}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
