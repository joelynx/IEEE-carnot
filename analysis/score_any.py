"""Thin read-only harness: call the toolkit's own score_submission on any split.

Usage: python -I score_any.py REPO QUESTIONS GOLD MANIFEST PREDICTIONS [--per-case OUT.jsonl]
"""
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo))
from finreason_task1.contracts import load_jsonl  # noqa: E402
from finreason_task1.scoring import score_case, score_submission  # noqa: E402


def index(path):
    loaded = load_jsonl(path)
    assert loaded.valid, loaded.as_dict()
    return {r["case_id"]: r for r in loaded.records}


questions = index(sys.argv[2])
gold = index(sys.argv[3])
manifest = list(index(sys.argv[4]).values())
preds = load_jsonl(sys.argv[5])
assert preds.valid, preds.as_dict()
report = score_submission(questions, gold, preds.records, manifest)
print(json.dumps(report.as_dict(), indent=1))
if "--per-case" in sys.argv:
    out = Path(sys.argv[sys.argv.index("--per-case") + 1])
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for p in preds.records:
            cs = score_case(questions[p["case_id"]], gold[p["case_id"]], p)
            fh.write(json.dumps({"case_id": cs.case_id, "fac": cs.fac,
                                 "matched": cs.matched_slots, "total": cs.total_slots}) + "\n")
