"""Continuation analysis (no model calls): regression gates, pool diagnostics, usage and reports.

  python -m carnot.continuation_analysis_v1 regression --run S=<dir> --run H=<dir> \
      [--historical S=<dir> --historical H=<dir>] --out <report.json>
  python -m carnot.continuation_analysis_v1 families --run <dir> [--run <dir> ...] --out <report.json> \
      --seed carnot-continuation-v1-development

Gold is read only from runs whose predictions were persisted and scored first.  Gold-based
subsets (oracle coverage, correct-minority cases) are diagnostics and never feed a selector.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import common, compare, harness
from .formatter import build_row, parse_gold_value
from .improvement_validation_v1 import (RECIPE_ARMS, RECIPES, fields_of, load_gold, load_panel, load_questions,
                                        read_json, resolve, save_json)
from .prospective import decision, paired_family_interval
from finreason_task1.scoring import score_case

MARGIN = 0.001
REGRESSION_SEED = "carnot-continuation-v1-regression"
REPLICATES = 10_000
CANDIDATES = ("P", "D", "J", "JB", "X1", "X1C", "V")
TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


# ---------------------------------------------------------------- loading


class Run:
    def __init__(self, run_dir: str | Path):
        self.dir = Path(run_dir)
        self.meta = read_json(self.dir / "run.json")
        self.scores = read_json(self.dir / "scores.json")
        self.panel, panel_sha = load_panel(resolve(self.meta["panel_path"]))
        if panel_sha != self.meta["identity"]["panel_sha256"] or panel_sha != self.scores["panel_sha256"]:
            raise RuntimeError(f"{self.dir}: panel identity mismatch")
        self.ids = sorted(self.panel["case_ids"])
        self._cases: dict[str, dict] | None = None

    @property
    def cases(self) -> dict[str, dict]:
        if self._cases is None:
            self._cases = {c: read_json(self.dir / "cases" / f"{c}.json") for c in self.ids}
        return self._cases

    def recipe_cases(self, recipe: str) -> dict[str, dict]:
        return self.scores["recipes"][recipe]["cases"]


# ---------------------------------------------------------------- statistics


def clopper_pearson_upper(k: int, n: int, level: float = 0.95) -> float:
    if k >= n:
        return 1.0
    from scipy.stats import beta
    return float(beta.ppf(level, k + 1, n - k))


def one_sided_lower(draws: Sequence[float]) -> float:
    ordered = sorted(draws)
    return ordered[math.floor(0.05 * (len(ordered) - 1))]


def as_fractions(cases: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, Fraction]]:
    return {c: {"fac": Fraction(v["fac"]),
                "checkpoint": Fraction(v["matched_slots"], v["total_slots"]) if v["total_slots"] else Fraction(0)}
            for c, v in cases.items()}


def paired_regression(a_cases, b_cases, ids, weights, split, schemes=("template",)) -> dict:
    """Official weighted delta (b - a) with cluster bootstrap gates for FAC and checkpoint."""

    a, b = as_fractions(a_cases), as_fractions(b_cases)
    manifest = common.data().manifest
    out = {}
    exact = {k: compare.weighted(b, weights)[k] - compare.weighted(a, weights)[k] for k in compare.KEYS}
    diffs = {c: {k: float(weights[c][k] * (b[c][k] - a[c][k])) for k in compare.KEYS} for c in ids}
    template_net = defaultdict(lambda: Counter())
    for c in ids:
        for k in compare.KEYS:
            template_net[manifest[c]["template_id"]][k] += weights[c][k] * (b[c][k] - a[c][k])
    n_templates = len(template_net)
    for scheme in schemes:
        draws = compare.bootstrap(diffs, compare.clusters(ids, scheme), REPLICATES, REGRESSION_SEED)
        out[scheme] = {}
        for k in compare.KEYS:
            changed = [c for c in ids if a[c][k] != b[c][k]]
            lower = one_sided_lower(draws[k])
            losing = sum(1 for t in template_net.values() if t[k] < 0)
            gaining = sum(1 for t in template_net.values() if t[k] > 0)
            out[scheme][k] = {
                "a": float(compare.weighted(a, weights)[k]), "b": float(compare.weighted(b, weights)[k]),
                "delta": float(exact[k]), "delta_exact": str(exact[k]), "ci95": list(compare.percentile_ci(draws[k])),
                "one_sided_95_lower": lower, "changed_cases": len(changed),
                "gate": decision(float(exact[k]), lower, MARGIN, all_differences_zero=not changed,
                                 independent_units=n_templates),
                "sensitivity": {"templates": n_templates, "losing_templates": losing, "gaining_templates": gaining,
                                "discordant_templates": losing + gaining,
                                "losing_template_share_95_upper": clopper_pearson_upper(losing, n_templates),
                                "sparse_discordance": losing + gaining < 10}}
    out["fac_losses"] = sorted((c, manifest[c]["template_id"]) for c in ids if a[c]["fac"] > b[c]["fac"])
    out["fac_gains"] = sorted((c, manifest[c]["template_id"]) for c in ids if a[c]["fac"] < b[c]["fac"])
    out["checkpoint_losses"] = sorted(c for c in ids if a[c]["checkpoint"] > b[c]["checkpoint"])
    out["checkpoint_gains"] = sorted(c for c in ids if a[c]["checkpoint"] < b[c]["checkpoint"])
    return out


def verify_official(run: Run, weights) -> dict:
    checked = {}
    for recipe, entry in run.scores["recipes"].items():
        compare.check_against_official({"run_id": f"{run.dir.name}/{recipe}", "official": entry["official"],
                                        "cases": as_fractions(entry["cases"])}, weights)
        checked[recipe] = {"seen_fac": entry["official"]["seen_fac"], "seen_checkpoint": entry["official"]["seen_checkpoint"],
                           "micro_correct_final": entry["correct_final"],
                           "micro_slots": f"{entry['matched_slots']}/{entry['total_slots']}"}
    return checked


# ---------------------------------------------------------------- diagnostics


def score_texts(question, gold, texts) -> tuple[int, int, int]:
    row, _ = build_row(question, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})
    s = score_case(question, gold, row)
    return s.fac, s.matched_slots, s.total_slots


def pool_oracle(question, gold, samples) -> dict:
    scored = [score_texts(question, gold, s["texts"]) for s in samples]
    return {"final": any(f for f, _, _ in scored),
            "complete": any(f and m == t for f, m, t in scored),
            "correct_final_samples": sum(f for f, _, _ in scored), "samples": len(scored)}


def plurality_tie(votes: Mapping[str, int]) -> bool:
    return bool(votes) and sum(v == max(votes.values()) for v in votes.values()) > 1


def auto_class(question, gold, row) -> str:
    final = row.get("final_answer")
    if final is None:
        return "arithmetic_or_program_failure"
    spec = question["answer_spec"]
    if spec["type"] == "enum":
        return "wrong_value_or_category"
    try:
        predicted, truth = parse_gold_value(final["value"], spec), parse_gold_value(gold["final_value"], spec)
    except Exception:  # noqa: BLE001
        return "formatting"
    places = spec["rounding"].get("decimal_places")
    tol = Fraction(0) if places is None else Fraction(1, 10 ** places)
    if abs(predicted + truth) <= tol:
        return "sign"
    if abs(predicted * 100 - truth) <= tol or abs(predicted - truth * 100) <= tol:
        return "unit_or_scale"
    if abs(predicted - truth) <= tol:
        return "formatting"
    return "unclassified_value"


def usage(attempts: Sequence[Mapping[str, Any]]) -> Counter:
    total = Counter()
    for a in attempts:
        u = a.get("usage") or {}
        cost = float(a.get("cost_equivalent_usd") or 0)
        total["calls"] += 1
        total["cached_calls" if a.get("cached") else "fresh_calls"] += 1
        total["cost_equivalent_usd_end_to_end"] += cost
        if not a.get("cached"):
            total["cost_equivalent_usd_fresh"] += cost
        for k in TOKEN_KEYS:
            total[k] += int(u.get(k) or 0)
        total["thinking_tokens"] += int(((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0)
    return total


def arm_attempts(record: Mapping[str, Any]) -> dict[str, list]:
    arms = record.get("arms", {})
    out = {}
    for name in ("r4", "p", "d5"):
        if name in arms:
            out[name] = [a for s in arms[name]["samples"] for a in s["attempts"]]
    if "x1" in arms:
        out["x1"] = list(arms["x1"]["extra_sample"]["attempts"])
    if "v" in arms:
        out["v"] = [arms["v"]["call"]]
    if "seen" in record:
        out["seen"] = [a for s in record["seen"]["samples"] for a in s["attempts"]]
    return out


def diagnostics(run: Run, baseline: str = "R4") -> dict:
    """Pool coverage, selection losses, flips against the baseline, subsets, usage. Diagnostic only."""

    questions, _, _ = load_questions(run.panel)
    gold = load_gold(run.panel)
    recipes = [r for r in RECIPES if r in run.scores["recipes"]]
    per = {r: run.recipe_cases(r) for r in recipes}
    out = {"recipes": {}, "subsets": {}, "usage_by_arm": {}, "usage_by_recipe": {}, "errors": {}, "verifier": {},
           "retries_by_arm": Counter(), "samples_by_arm": Counter()}
    pools = defaultdict(Counter)
    arm_usage = defaultdict(Counter)
    subsets = defaultdict(list)
    verifier = Counter()
    recipe_usage = defaultdict(Counter)
    for c in run.ids:
        rec, q, g = run.cases[c], questions[c], gold[c]
        attempts = arm_attempts(rec)
        for arm, items in attempts.items():
            arm_usage[arm].update(usage(items))
        for arm in ("r4", "p", "d5"):
            if arm in rec.get("arms", {}):
                for s in rec["arms"][arm]["samples"]:
                    out["samples_by_arm"][arm] += 1
                    out["retries_by_arm"][arm] += len(s["attempts"]) - 1
        for recipe in recipes:
            need = ["seen"] if rec.get("route") == "seen" else list(RECIPE_ARMS[recipe])
            recipe_usage[recipe].update(usage([a for arm in need for a in attempts.get(arm, [])]))
        arms = rec.get("arms", {})
        oracle = {}
        for arm in ("r4", "p", "d5"):
            if arm in arms:
                oracle[arm] = pool_oracle(q, g, arms[arm]["samples"])
                pools[arm]["cases"] += 1
                pools[arm]["oracle_final"] += oracle[arm]["final"]
                pools[arm]["oracle_complete"] += oracle[arm]["complete"]
        if "x1" in arms:
            six = arms["d5"]["samples"] + [arms["x1"]["extra_sample"]]
            oracle["x1"] = pool_oracle(q, g, six)
        if "d5" in arms:
            trig = rec["trigger"]["triggered"]
            d5 = arms["d5"]
            j_correct = per["J"][c]["fac"] if "J" in per else None
            if trig:
                subsets["triggered"].append(c)
                finals = {s["texts"].get("final") for s in d5["samples"] if all(f in s["texts"] for f in fields_of(q))}
                if len(finals) == 1:
                    subsets["checkpoint_only_disagreement"].append(c)
                if j_correct:
                    subsets["triggered_with_correct_j"].append(c)
            if plurality_tie(d5["votes"].get("final", {})):
                subsets["final_tie"].append(c)
            if not oracle["d5"]["final"]:
                subsets["missing_correct_candidate"].append(c)
            elif not per["D"][c]["fac"]:
                subsets["correct_minority"].append(c)
        if "v" in arms:
            verdict = arms["v"]["verdict"]
            verifier["calls"] += 1
            verifier[f"reason:{verdict['reason']}"] += 1
            j, v = per["J"][c], per["V"][c]
            if verdict.get("selected_original_index") is not None and rec["selections"]["V"]["row"] != rec["selections"]["J"]["row"]:
                verifier["overrides"] += 1
                verifier["harmful_final_overrides"] += int(j["fac"] and not v["fac"])
                verifier["helpful_final_overrides"] += int(not j["fac"] and v["fac"])
                verifier["harmful_slot_overrides"] += int(v["matched_slots"] < j["matched_slots"])
            if "selected_anonymous_index" in verdict:
                verifier[f"position:{verdict['selected_anonymous_index']}"] += 1
        for recipe in recipes:
            sel = per[recipe][c]
            if not sel["fac"] or sel["matched_slots"] < sel["total_slots"]:
                row = rec["selections"][recipe]["row"]
                arm = "x1" if recipe in ("X1", "X1C") and "x1" in arms else RECIPE_ARMS[recipe][0]
                out["errors"].setdefault(recipe, []).append({
                    "case_id": c, "final_correct": sel["fac"], "missed_slots": sel["total_slots"] - sel["matched_slots"],
                    "auto_class": auto_class(q, g, row) if not sel["fac"] else "checkpoint_only",
                    "pool_oracle_final": oracle.get(arm, {}).get("final"),
                    "pool_oracle_complete": oracle.get(arm, {}).get("complete"),
                    "selection_loss": bool(oracle.get(arm, {}).get("final")) and not sel["fac"]})
    base = per.get(baseline)
    for recipe in recipes:
        sel = per[recipe]
        arm = RECIPE_ARMS[recipe][0]
        entry = {"correct_final": sum(v["fac"] for v in sel.values()),
                 "matched_slots": sum(v["matched_slots"] for v in sel.values()),
                 "total_slots": sum(v["total_slots"] for v in sel.values()),
                 "pool": arm, "final_selection_losses": sum(e["selection_loss"] for e in out["errors"].get(recipe, []))}
        if base is not None and recipe != baseline:
            entry["wrong_to_correct_vs_" + baseline] = sum(1 for c in run.ids if not base[c]["fac"] and sel[c]["fac"])
            entry["correct_to_wrong_vs_" + baseline] = sum(1 for c in run.ids if base[c]["fac"] and not sel[c]["fac"])
            entry["checkpoint_gain_cases"] = sum(1 for c in run.ids if sel[c]["matched_slots"] > base[c]["matched_slots"])
            entry["checkpoint_harm_cases"] = sum(1 for c in run.ids if sel[c]["matched_slots"] < base[c]["matched_slots"])
        entry["subsets"] = {name: {"cases": len(ids), "correct_final": sum(sel[c]["fac"] for c in ids)}
                            for name, ids in subsets.items()}
        out["recipes"][recipe] = entry
    out["pools"] = {k: dict(v) for k, v in pools.items()}
    out["subsets"] = {k: sorted(v) for k, v in subsets.items()}
    out["usage_by_arm"] = {k: dict(v) for k, v in arm_usage.items()}
    out["usage_by_recipe"] = {k: dict(v) for k, v in recipe_usage.items()}
    out["verifier"] = dict(verifier)
    out["retries_by_arm"] = dict(out["retries_by_arm"])
    out["samples_by_arm"] = dict(out["samples_by_arm"])
    return out


def request_keys(run: Run) -> dict[str, set]:
    keys = defaultdict(set)
    for rec in run.cases.values():
        for arm, items in arm_attempts(rec).items():
            keys[arm].update(a["cache_key"] for a in items)
    return keys


# ---------------------------------------------------------------- commands


def regression(args) -> int:
    runs = dict(item.split("=", 1) for item in args.run)
    historical = dict(item.split("=", 1) for item in (args.historical or []))
    report = {"margin": MARGIN, "replicates": REPLICATES, "seed": REGRESSION_SEED, "views": {}}
    loaded = {}
    for mode, path in sorted(runs.items()):
        run = Run(path)
        loaded[mode] = run
        split = run.panel["split"]
        weights = harness.cached_weights(split, run.ids)
        view = {"run_dir": run.dir.as_posix(), "split": split, "mode": mode, "official": verify_official(run, weights),
                "official_recomputation_verified": True, "comparisons_vs_R4c": {}, "historical": {}}
        schemes = ("template", "case") if mode == "S" else ("template",)
        base = run.recipe_cases("R4")
        for recipe in CANDIDATES:
            if recipe in run.scores["recipes"]:
                view["comparisons_vs_R4c"][recipe] = paired_regression(base, run.recipe_cases(recipe), run.ids,
                                                                       weights, split, schemes)
        if mode in historical:
            hist = Run(historical[mode])
            verify_official(hist, weights)
            hist_cases = hist.recipe_cases("R4")
            view["historical"]["R4c_vs_R4_historical"] = paired_regression(hist_cases, base, run.ids, weights, split)
            for recipe in CANDIDATES:
                if recipe in run.scores["recipes"]:
                    view["historical"][f"{recipe}_vs_R4_historical"] = paired_regression(
                        hist_cases, run.recipe_cases(recipe), run.ids, weights, split)
        view["diagnostics"] = diagnostics(run)
        report["views"][f"{split}_{mode}"] = view
    if {"S", "H"} <= set(loaded):
        s_keys, h_keys = request_keys(loaded["S"]), request_keys(loaded["H"])
        report["s_h_overlap"] = {arm: {"S": len(s_keys[arm]), "H": len(h_keys[arm]),
                                       "shared": len(s_keys[arm] & h_keys[arm])} for arm in sorted(s_keys)}
        manifest = read_json(resolve(loaded["S"].meta["panel_path"]))
        report["s_h_overlap"]["note"] = "S and H share identical requests except where H swaps an exemplar; not independent replications"
    save_json(Path(args.out), report)
    summary = {}
    for name, view in report["views"].items():
        summary[name] = {r: {"fac": c["template"]["fac"]["delta"], "fac_gate": c["template"]["fac"]["gate"]["status"],
                             "ckpt": c["template"]["checkpoint"]["delta"],
                             "ckpt_gate": c["template"]["checkpoint"]["gate"]["status"],
                             "fac_losses": len(c["fac_losses"]), "fac_gains": len(c["fac_gains"])}
                         for r, c in view["comparisons_vs_R4c"].items()}
        summary[name]["_official"] = view["official"]
    print(json.dumps(summary, indent=1))
    return 0


def family_info(panel: Mapping[str, Any], case_id: str) -> dict:
    entry = panel["families"][case_id]
    return {"family": entry} if isinstance(entry, str) else entry


def family_scores(run: Run, recipe: str) -> dict[str, dict[str, float]]:
    """Mean FAC and mean checkpoint share over each family's scored instances."""

    by_family = defaultdict(list)
    for c, v in run.recipe_cases(recipe).items():
        by_family[family_info(run.panel, c)["family"]].append(v)
    return {f: {"fac": sum(v["fac"] for v in vals) / len(vals),
                "checkpoint": sum(v["matched_slots"] / v["total_slots"] for v in vals) / len(vals), "n": len(vals)}
            for f, vals in by_family.items()}


def family_comparison(a: Mapping[str, Mapping], b: Mapping[str, Mapping], seed: str) -> dict:
    families = sorted(a)
    out = {}
    for metric in ("fac", "checkpoint"):
        diffs = [b[f][metric] - a[f][metric] for f in families]
        interval = paired_family_interval(diffs, seed=seed, replicates=REPLICATES)
        out[metric] = {**interval, "improved_families": sum(d > 0 for d in diffs),
                       "regressed_families": sum(d < 0 for d in diffs),
                       "positive_claim": interval["delta"] > 0 and interval["ci95"][0] > 0,
                       "noninferiority": decision(interval["delta"], interval["one_sided_95_lower"], MARGIN,
                                                  all_differences_zero=not any(diffs), independent_units=len(diffs)),
                       "leave_one_family_out": [min(sum(diffs) - d for d in diffs) / (len(diffs) - 1),
                                                max(sum(diffs) - d for d in diffs) / (len(diffs) - 1)] if len(diffs) > 1 else None}
    return out


def families(args) -> int:
    runs = [Run(p) for p in args.run]
    report = {"seed": args.seed, "replicates": REPLICATES, "panels": {}}
    for run in runs:
        info = {c: family_info(run.panel, c) for c in run.ids}
        recipes = [r for r in RECIPES if r in run.scores["recipes"]]
        fam = {r: family_scores(run, r) for r in recipes}
        meta = {}
        for c, entry in info.items():
            meta.setdefault(entry["family"], {k: entry.get(k) for k in ("mechanism_class", "domain_id", "difficulty",
                                                                         "pair_id", "group", "variant")})
        view = {"run_dir": run.dir.as_posix(), "partition": run.panel["partition"], "families": len(fam[recipes[0]]),
                "cases": len(run.ids), "macro": {}, "vs_R4": {}, "pairwise": {}, "breakdowns": {}}
        for r in recipes:
            view["macro"][r] = {m: sum(v[m] for v in fam[r].values()) / len(fam[r]) for m in ("fac", "checkpoint")}
            view["macro"][r]["correct_final"] = run.scores["recipes"][r]["correct_final"]
            view["macro"][r]["slots"] = f"{run.scores['recipes'][r]['matched_slots']}/{run.scores['recipes'][r]['total_slots']}"
        if "R4" in fam:
            for r in recipes:
                if r != "R4":
                    view["vs_R4"][r] = family_comparison(fam["R4"], fam[r], args.seed)
        if "V" in fam:
            for r in ("J", "JB", "X1", "X1C"):
                if r in fam:
                    view["pairwise"][f"V_vs_{r}"] = family_comparison(fam[r], fam["V"], args.seed)
        for key in ("mechanism_class", "domain_id", "difficulty", "group", "variant"):
            groups = defaultdict(list)
            for f, m in meta.items():
                if m.get(key) is not None:
                    groups[m[key]].append(f)
            if groups:
                view["breakdowns"][key] = {g: {r: {"fac": sum(fam[r][f]["fac"] for f in fs) / len(fs),
                                                   "checkpoint": sum(fam[r][f]["checkpoint"] for f in fs) / len(fs)}
                                               for r in recipes} | {"families": len(fs)} for g, fs in sorted(groups.items())}
        view["per_family"] = {f: {r: fam[r][f] for r in recipes} | {"meta": meta[f]} for f in sorted(meta)}
        view["diagnostics"] = diagnostics(run)
        # Wave assessment (preregistered): R4 final errors, pool disagreements, informative families.
        d5_disagree = set()
        for c in run.ids:
            rec = run.cases[c]
            if "d5" in rec.get("arms", {}):
                finals = {s["texts"].get("final") for s in rec["arms"]["d5"]["samples"] if "final" in s["texts"]}
                if len(finals) > 1:
                    d5_disagree.add(info[c]["family"])
        r4_error = {f for f, v in fam.get("R4", {}).items() if v["fac"] < 1}
        any_error = {f for r in recipes for f, v in fam[r].items() if v["fac"] < 1}
        informative = any_error | d5_disagree
        by_class = Counter(meta[f].get("mechanism_class") for f in informative)
        view["assessment"] = {
            "families_with_r4_final_error": sorted(r4_error), "families_with_any_recipe_final_error": sorted(any_error),
            "families_with_d5_final_disagreement": sorted(d5_disagree), "informative_families": sorted(informative),
            "informative_by_class": dict(by_class),
            "ceiling": len(r4_error) < 5 if run.panel["partition"] == "development" else None,
            "concentration": (max(by_class.values()) / len(informative) >= 0.75) if informative else None}
        report["panels"][run.panel["panel_id"]] = view
    save_json(Path(args.out), report)
    for name, view in report["panels"].items():
        print(name, json.dumps({"macro": view["macro"], "assessment": {k: (len(v) if isinstance(v, list) else v)
                                                                        for k, v in view["assessment"].items()}}, indent=1))
    return 0


SIMPLICITY = ("R4", "P", "D", "J", "JB", "X1", "X1C", "V")


def select_candidate(args) -> int:
    """The preregistered development selection rule (Package F)."""

    regression_report = read_json(Path(args.regression))
    runs = [Run(p) for p in args.development]
    if any(r.panel["partition"] != "development" for r in runs):
        raise SystemExit("selection reads development panels only")
    recipes = [r for r in RECIPES if all(r in run.scores["recipes"] for run in runs)]
    merged = {r: {} for r in recipes}
    cost, cases = Counter(), 0
    for run in runs:
        for r in recipes:
            overlap = set(merged[r]) & set(family_scores(run, r))
            if overlap:
                raise SystemExit(f"family appears in two development runs: {sorted(overlap)[:3]}")
            merged[r].update(family_scores(run, r))
        diag = diagnostics(run)
        for r in recipes:
            cost[r] += diag["usage_by_recipe"][r]["cost_equivalent_usd_end_to_end"]
        cases += len(run.ids)
    n_families = len(merged["R4"])
    macro = {r: {m: sum(v[m] for v in merged[r].values()) / n_families for m in ("fac", "checkpoint")} for r in recipes}
    for r in recipes:
        macro[r]["cost_per_case"] = cost[r] / cases
    eligibility = {}
    for r in recipes:
        if r == "R4":
            continue
        reasons = []
        for mode in ("S", "H"):
            view = regression_report["views"].get(f"tuning-eval_{mode}")
            if view is None or r not in view["comparisons_vs_R4c"]:
                reasons.append(f"tuning-eval {mode} missing")
                continue
            comp = view["comparisons_vs_R4c"][r]["template"]
            if comp["fac"]["delta"] < 0:
                reasons.append(f"tuning-eval {mode} FAC delta {comp['fac']['delta']:.6f} < 0")
            if comp["checkpoint"]["delta"] < -MARGIN:
                reasons.append(f"tuning-eval {mode} checkpoint delta {comp['checkpoint']['delta']:.6f} < -{MARGIN}")
        eligibility[r] = {"eligible": not reasons, "reasons": reasons}
    ranked = sorted((r for r in recipes if r != "R4" and eligibility[r]["eligible"]),
                    key=lambda r: (-macro[r]["fac"], -macro[r]["checkpoint"], macro[r]["cost_per_case"], SIMPLICITY.index(r)))
    top = ranked[0] if ranked else None
    nominee = top if top is not None and macro[top]["fac"] > macro["R4"]["fac"] else None
    decision_record = {"rule": "preregistration.json selection_rule", "development_families": n_families,
                       "development_cases": cases, "macro": macro, "eligibility": eligibility, "ranking": ranked,
                       "top_ranked": top, "nominee": nominee,
                       "outcome": f"nominate {nominee}" if nominee else "no candidate beats R4 on development FAC; retain R4"}
    if nominee:
        decision_record["nominee_vs_R4_development"] = family_comparison(merged["R4"], merged[nominee],
                                                                         "carnot-continuation-v1-development")
    save_json(Path(args.out), decision_record)
    print(json.dumps({k: v for k, v in decision_record.items() if k != "nominee_vs_R4_development"}, indent=1))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_reg = sub.add_parser("regression")
    p_reg.add_argument("--run", action="append", required=True, help="MODE=run_dir")
    p_reg.add_argument("--historical", action="append", help="MODE=run_dir of the cache-only historical R4 replay")
    p_reg.add_argument("--out", required=True)
    p_fam = sub.add_parser("families")
    p_fam.add_argument("--run", action="append", required=True)
    p_fam.add_argument("--seed", required=True)
    p_fam.add_argument("--out", required=True)
    p_sel = sub.add_parser("select")
    p_sel.add_argument("--regression", required=True, help="tuning-eval regression report.json")
    p_sel.add_argument("--development", action="append", required=True, help="scored development run directories")
    p_sel.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "regression":
        return regression(args)
    if args.command == "select":
        return select_candidate(args)
    return families(args)


if __name__ == "__main__":
    raise SystemExit(main())
