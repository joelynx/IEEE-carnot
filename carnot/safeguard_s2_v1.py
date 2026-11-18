"""S2 no-harm safeguard analysis (docs/task1-safeguard-v2-plan.md; frozen preregistration in
experiments/safeguard_s2_20261022/preregistration.json).  No model calls.

  python -m carnot.safeguard_s2_v1 --run S=<scored run dir> --run H=<scored run dir> --out <report.json>
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Mapping

from . import common
from .improvement_validation_v1 import read_json, save_json

BOUND = 0.011          # G2
NOISE_LIMIT = 2        # G3
MIN_SLOT_TOLERANCE = 2  # G4


def clopper_pearson_upper(k: int, n: int, level: float = 0.95) -> float:
    if k >= n:
        return 1.0
    from scipy.stats import beta
    return float(beta.ppf(level, k + 1, n - k))


def gates(baseline: Mapping[str, dict], replicate: Mapping[str, dict], candidate: Mapping[str, dict],
          templates: Mapping[str, str]) -> dict:
    """Per-mode S2 gates from per-case scores {case: {fac, matched_slots, total_slots}}."""

    ids = sorted(baseline)
    if set(ids) != set(replicate) or set(ids) != set(candidate):
        raise ValueError("arms must cover the same cases")
    losses = [c for c in ids if baseline[c]["fac"] and not candidate[c]["fac"]]
    gains = [c for c in ids if not baseline[c]["fac"] and candidate[c]["fac"]]
    net = defaultdict(int)
    for c in ids:
        net[templates[c]] += candidate[c]["fac"] - baseline[c]["fac"]
    n_templates = len(set(templates[c] for c in ids))
    losing = sorted(t for t, v in net.items() if v < 0)
    upper = clopper_pearson_upper(len(losing), n_templates)
    noise_final = [c for c in ids if baseline[c]["fac"] != replicate[c]["fac"]]
    slot_noise = sum(abs(baseline[c]["matched_slots"] - replicate[c]["matched_slots"]) for c in ids)
    k = max(MIN_SLOT_TOLERANCE, slot_noise)
    slot_delta = sum(candidate[c]["matched_slots"] - baseline[c]["matched_slots"] for c in ids)
    valid = len(noise_final) <= NOISE_LIMIT
    g = {"G1": not losses, "G2": upper <= BOUND, "G4": slot_delta >= -k}
    return {"cases": len(ids), "templates": n_templates,
            "G1_final_losses": losses, "final_gains": gains, "G1": g["G1"],
            "G2_losing_templates": losing, "G2_upper_95": upper, "G2": g["G2"],
            "G3_r4_self_discordant_finals": noise_final, "G3_valid": valid,
            "G4_slot_delta": slot_delta, "G4_tolerance": k, "G4_r4_self_slot_discordance": slot_noise, "G4": g["G4"],
            "replicate_vs_baseline_finals": sum(replicate[c]["fac"] for c in ids) - sum(baseline[c]["fac"] for c in ids),
            "status": "invalid" if not valid else ("pass" if all(g.values()) else "fail")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="MODE=scored run dir")
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline", default="R4a")
    parser.add_argument("--replicate", default="R4b")
    parser.add_argument("--candidate", default="P")
    parser.add_argument("--exclude-panel", default=None, help="also report gates on cases outside this panel")
    args = parser.parse_args(argv)
    manifest = common.data().manifest
    report = {"preregistration_sha256": common.sha256_file(common.ROOT / "experiments/safeguard_s2_20261022/preregistration.json"),
              "modes": {}}
    for item in args.run:
        mode, path = item.split("=", 1)
        scores = read_json(Path(path) / "scores.json")["recipes"]
        cases = {name: scores[name]["cases"] for name in (args.baseline, args.replicate, args.candidate)}
        templates = {c: manifest[c]["template_id"] for c in cases[args.baseline]}
        result = gates(cases[args.baseline], cases[args.replicate], cases[args.candidate], templates)
        if args.exclude_panel:
            excluded = set(read_json(Path(args.exclude_panel))["case_ids"])
            keep = [c for c in templates if c not in excluded]
            sub = {name: {c: v[c] for c in keep} for name, v in cases.items()}
            result["outside_excluded_panel"] = gates(sub[args.baseline], sub[args.replicate], sub[args.candidate],
                                                     {c: templates[c] for c in keep})
        result["official"] = {name: scores[name]["official"] for name in cases}
        result["micro"] = {name: {"correct_final": scores[name]["correct_final"],
                                  "slots": f"{scores[name]['matched_slots']}/{scores[name]['total_slots']}"} for name in cases}
        report["modes"][mode] = result
    statuses = [m["status"] for m in report["modes"].values()]
    report["s2_verdict"] = ("invalid" if "invalid" in statuses else "pass" if set(statuses) == {"pass"} else "fail")
    report["gate5"] = "pending: tuning-noex repeat not authorized in this run"
    report["meaning"] = ("A pass shows no observed final-answer loss against fresh R4 and a per-template loss-rate bound "
                         "below the frozen threshold. It is not evidence of improvement and does not authorize promotion.")
    save_json(Path(args.out), report)
    print(json.dumps({m: {k: v for k, v in r.items() if k not in ("official",)} for m, r in report["modes"].items()}
                     | {"s2_verdict": report["s2_verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
