"""Keyword counts behind the description of the novel-route questions (public question text only).

  python -I paper/working_notes/verify/hidden_form_stats.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUF = re.compile(r"\n\nAnswer format: .*\Z", re.S)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def jl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def skel(text):
    return NUM.sub("#", " ".join(SUF.sub("", text).lower().split()))


def sig(q):
    return tuple((s["slot_id"], s["description"]) for s in q["trace_spec"]["slots"])


train = jl(ROOT / "development_files" / "train_questions.jsonl")
test = jl(ROOT / "test_questions" / "test_questions.jsonl")
sk, sg = {skel(q["question"]) for q in train}, {sig(q) for q in train}
novel = [q for q in test if skel(q["question"]) not in sk and sig(q) not in sg]
body = lambda q: SUF.sub("", q["question"]).lower()


def count(qs, words):
    return sum(1 for q in qs if any(w in body(q) for w in words))


groups = {
    "conditional cue": ("if ", "otherwise", "unless", "at least", "at most", "exceed", "whichever", "when "),
    "threshold / cap / floor": ("threshold", "cap ", "caps ", "capped", "floor", "limit", "at least", "at most", "exceed", "minimum", "maximum"),
    "selection between alternatives": ("otherwise", "whichever", "the larger", "the smaller", "the greater", "the lesser", "the lower", "the higher", "binding"),
    "solve-for wording": ("makes this", "make this", "at which", "break-even", "breakeven", "implied", "what ", "that makes", "equals the target", "binding", "required "),
    "scenario-defined rule": ("scenario-defined", "under this scenario", "scenario defines", "fictional", "internal policy", "this policy", "scenario gives"),
}
print("train", len(train), "novel", len(novel))
for name, words in groups.items():
    print(f"{name:32s} train {count(train, words):5d}/{len(train)}   novel {count(novel, words):4d}/{len(novel)}   {words}")
for w in ("what ", "at which", "makes ", "implied", "break-even", "binding", "target"):
    print(f"  '{w}': train {count(train, (w,))}  novel {count(novel, (w,))}")

# Figures used in the paper (Section "The hidden-stratum gap", paragraph "Form").
flat = lambda q: " ".join(body(q).split())
SOLVE_FOR = re.compile(r"at which|what [^.?]*\bmakes\b|that makes")
print("PAPER conditional cue:", count(train, groups["conditional cue"]), "of", len(train), "train;",
      count(novel, groups["conditional cue"]), "of", len(novel), "novel")
print("PAPER solve-for wording (at which | what ... makes | that makes):",
      sum(bool(SOLVE_FOR.search(flat(q))) for q in train), "of", len(train), "train;",
      sum(bool(SOLVE_FOR.search(flat(q))) for q in novel), "of", len(novel), "novel")
note = "use exact arithmetic through all intermediate steps"
decimal_finals = [q for q in novel if q["answer_spec"]["type"] == "decimal"]
print("PAPER novel questions with a numeric final:", len(decimal_finals), "| of these with the exact-arithmetic, half-up answer-format note:",
      sum(note in q["question"] and "half up" in q["question"] for q in decimal_finals))
