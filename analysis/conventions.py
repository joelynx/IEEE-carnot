"""Read-only: value conventions in gold, and seen/hidden proxy for test. Usage: python -I conventions.py DEV_DIR TEST_DIR"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

D, T = Path(sys.argv[1]), Path(sys.argv[2])


def jl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]


trq = jl(D / "train_questions.jsonl")
trg = {r["case_id"]: r for r in jl(D / "train_gold.jsonl")}
trm = {r["case_id"]: r for r in jl(D / "train_manifest.jsonl")}
lbq = jl(D / "leaderboard_questions.jsonl")
teq = jl(T / "test_questions.jsonl")
SUFFIX_RE = re.compile(r"\n\nAnswer format: .*\Z", re.S)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def skel(t):
    return NUM.sub("#", " ".join(SUFFIX_RE.sub("", t).lower().split()))


print("=== exponent-notation gold slot values (sample) ===")
ex = [(sl["slot_id"], sl["result_spec"]["unit"], trg[q["case_id"]]["slot_values"][sl["slot_id"]])
      for q in trq for sl in q["trace_spec"]["slots"]
      if sl["result_spec"]["type"] == "decimal" and "e" in trg[q["case_id"]]["slot_values"][sl["slot_id"]].lower()]
print(len(ex), ex[:12])
print("exponent forms:", Counter(re.sub(r"\d", "9", v) for _, _, v in ex).most_common(8))
print("=== rational gold slot values (sample) ===")
ra = [(sl["slot_id"], sl["result_spec"]["unit"], trg[q["case_id"]]["slot_values"][sl["slot_id"]])
      for q in trq for sl in q["trace_spec"]["slots"] if "/" in trg[q["case_id"]]["slot_values"][sl["slot_id"]]]
print(len(ra), ra[:10])
print("=== exact-mode slot values: max significant digits / decimals ===")
lens = Counter()
for q in trq:
    for sl in q["trace_spec"]["slots"]:
        if sl["result_spec"]["type"] == "decimal" and sl["result_spec"]["rounding"]["mode"] == "exact":
            v = trg[q["case_id"]]["slot_values"][sl["slot_id"]]
            if "/" in v or "e" in v.lower():
                continue
            dec = len(v.split(".")[1]) if "." in v else 0
            lens[min(dec, 12)] += 1
print("decimal places in exact finite-decimal slot gold:", dict(sorted(lens.items())))

print("=== percent / ratio conventions ===")
for unit in ("percent", "ratio", "real_percent", "nominal_percent", "basis_point", "dimensionless", "multiple"):
    finals = [(trg[q["case_id"]]["final_value"]) for q in trq if q["answer_spec"].get("unit") == unit]
    slots = [trg[q["case_id"]]["slot_values"][sl["slot_id"]] for q in trq for sl in q["trace_spec"]["slots"] if sl["result_spec"].get("unit") == unit]
    print(unit, "final sample:", finals[:8], "| slot sample:", slots[:8])
# Show one full percent-final question and one ratio-slot question
for pred in (lambda q: q["answer_spec"].get("unit") == "percent",
             lambda q: any(sl["result_spec"].get("unit") == "ratio" for sl in q["trace_spec"]["slots"]),
             lambda q: any(sl["result_spec"].get("unit") == "percent" for sl in q["trace_spec"]["slots"]),
             lambda q: q["answer_spec"]["type"] == "enum" and len(q["trace_spec"]["slots"]) > 0):
    q = next(q for q in trq if pred(q))
    print("\n--- example", trm[q["case_id"]]["template_id"])
    print(q["question"])
    print("slots:", [(s["slot_id"], s["description"], s["result_spec"]) for s in q["trace_spec"]["slots"]])
    print("gold:", trg[q["case_id"]]["final_value"], trg[q["case_id"]]["slot_values"])

print("\n=== slot descriptions: generic ids (trace_N) vs named ids ===")
gen = Counter(bool(re.fullmatch(r"trace_\d+", sl["slot_id"])) for q in trq for sl in q["trace_spec"]["slots"])
print("train slot instances with generic trace_N id:", gen)
suffixes = Counter(re.sub(r"^.*_", "_", sl["slot_id"]) for q in teq for sl in q["trace_spec"]["slots"] if not re.fullmatch(r"trace_\d+", sl["slot_id"]))
print("test named slot-id suffixes:", suffixes.most_common(6))

print("\n=== test seen/hidden proxy (text + public spec only) ===")
tr_sk = {skel(q["question"]) for q in trq}
tr_sig = {tuple((s["slot_id"], s["description"]) for s in q["trace_spec"]["slots"]) for q in trq}
lab = Counter()
hid = []
for q in teq:
    a = skel(q["question"]) in tr_sk
    b = tuple((s["slot_id"], s["description"]) for s in q["trace_spec"]["slots"]) in tr_sig
    lab[(a, b)] += 1
    if not a and not b:
        hid.append(q)
print("(skeleton in train, slot signature in train):", lab)
print("hidden-proxy n=", len(hid), "slot-count:", Counter(len(q["trace_spec"]["slots"]) for q in hid))
print("hidden-proxy answer type:", Counter(q["answer_spec"]["type"] for q in hid), "units:", Counter(q["answer_spec"].get("unit", "ENUM") for q in hid).most_common(8))
print("hidden-proxy answer rounding:", Counter(q["answer_spec"]["rounding"]["mode"] + str(q["answer_spec"]["rounding"].get("decimal_places", "")) if q["answer_spec"]["type"] == "decimal" else "enum" for q in hid))
print("hidden-proxy slot rounding:", Counter(s["result_spec"]["rounding"]["mode"] + str(s["result_spec"]["rounding"].get("decimal_places", "")) if s["result_spec"]["type"] == "decimal" else "enum" for q in hid for s in q["trace_spec"]["slots"]))
print("hidden-proxy question chars median:", sorted(len(q["question"]) for q in hid)[len(hid) // 2])
seenish = [q for q in teq if q not in hid]
print("seen-proxy n=", len(seenish), "slots", sum(len(q["trace_spec"]["slots"]) for q in seenish), "zero-slot", sum(not q["trace_spec"]["slots"] for q in seenish))
# hidden skeleton clusters (how many distinct structures?)
hsk = Counter(skel(q["question"]) for q in hid)
print("hidden-proxy distinct skeletons:", len(hsk), "size dist:", Counter(hsk.values()))
hsig = Counter(tuple(s["slot_id"] for s in q["trace_spec"]["slots"]) for q in hid)
print("hidden-proxy distinct slot-id sequences:", len(hsig), "size dist:", Counter(hsig.values()))
# leaderboard: cases per train template via skeleton
sk2t = {}
for q in trq:
    sk2t[skel(q["question"])] = trm[q["case_id"]]["template_id"]
lbt = Counter(sk2t.get(skel(q["question"])) for q in lbq)
print("\nleaderboard cases per train template (via skeleton):", Counter(v for k, v in lbt.items() if k), "unmatched:", lbt.get(None))
tet = Counter(sk2t.get(skel(q["question"])) for q in teq)
print("test cases per train template (via skeleton):", Counter(v for k, v in tet.items() if k), "unmatched:", tet.get(None))
