"""Effort and sampling decomposition from stored run records (camera-ready revision, 18 November 2026).

Read-only: no model call, no sandbox execution, nothing written outside stdout.
For every tuning-eval run it rebuilds, per sample index k, the prediction rows that the
pipeline would have submitted with that single sample (the rendered strings stored in
runs/<run>/cases.jsonl under samples[k].texts, gated by the same build_row), and scores
them with the organisers' score_submission through carnot.harness.  The stored vote row
is rescored as a check against the run's own summary.

  python -I paper/working_notes/verify/component_analysis.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from carnot import common, harness  # noqa: E402
from carnot.formatter import build_row  # noqa: E402

RUNS = [
    ("R0  (Sonnet low, N=1)", "20261011T184257Z_r0_tuning-eval_S"),
    ("R0  (Sonnet low, N=1)", "20261011T190219Z_r0_tuning-eval_H"),
    ("R1f (Sonnet medium, N=5)", "20261012T051314Z_r1_tuning-eval_S_forced-novel"),
    ("R1f (Sonnet medium, N=5)", "20261012T055322Z_r1_tuning-eval_H_forced-novel"),
    ("R2f (Opus medium, N=5)", "20261012T065939Z_r2_tuning-eval_S_forced-novel"),
    ("R2f (Opus medium, N=5)", "20261012T074942Z_r2_tuning-eval_H_forced-novel"),
    ("R3f (Sonnet medium, N=5, hint v2)", "20261012T132507Z_r3_tuning-eval_S_forced-novel"),
    ("R3f (Sonnet medium, N=5, hint v2)", "20261012T133010Z_r3_tuning-eval_H_forced-novel"),
    ("R4f (Sonnet medium, N=5, hint v2, echo notes)", "20261012T163526Z_r4_tuning-eval_S_forced-novel"),
    ("R4f (Sonnet medium, N=5, hint v2, echo notes)", "20261012T163913Z_r4_tuning-eval_H_forced-novel"),
]


def jl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def summarise(rows, case_ids):
    scored = harness.score(rows, case_ids)
    s = scored["report"]["scores"]
    wrong_finals = sum(1 for c in scored["cases"] if c["fac"] != 1)
    missed = sum(c["total_slots"] - c["matched_slots"] for c in scored["cases"])
    total = sum(c["total_slots"] for c in scored["cases"])
    return float(s["seen_fac"]), float(s["seen_checkpoint"]), wrong_finals, missed, total, scored["cases"]


def main():
    d = common.data()
    for label, run in RUNS:
        run_dir = ROOT / "runs" / run
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        cases = jl(run_dir / "cases.jsonl")
        case_ids = [c["case_id"] for c in cases]
        n = len(cases[0]["samples"])
        assert all(len(c["samples"]) == n for c in cases)
        fac, ckpt, wf, ms, total, _ = summarise([c["row"] for c in cases], case_ids)
        official = summary["score"]["scores"]
        assert abs(fac - float(official["seen_fac"])) < 1e-12 and abs(ckpt - float(official["seen_checkpoint"])) < 1e-12
        print(f"\n{label}  [{summary['mode']}-mode]  {run}  questions={len(cases)} slots={total}")
        print(f"  stored row (vote of {n}): FAC {fac:.6f}  checkpoint {ckpt:.6f}  wrong finals {wf}  missed slots {ms}")
        if n == 1:
            continue
        per_sample = []
        for k in range(n):
            rows, dropped = [], 0
            for c in cases:
                q = d.questions[c["case_id"]]
                texts = c["samples"][k]["texts"]
                row, drop = build_row(q, texts.get("final"),
                                      {s["slot_id"]: texts.get(s["slot_id"]) for s in q["trace_spec"]["slots"]})
                dropped += len(drop)
                rows.append(row)
            f, cp, w, m, _, _ = summarise(rows, case_ids)
            missing = sum(1 for c in cases for name in ["final"] + [s["slot_id"] for s in d.questions[c["case_id"]]["trace_spec"]["slots"]]
                          if name not in c["samples"][k]["texts"])
            per_sample.append((f, cp, w, m))
            print(f"  sample {k} alone:        FAC {f:.6f}  checkpoint {cp:.6f}  wrong finals {w}  missed slots {m}"
                  f"  (unrendered fields {missing}, dropped by gate {dropped})")
        print(f"  single-sample range: wrong finals {min(p[2] for p in per_sample)}-{max(p[2] for p in per_sample)},"
              f" missed slots {min(p[3] for p in per_sample)}-{max(p[3] for p in per_sample)},"
              f" mean missed slots {sum(p[3] for p in per_sample) / n:.1f}")
        # agreement among the samples
        fields = disagree_fields = disagree_questions = vote_differs_from_s0 = disagree_finals = 0
        for c in cases:
            disagree_finals += len({s["texts"].get("final") for s in c["samples"]}) > 1
            q = d.questions[c["case_id"]]
            names = ["final"] + [s["slot_id"] for s in q["trace_spec"]["slots"]]
            voted = {"final": (c["row"]["final_answer"] or {}).get("value")}
            voted.update({s["slot_id"]: s["value"] for s in c["row"]["steps"]})
            any_dis = False
            for name in names:
                fields += 1
                values = {s["texts"].get(name) for s in c["samples"]}
                if len(values) > 1:
                    disagree_fields += 1
                    any_dis = True
                if voted.get(name) != c["samples"][0]["texts"].get(name):
                    vote_differs_from_s0 += 1
            disagree_questions += any_dis
        print(f"  fields {fields}: samples not unanimous on {disagree_fields} fields in {disagree_questions} questions"
              f" ({disagree_finals} of them on the final); vote differs from sample 0 on {vote_differs_from_s0} fields")


if __name__ == "__main__":
    main()
