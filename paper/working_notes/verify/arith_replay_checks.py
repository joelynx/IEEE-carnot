"""Read-only cross-checks of statements about the arithmetic replay (camera-ready revision, 18 November 2026).

1. How the two input runs overlap: the tuning-noex run reused the cached responses of the
   tuning-eval run, so the 580 shared questions carry the same programs in both.
2. Field changes on the 1,734 programs that are only in the tuning-noex run.
3. Set differences between the three rendering rules.

No model call, no execution.  Reads runs/ and experiments/arith_replay_20261118/results/.

  python -I paper/working_notes/verify/arith_replay_checks.py
"""
import json
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from carnot import common  # noqa: E402
from carnot.sandbox.executor import decode  # noqa: E402
from finreason_task1.scoring import value_matches  # noqa: E402

RESULTS = ROOT / "experiments" / "arith_replay_20261118" / "results"
RUNS = (("tuning-eval", "20261011T184257Z_r0_tuning-eval_S"), ("tuning-noex", "20261012T155533Z_r0_tuning-noex_S"))
RULES = ("repr", "15g", "rational")


def row_texts(row):
    texts = {s["slot_id"]: s["value"] for s in row["steps"]}
    if row["final_answer"] is not None:
        texts["final"] = row["final_answer"]["value"]
    return texts


d = common.data()
stored = {split: {c["case_id"]: c for c in common.read_jsonl(ROOT / "runs" / run / "cases.jsonl")} for split, run in RUNS}

# 1. overlap of the two runs
shared = sorted(set(stored["tuning-eval"]) & set(stored["tuning-noex"]))
same_program = sum(1 for c in shared if stored["tuning-eval"][c]["samples"][0]["attempts"][0]["code"]
                   == stored["tuning-noex"][c]["samples"][0]["attempts"][0]["code"])
same_key = sum(1 for c in shared if stored["tuning-eval"][c]["samples"][0]["attempts"][0]["cache_key"]
               == stored["tuning-noex"][c]["samples"][0]["attempts"][0]["cache_key"])
cached = sum(1 for c in shared if stored["tuning-noex"][c]["samples"][0]["attempts"][0]["cached"])
summary = json.loads((ROOT / "runs" / RUNS[1][1] / "summary.json").read_text(encoding="utf-8"))
print("1. shared questions:", len(shared), "| same program text:", same_program, "| same cache key:", same_key,
      "| served from the cache in the tuning-noex run:", cached,
      "| tuning-noex summary fresh/cached calls:", summary.get("fresh_calls"), summary.get("cached_calls"))
outside = sorted(set(stored["tuning-noex"]) - set(stored["tuning-eval"]))
print("   programs only in the tuning-noex run:", len(outside), "| distinct programs in all:", len(stored["tuning-noex"]))
fields = {split: sum(1 + len(d.questions[c]["trace_spec"]["slots"]) for c in stored[split]) for split, _ in RUNS}
print("   fields: tuning-eval", fields["tuning-eval"], "| tuning-noex", fields["tuning-noex"])

# 2 and 3. field changes
for split, run in RUNS:
    executed = {c["case_id"]: c for c in common.read_jsonl(RESULTS / split / "binary64_execution.jsonl")}
    lost = {}
    for rule in RULES:
        arm = {c["case_id"]: c for c in common.read_jsonl(RESULTS / split / f"binary64_{rule}" / "cases.jsonl")}
        lost[rule] = {}
        for case_id, case in stored[split].items():
            q, g = d.questions[case_id], d.gold[case_id]
            before, after = row_texts(case["row"]), row_texts(arm[case_id]["row"])
            targets = [("final", q["answer_spec"], g["final_value"])] + [
                (s["slot_id"], s["result_spec"], g["slot_values"][s["slot_id"]]) for s in q["trace_spec"]["slots"]]
            for name, spec, target in targets:
                if spec["type"] == "enum":
                    kind = "enum"
                elif spec["rounding"]["mode"] == "exact":
                    kind = "exact fraction" if "/" in target else "exact decimal"
                else:
                    kind = "half-up"
                kind = ("final " if name == "final" else "slot ") + kind
                was = name in before and value_matches(before[name], target, spec)
                now = name in after and value_matches(after[name], target, spec)
                lost[rule][(case_id, name)] = (kind, was, now, target, after.get(name),
                                               repr(decode(executed[case_id]["values"][name])))
    print("=" * 6, split)
    if split == "tuning-noex":
        only = set(outside)
        for rule in RULES:
            table = Counter()
            for (case_id, name), (kind, was, now, *_rest) in lost[rule].items():
                if case_id in only:
                    table[(kind, "matched exactly")] += was
                    table[(kind, "lost")] += was and not now
                    table[(kind, "wrong in both")] += (not was) and (not now)
                    table[(kind, "gained")] += (not was) and now
            wrong_finals = sum(v for (kind, what), v in table.items() if kind.startswith("final") and what in ("lost", "wrong in both"))
            missed_slots = sum(v for (kind, what), v in table.items() if kind.startswith("slot") and what in ("lost", "wrong in both"))
            print(f"2. outside the overlap ({len(only)} programs), rule {rule}: wrong finals {wrong_finals}, missed slots {missed_slots}")
            for kind in sorted({k for k, _ in table}):
                print("     ", kind, {what: table[(kind, what)] for what in ("matched exactly", "lost", "wrong in both", "gained")})
    dec = {rule: {k for k, v in lost[rule].items() if v[0] == "slot exact decimal" and v[1] and not v[2]} for rule in RULES}
    frac = {rule: {k for k, v in lost[rule].items() if v[0] == "slot exact fraction" and v[1] and not v[2]} for rule in RULES}
    print("3. decimal slots lost: repr", len(dec["repr"]), "15g", len(dec["15g"]), "rational", len(dec["rational"]))
    print("   lost by rational but not 15g:", len(dec["rational"] - dec["15g"]), "| lost by 15g but not rational:", len(dec["15g"] - dec["rational"]))
    print("   lost by repr but not 15g:", len(dec["repr"] - dec["15g"]), "| lost by 15g but not repr:", len(dec["15g"] - dec["repr"]))
    for key in sorted(dec["rational"] - dec["15g"])[:3]:
        print("     newly lost by rational (gold, written, double):", lost["rational"][key][3:])
    written = [k for k in dec["rational"] if "/" in (lost["rational"][k][4] or "")]
    print("   rational wrote a fraction for a lost decimal slot:", len(written), "| of these also lost under 15g:", len(set(written) & dec["15g"]))
    print("   fraction slots lost: repr", len(frac["repr"]), "15g", len(frac["15g"]), "rational", len(frac["rational"]))
    nearest = above = other = 0
    for key in sorted(frac["rational"]):
        _kind, _was, _now, target, text, value = lost["rational"][key]
        truth = Fraction(int(target.split("/")[0]), int(target.split("/")[1]))
        if float(truth) != float(value):
            nearest += 1
        elif truth.denominator > 10**6:
            above += 1
        else:
            other += 1
            fifteen = Decimal(format(float(value), ".15g"))
            print("     other case: gold", target, "| double", value, "| written", text,
                  "| 15-digit decimal has", len(fifteen.normalize().as_tuple().digits), "significant digits")
    print("   fraction slots lost under rational: computed double not the nearest", nearest,
          "| nearest, denominator above 10**6", above, "| other", other)
    ties = json.loads((RESULTS / "posthoc_analysis.json").read_text(encoding="utf-8"))[split]["rational"]
    finals = [f for f in ties["lost_finals"] if f["kind"] == "half_up"]
    inside = sum(1 for f in finals if f["case_id"] in stored["tuning-eval"])
    print("   half-up finals lost:", len(finals), "| exact ties:", sum(1 for f in finals if f["exact_value_is_a_rounding_tie"]),
          "| of them in the tuning-eval programs:", inside)
