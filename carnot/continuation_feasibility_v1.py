"""Statistical feasibility of the continuation gates under the frozen estimators (no model calls).

  python -m carnot.continuation_feasibility_v1      # writes statistical_feasibility.json

All inputs are hypothetical difference patterns pushed through the exact estimators the
continuation uses: carnot.prospective for family panels and carnot.compare's cluster
bootstrap with the official tuning-eval weights for regression panels.
"""

from __future__ import annotations

import json
import math

from . import common, compare, harness, splits
from .continuation_state_v1 import ROOT
from .prospective import decision, paired_family_interval, zero_event_upper

MARGIN = 0.001
CONFIRMATION_SEED = "carnot-continuation-v1-confirmation"
REGRESSION_SEED = "carnot-continuation-v1-regression"
REPLICATES = 10_000


def one_sided_lower(draws: list[float]) -> float:
    ordered = sorted(draws)
    return ordered[math.floor(0.05 * (len(ordered) - 1))]


def family_scenarios(n_families: int = 48) -> list[dict]:
    rows = []
    for size in (0.25, 0.5):
        for improved in (1, 2, 3, 4, 5, 6, 8):
            for regressed in (0, 1, 2):
                diffs = [size] * improved + [-size] * regressed + [0.0] * (n_families - improved - regressed)
                r = paired_family_interval(diffs, seed=CONFIRMATION_SEED, replicates=REPLICATES)
                rows.append({"family_delta": size, "improved": improved, "regressed": regressed,
                             "delta": r["delta"], "ci95": r["ci95"],
                             "positive_claim": r["delta"] > 0 and r["ci95"][0] > 0})
    return rows


def split_ids(split: str) -> list[str]:
    """tuning-noex is derived exactly as carnot.run derives it: tuning minus R4's exemplars."""

    if split != "tuning-noex":
        return sorted(splits.load()[split])
    exemplar_ids = {e["case_id"] for e in json.loads((common.ROOT / "exemplars/r0_exemplars.json")
                                                     .read_text(encoding="utf-8"))["exemplars"]}
    return sorted(c for c in splits.load()["tuning"] if c not in exemplar_ids)


def regression_scenarios(split: str = "tuning-eval") -> dict:
    ids = split_ids(split)
    weights = harness.cached_weights(split, ids)
    strata = compare.clusters(ids, "template")
    first_cases = [unit[0] for units in strata for unit in units]  # one case from each template
    rows = []
    for losses, gains in ((0, 0), (0, 1), (1, 0), (1, 1), (1, 3), (2, 2), (3, 0)):
        diffs = {c: {"fac": 0.0, "checkpoint": 0.0} for c in ids}
        for c in first_cases[:losses]:
            diffs[c]["fac"] = -float(weights[c]["fac"])
        for c in first_cases[losses:losses + gains]:
            diffs[c]["fac"] = float(weights[c]["fac"])
        lower = one_sided_lower(compare.bootstrap(diffs, strata, REPLICATES, REGRESSION_SEED)["fac"])
        delta = sum(d["fac"] for d in diffs.values())
        rows.append({"case_losses": losses, "case_gains": gains, "delta": delta, "one_sided_95_lower": lower,
                     "status": decision(delta, lower, MARGIN, all_differences_zero=not (losses or gains),
                                        independent_units=len(first_cases))["status"]})
    fac = [float(w["fac"]) for w in weights.values()]
    return {"split": split, "cases": len(ids), "template_units": len(first_cases),
            "case_fac_weight_min": min(fac), "case_fac_weight_max": max(fac), "scenarios": rows}


def main() -> int:
    result = {
        "margin": MARGIN, "replicates": REPLICATES,
        "zero_event_95_upper": {str(n): zero_event_upper(n) for n in (24, 48, 96, 290)},
        "independent_units_for_zero_event_bound_below_margin": math.ceil(math.log(0.05) / math.log(1 - MARGIN)),
        "confirmation_48_families": family_scenarios(48),
        "regression_tuning_eval": regression_scenarios("tuning-eval"),
        "regression_tuning_noex": regression_scenarios("tuning-noex"),
        "inputs": "hypothetical difference patterns; no model outputs",
    }
    path = ROOT / "statistical_feasibility.json"
    common.write_bytes_atomic(path, (json.dumps(result, indent=1) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in result.items() if k not in ("confirmation_48_families",)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
