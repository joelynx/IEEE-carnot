"""Arithmetic replay: stored programs of two R0 runs re-executed in exact arithmetic and in binary64.

Pre-registered in experiments/arith_replay_20261118/preregistration.json.  No model call: the
programs are read from runs/<run>/cases.jsonl.  Each program is executed twice inside the same
WSL sandbox, once with the frozen exact modules (carnot/sandbox) and once with the binary64 twin
(sandbox_binary64/).  The exact execution must reproduce every stored rendered field before any
binary64 result is looked at.  The binary64 values are rendered in three pre-registered ways.

  python -I experiments/arith_replay_20261118/run_arith_replay.py --selftest     toy programs only
  python -I experiments/arith_replay_20261118/run_arith_replay.py --exact-only   reproduction check
  python -I experiments/arith_replay_20261118/run_arith_replay.py                full replay (needs the frozen pre-registration)

Writes only under experiments/arith_replay_20261118/results/.  It does not touch runs/,
experiments/log.jsonl, the response cache, the lockbox, the leaderboard or the test set.
"""

import argparse
import json
import math
import queue
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from carnot import common, compare, harness  # noqa: E402
from carnot.formatter import Rendered, build_row, fraction_to_exact_text, render  # noqa: E402
from carnot.sandbox import executor  # noqa: E402
from carnot.sandbox.executor import Sandbox, decode  # noqa: E402
from carnot.solver import Solver  # noqa: E402
from finreason_task1.scoring import value_matches  # noqa: E402

TWIN = HERE / "sandbox_binary64"
RESULTS = HERE / "results"
PREREG = HERE / "preregistration.json"
RUNS = (("tuning-eval", "20261011T184257Z_r0_tuning-eval_S"), ("tuning-noex", "20261012T155533Z_r0_tuning-noex_S"))
RENDERINGS = ("repr", "15g", "rational")
FROZEN = {  # files the replay relies on without changing them
    "carnot/sandbox/executor.py": "7d15a38cb62a5c2a7660d9417fd1cc13291ab921f5b5e0187370e5121e449026",
    "carnot/sandbox/worker.py": "e57fbe679799d01841c27181c6fcc504c2d863eb4f0e163763b261bca19ff9e4",
    "carnot/sandbox/policy.py": "50222c16a657e28e1cdde3de4d1010bc1988a93848a40467e62647c28d28cb90",
    "carnot/sandbox/runner.py": "2d50d90e2724259c0948697380c9364a833642fa281764c04f1125998520ed2f",
    "carnot/sandbox/finq.py": "85ff980722722bdc975872eb0000efaf77dcfadf0f7ad16528b2d5157bf12c64",
    "carnot/formatter.py": "06156aa7d004d01d46debc7d19f6324d035e6f7f2b345a96833145e9188703d0",
}
SEALED = ("sandbox_binary64/finq.py", "sandbox_binary64/runner.py", "run_arith_replay.py")
SHORT_DECIMAL_DIGITS = 12
WORKERS = 4
TIMEOUT = 5.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    common.write_bytes_atomic(path, (json.dumps(value, indent=1) + "\n").encode("utf-8"))


def check_files(require_frozen: bool) -> dict:
    """Frozen modules untouched, twin copies identical, and (full run) the pre-registration sealed."""

    for relative, expected in FROZEN.items():
        if common.sha256_file(ROOT / relative) != expected:
            raise SystemExit(f"{relative} differs from the frozen version")
    for name in ("worker.py", "policy.py"):
        if common.sha256_file(TWIN / name) != FROZEN[f"carnot/sandbox/{name}"]:
            raise SystemExit(f"sandbox_binary64/{name} is not a byte-identical copy of the frozen file")
    sealed = {relative: common.sha256_file(HERE / relative) for relative in SEALED}
    if require_frozen:
        record = json.loads(PREREG.read_text(encoding="utf-8"))
        if record.get("status") != "frozen_before_binary64_execution":
            raise SystemExit("the pre-registration is not frozen; the binary64 replay may not run")
        if record.get("sealed_files_sha256") != sealed:
            raise SystemExit("a sealed file changed after the pre-registration was frozen")
    return sealed


def make_box(twin: bool) -> Sandbox:
    box = Sandbox("wsl", timeout=TIMEOUT)
    if twin:  # same command, same isolation; only the folder the four sandbox files are copied from differs
        exact_dir, twin_dir = executor._wsl_path(executor.SANDBOX_DIR), executor._wsl_path(TWIN)
        script = box.command[-1]
        if script.count(exact_dir) != len(executor.SANDBOX_FILES):
            raise SystemExit("unexpected sandbox command; refusing to redirect it")
        box.command = box.command[:-1] + [script.replace(exact_dir, twin_dir)]
    return box


def run_programs(programs: list[tuple[str, str]], twin: bool, label: str) -> tuple[dict[str, dict], dict]:
    boxes: queue.Queue = queue.Queue()
    made = [make_box(twin) for _ in range(WORKERS)]
    for box in made:
        boxes.put(box)

    def work(item: tuple[str, str]) -> tuple[str, dict]:
        key, code = item
        box = boxes.get()
        try:
            return key, box.run(code)
        finally:
            boxes.put(box)

    replies: dict[str, dict] = {}
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for done, (key, reply) in enumerate(pool.map(work, programs), start=1):
                replies[key] = reply
                if done % 500 == 0 or done == len(programs):
                    print(f"[{label}] {done}/{len(programs)} elapsed={time.perf_counter() - started:.0f}s", flush=True)
        info = dict(made[0].info)
    finally:
        for box in made:
            box.close()
    return replies, info


def fields_of(question) -> list[tuple[str, dict]]:
    return [("final", question["answer_spec"])] + [
        (slot["slot_id"], slot["result_spec"]) for slot in question["trace_spec"]["slots"]]


def render_binary64(value, spec, rendering: str) -> Rendered:
    """The frozen formatter, except for the two cases it refuses or cannot take: a float in an
    exact field (rendered by the pre-registered rule) and a non-finite float (dropped)."""

    if spec["type"] != "enum" and isinstance(value, float):
        if not math.isfinite(value):
            return Rendered(None, "non-finite value", ["float"])
        if spec["rounding"]["mode"] == "exact":
            fifteen = Decimal(format(value, ".15g"))
            if rendering == "repr":  # shortest decimal that round-trips to the same double
                number = Fraction(Decimal(repr(value)))
            elif rendering == "15g":  # 15 significant digits (DBL_DIG)
                number = Fraction(fifteen)
            elif rendering == "rational":
                # A short decimal is kept; otherwise Python's default rational reconstruction
                # (denominator <= 10**6) is used if it maps back to the same double.
                candidate = Fraction(value).limit_denominator()
                short = len(fifteen.normalize().as_tuple().digits) <= SHORT_DECIMAL_DIGITS
                number = candidate if not short and float(candidate) == value else Fraction(fifteen)
            else:
                raise ValueError(rendering)
            text = fraction_to_exact_text(number)
            if len(text) > 256:
                return Rendered(None, "rendered value exceeds 256 characters", ["float"])
            return Rendered(text, None, ["float"])
    return render(value, spec)


def texts_binary64(question, reply: dict, rendering: str) -> tuple[dict, dict]:
    if not reply.get("ok"):
        return {}, {name: f"execution failed at the {reply.get('stage')} stage" for name, _ in fields_of(question)}
    values = {key: decode(encoded) for key, encoded in reply["values"].items()}
    texts, issues = {}, {}
    for name, spec in fields_of(question):
        if name not in values:
            issues[name] = "missing key"
            continue
        rendered = render_binary64(values[name], spec, rendering)
        if rendered.text is None:
            issues[name] = rendered.issue or "unrenderable"
        else:
            texts[name] = rendered.text
    return texts, issues


def texts_exact(question, reply: dict) -> tuple[dict, dict]:
    if not reply.get("ok"):
        return {}, {name: f"execution failed at the {reply.get('stage')} stage" for name, _ in fields_of(question)}
    values = {key: decode(encoded) for key, encoded in reply["values"].items()}
    texts, issues, _flags = Solver._render_all(None, question, values)  # the pipeline's own rendering loop
    return texts, issues


def row_from(question, texts: dict) -> tuple[dict, list[str]]:
    return build_row(question, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})


def row_texts(row: dict) -> dict:
    texts = {step["slot_id"]: step["value"] for step in row["steps"]}
    if row["final_answer"] is not None:
        texts["final"] = row["final_answer"]["value"]
    return texts


def write_arm(split: str, run: str, arm: str, case_ids: list[str], rows: dict, extra: dict, info: dict) -> dict:
    out = RESULTS / split / arm
    out.mkdir(parents=True, exist_ok=True)
    ordered = [rows[c] for c in case_ids]
    scored = harness.score(ordered, case_ids)
    per_case = {c["case_id"]: c for c in scored["cases"]}
    wrong_finals = sum(1 for c in per_case.values() if c["fac"] != 1)
    missed = sum(c["total_slots"] - c["matched_slots"] for c in per_case.values())
    total = sum(c["total_slots"] for c in per_case.values())
    record = {
        "run_id": f"arith_replay_20261118_{split}_{arm}", "recorded_at": now(), "split": split, "mode": "S",
        "complete": True, "source_run": run, "arm": arm, "n_cases": len(case_ids), "sandbox": info,
        "score": scored["report"], "wrong_finals": wrong_finals, "missed_slots": missed, "total_slots": total,
        "micro": {"fac": f"{len(case_ids) - wrong_finals}/{len(case_ids)}", "slots": f"{total - missed}/{total}"},
        **extra,
    }
    common.write_jsonl(out / "cases.jsonl", [{"case_id": c, **per_case[c], "row": rows[c]} for c in case_ids])
    record["predictions_sha256"] = common.write_jsonl(out / "predictions.jsonl", ordered)
    save_json(out / "summary.json", record)
    return record


def transitions(d, case_ids: list[str], stored_rows: dict, arm_rows: dict) -> dict:
    """Field-level changes against the stored exact run, by field kind and gold form."""

    table: dict[str, Counter] = {}
    examples: dict[str, list] = {}
    for case_id in case_ids:
        question, gold = d.questions[case_id], d.gold[case_id]
        before, after = row_texts(stored_rows[case_id]), row_texts(arm_rows[case_id])
        for name, spec in fields_of(question):
            target = gold["final_value"] if name == "final" else gold["slot_values"][name]
            if spec["type"] == "enum":
                kind = "enum"
            elif spec["rounding"]["mode"] == "exact":
                kind = "exact, gold a fraction" if "/" in target else "exact, gold a decimal"
            else:
                kind = "half-up"
            key = f"{'final' if name == 'final' else 'slot'} | {kind}"
            was = name in before and value_matches(before[name], target, spec)
            is_now = name in after and value_matches(after[name], target, spec)
            outcome = {(True, True): "kept", (True, False): "lost", (False, True): "gained", (False, False): "still wrong"}[(was, is_now)]
            if outcome == "lost" and name not in after:
                outcome = "lost (field absent)"
            table.setdefault(key, Counter())[outcome] += 1
            if outcome.startswith("lost") or outcome == "gained":
                examples.setdefault(f"{key} | {outcome}", [])
                if len(examples[f"{key} | {outcome}"]) < 5:
                    examples[f"{key} | {outcome}"].append(
                        {"case_id": case_id, "field": name, "gold": target, "exact": before.get(name), "binary64": after.get(name)})
    return {"counts": {key: dict(counter) for key, counter in sorted(table.items())}, "examples": examples}


def selftest() -> int:
    toys = [
        ("a", "def solve():\n    return {'final': 0.1 + 0.2, 'third': 1/3, 'floor': 7//2, 'p': Q('33.325') / Q(100) * 100}"),
        ("b", "def solve():\n    x = Q(2) ** Q('0.5')\n    return {'final': x * x, 'half': round_half_up(Q('2.675'), 2), 'big': 2 ** 10, 'root': sqrt(Q(2))}"),
        ("c", "def solve():\n    v = [Q('0.1')] * 10\n    return {'final': sum(v), 'm': max(Q(1), Q(3) / 7), 'e': 'yes' if Q('0.1') * 3 == Q('0.3') else 'no'}"),
        ("d", "def solve():\n    return {'final': Q(1) / Q(0)}"),
    ]
    exact, info_exact = run_programs(toys, twin=False, label="selftest exact")
    twin, info_twin = run_programs(toys, twin=True, label="selftest binary64")
    print("exact sandbox", info_exact, "| binary64 sandbox", info_twin)
    for key, _ in toys:
        print(key, "exact   ", json.dumps(exact[key])[:400])
        print(key, "binary64", json.dumps(twin[key])[:400])
    exact_spec = {"type": "decimal", "unit": "x", "rounding": {"mode": "exact"}}
    two_places = {"type": "decimal", "unit": "x", "rounding": {"mode": "half_up", "decimal_places": 2}}
    for value in (0.1 + 0.2, 1 / 3, 33.325, 2.0000000000000004, 10910.5752148948304, 12345.6789012, 1234567 / 3,
                  0.1 * 3 / 7, 1e-7, 123456789.125, float("inf"), 7):
        shown = {r: render_binary64(value, exact_spec, r).text for r in RENDERINGS}
        print(repr(value), "exact field:", shown, "| 2 places:", render_binary64(value, two_places, "repr").text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true", help="toy programs only; no stored program is run")
    parser.add_argument("--exact-only", action="store_true", help="reproduction check with the frozen exact sandbox only")
    args = parser.parse_args()

    sealed = check_files(require_frozen=not (args.selftest or args.exact_only))
    if args.selftest:
        return selftest()
    release = common.verify_release()
    d = common.data()
    started = now()

    loaded = {}
    for split, run in RUNS:
        cases = common.read_jsonl(ROOT / "runs" / run / "cases.jsonl")
        for case in cases:
            attempts = case["samples"][0]["attempts"]
            if len(case["samples"]) != 1 or len(attempts) != 1 or not attempts[0].get("code"):
                raise SystemExit(f"{run}: {case['case_id']} is not a one-sample, one-attempt record with a program")
        loaded[split] = {"run": run, "cases": {case["case_id"]: case for case in cases},
                         "case_ids": [case["case_id"] for case in cases]}

    # Step 1: exact execution of every program; it must reproduce the stored fields and rows.
    reproduction, exact_rows, exact_info = {}, {}, {}
    for split, item in loaded.items():
        programs = [(c, item["cases"][c]["samples"][0]["attempts"][0]["code"]) for c in item["case_ids"]]
        replies, exact_info[split] = run_programs(programs, twin=False, label=f"{split} exact")
        mismatches, rows = [], {}
        for case_id in item["case_ids"]:
            stored = item["cases"][case_id]
            attempt = stored["samples"][0]["attempts"][0]
            texts, issues = texts_exact(d.questions[case_id], replies[case_id])
            rows[case_id], _dropped = row_from(d.questions[case_id], texts)
            if texts != attempt.get("rendered") or issues != (attempt.get("issues") or {}) or rows[case_id] != stored["row"]:
                mismatches.append({"case_id": case_id, "stored": attempt.get("rendered"), "replayed": texts,
                                   "sandbox": {k: replies[case_id].get(k) for k in ("ok", "stage", "error")}})
        exact_rows[split] = rows
        reproduction[split] = {"run": item["run"], "programs": len(programs), "reproduced": len(programs) - len(mismatches),
                               "mismatches": mismatches, "sandbox": exact_info[split]}
    reproduced = all(not entry["mismatches"] for entry in reproduction.values())
    save_json(RESULTS / "exact_reproduction.json", {"recorded_at": now(), "started": started, "reproduced_all": reproduced,
                                                    "release_manifest_sha256": release, "runs": reproduction})
    print(json.dumps({s: {k: v for k, v in e.items() if k != "mismatches"} | {"mismatches": len(e["mismatches"])}
                      for s, e in reproduction.items()}, indent=1))
    if not reproduced:
        print("STOP: the exact execution did not reproduce the stored runs; no binary64 result was produced.")
        return 2

    overview = {"recorded_at": None, "started": started, "sealed_files_sha256": sealed, "arms": {}}
    for split, item in loaded.items():
        record = write_arm(split, item["run"], "exact_replay", item["case_ids"], exact_rows[split],
                           {"description": "stored programs re-executed with the frozen exact sandbox and formatter"},
                           exact_info[split])
        result = compare.compare(str(ROOT / "runs" / item["run"]), str(RESULTS / split / "exact_replay"), [], 10_000, "case")
        save_json(RESULTS / split / "comparison_exact_replay.json", {**result, "recorded_at": now()})
        overview["arms"][f"{split} | exact_replay"] = {k: record[k] for k in ("micro", "wrong_finals", "missed_slots")} | {
            "scores": {k: record["score"]["scores"][k] for k in ("seen_fac", "seen_checkpoint")},
            "delta_vs_stored": {k: result[k]["delta_exact"] for k in compare.KEYS}}
    if args.exact_only:
        overview["recorded_at"] = now()
        save_json(RESULTS / "overview_exact_only.json", overview)
        print(json.dumps(overview, indent=1))
        return 0

    # Step 2: binary64 execution of the same programs, then the three renderings.
    for split, item in loaded.items():
        programs = [(c, item["cases"][c]["samples"][0]["attempts"][0]["code"]) for c in item["case_ids"]]
        replies, info = run_programs(programs, twin=True, label=f"{split} binary64")
        common.write_jsonl(RESULTS / split / "binary64_execution.jsonl",
                           [{"case_id": c, **{k: replies[c].get(k) for k in ("ok", "stage", "error", "elapsed_ms", "values")}}
                            for c in item["case_ids"]])
        failures = Counter(str(replies[c].get("stage")) for c in item["case_ids"] if not replies[c].get("ok"))
        stored_rows = {c: item["cases"][c]["row"] for c in item["case_ids"]}
        for rendering in RENDERINGS:
            arm = f"binary64_{rendering}"
            rows, unrendered, dropped_total = {}, Counter(), 0
            for case_id in item["case_ids"]:
                texts, issues = texts_binary64(d.questions[case_id], replies[case_id], rendering)
                unrendered.update(issues.values())
                rows[case_id], dropped = row_from(d.questions[case_id], texts)
                dropped_total += len(dropped)
            record = write_arm(split, item["run"], arm, item["case_ids"], rows,
                               {"description": f"stored programs executed in binary64, exact fields rendered by rule '{rendering}'",
                                "execution_failures": dict(failures), "unrendered_fields": dict(unrendered),
                                "fields_dropped_by_gate": dropped_total}, info)
            result = compare.compare(str(ROOT / "runs" / item["run"]), str(RESULTS / split / arm), [], 10_000, "case")
            save_json(RESULTS / split / f"comparison_{arm}.json", {**result, "recorded_at": now()})
            changes = transitions(d, item["case_ids"], stored_rows, rows)
            save_json(RESULTS / split / f"field_transitions_{arm}.json", changes)
            overview["arms"][f"{split} | {arm}"] = {k: record[k] for k in ("micro", "wrong_finals", "missed_slots")} | {
                "scores": {k: record["score"]["scores"][k] for k in ("seen_fac", "seen_checkpoint")},
                "delta_vs_stored": {k: {"delta": result[k]["delta"], "ci95": result[k]["ci95"]} for k in compare.KEYS},
                "changed_cases": result["changed_cases"], "execution_failures": dict(failures),
                "unrendered_fields": dict(unrendered), "fields_dropped_by_gate": dropped_total,
                "field_transitions": changes["counts"]}
    overview["recorded_at"] = now()
    save_json(RESULTS / "overview.json", overview)
    print(json.dumps(overview, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
