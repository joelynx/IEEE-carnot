"""Check synthetic oracles on deterministic parameter endpoints before evaluation.

This verifies executable/format robustness, not semantic truth. Independent blind
derivations remain mandatory. No solver-performance filtering is performed.
"""

import json
from fractions import Fraction

from . import common
from .config import load_config, make_sandbox
from .formatter import render
from .improvement_campaign import PILOT, ROOT, save, verify_protected
from .sandbox.executor import decode
from .synth.template import program_source


def endpoints(params):
    def values(spec):
        if spec["kind"] == "choice":
            return spec["values"][0], spec["values"][-1]
        parse = int if spec["kind"] == "int" else lambda x: Fraction(str(x))
        return parse(spec["min"]), parse(spec["max"])
    bounds = {k: values(s) for k, s in params.items()}
    low, high = ({k: v[j] for k, v in bounds.items()} for j in (0, 1))
    candidates = [("all_min", low), ("all_max", high)]
    candidates += [(f"min_except_{k}", dict(low, **{k: bounds[k][1]})) for k in bounds]
    candidates += [(f"max_except_{k}", dict(high, **{k: bounds[k][0]})) for k in bounds]
    unique, seen = [], set()
    for label, p in candidates:
        signature = tuple((k, repr(v)) for k, v in sorted(p.items()))
        if signature not in seen:
            unique.append((label, p))
            seen.add(signature)
    return unique


def main():
    verify_protected()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 deterministic oracle endpoints")
    box = make_sandbox(load_config("configs/r4.json"))
    reports = []
    try:
        for path in sorted(PILOT.glob("family_*/template.json")):
            tpl = json.loads(path.read_text())
            checks = []
            for label, params in endpoints(tpl["params"]):
                reply = box.run(program_source(tpl, params))
                check = {"endpoint": label, "params": {k: str(v) for k, v in params.items()},
                         "ok": reply.get("ok"), "stage": reply.get("stage"), "error": reply.get("error")}
                if reply.get("ok"):
                    outputs = {k: decode(v) for k, v in reply["values"].items()}
                    fields = [("final", tpl["answer_spec"])] + [(s["slot_id"], s["result_spec"]) for s in tpl["slots"]]
                    errors = {k: ("missing" if k not in outputs else render(outputs[k], spec).issue)
                              for k, spec in fields}
                    check["format_errors"] = {k: v for k, v in errors.items() if v}
                    check["ok"] = not check["format_errors"]
                check["declared_invalid"] = not reply.get("ok") and "ValueError" in str(reply.get("error"))
                checks.append(check)
            failures = [c for c in checks if not c["ok"] and not c["declared_invalid"]]
            report = {"family": path.parent.name, "template_sha256": common.sha256_file(path),
                      "checks": checks, "unexpected_failures": len(failures),
                      "declared_invalid": sum(c["declared_invalid"] for c in checks),
                      "semantic_correctness": "not_established_by_endpoint_execution"}
            save(path.parent / "endpoint_check.json", report)
            reports.append({k: v for k, v in report.items() if k != "checks"})
    finally:
        box.close()
    save(ROOT / "endpoint_report.json", reports)
    print(json.dumps(reports, indent=2))
    if any(r["unexpected_failures"] for r in reports):
        raise SystemExit("unexpected oracle endpoint failures require investigation")


if __name__ == "__main__":
    main()
