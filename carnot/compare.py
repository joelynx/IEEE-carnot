"""Paired comparison of two runs on the same gold split (PLAN.md §5.6, §4a(c)).

  python -m carnot.compare --a runs/<A> --b runs/<B> [--sigma-runs runs/<r1> runs/<r2> runs/<r3>]

Delta = official score of B minus A for seen FAC and seen checkpoint, recomputed
from per-case results and per-case weights probed from the toolkit scorer
(harness.cached_weights); the recomputation is checked against both runs'
official reports before anything is reported.  The 95% CI comes from a paired
bootstrap that draws the same resample indices for both systems and both keys:

  S-mode: cases resampled within each template;
  H-mode: templates resampled within each topic (cluster bootstrap).

sigma_run is the sample standard deviation (n-1) of the official aggregates of
replicate runs of one configuration (--sigma-runs).  Output is aggregates only,
so it is safe on lockbox runs (§5.3).  Every comparison is appended to
experiments/comparisons.jsonl.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import common, harness

KEYS = ("fac", "checkpoint")
OFFICIAL = {"fac": "seen_fac", "checkpoint": "seen_checkpoint"}
SEED = "carnot-compare-v1"
LOG = common.EXPERIMENTS_DIR / "comparisons.jsonl"


def load_run(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if not summary.get("complete") or not summary.get("score"):
        raise SystemExit(f"{run_dir.name}: not a complete, scored run")
    cases = {}
    for row in common.read_jsonl(run_dir / "cases.jsonl"):
        total = row["total_slots"]
        cases[row["case_id"]] = {
            "fac": Fraction(row["fac"]),
            "checkpoint": Fraction(row["matched_slots"], total) if total else Fraction(0),
        }
    return {"run_id": summary["run_id"], "split": summary["split"], "mode": summary["mode"],
            "official": summary["score"]["scores"], "cases": cases}


def weighted(cases: Mapping[str, Mapping[str, Fraction]], weights: Mapping[str, Mapping[str, Fraction]]) -> dict[str, Fraction]:
    return {key: sum((weights[c][key] * cases[c][key] for c in cases), Fraction(0)) for key in KEYS}


def check_against_official(run: Mapping[str, Any], weights) -> None:
    recomputed = weighted(run["cases"], weights)
    for key in KEYS:
        official = run["official"][OFFICIAL[key]]
        if official is None or abs(float(recomputed[key]) - float(official)) > 1e-12:
            raise SystemExit(f"{run['run_id']}: recomputed {key} {float(recomputed[key])} != official {official}")


def clusters(case_ids: Sequence[str], scheme: str) -> list[list[list[str]]]:
    """Strata -> resampling units -> case_ids."""

    manifest = common.data().manifest
    if scheme == "case":  # S-mode: cases within templates
        by_template: dict[str, list[str]] = defaultdict(list)
        for c in case_ids:
            by_template[manifest[c]["template_id"]].append(c)
        return [[[c] for c in sorted(members)] for _, members in sorted(by_template.items())]
    by_topic: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for c in case_ids:  # H-mode: templates within topics
        row = manifest[c]
        by_topic[(row["domain_id"], row["topic_id"])][row["template_id"]].append(c)
    return [[sorted(members) for _, members in sorted(templates.items())]
            for _, templates in sorted(by_topic.items())]


def bootstrap(diffs: Mapping[str, Mapping[str, float]], strata, replicates: int, seed: str) -> dict[str, list[float]]:
    unit_values = [[{k: sum(diffs[c][k] for c in unit) for k in KEYS} for unit in units] for units in strata]
    rng = random.Random(seed)
    draws: dict[str, list[float]] = {k: [] for k in KEYS}
    for _ in range(replicates):
        totals = dict.fromkeys(KEYS, 0.0)
        for units in unit_values:
            n = len(units)
            for _ in range(n):
                unit = units[rng.randrange(n)]
                for k in KEYS:
                    totals[k] += unit[k]
        for k in KEYS:
            draws[k].append(totals[k])
    return draws


def percentile_ci(values: Sequence[float], level: float = 0.95) -> tuple[float, float]:
    ordered = sorted(values)
    tail = (1 - level) / 2
    low = ordered[math.floor(tail * (len(ordered) - 1))]
    high = ordered[math.ceil((1 - tail) * (len(ordered) - 1))]
    return low, high


def sigma_run(run_dirs: Sequence[str]) -> dict[str, float] | None:
    if not run_dirs:
        return None
    runs = [load_run(d) for d in run_dirs]
    if len(runs) < 2 or len({(r["split"], r["mode"]) for r in runs}) != 1:
        raise SystemExit("--sigma-runs needs >= 2 replicate runs on one split and mode")
    return {k: statistics.stdev(float(r["official"][OFFICIAL[k]]) for r in runs) for k in KEYS}


def verdicts(delta: float, low: float, high: float, sigma: float | None) -> dict[str, Any]:
    if sigma is None:
        return {"improved": None, "tied": None, "worse": None, "non_inferior": None}
    margin = 2 * sigma
    return {
        "improved": low > 0 and delta > margin,                    # §5.6
        "tied": low <= 0 <= high and abs(delta) <= margin,         # §5.6
        "worse": high < 0 and delta < -margin,
        "non_inferior": delta >= -margin and high >= 0,            # §4a(c), proposed
    }


def compare(a_dir: str, b_dir: str, sigma_dirs: Sequence[str] = (), replicates: int = 10_000,
            scheme: str | None = None, seed: str = SEED) -> dict[str, Any]:
    a, b = load_run(a_dir), load_run(b_dir)
    if a["split"] != b["split"] or set(a["cases"]) != set(b["cases"]):
        raise SystemExit("runs must cover the same split and case set")
    scheme = scheme or {"S": "case", "H": "template"}[b["mode"]]
    ids = sorted(a["cases"])
    weights = harness.cached_weights(a["split"], ids)
    check_against_official(a, weights)
    check_against_official(b, weights)
    exact = {k: weighted(b["cases"], weights)[k] - weighted(a["cases"], weights)[k] for k in KEYS}
    diffs = {c: {k: float(weights[c][k] * (b["cases"][c][k] - a["cases"][c][k])) for k in KEYS} for c in ids}
    draws = bootstrap(diffs, clusters(ids, scheme), replicates, seed)
    sigma = sigma_run(sigma_dirs)
    result: dict[str, Any] = {
        "a": a["run_id"], "b": b["run_id"], "split": a["split"], "modes": [a["mode"], b["mode"]],
        "scheme": scheme, "replicates": replicates, "seed": seed, "sigma_runs": list(map(str, sigma_dirs)),
        "changed_cases": {k: sum(1 for c in ids if a["cases"][c][k] != b["cases"][c][k]) for k in KEYS},
    }
    for k in KEYS:
        low, high = percentile_ci(draws[k])
        s = None if sigma is None else sigma[k]
        result[k] = {"a": float(weighted(a["cases"], weights)[k]), "b": float(weighted(b["cases"], weights)[k]),
                     "delta": float(exact[k]), "delta_exact": str(exact[k]), "ci95": [low, high],
                     "sigma_run": s, **verdicts(float(exact[k]), low, high, s)}
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", required=True, help="baseline run directory")
    parser.add_argument("--b", required=True, help="candidate run directory")
    parser.add_argument("--sigma-runs", nargs="*", default=[], help="replicate runs of one configuration")
    parser.add_argument("--replicates", type=int, default=10_000)
    parser.add_argument("--scheme", choices=["case", "template"], default=None, help="default: from the run's mode")
    parser.add_argument("--no-log", action="store_true")
    args = parser.parse_args(argv)
    result = compare(args.a, args.b, args.sigma_runs, args.replicates, args.scheme)
    if not args.no_log:
        common.append_jsonl(LOG, {**result, "recorded_at": datetime.now(timezone.utc).isoformat()})
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
