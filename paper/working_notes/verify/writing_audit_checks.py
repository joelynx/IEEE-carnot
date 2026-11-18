"""Checks behind three sentences reworded in the third camera-ready build (paper/VERIFICATION.md, section 10).

  python -I paper/working_notes/verify/writing_audit_checks.py

Read-only.  It compares stored prediction files field by field and reads the log of the
worked-example selection.  No model call, no sandbox.

  1. R4 forced against R3 forced on tuning-eval, S- and H-mode (Section V-C).
  2. The run without examples against the first R0 run on tuning-eval (Section VI).
  3. The log of the worked-example selection (Section III-B).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def rows(path: Path) -> dict:
    out = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            out[row["case_id"]] = row
    return out


def fields(row: dict) -> dict:
    """One prediction row as {field name: submitted string}."""
    out = {"final": json.dumps(row["final_answer"], sort_keys=True)}
    for step in row["steps"]:
        out[step["slot_id"]] = json.dumps(step.get("value", step.get("result")), sort_keys=True)
    return out


def diff(a_dir: str, b_dir: str, label: str) -> list:
    a, b = rows(ROOT / a_dir / "predictions.jsonl"), rows(ROOT / b_dir / "predictions.jsonl")
    if set(a) != set(b):
        raise SystemExit(f"{label}: the two runs cover different cases")
    total = 0
    changed = []
    for case_id in sorted(a):
        fa, fb = fields(a[case_id]), fields(b[case_id])
        keys = sorted(set(fa) | set(fb))
        total += len(keys)
        differing = [k for k in keys if fa.get(k) != fb.get(k)]
        if differing:
            changed.append((case_id, differing))
    n_fields = sum(len(d) for _, d in changed)
    n_finals = sum("final" in d for _, d in changed)
    print(f"   {label}: {len(a)} rows, {total} fields; {len(changed)} rows and {n_fields} fields differ, "
          f"{n_finals} of them finals")
    return changed


print("1. R4 forced against R3 forced on tuning-eval")
diff("runs/20261012T132507Z_r3_tuning-eval_S_forced-novel",
     "runs/20261012T163526Z_r4_tuning-eval_S_forced-novel", "S-mode")
diff("runs/20261012T133010Z_r3_tuning-eval_H_forced-novel",
     "runs/20261012T163913Z_r4_tuning-eval_H_forced-novel", "H-mode")

print("2. Run without examples against the first R0 run on tuning-eval")
for case_id, differing in diff("runs/20261011T184257Z_r0_tuning-eval_S",
                               "experiments/ablation_zeroshot_20261118/run", "S-mode"):
    print("     ", case_id, ", ".join(differing))

print("3. Selection of the worked examples")
with open(ROOT / "exemplars/r0_exemplars.json", encoding="utf-8") as handle:
    exemplars = json.load(handle)
log = exemplars["bootstrap_log"]
print(f"   candidates tried {len(log)}, verified {sum(1 for e in log if e['verified'])}, "
      f"kept {len(exemplars['exemplars'])}, attempts per candidate {sorted({e['attempts'] for e in log})}")
