"""Read-only tabulation of the Task 1 release. Usage: python -I data_stats.py DEV_DIR TEST_DIR"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

D, T = Path(sys.argv[1]), Path(sys.argv[2])


def jl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]


Q = {
    "train": jl(D / "train_questions.jsonl"),
    "dev": jl(D / "dev_questions.jsonl"),
    "lb": jl(D / "leaderboard_questions.jsonl"),
    "test": jl(T / "test_questions.jsonl"),
}
G = {s: {r["case_id"]: r for r in jl(D / f"{s}_gold.jsonl")} for s in ("train", "dev")}
M = {s: {r["case_id"]: r for r in jl(D / f"{s}_manifest.jsonl")} for s in ("train", "dev")}
TG = {s: {r["case_id"]: r for r in jl(D / f"{s}_targets.jsonl")} for s in ("train", "dev")}


def h(title):
    print("\n" + "=" * 8 + " " + title + " " + "=" * 8)


def spec_key(spec):
    if spec["type"] == "enum":
        return f"enum[{len(spec['allowed_values'])}]"
    r = spec["rounding"]
    rk = "exact" if r["mode"] == "exact" else f"half_up{r['decimal_places']}"
    return f"decimal/{spec['unit']}/{rk}"


SUFFIX_RE = re.compile(r"\n\nAnswer format: .*\Z", re.S)

h("A. question files")
for s, rows in Q.items():
    keys = Counter(tuple(sorted(r)) for r in rows)
    print(s, "n=", len(rows), "field-sets=", len(keys), list(keys)[0])
    print("  dataset_version:", Counter(r["dataset_version"] for r in rows))
    print("  schema_version:", Counter(r["schema_version"] for r in rows))
    lens = [len(r["question"]) for r in rows]
    print("  question chars: min", min(lens), "median", statistics.median(lens), "max", max(lens), "mean", round(statistics.mean(lens)))
    nslots = Counter(len(r["trace_spec"]["slots"]) for r in rows)
    print("  slot-count dist:", dict(sorted(nslots.items())))
    print("  cases with >=1 slot:", sum(len(r["trace_spec"]["slots"]) > 0 for r in rows), "total slots:", sum(len(r["trace_spec"]["slots"]) for r in rows))
    print("  answer type:", Counter(r["answer_spec"]["type"] for r in rows))
    print("  answer unit:", Counter(r["answer_spec"].get("unit", "ENUM") for r in rows).most_common())
    print("  answer rounding:", Counter(("exact" if r["answer_spec"]["type"] == "decimal" and r["answer_spec"]["rounding"]["mode"] == "exact" else (f"half_up{r['answer_spec']['rounding']['decimal_places']}" if r["answer_spec"]["type"] == "decimal" else "enum")) for r in rows).most_common())
    slot_specs = Counter(spec_key(sl["result_spec"]) for r in rows for sl in r["trace_spec"]["slots"])
    print("  slot type:", Counter(sl["result_spec"]["type"] for r in rows for sl in r["trace_spec"]["slots"]))
    print("  slot unit:", Counter(sl["result_spec"].get("unit", "ENUM") for r in rows for sl in r["trace_spec"]["slots"]).most_common())
    print("  slot rounding:", Counter((sl["result_spec"]["rounding"]["mode"] + str(sl["result_spec"]["rounding"].get("decimal_places", ""))) if sl["result_spec"]["type"] == "decimal" else "enum" for r in rows for sl in r["trace_spec"]["slots"]).most_common())
    suf = Counter(bool(SUFFIX_RE.search(r["question"])) for r in rows)
    print("  has 'Answer format:' suffix:", suf)
    sufkinds = Counter(re.sub(r"`[^`]*`", "`U`", re.sub(r"\d+", "N", SUFFIX_RE.search(r["question"]).group(0))) if SUFFIX_RE.search(r["question"]) else None for r in rows)
    print("  suffix variants (numbers/units masked):", len(sufkinds))
    for k, v in sufkinds.most_common(6):
        print("     ", v, repr(k)[:260])

h("B. manifests")
for s in ("train", "dev"):
    rows = list(M[s].values())
    print(s, "fields:", sorted(rows[0]))
    print("  split:", Counter(r["split"] for r in rows), "stratum:", Counter(r["structure_stratum"] for r in rows))
    print("  domains:", len({r["domain_id"] for r in rows}), "topics:", len({(r["domain_id"], r["topic_id"]) for r in rows}), "templates:", len({r["template_id"] for r in rows}))
    print("  difficulty:", Counter(r["difficulty"] for r in rows))
    per_t = Counter(r["template_id"] for r in rows)
    print("  cases per template:", Counter(per_t.values()))
    cells = Counter((r["domain_id"], r["topic_id"], r["difficulty"]) for r in rows)
    print("  templates per (domain,topic,difficulty) cell:", Counter(Counter((r["domain_id"], r["topic_id"], r["difficulty"]) for r in {r["template_id"]: r for r in rows}.values()).values()))
    tpt = Counter((r["domain_id"], r["topic_id"]) for r in {r["template_id"]: r for r in rows}.values())
    print("  templates per topic:", Counter(tpt.values()))
    tpd = defaultdict(set)
    for r in rows:
        tpd[r["domain_id"]].add(r["topic_id"])
    print("  topics per domain:", {k: len(v) for k, v in sorted(tpd.items())})
same_t = {r["template_id"] for r in M["train"].values()} == {r["template_id"] for r in M["dev"].values()}
print("train and dev share identical template set:", same_t)
print("template_id examples:", sorted({r["template_id"] for r in M["train"].values()})[:3])
print("template_id shape:", Counter(len(t.split(".")) for t in {r["template_id"] for r in M["train"].values()}))
# Does template id determine slot list? (slot ids, units, rounding)
for s in ("train",):
    sig = defaultdict(set)
    for q in Q[s]:
        t = M[s][q["case_id"]]["template_id"]
        sig[t].add(json.dumps([q["answer_spec"], q["trace_spec"]], sort_keys=True))
    print("templates with >1 distinct scoring spec across cases:", sum(len(v) > 1 for v in sig.values()))

h("C. gold formats")
for s in ("train", "dev"):
    qs = {q["case_id"]: q for q in Q[s]}
    fmt = Counter()
    dp_mismatch = 0
    rationals = 0
    neg = 0
    for cid, g in G[s].items():
        spec = qs[cid]["answer_spec"]
        v = g["final_value"]
        if spec["type"] == "enum":
            fmt["enum"] += 1
            continue
        if "/" in v:
            rationals += 1
        if v.startswith("-"):
            neg += 1
        if spec["rounding"]["mode"] == "half_up":
            dp = len(v.split(".")[1]) if "." in v else 0
            if dp != spec["rounding"]["decimal_places"]:
                dp_mismatch += 1
    print(s, "final: enum", fmt["enum"], "rational strings", rationals, "negative", neg, "half_up values not padded to decimal_places", dp_mismatch)
    slot_rat = sum("/" in v for g in G[s].values() for v in g["slot_values"].values())
    slot_exp = sum(("e" in v.lower()) for g in G[s].values() for v in g["slot_values"].values())
    print(s, "slot rational strings", slot_rat, "slot exponent strings", slot_exp)
    enum_final = Counter(G[s][q["case_id"]]["final_value"] for q in Q[s] if q["answer_spec"]["type"] == "enum")
    print(s, "enum final values:", enum_final.most_common(12))
    enum_vocab = Counter(tuple(q["answer_spec"]["allowed_values"]) for q in Q[s] if q["answer_spec"]["type"] == "enum")
    print(s, "enum vocabularies:", enum_vocab.most_common(8))

h("D. targets == gold?")
for s in ("train", "dev"):
    qs = {q["case_id"]: q for q in Q[s]}
    bad = 0
    for cid, t in TG[s].items():
        g = G[s][cid]
        steps = [{"slot_id": sl["slot_id"], "value": g["slot_values"][sl["slot_id"]]} for sl in qs[cid]["trace_spec"]["slots"]]
        if t["final_answer"] != {"value": g["final_value"]} or t["steps"] != steps:
            bad += 1
    print(s, "targets differing from gold:", bad, "of", len(TG[s]), "target fields:", sorted(next(iter(TG[s].values()))))

h("E. overlaps")
ids = {s: {q["case_id"] for q in rows} for s, rows in Q.items()}
names = list(Q)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        print(f"case_id {a}&{b}:", len(ids[a] & ids[b]))


def norm(t):
    return " ".join(t.lower().split())


NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def skel(t):
    return NUM.sub("#", norm(SUFFIX_RE.sub("", t)))


texts = {s: Counter(norm(q["question"]) for q in rows) for s, rows in Q.items()}
skels = {s: Counter(skel(q["question"]) for q in rows) for s, rows in Q.items()}
for s in names:
    print(s, "duplicate normalised texts within split:", sum(v - 1 for v in texts[s].values() if v > 1), "distinct skeletons:", len(skels[s]))
for i, a in enumerate(names):
    for b in names[i + 1:]:
        print(f"norm-text {a}&{b}: {len(set(texts[a]) & set(texts[b]))}   skeleton {a}&{b}: distinct={len(set(skels[a]) & set(skels[b]))}")
for s in ("dev", "lb", "test"):
    hit = sum(1 for q in Q[s] if skel(q["question"]) in skels["train"])
    print(f"{s} questions whose number-masked skeleton appears in train: {hit}/{len(Q[s])}")
# train skeletons per template
tsk = defaultdict(set)
for q in Q["train"]:
    tsk[M["train"][q["case_id"]]["template_id"]].add(skel(q["question"]))
print("train: skeletons per template:", Counter(len(v) for v in tsk.values()))
sk2t = defaultdict(set)
for t, ss in tsk.items():
    for x in ss:
        sk2t[x].add(t)
print("train: skeletons shared by >1 template:", sum(len(v) > 1 for v in sk2t.values()))

h("F. slot vocabulary")
voc = {s: Counter(sl["slot_id"] for q in rows for sl in q["trace_spec"]["slots"]) for s, rows in Q.items()}
for s in names:
    print(s, "distinct slot_ids:", len(voc[s]), "slot instances:", sum(voc[s].values()))
for s in ("dev", "lb", "test"):
    inst_in = sum(v for k, v in voc[s].items() if k in voc["train"])
    print(f"{s}: slot_id instances whose slot_id occurs in train: {inst_in}/{sum(voc[s].values())}; distinct new slot_ids: {len(set(voc[s]) - set(voc['train']))}")
print("train top slot_ids:", voc["train"].most_common(15))
print("test top slot_ids:", voc["test"].most_common(15))
# slot signature (list of slot ids) per question
sig = {s: Counter(tuple(sl["slot_id"] for sl in q["trace_spec"]["slots"]) for q in rows if q["trace_spec"]["slots"]) for s, rows in Q.items()}
for s in ("dev", "lb", "test"):
    hit = sum(v for k, v in sig[s].items() if k in sig["train"])
    print(f"{s}: questions (with slots) whose full slot-id sequence occurs in train: {hit}/{sum(sig[s].values())}")
desc = {s: Counter((sl["slot_id"], sl["description"]) for q in rows for sl in q["trace_spec"]["slots"]) for s, rows in Q.items()}
for s in ("test",):
    hit = sum(v for k, v in desc[s].items() if k in desc["train"])
    print(f"{s}: (slot_id, description) instances seen in train: {hit}/{sum(desc[s].values())}")
ex = Q["train"][next(i for i, q in enumerate(Q["train"]) if len(q["trace_spec"]["slots"]) >= 3)]
print("example slots:", json.dumps(ex["trace_spec"]["slots"], indent=None)[:1200])
