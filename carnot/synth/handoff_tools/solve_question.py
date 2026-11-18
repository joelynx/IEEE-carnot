"""Phase 2: run your program for one cross-check question and record the answer.

  python tools/solve_question.py phase2/items/item_07.json outputs/programs/item_07_attempt1.py

The program must define solve() returning a dict with "final" and every slot_id,
exactly as reference/solving_rules.txt describes.  It runs in the same exact-
arithmetic sandbox our solvers use, and every value is rendered from its spec.
The answer goes to outputs/solutions/item_07.json; every attempt is logged to
outputs/logs/solve_log.jsonl.  At most 3 attempts per question, and a retry is
allowed only after an attempt that failed to run or left a field unrenderable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works with python -I too

from _common import MAX_ATTEMPTS, OUT, PHASE1_DONE, PKG, load_json, log, read_log, sandbox, sha256_bytes, write_json

ITEM = re.compile(r"item_(\d\d)\.json\Z")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    item_path, program_path = Path(argv[0]), Path(argv[1])
    if not PHASE1_DONE.exists():
        print("REFUSED: finish phase 1 first (python tools/start_phase2.py).")
        return 2
    if not ITEM.fullmatch(item_path.name) or item_path.resolve().parent != (PKG / "phase2" / "items").resolve():
        print("REFUSED: the first argument must be a file in phase2/items/.")
        return 2
    item = load_json(item_path)
    previous = [r for r in read_log("solve_log") if r["item"] == item["item"]]
    if len(previous) >= MAX_ATTEMPTS:
        print(f"REFUSED: all {MAX_ATTEMPTS} attempts for {item['item']} are used.")
        return 2
    if previous and previous[-1]["complete"]:
        print(f"REFUSED: {item['item']} already has a complete answer; retries are only for failed attempts.")
        return 2
    attempt = len(previous) + 1
    code = program_path.read_bytes()
    programs = OUT / "programs"
    programs.mkdir(parents=True, exist_ok=True)
    (programs / f"{item['item']}_attempt{attempt}.py").write_bytes(code)

    from carnot.formatter import build_row, render
    from carnot.sandbox.executor import decode

    question = item["question"]
    box = sandbox()
    try:
        reply = box.run(code.decode("utf-8"))
    finally:
        box.close()
    record = {"item": item["item"], "case_id": question["case_id"], "attempt": attempt, "program_sha256": sha256_bytes(code)}
    if not reply.get("ok"):
        record.update(complete=False, error=f"the program failed at the {reply.get('stage')} stage: {reply.get('error')}")
        log("solve_log", record)
        print(f"FAILED: {record['error']}\nAttempts left: {MAX_ATTEMPTS - attempt}.")
        return 1
    values = {k: decode(v) for k, v in reply["values"].items()}
    fields = [("final", question["answer_spec"])] + [(s["slot_id"], s["result_spec"]) for s in question["trace_spec"]["slots"]]
    texts, issues = {}, {}
    for name, spec in fields:
        if name not in values:
            issues[name] = "missing key"
            continue
        rendered = render(values[name], spec)
        if rendered.text is None:
            issues[name] = rendered.issue or "unrenderable"
        else:
            texts[name] = rendered.text
    row, dropped = build_row(question, texts.get("final"), {k: v for k, v in texts.items() if k != "final"})
    record.update(complete=not issues and not dropped, values=texts, issues=issues, dropped=dropped)
    write_json(OUT / "solutions" / f"{item['item']}.json",
               {"item": item["item"], "case_id": question["case_id"], "attempt": attempt, "values": texts,
                "issues": issues, "row": row})
    log("solve_log", record)
    if record["complete"]:
        print(f"OK: {item['item']} answered (attempt {attempt}).")
        return 0
    problems = "; ".join(f"{k}: {v}" for k, v in issues.items()) or f"fields dropped by the validator: {dropped}"
    print(f"INCOMPLETE: {problems}\nAttempts left: {MAX_ATTEMPTS - attempt}.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
