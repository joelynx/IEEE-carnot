"""Derived facts for the hidden-template discussion (camera-ready revision, 18 November 2026).

Read-only; uses published aggregates, the released manifests and public question fields only.
No prediction of ours on the test set is read.

 1. Seen-route test questions per train template (public text skeleton match).
 2. Which numbers of wrong seen-stratum finals are consistent with the published scores.
 3. Exact gold fields that no finite decimal / no double can represent (train + development gold).
 4. Further public-field contrasts between the novel-route test questions and train.

  python -I paper/working_notes/verify/derived_strata.py
"""

import itertools
import json
import re
import statistics
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def jl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


SUF = re.compile(r"\n\nAnswer format: .*\Z", re.S)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def skel(text):
    return NUM.sub("#", " ".join(SUF.sub("", text).lower().split()))


def sig(q):
    return tuple((s["slot_id"], s["description"]) for s in q["trace_spec"]["slots"])


dev = ROOT / "development_files"
train = jl(dev / "train_questions.jsonl")
train_manifest = {r["case_id"]: r for r in jl(dev / "train_manifest.jsonl")}
test = jl(ROOT / "test_questions" / "test_questions.jsonl")
sk, sg = {skel(q["question"]) for q in train}, {sig(q) for q in train}
novel = [q for q in test if skel(q["question"]) not in sk and sig(q) not in sg]
seen = [q for q in test if not (skel(q["question"]) not in sk and sig(q) not in sg)]
print("1. routes: novel", len(novel), "seen", len(seen))

# 1. seen-route test questions per train template, by skeleton or slot signature
by_skel, by_sig = defaultdict(set), defaultdict(set)
for q in train:
    t = train_manifest[q["case_id"]]["template_id"]
    by_skel[skel(q["question"])].add(t)
    by_sig[sig(q)].add(t)
per_template, unresolved = Counter(), 0
for q in seen:
    cands = by_skel.get(skel(q["question"])) or by_sig.get(sig(q)) or set()
    if len(cands) == 1:
        per_template[next(iter(cands))] += 1
    else:
        unresolved += 1
print("   seen-route questions matched to exactly one train template:", sum(per_template.values()),
      "unresolved:", unresolved, "| templates hit:", len(per_template),
      "| questions per template:", dict(Counter(per_template.values())))

# 2. wrong seen finals consistent with the published aggregates
topics = defaultdict(set)
for r in train_manifest.values():
    topics[r["domain_id"]].add(r["topic_id"])
tcount = Counter(len(v) for v in topics.values())
print("2. topics per domain (count of domains):", dict(sorted(tcount.items())))
results = json.loads((ROOT / "paper/working_notes/verify/official_test_results_20261028.json").read_text(encoding="utf-8"))
row = next(r for r in results["rows"] if r["team"] == "carnot")
half = Fraction(1, 2_000_000)
c, h = Fraction(row["combined_fac"]), Fraction(row["hidden_fac"])
lo, hi = 1 - (2 * (c + half) - (h - half)), 1 - (2 * (c - half) - (h + half))  # seen FAC loss interval
print(f"   seen-stratum FAC loss in [{float(lo):.7f}, {float(hi):.7f}]; wrong finals in total: {results['cases'] - row['correct_final']}")
# per-case weight in the seen stratum with two cases per template: 1 / (120 * topics in the domain).
# Checked against the weights probed from the organisers' scorer for tuning-eval (also two cases per template).
probed = json.loads((ROOT / "experiments/weights/tuning-eval.json").read_text(encoding="utf-8"))["weights"]
bad = sum(1 for cid, w in probed.items()
          if Fraction(w["fac"]) != Fraction(1, 120 * len(topics[train_manifest[cid]["domain_id"]])))
print(f"   probed tuning-eval FAC weights equal to 1/(120 x topics in the domain): {len(probed) - bad} of {len(probed)}")
weights = sorted({Fraction(1, 120 * n) for n in tcount})
solutions = []
total_wrong = results["cases"] - row["correct_final"]
for k in range(0, total_wrong + 1):
    for combo in itertools.combinations_with_replacement(weights, k):
        if lo <= sum(combo, Fraction(0)) <= hi:
            solutions.append(sorted(int(1 / (120 * w)) for w in combo))
print("   multisets of domain topic-counts of wrong seen cases that fit:", solutions)
print("   => wrong seen finals:", sorted({len(s) for s in solutions}),
      "=> wrong hidden finals:", sorted({total_wrong - len(s) for s in solutions}))

# 3. exact gold fields beyond finite decimals / doubles
gold = {}
questions = {}
for name in ("train", "dev"):
    for r in jl(dev / f"{name}_gold.jsonl"):
        gold[r["case_id"]] = r
    for r in jl(dev / f"{name}_questions.jsonl"):
        questions[r["case_id"]] = r
from decimal import Decimal  # noqa: E402

dev_manifest = {r["case_id"]: r for r in jl(dev / "dev_manifest.jsonl")}
template_of = {cid: (train_manifest.get(cid) or dev_manifest[cid])["template_id"] for cid in questions}
exact = frac = long_dec = lost_in_double = exact_finals = unreachable_finals = 0
cases_hit, templates_hit = set(), set()
for cid, q in questions.items():
    g = gold[cid]
    fields = [("final", q["answer_spec"], g["final_value"])] + [
        (s["slot_id"], s["result_spec"], g["slot_values"][s["slot_id"]]) for s in q["trace_spec"]["slots"]]
    for name, spec, text in fields:
        if spec["type"] != "decimal" or spec["rounding"]["mode"] != "exact":
            continue
        exact += 1
        exact_finals += name == "final"
        unreachable = False
        if "/" in text:
            frac += 1
            unreachable = True
        else:
            if len(text.replace("-", "").replace(".", "").lstrip("0")) > 15:
                long_dec += 1
            # the nearest double, printed with Python's shortest round-trip repr, is a different number
            if Fraction(Decimal(repr(float(text)))) != Fraction(Decimal(text)):
                lost_in_double += 1
                unreachable = True
        if unreachable:
            cases_hit.add(cid)
            templates_hit.add(template_of[cid])
            unreachable_finals += name == "final"
print(f"3. exact gold fields {exact} ({exact_finals} finals): non-terminating fractions (n/d) {frac};"
      f" finite decimals with more than 15 significant digits {long_dec};"
      f" finite decimals that the nearest double does not print back {lost_in_double}")
print(f"   exact gold fields no double-precision value can match: {frac + lost_in_double} of {exact}"
      f" ({unreachable_finals} finals), in {len(cases_hit)} of {len(questions)} questions and {len(templates_hit)} of {len(set(template_of.values()))} templates")

# 4. more public-field contrasts
def share(qs, pred):
    return f"{sum(1 for q in qs if pred(q))}/{len(qs)}"

def final_mode(q):
    a = q["answer_spec"]
    return a["type"] if a["type"] == "enum" else a["rounding"]["mode"]

print("4. final answer kinds  train:", dict(Counter(final_mode(q) for q in train)), " novel:", dict(Counter(final_mode(q) for q in novel)),
      " seen-route test:", dict(Counter(final_mode(q) for q in seen)))
print("   slots per question  train:", dict(sorted(Counter(len(q['trace_spec']['slots']) for q in train).items())),
      " novel:", dict(sorted(Counter(len(q['trace_spec']['slots']) for q in novel).items())))
print("   numbers per question (median)  train:", statistics.median(len(NUM.findall(SUF.sub('', q['question']))) for q in train),
      " novel:", statistics.median(len(NUM.findall(SUF.sub('', q['question']))) for q in novel))
for word in ("round", "if ", "otherwise", "unless", "threshold", "at least", "exceed", "only", "ignore", "not "):
    print(f"   contains '{word}':  train {share(train, lambda q: word in q['question'].lower())}  novel {share(novel, lambda q: word in q['question'].lower())}")
print("   distinct text skeletons  train:", len(sk), " novel:", len({skel(q['question']) for q in novel}),
      "| distinct slot signatures novel:", len({sig(q) for q in novel}))
print("   novel units (final):", dict(Counter(q['answer_spec'].get('unit', 'enum') for q in novel).most_common(12)))
for word in ("scenario", "fictional", "exact"):
    print(f"   contains '{word}':  train {share(train, lambda q: word in SUF.sub('', q['question']).lower())}  novel {share(novel, lambda q: word in SUF.sub('', q['question']).lower())}")
cond = ("if ", "otherwise", "unless", "at least", "at most", "exceed", "whichever", "when ")
print("   any conditional cue", cond, ": train", share(train, lambda q: any(w in SUF.sub('', q['question']).lower() for w in cond)),
      " novel", share(novel, lambda q: any(w in SUF.sub('', q['question']).lower() for w in cond)))
print("   slot-id suffixes  train:", dict(Counter(s['slot_id'].rsplit('_', 1)[-1] for q in train for s in q['trace_spec']['slots']).most_common(4)),
      " novel:", dict(Counter(s['slot_id'].rsplit('_', 1)[-1] for q in novel for s in q['trace_spec']['slots']).most_common(4)))
print("   median characters  train:", statistics.median(len(q['question']) for q in train), " novel:", statistics.median(len(q['question']) for q in novel))
sent = lambda q: len([x for x in re.split(r'(?<=[.!?])\s+', SUF.sub('', q['question']).strip()) if x.strip()])
print("   median sentences before the answer-format note  train:", statistics.median(sent(q) for q in train), " novel:", statistics.median(sent(q) for q in novel))
