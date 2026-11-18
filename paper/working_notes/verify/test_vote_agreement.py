"""Post hoc descriptive statistic on our own test outputs (approved by the author on 18 November 2026).

How often did the five samples of the novel route disagree on the 348 novel-route test questions
of the scored submission (R4)?  Computed after the official results were published, used for no
decision, and involving no reference answer (none is public).  Read-only; aggregates only: no
case id, question text or answer value is printed.

  python -I paper/working_notes/verify/test_vote_agreement.py
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "runs" / "20261012T165330Z_r4_test928_S"

cases = [json.loads(line) for line in (RUN / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
questions = {json.loads(line)["case_id"]: json.loads(line)
             for line in (ROOT / "test_questions" / "test_questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
novel = [c for c in cases if c["route"] == "novel"]
print("questions", len(cases), "novel route", len(novel), "samples per novel question", dict(Counter(len(c["samples"]) for c in novel)))

final_top = Counter()        # size of the plurality on the final answer
slot_top = Counter()
fields = nonunanimous_fields = 0
q_final_split = q_any_split = q_slot_only_split = 0
unrendered = 0
by_kind = Counter()
for c in novel:
    q = questions[c["case_id"]]
    names = ["final"] + [s["slot_id"] for s in q["trace_spec"]["slots"]]
    any_split = final_split = False
    for name in names:
        values = [s["texts"].get(name) for s in c["samples"]]
        unrendered += sum(v is None for v in values)
        counts = Counter(values)
        top = counts.most_common(1)[0][1]
        fields += 1
        if name == "final":
            final_top[top] += 1
            final_split = len(counts) > 1
        else:
            slot_top[top] += 1
        if len(counts) > 1:
            nonunanimous_fields += 1
            any_split = True
    q_final_split += final_split
    q_any_split += any_split
    q_slot_only_split += any_split and not final_split
    if final_split:
        by_kind[q["answer_spec"]["type"]] += 1

print("fields (finals + slots):", fields, "| not unanimous:", nonunanimous_fields, "| unrendered sample fields:", unrendered)
print("final answer, size of the plurality among five samples:", dict(sorted(final_top.items(), reverse=True)))
print("slots, size of the plurality among five samples:", dict(sorted(slot_top.items(), reverse=True)))
print("questions with a non-unanimous final:", q_final_split, "of", len(novel), "| by final type:", dict(by_kind))
print("questions with any non-unanimous field:", q_any_split, "| with a split on a slot only:", q_slot_only_split)
