"""Descriptive analysis of the arithmetic replay, written AFTER its results were seen.

Not part of the pre-registration: it explains the field changes that run_arith_replay.py
counted.  It reads the stored results, re-executes in the frozen exact sandbox only the
programs whose final answer was lost in binary64 (to see the unrounded exact value), and
writes results/posthoc_analysis.json.  No model call, no binary64 execution.

  python -I experiments/arith_replay_20261118/analyse_replay.py
"""

import json
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from carnot import common  # noqa: E402
from carnot.sandbox.executor import Sandbox, decode  # noqa: E402
from finreason_task1.scoring import value_matches  # noqa: E402

RESULTS = HERE / "results"
RUNS = (("tuning-eval", "20261011T184257Z_r0_tuning-eval_S"), ("tuning-noex", "20261012T155533Z_r0_tuning-noex_S"))
RENDERINGS = ("repr", "15g", "rational")


def row_texts(row):
    texts = {step["slot_id"]: step["value"] for step in row["steps"]}
    if row["final_answer"] is not None:
        texts["final"] = row["final_answer"]["value"]
    return texts


def significant_digits(text: str) -> int:
    return len(Decimal(text).normalize().as_tuple().digits)


def as_fraction(text: str) -> Fraction:
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(Decimal(text))


def main() -> int:
    d = common.data()
    report = {}
    box = Sandbox("wsl", timeout=5.0)
    try:
        for split, run in RUNS:
            stored = {c["case_id"]: c for c in common.read_jsonl(ROOT / "runs" / run / "cases.jsonl")}
            executed = {c["case_id"]: c for c in common.read_jsonl(RESULTS / split / "binary64_execution.jsonl")}
            entry = report[split] = {}
            for rendering in RENDERINGS:
                arm = {c["case_id"]: c for c in common.read_jsonl(RESULTS / split / f"binary64_{rendering}" / "cases.jsonl")}
                finals, decimals, fractions = [], Counter(), Counter()
                for case_id, case in stored.items():
                    question, gold = d.questions[case_id], d.gold[case_id]
                    before, after = row_texts(case["row"]), row_texts(arm[case_id]["row"])
                    fields = [("final", question["answer_spec"], gold["final_value"])] + [
                        (s["slot_id"], s["result_spec"], gold["slot_values"][s["slot_id"]]) for s in question["trace_spec"]["slots"]]
                    for name, spec, target in fields:
                        if spec["type"] == "enum":
                            continue
                        was = name in before and value_matches(before[name], target, spec)
                        now = name in after and value_matches(after[name], target, spec)
                        if not was or now:
                            if was and now and spec["rounding"]["mode"] == "exact" and "/" in target:
                                fractions["kept"] += 1
                            continue
                        value = decode(executed[case_id]["values"][name])
                        if name == "final":
                            item = {"case_id": case_id, "kind": spec["rounding"]["mode"], "gold": target,
                                    "binary64_value": repr(value), "binary64_text": after.get(name)}
                            if spec["rounding"]["mode"] == "half_up":
                                reply = box.run(case["samples"][0]["attempts"][0]["code"])
                                exact = decode(reply["values"][name])
                                places = spec["rounding"]["decimal_places"]
                                item["exact_unrounded"] = str(exact) if not isinstance(exact, Fraction) else (
                                    str(exact.numerator) if exact.denominator == 1 else f"{exact.numerator}/{exact.denominator}")
                                if isinstance(exact, Fraction):
                                    scaled = exact * 10 ** (places + 1)
                                    item["exact_value_is_a_rounding_tie"] = scaled.denominator == 1 and abs(scaled.numerator) % 10 == 5
                                    item["relative_error_of_double"] = float(abs(Fraction(value) - exact) / abs(exact)) if exact else None
                                else:
                                    item["exact_value_is_a_rounding_tie"] = None
                            finals.append(item)
                        elif spec["rounding"]["mode"] == "exact" and "/" not in target:
                            digits = significant_digits(target)
                            if digits > 15 and rendering != "repr":
                                decimals["gold has more than 15 significant digits"] += 1
                            elif "/" in after.get(name, ""):
                                decimals["a fraction was written for a finite decimal"] += 1
                            elif isinstance(value, float) and float(as_fraction(target)) == value:
                                decimals["the double is the nearest one to the gold, the rendering loses it"] += 1
                            else:
                                decimals["arithmetic error: the double is not the nearest one to the gold"] += 1
                        elif spec["rounding"]["mode"] == "exact":
                            truth = as_fraction(target)
                            if isinstance(value, float) and float(truth) != value:
                                fractions["lost: arithmetic error, the double is not the nearest one to the gold"] += 1
                            elif truth.denominator > 10**6:
                                fractions["lost: denominator above 10**6"] += 1
                            else:
                                fractions["lost: other"] += 1
                entry[rendering] = {
                    "lost_finals": finals,
                    "lost_half_up_finals_that_are_exact_ties": sum(1 for f in finals if f.get("exact_value_is_a_rounding_tie")),
                    "lost_half_up_finals": sum(1 for f in finals if f["kind"] == "half_up"),
                    "lost_exact_decimal_slots": dict(decimals), "exact_fraction_slots": dict(fractions)}
    finally:
        box.close()
    common.write_bytes_atomic(RESULTS / "posthoc_analysis.json", (json.dumps(report, indent=1) + "\n").encode("utf-8"))
    for split, entry in report.items():
        for rendering, item in entry.items():
            print("=" * 6, split, rendering)
            print("  lost half-up finals:", item["lost_half_up_finals"], "| of these exact ties:", item["lost_half_up_finals_that_are_exact_ties"])
            for final in item["lost_finals"][:6]:
                print("    ", {k: final[k] for k in final if k != "case_id"})
            print("  lost exact decimal slots:", item["lost_exact_decimal_slots"])
            print("  exact fraction slots:", item["exact_fraction_slots"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
