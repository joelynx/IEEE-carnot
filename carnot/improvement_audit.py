"""Read historical tuning artifacts only; produce a baseline audit and protected hashes."""

import json
from collections import Counter
from pathlib import Path

from . import common, splits
from .formatter import build_row
from .selection import final_first_complete
from finreason_task1.scoring import score_case

OUT = common.ROOT / "experiments/improvement_20261020"
RUNS = (
    "20261012T163028Z_r4_tuning-noex_S",
    "20261012T163526Z_r4_tuning-eval_S_forced-novel",
)


def audit_run(name, d, tuning):
    path = common.RUNS_DIR / name
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    assert summary["split"] in ("tuning-noex", "tuning-eval")
    counts, errors = Counter(), []
    for c in common.read_jsonl(path / "cases.jsonl"):
        cid = c["case_id"]
        assert cid in tuning, "audit must not inspect lockbox or test cases"
        q, g = d.questions[cid], d.gold[cid]
        fields = ["final"] + [s["slot_id"] for s in q["trace_spec"]["slots"]]
        scores, texts = [], [s["texts"] for s in c["samples"]]
        counts["cases"] += 1
        counts["wrong_final"] += 1 - c["fac"]
        counts["slot_misses"] += c["total_slots"] - c["matched_slots"]
        for sample in texts:
            row, dropped = build_row(q, sample.get("final"), {k: v for k, v in sample.items() if k != "final"})
            score = score_case(q, g, row)
            scores.append(score)
            counts["samples"] += 1
            counts["incomplete_samples"] += int(not all(f in sample for f in fields) or bool(dropped))
        has_final = any(s.fac for s in scores)
        has_complete = any(s.fac and s.matched_slots == s.total_slots for s in scores)
        counts["oracle_final_cases"] += has_final
        counts["oracle_all_fields_cases"] += has_complete
        counts["final_selection_losses"] += int(has_final and not c["fac"])
        counts["all_fields_selection_losses"] += int(has_complete and (not c["fac"] or c["matched_slots"] < c["total_slots"]))
        counts["unanimous_wrong_final"] += int(len({s.get("final") for s in texts}) == 1 and not has_final)
        final = c["row"]["final_answer"]
        selected = {"final": final["value"]} if final else {}
        selected.update({s["slot_id"]: s["value"] for s in c["row"]["steps"]})
        counts["mixed_rows"] += int(not any(t == selected for t in texts))
        selection = final_first_complete(texts, fields)
        if selection["index"] is not None:
            alternate = scores[selection["index"]]
            counts["whole_row_final_delta"] += alternate.fac - c["fac"]
            counts["whole_row_slot_delta"] += alternate.matched_slots - c["matched_slots"]
        else:
            counts["whole_row_fallbacks"] += 1
        if not c["fac"] or c["matched_slots"] < c["total_slots"]:
            errors.append({"case_id": cid, "template": d.template(cid), "final_correct": c["fac"],
                           "missed_slots": c["total_slots"] - c["matched_slots"],
                           "oracle_all_fields": has_complete})
    return {"run": name, "official_scores": summary["score"]["scores"], "counts": dict(counts), "errors": errors}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, tuning = common.data(), set(splits.load()["tuning"])
    reports = [audit_run(n, d, tuning) for n in RUNS]
    protected = ["configs/r4.json", "carnot/prompts/pot_system_v1.txt", "splits/splits_v1.json",
                 "exemplars/r0_exemplars.json",
                 "runs/20261012T165330Z_r4_test928_S/submission.zip",
                 "runs/20261012T165330Z_r4_test928_S/predictions.jsonl"]
    hashes = {p: common.sha256_file(common.ROOT / p) for p in protected}
    cache = common.CACHE_DIR / "llm_cache.sqlite3"
    record = {"release_manifests": common.verify_release(), "protected": hashes,
              "cache_initial_sha256": common.sha256_file(cache), "cache_initial_bytes": cache.stat().st_size,
              "runs": reports, "scope": "Historical tuning only; no fresh model calls or test-output analysis."}
    target = OUT / "baseline_audit.json"
    if target.exists():
        raise SystemExit("baseline audit already frozen; refusing to overwrite")
    common.write_bytes_atomic(target, (json.dumps(record, indent=2) + "\n").encode())
    lines = ["# R5 baseline audit", "", record["scope"], ""]
    for r in reports:
        lines += [f"## {r['run']}", "", "Official scores: " + json.dumps(r["official_scores"]), "",
                  "| Diagnostic | Count |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in r["counts"].items()]
        lines += ["", "Errors (tuning only):", "", "```json", json.dumps(r["errors"], indent=2), "```", ""]
    lines += ["No Test correctness is known. Diagnostic oracle scores use public tuning gold only.",
              "Protected hashes and cache snapshot identity are in baseline_audit.json.", ""]
    common.write_bytes_atomic(OUT / "baseline_audit.md", "\n".join(lines).encode())
    print(json.dumps([{"run": r["run"], "counts": r["counts"]} for r in reports], indent=2))


if __name__ == "__main__":
    main()
