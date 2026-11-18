"""Report the synthetic development pilot without presenting it as confirmation."""

import json
from collections import Counter
from fractions import Fraction

from . import common
from .improvement_campaign import PILOT, ROOT, save, verify_protected
from .formatter import build_row
from .prospective import decision, paired_family_interval
from .selection import final_first_complete
from .campaign_integrity import require_family_checks, require_evaluation_identity
from .config import load_config, system_prompt_path
from finreason_task1.scoring import score_case


def diagnostics(cases, items):
    counts = Counter()
    for case in cases:
        item = items[case["case_id"]]
        q, g = item["question"], item["gold"]
        samples = [s["texts"] for s in case["outcome"]["samples"]]
        scores = []
        for texts in samples:
            row, _ = build_row(q, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})
            scores.append(score_case(q, g, row))
        counts["cases"] += 1
        counts["oracle_final"] += any(s.fac for s in scores)
        counts["oracle_complete"] += any(s.fac and s.matched_slots == s.total_slots for s in scores)
        counts["final_selection_loss"] += int(any(s.fac for s in scores) and not case["fac"])
        counts["complete_selection_loss"] += int(any(s.fac and s.matched_slots == s.total_slots for s in scores)
                                                 and (not case["fac"] or case["matched_slots"] != case["total_slots"]))
        choice = final_first_complete(samples, ["final"] + [s["slot_id"] for s in q["trace_spec"]["slots"]])
        if choice["index"] is not None:
            alt = scores[choice["index"]]
            counts["whole_row_final_delta"] += alt.fac - case["fac"]
            counts["whole_row_slot_delta"] += alt.matched_slots - case["matched_slots"]
    return dict(counts)


def main():
    verify_protected()
    seal = json.loads((ROOT / "execution_seal.json").read_text())
    for path, expected in seal["hashes"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"comparison artifact changed: {path}")
    prereg = json.loads((ROOT / "preregistration.json").read_text())
    by_config = {c: {"counts": Counter(), "diagnostics": Counter(), "resources": Counter(),
                     "family_fac": [], "family_checkpoint": []}
                 for c in ("r4", "r5p")}
    families, missing, failed = [], [], []
    for a in prereg["assignments"]:
        directory = PILOT / f"family_{a['index']:02d}"
        if not (directory / "instances.jsonl").exists():
            missing.append(directory.name)
            continue
        check = directory / "blind_check.json"
        if not check.exists() or not json.loads(check.read_text())["all_agree"]:
            failed.append(directory.name)
            continue
        if not all((directory / f"evaluation_{c}.json").exists() for c in by_config):
            missing.append(directory.name)
            continue
        instances_hash = require_family_checks(directory)
        items = {i["question"]["case_id"]: i for i in common.read_jsonl(directory / "instances.jsonl")}
        family = {"family": directory.name, "domain": a["domain_id"], "difficulty": a["difficulty"]}
        for config in by_config:
            result = json.loads((directory / f"evaluation_{config}.json").read_text())
            recipe = load_config(f"configs/{config}.json")
            require_evaluation_identity(result, recipe["_sha256"],
                                        common.sha256_file(system_prompt_path(recipe, "novel")), instances_hash)
            ids = [c["case_id"] for c in result["cases"]]
            if len(ids) != len(items) or set(ids) != set(items):
                raise RuntimeError(f"{directory.name}/{config}: incomplete or duplicate case coverage")
            resources = by_config[config]["resources"]
            for case in result["cases"]:
                for sample in case["outcome"]["samples"]:
                    resources["samples"] += 1
                    resources["retries"] += max(0, len(sample["attempts"]) - 1)
                    for attempt in sample["attempts"]:
                        resources["calls"] += 1
                        resources["cached_calls"] += bool(attempt["cached"])
                        resources["cost_equivalent_usd"] += attempt.get("cost_equivalent_usd") or 0
                        for key, value in (attempt.get("usage") or {}).items():
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                resources[key] += value
            by_config[config]["counts"].update(result["scores"])
            by_config[config]["diagnostics"].update(diagnostics(result["cases"], items))
            fac = sum(c["fac"] for c in result["cases"]) / len(result["cases"])
            checkpoint = sum(float(Fraction(c["matched_slots"], c["total_slots"])) for c in result["cases"]) / len(result["cases"])
            by_config[config]["family_fac"].append(fac)
            by_config[config]["family_checkpoint"].append(checkpoint)
            family[config] = {"fac": fac, "checkpoint": checkpoint}
        families.append(family)
    result = {"panel": "development_pilot_not_confirmation", "families": families,
              "missing": missing, "unresolved_oracles": failed, "configs": {},
              "promotion": "not_eligible_pilot_only", "confirmation_opened": False}
    for config, values in by_config.items():
        result["configs"][config] = {"counts": dict(values["counts"]), "diagnostics": dict(values["diagnostics"]),
                                     "resources": dict(values["resources"]),
                                     "family_macro_fac": sum(values["family_fac"]) / len(families) if families else None,
                                     "family_macro_checkpoint": sum(values["family_checkpoint"]) / len(families) if families else None}
    if families:
        result["comparisons"] = {}
        for metric in ("fac", "checkpoint"):
            diffs = [f["r5p"][metric] - f["r4"][metric] for f in families]
            interval = paired_family_interval(diffs)
            result["comparisons"][metric] = {**interval, "prospective": decision(interval["delta"],
                interval["one_sided_95_lower"], all_differences_zero=not any(diffs), independent_units=len(families))}
    save(ROOT / "pilot_report.json", result)
    lines = ["# R5 synthetic pilot report", "", "Development evidence only. No confirmation or private Test accuracy.", "",
             f"Paired families: {len(families)}/24; missing: {missing}; unresolved oracles: {failed}.", "",
             "| Config | Family-macro FAC | Family-macro checkpoints |", "|---|---|---|"]
    for name, r in result["configs"].items():
        lines.append(f"| {name} | {r['family_macro_fac']} | {r['family_macro_checkpoint']} |")
    lines += ["", "```json", json.dumps(result.get("comparisons", {}), indent=2), "```", "",
              "Full candidate-generation/selection diagnostics and per-family results are in pilot_report.json.", ""]
    common.write_bytes_atomic(ROOT / "pilot_report.md", "\n".join(lines).encode())
    print(json.dumps({k: v for k, v in result.items() if k != "families"}, indent=2))


if __name__ == "__main__":
    main()
