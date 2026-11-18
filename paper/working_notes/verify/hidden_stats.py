import json, re, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]  # repository root
def jl(p): return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
SUF = re.compile(r"\n\nAnswer format: .*\Z", re.S); NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
def skel(t): return NUM.sub("#", " ".join(SUF.sub("", t).lower().split()))
def sig(q): return tuple((s["slot_id"], s["description"]) for s in q["trace_spec"]["slots"])
train = jl(ROOT/"development_files/train_questions.jsonl"); test = jl(ROOT/"test_questions/test_questions.jsonl")
sk = {skel(q["question"]) for q in train}; sg = {sig(q) for q in train}
novel = [q for q in test if skel(q["question"]) not in sk and sig(q) not in sg]
seen = [q for q in test if not (skel(q["question"]) not in sk and sig(q) not in sg)]
print("novel", len(novel), "seen", len(seen))
train_ids = {s["slot_id"] for q in train for s in q["trace_spec"]["slots"]}
test_ids = {s["slot_id"] for q in test for s in q["trace_spec"]["slots"]}
print("distinct slot ids train", len(train_ids), "test", len(test_ids), "test not in train", len(test_ids - train_ids))
novel_ids = {s["slot_id"] for q in novel for s in q["trace_spec"]["slots"]}
print("novel-route slot ids", len(novel_ids), "not in train", len(novel_ids - train_ids))
from collections import Counter
print("novel slot rounding", Counter(s["result_spec"].get("rounding",{}).get("mode", s["result_spec"]["type"]) for q in novel for s in q["trace_spec"]["slots"]))
print("train slot rounding", Counter(s["result_spec"].get("rounding",{}).get("mode", s["result_spec"]["type"]) for q in train for s in q["trace_spec"]["slots"]))
print("novel enum finals", sum(1 for q in novel if q["answer_spec"]["type"]=="enum"), "train enum finals", sum(1 for q in train if q["answer_spec"]["type"]=="enum"))
print("novel slots/question", Counter(len(q["trace_spec"]["slots"]) for q in novel))
print("median len train", statistics.median(len(q["question"]) for q in train), "novel", statistics.median(len(q["question"]) for q in novel), "seen-route test", statistics.median(len(q["question"]) for q in seen))
