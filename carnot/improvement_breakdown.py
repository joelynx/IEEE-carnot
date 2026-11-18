"""Descriptive pilot breakdowns; does not alter the frozen comparison or its gates."""

import json
from collections import Counter, defaultdict

from . import common
from .formatter import build_row
from .improvement_campaign import ROOT, PILOT, save, verify_protected
from finreason_task1.scoring import score_case


def main():
    verify_protected()
    report = json.loads((ROOT / "pilot_report.json").read_text())
    if report["missing"] or report["unresolved_oracles"] or len(report["families"]) != 24:
        raise SystemExit("complete validated pilot report required")
    groups = defaultdict(list)
    for family in report["families"]:
        groups["domain=" + family["domain"]].append(family)
        groups["difficulty=" + family["difficulty"]].append(family)
    breakdowns = {}
    for key, families in sorted(groups.items()):
        values = {c: {metric: sum(f[c][metric] for f in families) / len(families)
                      for metric in ("fac", "checkpoint")} for c in ("r4", "r5p")}
        breakdowns[key] = {"families": len(families), **values}
    sampling = {c: Counter() for c in ("r4", "r5p")}
    usage = {c: {"fresh": Counter(), "cached": Counter()} for c in sampling}
    changes = []
    for family in report["families"]:
        directory = PILOT / family["family"]
        items = {x["question"]["case_id"]: x for x in common.read_jsonl(directory / "instances.jsonl")}
        paired = {}
        for config in sampling:
            record = json.loads((directory / f"evaluation_{config}.json").read_text())
            paired[config] = {c["case_id"]: c for c in record["cases"]}
            for case in record["cases"]:
                item = items[case["case_id"]]
                counts = sampling[config]
                any_bad_final = any_bad_slot = False
                for sample in case["outcome"]["samples"]:
                    texts = sample["texts"]
                    row, _ = build_row(item["question"], texts.get("final"),
                                       {k: v for k, v in texts.items() if k != "final"})
                    score = score_case(item["question"], item["gold"], row)
                    bad_final, bad_slot = not score.fac, score.matched_slots != score.total_slots
                    counts["samples"] += 1
                    counts["samples_with_wrong_final"] += bad_final
                    counts["samples_with_slot_error"] += bad_slot
                    any_bad_final |= bad_final
                    any_bad_slot |= bad_slot
                    counts["retries"] += len(sample["attempts"]) - 1
                    for attempt in sample["attempts"]:
                        counter = usage[config]["cached" if attempt["cached"] else "fresh"]
                        counter["calls"] += 1
                        counter["cost_equivalent_usd"] += attempt.get("cost_equivalent_usd") or 0
                        tokens = attempt.get("usage") or {}
                        for name in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                            counter[name] += tokens.get(name) or 0
                        counter["thinking_tokens"] += (tokens.get("output_tokens_details") or {}).get("thinking_tokens") or 0
                counts["cases_with_sample_final_error_but_correct_vote"] += bool(any_bad_final and case["fac"])
                counts["cases_with_sample_slot_error_but_correct_vote"] += bool(
                    any_bad_slot and case["matched_slots"] == case["total_slots"])
        for cid in items:
            a, b = paired["r4"][cid], paired["r5p"][cid]
            if a["fac"] != b["fac"] or a["matched_slots"] != b["matched_slots"]:
                changes.append({"family": family["family"], "case_id": cid,
                                "final_delta": b["fac"] - a["fac"],
                                "matched_slot_delta": b["matched_slots"] - a["matched_slots"]})
    result = {"panel": "development_pilot_not_confirmation", "breakdowns": breakdowns,
              "sampling": sampling, "usage": usage, "selected_score_changes": changes,
              "source_report_sha256": common.sha256_file(ROOT / "pilot_report.json"),
              "report_code_sha256": common.sha256_file(common.ROOT / "carnot/improvement_breakdown.py")}
    save(ROOT / "pilot_breakdown.json", result)
    lines = ["# Pilot domain and difficulty breakdown", "",
             "Family-macro scores on synthetic development data; these are not official hidden scores.", "",
             "| Group | Families | R4 FAC | R5-P FAC | R4 checkpoints | R5-P checkpoints |",
             "|---|---:|---:|---:|---:|---:|"]
    for key, value in breakdowns.items():
        lines.append(f"| {key} | {value['families']} | {value['r4']['fac']:.6f} | {value['r5p']['fac']:.6f} | "
                     f"{value['r4']['checkpoint']:.6f} | {value['r5p']['checkpoint']:.6f} |")
    lines += ["", "Sample-level errors, fresh/cached usage and every selected-score change are recorded in",
              "`pilot_breakdown.json`. Costs are list-price equivalents, not subscription invoices.", ""]
    common.write_bytes_atomic(ROOT / "pilot_breakdown.md", "\n".join(lines).encode())
    print(json.dumps({"sampling": sampling, "usage": usage, "selected_score_changes": changes}, indent=2))


if __name__ == "__main__":
    main()
